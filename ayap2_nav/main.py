"""AYAP-2 4D Rota Optimizasyonu — Ana Orkestratör (Entry Point).

Bu dosya projenin ana giriş noktasıdır. İş akışı KESİNLİKLE şu sırayı izler:

    1. dem_loader ile .tif dosyasını yükle ve Cost katmanlarını çıkar.
    2. config'deki UV oranlarını kullanarak A ve B grid indekslerini bul.
    3. input.png: 3D DEM + A/B markers
    4. topview.png: 2D heatmap top view
    5. planner ile 3 farklı profil için A* çalıştır.
    6. output.png: 3D DEM + A/B + Routes + Legend

Jury Requirements (3 mandatory output files):
    - input.png: 3D surface with A/B markers (no routes)
    - topview.png: 2D heatmap with elevation colorbar
    - output.png: 3D surface with all 3 routes overlaid + legend

Kullanım:
    python main.py
    python main.py --tif /path/to/dem.tif
    python main.py --output-dir ./results
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
        description="TUA AYAP-2 | 4D Multi-Objective Dynamic Route Optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tif",
        type=str,
        default=None,
        help="Path to GeoTIFF DEM file. Auto-detected if not specified.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Output directory for PNG files (default: current directory).",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=None,
        help="GeoTIFF center crop size (pixels).",
    )
    parser.add_argument(
        "--downsample",
        type=int,
        default=None,
        help="Downsample factor (min_grid_size protection active).",
    )
    return parser.parse_args()


# ─────────────────────────────────────────────────
# Camera/Perception Helpers (only loaded when CAMERA_CONNECTED=True)
# ─────────────────────────────────────────────────

def _generate_fallback_mock_frame(
    index: int,
    shape: tuple[int, int, int] = (720, 960, 3),
) -> np.ndarray:
    """Kamera yoksa pipeline testi için sentetik BGR frame üretir.

    This fallback ensures the perception pipeline can be tested even
    without physical camera hardware attached.
    """
    # Lazy import: only load cv2 when actually needed
    try:
        import cv2
    except ModuleNotFoundError as err:
        raise ModuleNotFoundError(
            "Mock camera fallback requires 'opencv-python'."
        ) from err

    h, w, _ = shape
    frame = np.zeros(shape, dtype=np.uint8)
    frame[:, :] = (22, 22, 26)  # Dark lunar regolith base color

    # Subtle gradient to simulate lighting variation
    grad = np.linspace(0, 28, w, dtype=np.uint8)
    frame[:, :, 1] = np.clip(frame[:, :, 1] + grad[None, :], 0, 255)

    # Animated mock rocks for testing segmentation
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
    """OpenCV VideoCapture tabanlı mock kamera okuma döngüsü.

    Attempts to open physical camera first; falls back to synthetic
    frames if camera is not available (for testing without hardware).
    """
    # Lazy import: only load cv2 when camera is connected
    try:
        import cv2
    except ModuleNotFoundError as err:
        raise ModuleNotFoundError(
            "Camera loop requires 'opencv-python' package."
        ) from err

    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print(
            "  [CAMERA] VideoCapture failed to open. "
            "Falling back to synthetic mock frames."
        )
        for idx in range(max_frames):
            yield _generate_fallback_mock_frame(idx)
        return

    try:
        read_count = 0
        while read_count < max_frames:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("  [CAMERA] Frame read failed, ending capture loop.")
                break

            read_count += 1
            yield frame
    finally:
        cap.release()


def _run_camera_perception_and_build_mask(
    grid_shape: tuple[int, int],
) -> np.ndarray | None:
    """Runs U-Net segmentation on camera frames and builds rock obstacle mask.

    This function only loads the TensorFlow model when CAMERA_CONNECTED=True
    and actual frames are available, preserving RAM on RAD750 hardware.
    """
    perception: RockSegmentationPerception | None = None
    observed_rocks = np.zeros(grid_shape, dtype=np.uint8)
    processed_frames = 0

    for frame in _iter_mock_camera_frames(
        max_frames=CAMERA_MAX_FRAMES,
        device_index=CAMERA_DEVICE_INDEX,
    ):
        # CRITICAL: Model is only loaded when first frame arrives
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
        f"Processed frames={processed_frames} | "
        f"Rock pixels={rock_pixels}/{total} ({ratio:.2f}%)"
    )

    return observed_rocks


# ─────────────────────────────────────────────────
# Ana İş Akışı
# ─────────────────────────────────────────────────

def run() -> int:
    """AYAP-2 complete route simulation workflow.

    Generates three jury-required output files:
        - input.png: 3D DEM with A/B markers
        - topview.png: 2D elevation heatmap
        - output.png: 3D DEM with all routes

    Returns:
        Exit code (0 = success).
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
                "[ERROR] GeoTIFF file not found. "
                "Specify path with --tif argument.",
                file=sys.stderr,
            )
            return 1
        tif_path = tif_path_opt

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  TUA AYAP-2 | 4D Multi-Objective Dynamic Route Optimization")
    print("=" * 65)
    print(f"  GeoTIFF : {tif_path}")
    print(f"  Output  : {output_dir}")
    print()

    # ══════════════════════════════════════════════
    # STEP 0: Load DEM & Generate Cost Layers
    # ══════════════════════════════════════════════
    t0 = time.perf_counter()

    z_real = load_dem(
        tif_path=tif_path,
        window_size=args.window_size,
        downsample=args.downsample,
    )
    layers = build_cost_layers(z_real)

    print(f"  DEM Shape  : {z_real.shape[0]} × {z_real.shape[1]}")
    print(f"  Z Range    : {float(np.min(z_real)):.2f} — {float(np.max(z_real)):.2f} m")
    print()

    # ── UV → Grid Index Conversion ──
    start = uv_to_grid(START_UV, z_real.shape)
    goal = uv_to_grid(GOAL_UV, z_real.shape)

    print(f"  A (Start)  : UV={START_UV} → Grid={start}")
    print(f"  B (Goal)   : UV={GOAL_UV}  → Grid={goal}")
    print()

    # ══════════════════════════════════════════════
    # STEP 1: Generate input.png (3D DEM + A/B markers)
    # ══════════════════════════════════════════════
    print("─" * 50)
    print("  STEP 1/4: Generating input.png (3D DEM + markers)...")
    viz = DEMVisualizer()
    viz.plot_input_png(
        z_real=z_real,
        start=start,
        goal=goal,
        save_path=output_dir / cfg.output_input,
    )

    # ══════════════════════════════════════════════
    # STEP 2: Generate topview.png (2D heatmap)
    # ══════════════════════════════════════════════
    print("  STEP 2/4: Generating topview.png (2D heatmap)...")
    viz.plot_topview_png(
        z_real=z_real,
        save_path=output_dir / cfg.output_topview,
    )

    # ══════════════════════════════════════════════
    # STEP 2.5: Camera + Segmentation (if CAMERA_CONNECTED)
    # ══════════════════════════════════════════════
    planning_layers = layers
    if CAMERA_CONNECTED:
        print("  STEP 2.5: Camera active, running U-Net segmentation...")
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
                "  [PLANNER] Rock mask applied to cost layers "
                f"(target={ROCK_PENALTY_TARGET_LAYER}, "
                f"direct={ROCK_DIRECT_PENALTY:.1f})."
            )
        else:
            print(
                "  [PLANNER] No rocks detected in camera stream, "
                "using base cost layers."
            )
    else:
        print(
            "  STEP 2.5: CAMERA_CONNECTED=False → "
            "Model not loaded, perception skipped."
        )

    # ══════════════════════════════════════════════
    # STEP 3: A* Route Planning (3 profiles)
    # ══════════════════════════════════════════════
    print("  STEP 3/4: Running A* route planning...")
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
            f"    [{i}/3] {profile.name:30s} | "
            f"Steps={len(result.path):5d} | "
            f"Cost={result.cumulative_cost:12,.0f} | "
            f"Time={t_elapsed:.2f}s"
        )

    print()

    # ══════════════════════════════════════════════
    # STEP 4: Generate output.png (3D DEM + routes)
    # ══════════════════════════════════════════════
    print("  STEP 4/4: Generating output.png (3D DEM + routes)...")
    viz.plot_output_png(
        z_real=z_real,
        start=start,
        goal=goal,
        routes=routes,
        save_path=output_dir / cfg.output_final,
    )

    t_total = time.perf_counter() - t0
    print()
    print("─" * 50)
    print(f"  ✓ Complete! Total time: {t_total:.2f}s")
    print()
    print("  Jury-Required Output Files:")
    print(f"    • {output_dir / cfg.output_input}")
    print(f"    • {output_dir / cfg.output_topview}")
    print(f"    • {output_dir / cfg.output_final}")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except FileNotFoundError as err:
        print(f"[FILE ERROR] {err}", file=sys.stderr)
        raise SystemExit(1)
    except ValueError as err:
        print(f"[VALUE ERROR] {err}", file=sys.stderr)
        raise SystemExit(2)
    except RuntimeError as err:
        print(f"[PLANNING ERROR] {err}", file=sys.stderr)
        raise SystemExit(3)
    except ModuleNotFoundError as err:
        print(f"[DEPENDENCY ERROR] {err}", file=sys.stderr)
        raise SystemExit(4)
