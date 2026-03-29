"""Direct DEM plotting script for quick 3D visualization.

Usage:
    python3 plot.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_processing import BBox, PixelWindow, dem_statistics, find_first_tif, load_dem_window
from visualization import DEMVisualizer, RoutePath, SurfaceMarker, plot_dem_heatmap, plot_dem_surface, show_all


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
        "--save-surface",
        type=str,
        default=None,
        help="Optional output path to save the base 3D surface image.",
    )
    parser.add_argument(
        "--save-annotated",
        type=str,
        default=None,
        help="Optional output path to save the A/B annotated 3D surface image.",
    )
    parser.add_argument(
        "--stage1-markers",
        dest="stage1_markers",
        action="store_true",
        default=True,
        help="Overlay Stage-1 A/B markers and labels on the 3D surface (default: enabled).",
    )
    parser.add_argument(
        "--no-stage1-markers",
        dest="stage1_markers",
        action="store_false",
        help="Disable Stage-1 A/B markers on the 3D surface.",
    )
    parser.add_argument(
        "--view-elev",
        type=float,
        default=35.0,
        help="Camera elevation angle for 3D surface.",
    )
    parser.add_argument(
        "--view-azim",
        type=float,
        default=225.0,
        help="Camera azimuth angle for 3D surface.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI used while saving output images.",
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


def _ensure_output_path(raw_path: str) -> Path:
    """Resolves and prepares an output file path."""

    output_path = Path(raw_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def _clamp_point(row: int, col: int, shape: tuple[int, int]) -> tuple[int, int]:
    """Clamps a target point into DEM bounds."""

    rows, cols = shape
    return max(0, min(row, rows - 1)), max(0, min(col, cols - 1))


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

        marker_mode = args.stage1_markers or bool(args.save_annotated)
        stage1_markers = None
        if marker_mode:
            start_row, start_col = _clamp_point(0, 120, dem_tile.elevation.shape)
            end_row, end_col = _clamp_point(60, 5, dem_tile.elevation.shape)
            start_elevation = float(dem_tile.elevation[start_row, start_col])
            end_elevation = float(dem_tile.elevation[end_row, end_col])
            print(
                "Resolved markers: "
                f"A(Row={start_row}, Col={start_col}, Elev={start_elevation:.1f}) | "
                f"B(Row={end_row}, Col={end_col}, Elev={end_elevation:.1f})"
            )
            stage1_markers = [
                SurfaceMarker(
                    row=start_row,
                    col=start_col,
                    label="Start Point A",
                    color="red",
                    marker="v",
                    size=150.0,
                    label_offset=(18.0, 10.0, 0.0),
                ),
                SurfaceMarker(
                    row=end_row,
                    col=end_col,
                    label="End Point B",
                    color="lime",
                    marker="D",
                    size=150.0,
                    label_offset=(-22.0, 12.0, 0.0),
                ),
            ]

            mock_routes = DEMVisualizer.generate_mock_routes(
                start_row=start_row,
                start_col=start_col,
                end_row=end_row,
                end_col=end_col,
                elevation=dem_tile.elevation,
            )

        surface_figure = plot_dem_surface(
            elevation=dem_tile.elevation,
            markers=stage1_markers,
            routes=mock_routes if marker_mode else None,
            z_exaggeration=args.z_exaggeration,
            view_elev=args.view_elev,
            view_azim=args.view_azim,
            title="TUA AYAP-2 | Lunar Surface \u2013 Multi-Objective Route Analysis",
        )

        if args.save_surface:
            output_path = _ensure_output_path(args.save_surface)
            surface_figure.savefig(output_path, dpi=args.dpi)
            print(f"Saved base surface image: {output_path}")

        if args.save_annotated:
            output_path = _ensure_output_path(args.save_annotated)
            surface_figure.savefig(output_path, dpi=args.dpi)
            print(f"Saved annotated surface image: {output_path}")

        if not args.surface_only:
            plot_dem_heatmap(
                elevation=dem_tile.elevation,
                title="Lunar DEM Top View",
            )

        if not args.no_show:
            show_all()
        else:
            plt.close("all")

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
