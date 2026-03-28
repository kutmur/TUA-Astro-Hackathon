"""Matplotlib-based 2D/3D visualization helpers for DEM and planned paths."""

from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - registers 3D projection

GridPoint = tuple[int, int]


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


def plot_dem_surface(
    elevation: np.ndarray,
    path: Optional[list[GridPoint]] = None,
    z_exaggeration: float = 2.5,
    title: str = "Lunar DEM 3D Surface",
) -> Figure:
    """Plots a DEM tile as a 3D surface with optional path overlay.

    Args:
        elevation: Elevation matrix.
        path: Optional path as list of grid points.
        z_exaggeration: Vertical exaggeration factor.
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

    axis.set_title(title)
    axis.set_xlabel("Column")
    axis.set_ylabel("Row")
    axis.set_zlabel("Elevation (scaled)")
    axis.view_init(elev=35, azim=225)

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
