"""Direct DEM plotting script for quick 3D visualization.

Usage:
    python3 plot.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_processing import BBox, PixelWindow, dem_statistics, find_first_tif, load_dem_window
from visualization import plot_dem_heatmap, plot_dem_surface, show_all


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for direct plotting."""

    parser = argparse.ArgumentParser(
        description="Directly load and plot a GeoTIFF DEM in 3D."
    )
    parser.add_argument(
        "--tif-path",
        type=str,
        default=None,
        help="Optional explicit GeoTIFF path. If omitted, first file in data/ is used.",
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
        help="Downsample factor for faster rendering.",
    )
    parser.add_argument(
        "--z-exaggeration",
        type=float,
        default=2.5,
        help="Vertical exaggeration factor for 3D surface.",
    )
    parser.add_argument(
        "--surface-only",
        action="store_true",
        help="Only show 3D surface (skip 2D heatmap).",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Prepare plots without opening UI window (for testing).",
    )
    return parser.parse_args()


def resolve_tif_path(explicit_path: str | None) -> Path:
    """Resolves target GeoTIFF path from CLI or `data/` directory."""

    if explicit_path:
        tif_path = Path(explicit_path).expanduser().resolve()
        if not tif_path.exists():
            raise FileNotFoundError(f"GeoTIFF file not found: {tif_path}")
        return tif_path

    return find_first_tif(PROJECT_ROOT / "data")


def build_pixel_window(raw_values: list[int] | None) -> PixelWindow | None:
    """Builds optional pixel crop window from CLI values."""

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
    """Builds optional map-coordinate bounding box from CLI values."""

    if raw_values is None:
        return None

    xmin, ymin, xmax, ymax = raw_values
    if xmax <= xmin or ymax <= ymin:
        raise ValueError("Invalid bbox: must satisfy XMAX > XMIN and YMAX > YMIN.")
    return xmin, ymin, xmax, ymax


def run() -> int:
    """Runs direct plotting workflow.

    Returns:
        Exit code.
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

        plot_dem_surface(
            elevation=dem_tile.elevation,
            z_exaggeration=args.z_exaggeration,
            title="Lunar DEM 3D Surface",
        )
        if not args.surface_only:
            plot_dem_heatmap(
                elevation=dem_tile.elevation,
                title="Lunar DEM Top View",
            )

        if not args.no_show:
            show_all()

        return 0

    except FileNotFoundError as error:
        print(f"File error: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Argument/data error: {error}", file=sys.stderr)
        return 2
    except ModuleNotFoundError as error:
        print(
            f"Missing dependency: {error}. Please install required packages "
            "(numpy, rasterio, matplotlib).",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    sys.exit(run())
