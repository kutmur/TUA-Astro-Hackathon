"""Utilities for memory-safe GeoTIFF window loading and cleaning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.transform import Affine
from rasterio.windows import Window, from_bounds

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class PixelWindow:
    """A pixel-space crop window.

    Attributes:
        col_start: Inclusive start column index.
        col_stop: Exclusive stop column index.
        row_start: Inclusive start row index.
        row_stop: Exclusive stop row index.
    """

    col_start: int
    col_stop: int
    row_start: int
    row_stop: int

    def __post_init__(self) -> None:
        if self.col_start < 0 or self.row_start < 0:
            raise ValueError("Pixel window start indices must be non-negative.")
        if self.col_stop <= self.col_start or self.row_stop <= self.row_start:
            raise ValueError("Pixel window stop indices must be greater than start indices.")

    @property
    def width(self) -> int:
        """Returns window width in pixels."""

        return self.col_stop - self.col_start

    @property
    def height(self) -> int:
        """Returns window height in pixels."""

        return self.row_stop - self.row_start

    def clamp_to_bounds(self, raster_width: int, raster_height: int) -> "PixelWindow":
        """Clamps this window to raster bounds.

        Args:
            raster_width: Full raster width.
            raster_height: Full raster height.

        Returns:
            A bounded PixelWindow.
        """

        col_start = max(0, min(self.col_start, raster_width))
        col_stop = max(0, min(self.col_stop, raster_width))
        row_start = max(0, min(self.row_start, raster_height))
        row_stop = max(0, min(self.row_stop, raster_height))

        if col_stop <= col_start or row_stop <= row_start:
            raise ValueError("Window is outside raster bounds after clamping.")

        return PixelWindow(
            col_start=col_start,
            col_stop=col_stop,
            row_start=row_start,
            row_stop=row_stop,
        )

    def to_rasterio_window(self) -> Window:
        """Converts to a rasterio Window."""

        return Window.from_slices(
            (self.row_start, self.row_stop),
            (self.col_start, self.col_stop),
        )


@dataclass(frozen=True)
class DEMTile:
    """DEM tile loaded from a GeoTIFF window.

    Attributes:
        elevation: Elevation matrix.
        transform: Affine transform for the loaded tile.
        crs: Tile coordinate reference system.
        nodata: Nodata value declared in source raster.
        pixel_window: Source pixel window used for reading.
    """

    elevation: np.ndarray
    transform: Affine
    crs: Optional[CRS]
    nodata: Optional[float]
    pixel_window: PixelWindow


def find_first_tif(data_directory: Path) -> Path:
    """Finds the first `.tif` or `.tiff` under a directory.

    Args:
        data_directory: Directory expected to contain DEM files.

    Returns:
        Path to the first TIFF file.

    Raises:
        FileNotFoundError: If directory or TIFF files are missing.
    """

    if not data_directory.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_directory}")

    tif_candidates = sorted(data_directory.glob("*.tif"))
    tiff_candidates = sorted(data_directory.glob("*.tiff"))
    candidates = tif_candidates + tiff_candidates
    if not candidates:
        raise FileNotFoundError(
            f"No .tif or .tiff files found in directory: {data_directory}"
        )

    return candidates[0]


def build_center_window(
    raster_width: int,
    raster_height: int,
    window_size: int,
) -> PixelWindow:
    """Builds a centered square pixel window.

    Args:
        raster_width: Full raster width in pixels.
        raster_height: Full raster height in pixels.
        window_size: Desired square window size.

    Returns:
        Centered PixelWindow inside bounds.
    """

    if window_size <= 0:
        raise ValueError("window_size must be a positive integer.")

    size = max(1, min(window_size, raster_width, raster_height))
    col_start = (raster_width - size) // 2
    row_start = (raster_height - size) // 2

    return PixelWindow(
        col_start=col_start,
        col_stop=col_start + size,
        row_start=row_start,
        row_stop=row_start + size,
    )


def clean_elevation_array(
    elevation: np.ndarray,
    nodata: Optional[float],
    fill_nan: bool = True,
) -> np.ndarray:
    """Cleans a DEM array by handling nodata and NaN values.

    Args:
        elevation: Raw elevation matrix.
        nodata: Optional nodata marker from source raster.
        fill_nan: Whether to fill NaN values with median elevation.

    Returns:
        Cleaned float32 elevation matrix.

    Raises:
        ValueError: If the tile has no valid values.
    """

    cleaned = elevation.astype(np.float32, copy=True)
    invalid_mask = np.isnan(cleaned)

    if nodata is not None and not np.isnan(nodata):
        invalid_mask |= np.isclose(cleaned, float(nodata))

    cleaned[invalid_mask] = np.nan
    finite_values = cleaned[np.isfinite(cleaned)]
    if finite_values.size == 0:
        raise ValueError("Loaded DEM window contains no valid elevation values.")

    if fill_nan:
        median_value = float(np.nanmedian(cleaned))
        cleaned = np.where(np.isnan(cleaned), median_value, cleaned).astype(np.float32)

    return cleaned


def _bbox_to_pixel_window(
    bounds: BBox,
    dataset: DatasetReader,
) -> PixelWindow:
    """Converts map-coordinate bounds to a bounded PixelWindow."""

    raw_window = from_bounds(*bounds, transform=dataset.transform)
    bounded = raw_window.round_offsets().round_lengths()

    pixel_window = PixelWindow(
        col_start=int(bounded.col_off),
        col_stop=int(bounded.col_off + bounded.width),
        row_start=int(bounded.row_off),
        row_stop=int(bounded.row_off + bounded.height),
    )

    return pixel_window.clamp_to_bounds(dataset.width, dataset.height)


def load_dem_window(
    tif_path: Path,
    pixel_window: Optional[PixelWindow] = None,
    bbox: Optional[BBox] = None,
    window_size: int = 1200,
    downsample: int = 1,
    fill_nan: bool = True,
    resampling: Resampling = Resampling.bilinear,
) -> DEMTile:
    """Loads a memory-safe DEM window from a GeoTIFF.

    Args:
        tif_path: Path to source GeoTIFF.
        pixel_window: Optional explicit pixel window.
        bbox: Optional map-coordinate bounding box as (xmin, ymin, xmax, ymax).
        window_size: Center window size when no explicit crop is provided.
        downsample: Pixel reduction factor for efficient plotting.
        fill_nan: Whether to fill NaNs by median.
        resampling: Rasterio resampling method used with downsampling.

    Returns:
        A DEMTile containing cropped elevation and metadata.

    Raises:
        FileNotFoundError: If the GeoTIFF does not exist.
        ValueError: If arguments are invalid.
    """

    if not tif_path.exists():
        raise FileNotFoundError(f"GeoTIFF file not found: {tif_path}")

    if downsample < 1:
        raise ValueError("downsample must be >= 1.")

    if pixel_window is not None and bbox is not None:
        raise ValueError("Provide either pixel_window or bbox, not both.")

    with rasterio.open(tif_path) as dataset:
        if pixel_window is not None:
            selected_window = pixel_window.clamp_to_bounds(dataset.width, dataset.height)
        elif bbox is not None:
            selected_window = _bbox_to_pixel_window(bbox, dataset)
        else:
            selected_window = build_center_window(
                raster_width=dataset.width,
                raster_height=dataset.height,
                window_size=window_size,
            )

        rio_window = selected_window.to_rasterio_window()
        out_height = max(1, int(np.ceil(selected_window.height / downsample)))
        out_width = max(1, int(np.ceil(selected_window.width / downsample)))

        elevation = dataset.read(
            1,
            window=rio_window,
            out_shape=(out_height, out_width),
            resampling=resampling,
        )

        window_transform = dataset.window_transform(rio_window)
        if downsample > 1:
            scale_x = selected_window.width / float(out_width)
            scale_y = selected_window.height / float(out_height)
            adjusted_transform = window_transform * Affine.scale(scale_x, scale_y)
        else:
            adjusted_transform = window_transform

        cleaned = clean_elevation_array(
            elevation=elevation,
            nodata=dataset.nodata,
            fill_nan=fill_nan,
        )

        return DEMTile(
            elevation=cleaned,
            transform=adjusted_transform,
            crs=dataset.crs,
            nodata=dataset.nodata,
            pixel_window=selected_window,
        )


def dem_statistics(elevation: np.ndarray) -> dict[str, float]:
    """Calculates descriptive statistics for a DEM tile.

    Args:
        elevation: Elevation matrix.

    Returns:
        Dictionary with min, max, mean, and std values.
    """

    finite_values = elevation[np.isfinite(elevation)]
    if finite_values.size == 0:
        raise ValueError("Cannot compute statistics for an empty DEM tile.")

    return {
        "min": float(np.min(finite_values)),
        "max": float(np.max(finite_values)),
        "mean": float(np.mean(finite_values)),
        "std": float(np.std(finite_values)),
    }
