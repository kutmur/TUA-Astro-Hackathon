"""Matplotlib-based 2D/3D visualization helpers for DEM and planned paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - registers 3D projection

GridPoint = tuple[int, int]


@dataclass(frozen=True)
class SurfaceMarker:
    """A labeled marker rendered on top of the 3D DEM surface.

    Attributes:
        row: Grid row index.
        col: Grid column index.
        label: Annotation text shown near the marker.
        color: Marker and glow color.
        marker: Matplotlib marker style (e.g. "*", "D").
        size: Base marker size.
        label_offset: Optional (dx, dy, dz) offset for label anchor.
    """

    row: int
    col: int
    label: str
    color: str
    marker: str
    size: float = 220.0
    label_offset: tuple[float, float, float] | None = None


def build_xy_mesh(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Builds meshgrid arrays for surface plotting.

    Args:
        shape: DEM shape as (rows, cols).

    Returns:
        X and Y mesh arrays.
    """

    rows, cols = shape
    x = np.arange(cols, dtype=np.float32)
    y = np.arange(rows, dtype=np.float32)
    return np.meshgrid(x, y)


def _path_to_arrays(path: list[GridPoint], elevation: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Converts path points to x, y, z coordinate arrays."""

    if not path:
        return np.array([]), np.array([]), np.array([])

    rows = np.array([point[0] for point in path], dtype=np.int32)
    cols = np.array([point[1] for point in path], dtype=np.int32)
    z_values = elevation[rows, cols]
    return cols, rows, z_values


def _default_label_offset(
    row: int,
    col: int,
    shape: tuple[int, int],
    z_span: float,
) -> tuple[float, float, float]:
    """Builds a readable default offset for marker labels."""

    rows, cols = shape
    x_sign = 1.0 if col < (cols / 2.0) else -1.0
    y_sign = 1.0 if row < (rows / 2.0) else -1.0

    dx = x_sign * max(10.0, cols * 0.12)
    dy = y_sign * max(10.0, rows * 0.12)
    dz = max(25.0, z_span * 0.13)
    return dx, dy, dz


def _clamp(value: float, low: float, high: float) -> float:
    """Clamps a value to an inclusive [low, high] range."""

    return max(low, min(value, high))


def _plot_surface_marker(
    axis: Axes3D,
    marker: SurfaceMarker,
    elevation: np.ndarray,
    z_exaggeration: float,
) -> None:
    """Draws one flagpole-style marker pinned to the DEM surface.

    Uses dynamic Z-offset (15% of total z-range), forced zorder=1000 on
    every drawn element, and depthshade=False to defeat mplot3d's chronic
    z-buffer occlusion issues.
    """

    rows, cols = elevation.shape
    if not (0 <= marker.row < rows and 0 <= marker.col < cols):
        raise ValueError(
            f"Marker point (row={marker.row}, col={marker.col}) is outside DEM bounds {elevation.shape}."
        )

    z_grid = elevation * float(z_exaggeration)
    z_surface = float(z_grid[marker.row, marker.col])
    z_range = float(np.nanmax(z_grid) - np.nanmin(z_grid))

    # --- Rule 1: Dynamic Z-offset (flagpole height = 15% of total z-range) ---
    z_offset = z_range * 0.15
    z_marker = z_surface + z_offset

    x_point = float(marker.col)
    y_point = float(marker.row)

    # --- Rule 3: Flagpole pin – thick, solid, black vertical line ---
    axis.plot(
        [x_point, x_point],
        [y_point, y_point],
        [z_surface, z_marker],
        color="black",
        linestyle="-",
        linewidth=2,
        alpha=1.0,
        zorder=1000,
    )

    # --- Rule 4 (marker): depthshade=False, edgecolors, zorder=1000 ---
    axis.scatter(
        x_point,
        y_point,
        z_marker,
        s=marker.size,
        marker=marker.marker,
        c=marker.color,
        edgecolors="black",
        linewidths=1.5,
        depthshade=False,
        zorder=1000,
    )

    # Label offset computation
    if marker.label_offset is not None:
        dx, dy, _dz = marker.label_offset
    else:
        dx, dy, _dz = _default_label_offset(marker.row, marker.col, elevation.shape, z_range)

    x_label = _clamp(x_point + dx, 0.0, float(cols - 1))
    y_label = _clamp(y_point + dy, 0.0, float(rows - 1))
    z_label = z_marker + z_range * 0.03  # label sits slightly above the marker

    # Leader line from marker top to label anchor
    axis.plot(
        [x_point, x_label],
        [y_point, y_label],
        [z_marker, z_label],
        color="#222222",
        linewidth=1.0,
        alpha=0.9,
        zorder=1000,
    )

    # --- Rule 4 (label): white bbox, alpha=0.9, edgecolor black, zorder=1000 ---
    horizontal_alignment = "left" if x_label >= x_point else "right"
    axis.text(
        x_label,
        y_label,
        z_label,
        marker.label,
        fontsize=9,
        fontweight="bold",
        color="black",
        ha=horizontal_alignment,
        va="center",
        bbox={
            "boxstyle": "round,pad=0.5",
            "facecolor": "white",
            "edgecolor": "black",
            "alpha": 0.9,
        },
        zorder=1000,
    )


def plot_dem_surface(
    elevation: np.ndarray,
    path: Optional[list[GridPoint]] = None,
    markers: Optional[list[SurfaceMarker]] = None,
    z_exaggeration: float = 2.5,
    view_elev: float = 35.0,
    view_azim: float = 225.0,
    title: str = "Lunar DEM 3D Surface",
) -> Figure:
    """Plots a DEM tile as a 3D surface with optional path overlay.

    Args:
        elevation: Elevation matrix.
        path: Optional path as list of grid points.
        markers: Optional annotated surface markers.
        z_exaggeration: Vertical exaggeration factor.
        view_elev: 3D camera elevation angle.
        view_azim: 3D camera azimuth angle.
        title: Figure title.

    Returns:
        Matplotlib figure object.
    """

    if elevation.ndim != 2:
        raise ValueError("Elevation matrix must be 2-dimensional.")
    if z_exaggeration <= 0:
        raise ValueError("z_exaggeration must be a positive number.")

    x_grid, y_grid = build_xy_mesh(elevation.shape)
    z_grid = elevation * float(z_exaggeration)

    figure = plt.figure(figsize=(12, 9))
    axis: Axes3D = figure.add_subplot(111, projection="3d")
    surface = axis.plot_surface(
        x_grid,
        y_grid,
        z_grid,
        cmap="terrain",
        linewidth=0,
        antialiased=True,
        alpha=0.95,
    )
    figure.colorbar(surface, shrink=0.6, pad=0.08, label="Elevation (scaled)")

    if path:
        x_path, y_path, z_path = _path_to_arrays(path, elevation)
        axis.plot(
            x_path,
            y_path,
            z_path * float(z_exaggeration) + 1.0,
            color="crimson",
            linewidth=2.0,
            label="Planned Path",
        )
        axis.scatter(
            x_path[0],
            y_path[0],
            z_path[0] * float(z_exaggeration) + 1.0,
            color="limegreen",
            s=50,
            label="Start",
        )
        axis.scatter(
            x_path[-1],
            y_path[-1],
            z_path[-1] * float(z_exaggeration) + 1.0,
            color="black",
            s=50,
            label="Goal",
        )
        axis.legend(loc="upper right")

    if markers:
        for marker in markers:
            _plot_surface_marker(
                axis=axis,
                marker=marker,
                elevation=elevation,
                z_exaggeration=z_exaggeration,
            )

    axis.set_title(title)
    axis.set_xlabel("Column")
    axis.set_ylabel("Row")
    axis.set_zlabel("Elevation (scaled)")
    axis.view_init(elev=float(view_elev), azim=float(view_azim))

    return figure


def plot_dem_heatmap(
    elevation: np.ndarray,
    path: Optional[list[GridPoint]] = None,
    title: str = "Lunar DEM Top View",
) -> tuple[Figure, Axes]:
    """Plots DEM as 2D heatmap with optional path overlay.

    Args:
        elevation: Elevation matrix.
        path: Optional path as list of grid points.
        title: Plot title.

    Returns:
        Figure and axes tuple.
    """

    if elevation.ndim != 2:
        raise ValueError("Elevation matrix must be 2-dimensional.")

    figure, axis = plt.subplots(figsize=(9, 7))
    image = axis.imshow(elevation, cmap="terrain", origin="upper")
    figure.colorbar(image, ax=axis, label="Elevation")

    if path:
        x_path, y_path, _ = _path_to_arrays(path, elevation)
        axis.plot(x_path, y_path, color="crimson", linewidth=1.8)
        axis.scatter(x_path[0], y_path[0], color="limegreen", s=35)
        axis.scatter(x_path[-1], y_path[-1], color="black", s=35)

    axis.set_title(title)
    axis.set_xlabel("Column")
    axis.set_ylabel("Row")

    return figure, axis


def show_all() -> None:
    """Displays all prepared matplotlib figures."""

    plt.tight_layout()
    plt.show()
