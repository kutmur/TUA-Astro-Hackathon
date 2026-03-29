"""Entry point for loading DEM tiles, planning path, and plotting in 3D."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from data_processing import (
    BBox,
    PixelWindow,
    dem_statistics,
    find_first_tif,
    load_dem_window,
)
from path_planner import CostContext, path_length, plan_path
from visualization import plot_dem_heatmap, plot_dem_surface, show_all


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments.

    Returns:
        Parsed argparse namespace.
    """

    parser = argparse.ArgumentParser(
        description="Memory-safe lunar DEM loading and 3D visualization in Python."
    )
    parser.add_argument(
        "--tif-path",
        type=str,
        default=None,
        help="Optional explicit path to GeoTIFF file. If omitted, first file in data/ is used.",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=1200,
        help="Centered square window size in pixels.",
    )
    parser.add_argument(
        "--pixel-window",
        type=int,
        nargs=4,
        metavar=("COL_START", "COL_STOP", "ROW_START", "ROW_STOP"),
        help="Explicit pixel crop window.",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
        help="Map-coordinate bounding box.",
    )
    parser.add_argument(
        "--downsample",
        type=int,
        default=2,
        help="Downsample factor for visualization and planning efficiency.",
    )
    parser.add_argument(
        "--z-exaggeration",
        type=float,
        default=2.5,
        help="Vertical exaggeration factor used only in 3D plot.",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip plotting and only run loading + planning.",
    )
    parser.add_argument(
        "--run-planner",
        action="store_true",
        help="Enable path planning (requires user-defined exact cost formula).",
    )

    return parser.parse_args()


def resolve_tif_path(explicit_path: str | None) -> Path:
    """Resolves GeoTIFF path from CLI or data directory.

    Args:
        explicit_path: Optional user-provided file path.

    Returns:
        Existing GeoTIFF path.
    """

    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"GeoTIFF path does not exist: {path}")
        return path

    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    return find_first_tif(data_dir)


def build_pixel_window(raw_values: list[int] | None) -> PixelWindow | None:
    """Builds PixelWindow from optional CLI values."""

    if raw_values is None:
        return None

    col_start, col_stop, row_start, row_stop = raw_values
    return PixelWindow(
        col_start=col_start,
        col_stop=col_stop,
        row_start=row_start,
        row_stop=row_stop,
    )


def build_bbox(raw_values: list[float] | None) -> BBox | None:
    """Builds map-coordinate bounding box tuple from CLI values."""

    if raw_values is None:
        return None

    xmin, ymin, xmax, ymax = raw_values
    if xmax <= xmin or ymax <= ymin:
        raise ValueError("Invalid bbox: must satisfy XMAX > XMIN and YMAX > YMIN.")
    return xmin, ymin, xmax, ymax


def choose_default_start_goal(shape: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Chooses deterministic start/goal points inside a DEM tile.

    Args:
        shape: Elevation matrix shape.

    Returns:
        Start and goal grid points.
    """

    rows, cols = shape
    if rows <= 0 or cols <= 0:
        raise ValueError(f"Invalid DEM shape: {shape}")

    margin_row = max(1, rows // 10)
    margin_col = max(1, cols // 10)

    start = (min(rows - 1, margin_row), min(cols - 1, margin_col))
    goal = (max(0, rows - 1 - margin_row), max(0, cols - 1 - margin_col))

    if goal == start and (rows > 1 or cols > 1):
        goal = (rows - 1, cols - 1)

    return start, goal


def user_cost_formula(context: CostContext) -> float:
    """Mission cost with weighted friction, distance, slope, and shadow terms."""

    friction_weight = 0.15
    distance_weight = 0.30
    slope_weight = 0.45
    shadow_weight = 0.10

    return (
        friction_weight * context.friction_coefficient
        + distance_weight * context.distance
        + slope_weight * context.local_slope
        + shadow_weight * context.solar_penalty
    )


def run() -> int:
    """Runs the full DEM pipeline.

    Returns:
        Process exit code.
    """

    args = parse_args()

    try:
        tif_path = resolve_tif_path(args.tif_path)
        pixel_window = build_pixel_window(args.pixel_window)
        bbox = build_bbox(args.bbox)

        dem_tile = load_dem_window(
            tif_path=tif_path,
            pixel_window=pixel_window,
            bbox=bbox,
            window_size=args.window_size,
            downsample=args.downsample,
            fill_nan=True,
        )

        stats = dem_statistics(dem_tile.elevation)
        print(f"Loaded DEM: {tif_path.name}")
        print(f"Tile shape: {dem_tile.elevation.shape}")
        print(
            "Elevation stats: "
            f"min={stats['min']:.3f}, max={stats['max']:.3f}, "
            f"mean={stats['mean']:.3f}, std={stats['std']:.3f}"
        )

        path = None
        if args.run_planner:
            start, goal = choose_default_start_goal(dem_tile.elevation.shape)
            path = plan_path(
                elevation=dem_tile.elevation,
                start=start,
                goal=goal,
                cost_function=user_cost_formula,
            )
            print(f"Path cells: {len(path)}")
            print(f"Path length: {path_length(path):.3f}")
        else:
            print("Path planning skipped (use --run-planner to enable).")

        if args.no_plot:
            return 0

        plot_dem_surface(
            elevation=dem_tile.elevation,
            path=path,
            z_exaggeration=args.z_exaggeration,
            title="Lunar DEM 3D Terrain + Planned Path",
        )
        plot_dem_heatmap(
            elevation=dem_tile.elevation,
            path=path,
            title="Lunar DEM Top View + Planned Path",
        )
        show_all()
        return 0

    except FileNotFoundError as error:
        print(f"File error: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Argument/data error: {error}", file=sys.stderr)
        return 2
    except NotImplementedError as error:
        print(f"Cost function error: {error}", file=sys.stderr)
        return 5
    except RuntimeError as error:
        print(f"Planning error: {error}", file=sys.stderr)
        return 3
    except ModuleNotFoundError as error:
        print(
            f"Missing dependency: {error}. Please install required packages "
            "(numpy, rasterio, matplotlib).",
            file=sys.stderr,
        )
        return 4


if __name__ == "__main__":
    sys.exit(run())
