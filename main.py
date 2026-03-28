from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from rasterio.transform import Affine

from data_processing import DemRegion, load_dem_region
from path_planner import AStarConfig, compute_slope_map, plan_path_astar


def _parse_int_pair(values: Sequence[str], arg_name: str) -> Tuple[int, int]:
    if len(values) != 2:
        raise ValueError(f"{arg_name} expects exactly 2 integers.")
    return int(values[0]), int(values[1])


def _parse_float_quad(values: Sequence[str], arg_name: str) -> Tuple[float, float, float, float]:
    if len(values) != 4:
        raise ValueError(f"{arg_name} expects exactly 4 floats.")
    return float(values[0]), float(values[1]), float(values[2]), float(values[3])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ay Yuzeyi Rota Optimizasyonu - LROC NAC DEM ile A* rota planlama"
    )
    parser.add_argument(
        "--dem",
        type=Path,
        help="Girdi DEM .tif dosya yolu (verilmezse sentetik DEM kullanilir)",
    )

    crop = parser.add_mutually_exclusive_group(required=False)
    crop.add_argument(
        "--pixel-window",
        nargs=4,
        metavar=("ROW_START", "ROW_END", "COL_START", "COL_END"),
        help="Piksel tabanli kirpma araligi",
    )
    crop.add_argument(
        "--bbox",
        nargs=4,
        metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
        help="Harita koordinatlarinda kirpma kutusu",
    )

    parser.add_argument(
        "--start",
        nargs=2,
        metavar=("ROW", "COL"),
        help="Baslangic hucre koordinati (verilmezse otomatik secilir)",
    )
    parser.add_argument(
        "--goal",
        nargs=2,
        metavar=("ROW", "COL"),
        help="Hedef hucre koordinati (verilmezse otomatik secilir)",
    )

    parser.add_argument("--max-slope", type=float, default=35.0, help="Maksimum izinli egim (derece)")
    parser.add_argument("--w-distance", type=float, default=1.0, help="Mesafe maliyeti agirligi")
    parser.add_argument("--w-slope", type=float, default=4.0, help="Egim maliyeti agirligi")
    parser.add_argument("--w-energy", type=float, default=0.15, help="Enerji maliyeti agirligi")
    parser.add_argument("--no-diagonal", action="store_true", help="Sadece 4-komsu hareket")

    parser.add_argument(
        "--downsample",
        type=int,
        default=1,
        help="Gorsellestirme icin yol ornekleme adimi (performans)",
    )

    return parser


def _safe_array_limits(array: np.ndarray) -> Tuple[float, float]:
    if np.all(np.isnan(array)):
        return 0.0, 1.0
    return float(np.nanmin(array)), float(np.nanmax(array))


def _build_synthetic_dem_region(rows: int = 220, cols: int = 220) -> DemRegion:
    y, x = np.indices((rows, cols), dtype=np.float32)

    undulation = 950.0 + 18.0 * np.sin(x / 24.0) + 16.0 * np.cos(y / 27.0)
    crater = -35.0 * np.exp(-(((x - cols * 0.58) ** 2) + ((y - rows * 0.44) ** 2)) / (2.0 * (0.13 * rows) ** 2))
    ridge = 22.0 * np.exp(-((y - rows * 0.74) ** 2) / (2.0 * (0.08 * rows) ** 2))
    dem = (undulation + crater + ridge).astype(np.float32)

    return DemRegion(
        array=dem,
        transform=Affine(5.0, 0.0, 0.0, 0.0, -5.0, 0.0),
        resolution=(5.0, 5.0),
        crs="SYNTHETIC",
        nodata=None,
    )


def _nearest_valid_cell(valid_cells: np.ndarray, target: Tuple[int, int]) -> Tuple[int, int]:
    tr, tc = target
    delta_r = valid_cells[:, 0].astype(np.int64) - int(tr)
    delta_c = valid_cells[:, 1].astype(np.int64) - int(tc)
    squared_distance = delta_r * delta_r + delta_c * delta_c
    idx = int(np.argmin(squared_distance))
    return int(valid_cells[idx, 0]), int(valid_cells[idx, 1])


def _fallback_anchor_pairs(shape: Tuple[int, int]) -> Sequence[Tuple[Tuple[int, int], Tuple[int, int]]]:
    rows, cols = shape
    r10, r90 = rows // 10, (rows * 9) // 10
    c10, c90 = cols // 10, (cols * 9) // 10
    rm, cm = rows // 2, cols // 2
    r25, r75 = rows // 4, (rows * 3) // 4
    c25, c75 = cols // 4, (cols * 3) // 4

    return (
        ((r10, c10), (r90, c90)),
        ((r10, c90), (r90, c10)),
        ((rm, c10), (rm, c90)),
        ((r10, cm), (r90, cm)),
        ((r25, c25), (r75, c75)),
        ((r25, c75), (r75, c25)),
    )


def visualize_3d(
    dem_region: DemRegion,
    path: Sequence[Tuple[int, int]],
    start: Tuple[int, int],
    goal: Tuple[int, int],
    slope_map: np.ndarray,
    downsample: int = 1,
) -> None:
    dem = dem_region.array
    res_x, res_y = dem_region.resolution

    ds = max(1, int(downsample))
    dem_show = dem[::ds, ::ds]

    rows, cols = dem_show.shape
    x = np.arange(cols, dtype=np.float32) * res_x * ds
    y = np.arange(rows, dtype=np.float32) * res_y * ds
    xx, yy = np.meshgrid(x, y)

    fig = plt.figure(figsize=(13, 8))
    ax = fig.add_subplot(111, projection="3d")

    z_min, z_max = _safe_array_limits(dem_show)
    norm_denom = max(z_max - z_min, 1e-6)
    color_values = (dem_show - z_min) / norm_denom

    ax.plot_surface(
        xx,
        yy,
        np.nan_to_num(dem_show, nan=z_min),
        facecolors=plt.cm.gray(np.clip(color_values, 0.0, 1.0)),
        rstride=1,
        cstride=1,
        linewidth=0,
        antialiased=False,
        shade=True,
        alpha=0.9,
    )

    path_arr = np.array(path, dtype=np.int32)
    pr = path_arr[:, 0]
    pc = path_arr[:, 1]
    pz = dem[pr, pc]

    path_x = pc.astype(np.float32) * res_x
    path_y = pr.astype(np.float32) * res_y

    ax.plot(path_x, path_y, pz + 3.0, color="crimson", linewidth=2.2, label="A* Rota")

    s_r, s_c = start
    g_r, g_c = goal
    ax.scatter(
        [s_c * res_x],
        [s_r * res_y],
        [dem[s_r, s_c] + 5.0],
        color="limegreen",
        s=65,
        label="Baslangic",
    )
    ax.scatter(
        [g_c * res_x],
        [g_r * res_y],
        [dem[g_r, g_c] + 5.0],
        color="dodgerblue",
        s=65,
        label="Hedef",
    )

    slope_min, slope_max = _safe_array_limits(slope_map)
    title_suffix = (
        f" | Egim min/max: {slope_min:.2f}/{slope_max:.2f} deg"
        if not np.isnan(slope_min)
        else ""
    )

    ax.set_title(f"Ay Yuzeyi 3D Rota Gorsellestirme{title_suffix}")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Yukseklik [m]")
    ax.legend(loc="upper right")

    plt.tight_layout()
    plt.show()


def run_pipeline(
    dem_path: Optional[Path],
    start: Optional[Tuple[int, int]],
    goal: Optional[Tuple[int, int]],
    pixel_window: Optional[Tuple[int, int, int, int]] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    config: Optional[AStarConfig] = None,
    downsample: int = 1,
) -> None:
    cfg = config or AStarConfig()

    if dem_path is None:
        if pixel_window is not None or bbox is not None:
            raise ValueError("--pixel-window/--bbox secenekleri sentetik DEM ile kullanilamaz.")
        dem_region = _build_synthetic_dem_region()
        dem_name = "<synthetic>"
    else:
        dem_region = load_dem_region(dem_path, pixel_window=pixel_window, bbox=bbox)
        dem_name = str(dem_path)

    start_auto = start is None
    goal_auto = goal is None
    if start_auto or goal_auto:
        valid_cells = np.argwhere(~np.isnan(dem_region.array))
        if len(valid_cells) == 0:
            raise ValueError("DEM icinde otomatik baslangic/hedef secimi icin gecerli hucre bulunamadi.")

        if start is None and goal is None:
            selected_pair: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
            for start_anchor, goal_anchor in _fallback_anchor_pairs(dem_region.array.shape):
                candidate_start = _nearest_valid_cell(valid_cells, start_anchor)
                candidate_goal = _nearest_valid_cell(valid_cells, goal_anchor)
                if candidate_start == candidate_goal:
                    continue

                try:
                    plan_path_astar(
                        dem=dem_region.array,
                        start=candidate_start,
                        goal=candidate_goal,
                        resolution=dem_region.resolution,
                        config=cfg,
                    )
                    selected_pair = (candidate_start, candidate_goal)
                    break
                except RuntimeError:
                    continue

            if selected_pair is None:
                if len(valid_cells) < 2:
                    raise RuntimeError("Otomatik baslangic/hedef secimi icin yeterli gecerli hucre yok.")
                selected_pair = (
                    (int(valid_cells[0, 0]), int(valid_cells[0, 1])),
                    (int(valid_cells[-1, 0]), int(valid_cells[-1, 1])),
                )

            start, goal = selected_pair
        else:
            if start is None:
                start = _nearest_valid_cell(valid_cells, (0, 0))
                if start == goal:
                    for cell in valid_cells:
                        candidate = (int(cell[0]), int(cell[1]))
                        if candidate != goal:
                            start = candidate
                            break

            if goal is None:
                rows, cols = dem_region.array.shape
                goal = _nearest_valid_cell(valid_cells, (rows - 1, cols - 1))
                if goal == start:
                    for cell in valid_cells[::-1]:
                        candidate = (int(cell[0]), int(cell[1]))
                        if candidate != start:
                            goal = candidate
                            break

    assert start is not None and goal is not None
    if start == goal:
        raise ValueError("Baslangic ve hedef ayni hucreye denk geldi. Farkli bir cift secin.")

    slope_map = compute_slope_map(dem_region.array, dem_region.resolution)

    plan = plan_path_astar(
        dem=dem_region.array,
        start=start,
        goal=goal,
        resolution=dem_region.resolution,
        config=cfg,
    )

    print("=== A* Plan Sonucu ===")
    print(f"DEM: {dem_name}")
    if dem_path is None:
        print("Not: --dem verilmedigi icin sentetik DEM kullanildi.")
    if start_auto:
        print(f"Baslangic otomatik secildi: {start}")
    if goal_auto:
        print(f"Hedef otomatik secildi: {goal}")
    print(f"DEM boyutu: {dem_region.array.shape}")
    print(f"CRS: {dem_region.crs}")
    print(f"Cozunurluk: {dem_region.resolution[0]:.4f}m, {dem_region.resolution[1]:.4f}m")
    print(f"Yol uzunlugu: {len(plan.path)} nokta")
    print(f"Toplam mesafe: {plan.total_distance_m:.2f} m")
    print(f"Toplam enerji: {plan.total_energy:.2f} (bagil birim)")
    print(f"Maksimum segment egimi: {plan.max_segment_slope_deg:.2f} deg")
    print(f"Toplam maliyet: {plan.total_cost:.2f}")
    print(f"Genisletilen dugum sayisi: {plan.expanded_nodes}")

    visualize_3d(
        dem_region=dem_region,
        path=plan.path,
        start=start,
        goal=goal,
        slope_map=slope_map,
        downsample=downsample,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    start = _parse_int_pair(args.start, "--start") if args.start is not None else None
    goal = _parse_int_pair(args.goal, "--goal") if args.goal is not None else None

    dem_path = args.dem
    if dem_path is None:
        print("--dem verilmedi; sentetik DEM kullanilacak.")

    pixel_window = None
    bbox = None

    if args.pixel_window is not None:
        row_start, row_end, col_start, col_end = map(int, args.pixel_window)
        pixel_window = (row_start, row_end, col_start, col_end)
    elif args.bbox is not None:
        bbox = _parse_float_quad(args.bbox, "--bbox")

    cfg = AStarConfig(
        w_distance=args.w_distance,
        w_slope=args.w_slope,
        w_energy=args.w_energy,
        max_slope_deg=args.max_slope,
        allow_diagonal=not args.no_diagonal,
    )

    run_pipeline(
        dem_path=dem_path,
        start=start,
        goal=goal,
        pixel_window=pixel_window,
        bbox=bbox,
        config=cfg,
        downsample=args.downsample,
    )


if __name__ == "__main__":
    main()
