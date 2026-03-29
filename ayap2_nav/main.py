"""AYAP-2 4D Rota Optimizasyonu — Ana Orkestratör (Entry Point).

Bu dosya projenin ana giriş noktasıdır. İş akışı KESİNLİKLE şu sırayı izler:

    1. dem_loader ile .tif dosyasını yükle ve Cost katmanlarını çıkar.
    2. config'deki UV oranlarını kullanarak A ve B grid indekslerini bul.
    3. ADIM 1: Çıplak 3D DEM → 01_base_surface.png
    4. ADIM 2: DEM + A/B → 02_surface_with_markers.png
    5. planner ile 3 farklı profil için A* çalıştır.
    6. ADIM 3: DEM + A/B + Rotalar + Lejant → 03_final_routes_analyzed.png

Kullanım:
    python main.py
    python main.py --tif /yol/dosya.tif
    python main.py --output-dir ./sonuclar
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import numpy as np

try:
    from .config import (
        CAMERA_CONNECTED,
        CAMERA_DEVICE_INDEX,
        CAMERA_MAX_FRAMES,
        GOAL_UV,
        PROJECT_CONFIG,
        ROCK_DIRECT_PENALTY,
        ROCK_FAR_PENALTY,
        ROCK_FAR_WINDOW_RADIUS,
        ROCK_MASK_THRESHOLD,
        ROCK_NEAR_PENALTY,
        ROCK_NEAR_WINDOW_RADIUS,
        ROCK_PENALTY_TARGET_LAYER,
        ROUTE_PROFILES,
        SEGMENTATION_INPUT_SHAPE,
        SEGMENTATION_MODEL_WEIGHTS,
        SEGMENTATION_VGG16_WEIGHTS,
        START_UV,
        resolve_default_tif,
        uv_to_grid,
    )
    from .dem_loader import build_cost_layers, load_dem
    from .perception import RockSegmentationPerception
    from .planner import RouteResult, apply_rock_obstacle_penalty, astar_search
    from .visualization import DEMVisualizer
except ImportError:
    from config import (
        CAMERA_CONNECTED,
        CAMERA_DEVICE_INDEX,
        CAMERA_MAX_FRAMES,
        GOAL_UV,
        PROJECT_CONFIG,
        ROCK_DIRECT_PENALTY,
        ROCK_FAR_PENALTY,
        ROCK_FAR_WINDOW_RADIUS,
        ROCK_MASK_THRESHOLD,
        ROCK_NEAR_PENALTY,
        ROCK_NEAR_WINDOW_RADIUS,
        ROCK_PENALTY_TARGET_LAYER,
        ROUTE_PROFILES,
        SEGMENTATION_INPUT_SHAPE,
        SEGMENTATION_MODEL_WEIGHTS,
        SEGMENTATION_VGG16_WEIGHTS,
        START_UV,
        resolve_default_tif,
        uv_to_grid,
    )
    from dem_loader import build_cost_layers, load_dem
    from perception import RockSegmentationPerception
    from planner import RouteResult, apply_rock_obstacle_penalty, astar_search
    from visualization import DEMVisualizer


# ─────────────────────────────────────────────────
# CLI Argümanları
# ─────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    """Komut satırı argümanlarını ayrıştırır."""
    parser = argparse.ArgumentParser(
        description="TUA AYAP-2 | 4D Çok Amaçlı Dinamik Rota Optimizasyonu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tif",
        type=str,
        default=None,
        help="GeoTIFF DEM dosyasının yolu. Verilmezse otomatik bulunur.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Çıktı PNG dosyalarının kaydedileceği dizin (varsayılan: mevcut dizin).",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=None,
        help="GeoTIFF merkez kırpma boyutu (piksel).",
    )
    parser.add_argument(
        "--downsample",
        type=int,
        default=None,
        help="Downsample faktörü (min_grid_size koruması aktif).",
    )
    return parser.parse_args()


# ─────────────────────────────────────────────────
# Ana İş Akışı
# ─────────────────────────────────────────────────

def _generate_fallback_mock_frame(index: int, shape: tuple[int, int, int] = (720, 960, 3)) -> np.ndarray:
    """Kamera yoksa pipeline testi için sentetik BGR frame üretir."""
    try:
        import cv2
    except ModuleNotFoundError as err:
        raise ModuleNotFoundError(
            "Mock kamera fallback için 'opencv-python' gereklidir."
        ) from err

    h, w, _ = shape
    frame = np.zeros(shape, dtype=np.uint8)
    frame[:, :] = (22, 22, 26)

    # Hafif zemin gradienti
    grad = np.linspace(0, 28, w, dtype=np.uint8)
    frame[:, :, 1] = np.clip(frame[:, :, 1] + grad[None, :], 0, 255)

    # Hareketli mock kayalar
    center_x = int((w * 0.25) + (index * 11) % int(w * 0.5))
    center_y = int((h * 0.35) + (index * 7) % int(h * 0.3))
    cv2.circle(frame, (center_x, center_y), 54, (95, 95, 95), -1)
    cv2.circle(frame, (center_x + 130, center_y + 55), 38, (118, 118, 118), -1)
    cv2.circle(frame, (center_x - 110, center_y + 35), 27, (82, 82, 82), -1)

    return frame


def _iter_mock_camera_frames(
    *,
    max_frames: int,
    device_index: int,
) -> Iterator[np.ndarray]:
    """OpenCV VideoCapture tabanlı mock kamera okuma döngüsü."""
    try:
        import cv2
    except ModuleNotFoundError as err:
        raise ModuleNotFoundError(
            "Kamera döngüsü için 'opencv-python' paketi gereklidir."
        ) from err

    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print(
            "  [KAMERA] VideoCapture açılamadı. "
            "Mock sentetik frame akışına geçiliyor."
        )
        for idx in range(max_frames):
            yield _generate_fallback_mock_frame(idx)
        return

    try:
        read_count = 0
        while read_count < max_frames:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("  [KAMERA] Frame okunamadı, döngü sonlandırıldı.")
                break

            read_count += 1
            yield frame
    finally:
        cap.release()


def _run_camera_perception_and_build_mask(grid_shape: tuple[int, int]) -> np.ndarray | None:
    """Kameradan gelen frame'lerde segmentasyon çalıştırıp birleşik kaya maskesi döndürür."""
    perception: RockSegmentationPerception | None = None
    observed_rocks = np.zeros(grid_shape, dtype=np.uint8)
    processed_frames = 0

    for frame in _iter_mock_camera_frames(
        max_frames=CAMERA_MAX_FRAMES,
        device_index=CAMERA_DEVICE_INDEX,
    ):
        # KATI KURAL: model, ancak kamera bağlı + frame geldiyse RAM'e alınır.
        if perception is None:
            perception = RockSegmentationPerception(
                weights_path=SEGMENTATION_MODEL_WEIGHTS,
                input_shape=SEGMENTATION_INPUT_SHAPE,
                vgg16_weights=SEGMENTATION_VGG16_WEIGHTS,
            )

        frame_mask = perception.segment_rocks(
            frame,
            threshold=ROCK_MASK_THRESHOLD,
            output_shape=grid_shape,
        )
        observed_rocks = np.maximum(observed_rocks, frame_mask)
        processed_frames += 1

    if processed_frames == 0:
        return None

    rock_pixels = int(np.count_nonzero(observed_rocks))
    total = int(observed_rocks.size)
    ratio = (rock_pixels / max(total, 1)) * 100.0
    print(
        "  [PERCEPTION] "
        f"İşlenen frame={processed_frames} | "
        f"Kaya pikseli={rock_pixels}/{total} (%{ratio:.2f})"
    )

    return observed_rocks

def run() -> int:
    """AYAP-2 kademeli rota simülasyonu iş akışını çalıştırır.

    Returns:
        Çıkış kodu (0 = başarılı).
    """
    args = _parse_args()
    cfg = PROJECT_CONFIG

    # ── TIF Dosyasını Bul ──
    if args.tif is not None:
        tif_path = Path(args.tif).expanduser().resolve()
    else:
        tif_path_opt = resolve_default_tif()
        if tif_path_opt is None:
            print(
                "[HATA] GeoTIFF dosyası bulunamadı. "
                "--tif argümanı ile yol belirtin.",
                file=sys.stderr,
            )
            return 1
        tif_path = tif_path_opt

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  TUA AYAP-2 | 4D Çok Amaçlı Dinamik Rota Optimizasyonu")
    print("=" * 65)
    print(f"  GeoTIFF : {tif_path}")
    print(f"  Çıktı   : {output_dir}")
    print()

    # ══════════════════════════════════════════════
    # ADIM 0: DEM Yükle & Maliyet Katmanlarını Üret
    # ══════════════════════════════════════════════
    t0 = time.perf_counter()

    z_real = load_dem(
        tif_path=tif_path,
        window_size=args.window_size,
        downsample=args.downsample,
    )
    layers = build_cost_layers(z_real)

    print(f"  DEM Boyutu : {z_real.shape[0]} × {z_real.shape[1]}")
    print(f"  Z Aralığı  : {float(np.min(z_real)):.2f} — {float(np.max(z_real)):.2f}")
    print()

    # ── UV → Grid İndeks Dönüşümü ──
    start = uv_to_grid(START_UV, z_real.shape)
    goal = uv_to_grid(GOAL_UV, z_real.shape)

    print(f"  A (Başlangıç) : UV={START_UV} → Grid={start}")
    print(f"  B (Hedef)      : UV={GOAL_UV}  → Grid={goal}")
    print()

    # ══════════════════════════════════════════════
    # ADIM 1: Çıplak 3D DEM Yüzeyi
    # ══════════════════════════════════════════════
    print("─" * 50)
    print("  ADIM 1/3: Çıplak 3D DEM yüzeyi çiziliyor...")
    viz = DEMVisualizer()
    viz.plot_step1_base_surface(
        z_real=z_real,
        save_path=output_dir / cfg.output_step1,
    )

    # ══════════════════════════════════════════════
    # ADIM 2: DEM + A/B Bayrak Direkleri
    # ══════════════════════════════════════════════
    print("  ADIM 2/3: A ve B noktaları ekleniyor...")
    viz.plot_step2_with_markers(
        z_real=z_real,
        start=start,
        goal=goal,
        save_path=output_dir / cfg.output_step2,
    )

    # ══════════════════════════════════════════════
    # ADIM 2.5: Kamera + Segmentasyon + Katman Güncelleme
    # ══════════════════════════════════════════════
    planning_layers = layers
    if CAMERA_CONNECTED:
        print("  ADIM 2.5: Kamera aktif, U-Net segmentasyon çalıştırılıyor...")
        rock_mask = _run_camera_perception_and_build_mask(z_real.shape)

        if rock_mask is not None and np.any(rock_mask):
            planning_layers = apply_rock_obstacle_penalty(
                layers=layers,
                rock_mask=rock_mask,
                target_layer=ROCK_PENALTY_TARGET_LAYER,
                direct_penalty=ROCK_DIRECT_PENALTY,
                near_penalty=ROCK_NEAR_PENALTY,
                far_penalty=ROCK_FAR_PENALTY,
                near_radius=ROCK_NEAR_WINDOW_RADIUS,
                far_radius=ROCK_FAR_WINDOW_RADIUS,
            )
            print(
                "  [PLANLAYICI] Kaya maskesi maliyet katmanlarına işlendi "
                f"(target={ROCK_PENALTY_TARGET_LAYER}, "
                f"direct={ROCK_DIRECT_PENALTY:.1f})."
            )
        else:
            print("  [PLANLAYICI] Kamera akışında kaya tespiti yok, temel katmanlar kullanılacak.")
    else:
        print(
            "  ADIM 2.5: CAMERA_CONNECTED=False -> "
            "model RAM'e yüklenmedi, perception atlandı."
        )

    # ══════════════════════════════════════════════
    # ADIM 3: A* Rota Planlama + Final Görsel
    # ══════════════════════════════════════════════
    print("  ADIM 3/3: A* rota hesaplama başlıyor...")
    print()

    routes: list[RouteResult] = []
    for i, profile in enumerate(ROUTE_PROFILES, 1):
        t_start = time.perf_counter()
        result = astar_search(
            shape=z_real.shape,
            start=start,
            goal=goal,
            profile=profile,
            layers=planning_layers,
        )
        t_elapsed = time.perf_counter() - t_start

        routes.append(result)
        print(
            f"    [{i}/3] {profile.name:35s} | "
            f"Adım={len(result.path):5d} | "
            f"Maliyet={result.cumulative_cost:12,.0f} | "
            f"Süre={t_elapsed:.2f}s"
        )

    print()
    print("  Final görsel oluşturuluyor...")
    viz.plot_step3_final(
        z_real=z_real,
        start=start,
        goal=goal,
        routes=routes,
        save_path=output_dir / cfg.output_step3,
    )

    t_total = time.perf_counter() - t0
    print()
    print("─" * 50)
    print(f"  ✓ Tamamlandı! Toplam süre: {t_total:.2f}s")
    print(f"  Çıktılar:")
    print(f"    • {output_dir / cfg.output_step1}")
    print(f"    • {output_dir / cfg.output_step2}")
    print(f"    • {output_dir / cfg.output_step3}")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except FileNotFoundError as err:
        print(f"[DOSYA HATASI] {err}", file=sys.stderr)
        raise SystemExit(1)
    except ValueError as err:
        print(f"[DEĞER HATASI] {err}", file=sys.stderr)
        raise SystemExit(2)
    except RuntimeError as err:
        print(f"[PLANLAMA HATASI] {err}", file=sys.stderr)
        raise SystemExit(3)
    except ModuleNotFoundError as err:
        print(f"[BAĞIMLILIK HATASI] {err}", file=sys.stderr)
        raise SystemExit(4)
