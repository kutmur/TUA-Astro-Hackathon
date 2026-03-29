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
from pathlib import Path

import numpy as np

try:
    from .config import (
        GOAL_UV,
        PROJECT_CONFIG,
        ROUTE_PROFILES,
        START_UV,
        uv_to_grid,
        resolve_default_tif,
    )
    from .dem_loader import build_cost_layers, load_dem
    from .planner import RouteResult, astar_search
    from .visualization import DEMVisualizer
except ImportError:
    from config import (
        GOAL_UV,
        PROJECT_CONFIG,
        ROUTE_PROFILES,
        START_UV,
        uv_to_grid,
        resolve_default_tif,
    )
    from dem_loader import build_cost_layers, load_dem
    from planner import RouteResult, astar_search
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
            layers=layers,
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
