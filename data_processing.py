from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import rasterio
from rasterio.io import DatasetReader
from rasterio.transform import Affine
from rasterio.windows import Window, from_bounds

PixelWindow = Tuple[int, int, int, int]
Bounds = Tuple[float, float, float, float]


@dataclass(frozen=True)
class DemRegion:
    array: np.ndarray
    transform: Affine
    resolution: Tuple[float, float]
    crs: Optional[str]
    nodata: Optional[float]


def _clamp_window(window: Window, src: DatasetReader) -> Window:
    col_off = max(0, int(np.floor(window.col_off)))
    row_off = max(0, int(np.floor(window.row_off)))

    max_col = min(src.width, int(np.ceil(window.col_off + window.width)))
    max_row = min(src.height, int(np.ceil(window.row_off + window.height)))

    width = max_col - col_off
    height = max_row - row_off
    if width <= 0 or height <= 0:
        raise ValueError("Requested crop region is outside DEM bounds.")

    return Window(col_off=col_off, row_off=row_off, width=width, height=height)


def _window_from_pixel_range(pixel_window: PixelWindow, src: DatasetReader) -> Window:
    row_start, row_end, col_start, col_end = pixel_window
    if row_start < 0 or col_start < 0:
        raise ValueError("row_start and col_start must be >= 0.")
    if row_end <= row_start or col_end <= col_start:
        raise ValueError("row_end/col_end must be greater than row_start/col_start.")

    window = Window(
        col_off=col_start,
        row_off=row_start,
        width=col_end - col_start,
        height=row_end - row_start,
    )
    return _clamp_window(window, src)


def _window_from_bbox(bbox: Bounds, src: DatasetReader) -> Window:
    xmin, ymin, xmax, ymax = bbox
    if xmin >= xmax or ymin >= ymax:
        raise ValueError("Invalid bbox. Expected (xmin, ymin, xmax, ymax) with min < max.")

    window = from_bounds(xmin, ymin, xmax, ymax, transform=src.transform)
    return _clamp_window(window, src)


def load_dem_region(
    tif_path: str | Path,
    pixel_window: Optional[PixelWindow] = None,
    bbox: Optional[Bounds] = None,
    band: int = 1,
    fill_nodata_with_nan: bool = True,
) -> DemRegion:
    """
    Read a DEM GeoTIFF, crop a region, and return it as a NumPy array.

    Parameters
    ----------
    tif_path:
        Path to DEM .tif file.
    pixel_window:
        (row_start, row_end, col_start, col_end) in pixel coordinates.
    bbox:
        (xmin, ymin, xmax, ymax) in DEM map coordinates.
    band:
        Raster band index to read.
    fill_nodata_with_nan:
        If True, nodata/masked pixels are replaced with np.nan.
    """
    if pixel_window is not None and bbox is not None:
        raise ValueError("Use either pixel_window or bbox, not both.")

    tif_path = Path(tif_path)
    if not tif_path.exists():
        raise FileNotFoundError(f"DEM file not found: {tif_path}")

    with rasterio.open(tif_path) as src:
        if band < 1 or band > src.count:
            raise ValueError(f"Invalid band index {band}. DEM has {src.count} band(s).")

        if pixel_window is not None:
            window = _window_from_pixel_range(pixel_window, src)
        elif bbox is not None:
            window = _window_from_bbox(bbox, src)
        else:
            window = Window(col_off=0, row_off=0, width=src.width, height=src.height)

        dem = src.read(band, window=window).astype(np.float32, copy=False)

        if fill_nodata_with_nan:
            mask = src.read_masks(band, window=window) == 0
            if np.any(mask):
                dem = dem.copy()
                dem[mask] = np.nan

            if src.nodata is not None:
                dem = np.where(np.isclose(dem, src.nodata), np.nan, dem)

        transform = src.window_transform(window)
        resolution = (abs(transform.a), abs(transform.e))
        crs = src.crs.to_string() if src.crs else None

        return DemRegion(
            array=dem,
            transform=transform,
            resolution=resolution,
            crs=crs,
            nodata=src.nodata,
        )
