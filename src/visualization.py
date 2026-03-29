"""Matplotlib-based 2D/3D visualization helpers for DEM and planned paths."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class RoutePath:
    """A styled 3D route rendered on the DEM surface.

    Attributes:
        points: Ordered list of (row, col) grid coordinates.
        label: Legend label including cost info.
        color: Line color.
        linewidth: Line width.
        linestyle: Matplotlib linestyle (e.g. '-', '--', ':').
        cost: Simulated total cost value.
        zorder: Render order (higher = on top).
    """

    points: list[GridPoint] = field(default_factory=list)
    label: str = ""
    color: str = "white"
    linewidth: float = 2.0
    linestyle: str = "-"
    cost: float = 0.0
    zorder: int = 500


class DEMVisualizer:
    """Object-oriented renderer for DEM heatmaps and surface plots."""

    def __init__(self, surface_cmap: str = "terrain", heatmap_cmap: str = "terrain"):
        self._surface_cmap = surface_cmap
        self._heatmap_cmap = heatmap_cmap

    @staticmethod
    def build_xy_mesh(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
        """Builds meshgrid arrays for surface plotting."""

        rows, cols = shape
        x = np.arange(cols, dtype=np.float32)
        y = np.arange(rows, dtype=np.float32)
        return np.meshgrid(x, y)

    @staticmethod
    def _path_to_arrays(
        path: list[GridPoint], elevation: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Converts path points to x, y, z coordinate arrays."""

        if not path:
            return np.array([]), np.array([]), np.array([])

        rows = np.array([point[0] for point in path], dtype=np.int32)
        cols = np.array([point[1] for point in path], dtype=np.int32)
        z_values = elevation[rows, cols]
        return cols, rows, z_values

    @staticmethod
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

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        """Clamps a value to an inclusive [low, high] range."""

        return max(low, min(value, high))

    def _plot_surface_marker(
        self,
        axis: Axes3D,
        marker: SurfaceMarker,
        elevation: np.ndarray,
        z_exaggeration: float,
    ) -> None:
        """Draws one flagpole-style marker pinned to the DEM surface."""

        rows, cols = elevation.shape
        if not (0 <= marker.row < rows and 0 <= marker.col < cols):
            raise ValueError(
                f"Marker point (row={marker.row}, col={marker.col}) is outside DEM bounds {elevation.shape}."
            )

        z_grid = elevation * float(z_exaggeration)
        z_surface = float(z_grid[marker.row, marker.col])
        z_range = float(np.nanmax(z_grid) - np.nanmin(z_grid))
        z_offset = z_range * 0.15
        z_marker = z_surface + z_offset

        x_point = float(marker.col)
        y_point = float(marker.row)
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

        if marker.label_offset is not None:
            dx, dy, _dz = marker.label_offset
        else:
            dx, dy, _dz = self._default_label_offset(marker.row, marker.col, elevation.shape, z_range)

        x_label = self._clamp(x_point + dx, 0.0, float(cols - 1))
        y_label = self._clamp(y_point + dy, 0.0, float(rows - 1))
        z_label = z_marker + z_range * 0.03

        axis.plot(
            [x_point, x_label],
            [y_point, y_label],
            [z_marker, z_label],
            color="#222222",
            linewidth=1.0,
            alpha=0.9,
            zorder=1000,
        )

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

    @staticmethod
    def generate_mock_routes(
        start_row: int,
        start_col: int,
        end_row: int,
        end_col: int,
        elevation: np.ndarray,
    ) -> list[RoutePath]:
        """Generates 3 simulated parametric routes between A and B.

        Routes are projected onto the DEM surface so they follow the terrain.
        """

        num_points = 100
        t = np.linspace(0.0, 1.0, num_points)
        rows, cols = elevation.shape

        # Base linear interpolation
        base_row = start_row + t * (end_row - start_row)
        base_col = start_col + t * (end_col - start_col)

        # --- Route 1: Optimal (balanced 4D) – gentle sinusoidal detour ---
        lateral_offset_1 = np.sin(t * np.pi) * (cols * 0.12)
        opt_row = base_row + lateral_offset_1 * 0.3
        opt_col = base_col + lateral_offset_1
        opt_points: list[GridPoint] = []
        for r, c in zip(opt_row, opt_col):
            ri = int(np.clip(round(r), 0, rows - 1))
            ci = int(np.clip(round(c), 0, cols - 1))
            opt_points.append((ri, ci))

        # --- Route 2: Shortest distance (near-linear, high slope) ---
        noise = np.random.default_rng(42).normal(0, 1.5, num_points)
        short_row = base_row + noise * 0.5
        short_col = base_col + noise * 0.5
        short_points: list[GridPoint] = []
        for r, c in zip(short_row, short_col):
            ri = int(np.clip(round(r), 0, rows - 1))
            ci = int(np.clip(round(c), 0, cols - 1))
            short_points.append((ri, ci))

        # --- Route 3: Thermal-safe detour – large arc ---
        arc_offset = np.sin(t * np.pi) * (cols * 0.28)
        perp_row_dir = -(end_col - start_col)
        perp_col_dir = end_row - start_row
        perp_len = max(np.sqrt(perp_row_dir**2 + perp_col_dir**2), 1e-6)
        perp_row_dir /= perp_len
        perp_col_dir /= perp_len
        therm_row = base_row + arc_offset * perp_row_dir
        therm_col = base_col + arc_offset * perp_col_dir
        therm_points: list[GridPoint] = []
        for r, c in zip(therm_row, therm_col):
            ri = int(np.clip(round(r), 0, rows - 1))
            ci = int(np.clip(round(c), 0, cols - 1))
            therm_points.append((ri, ci))

        return [
            RoutePath(
                points=opt_points,
                label="Optimal Path (Balanced 4D) | Cost: 12.4K",
                color="gold",
                linewidth=3,
                linestyle="-",
                cost=12450.0,
                zorder=520,
            ),
            RoutePath(
                points=short_points,
                label="Alt 1 (Shortest, High Slope) | Cost: 18.2K",
                color="cyan",
                linewidth=2,
                linestyle="--",
                cost=18200.0,
                zorder=510,
            ),
            RoutePath(
                points=therm_points,
                label="Alt 2 (Thermal Safe, Long) | Cost: 15.8K",
                color="magenta",
                linewidth=2,
                linestyle=":",
                cost=15850.0,
                zorder=500,
            ),
        ]

    def _plot_routes(
        self,
        axis: Axes3D,
        routes: list[RoutePath],
        elevation: np.ndarray,
        z_exaggeration: float,
    ) -> None:
        """Renders multiple styled routes on the 3D surface with a legend."""

        z_grid = elevation * float(z_exaggeration)
        z_range = float(np.nanmax(z_grid) - np.nanmin(z_grid))
        z_offset = z_range * 0.02

        for route in routes:
            if not route.points:
                continue

            rows_arr = np.array([p[0] for p in route.points], dtype=np.int32)
            cols_arr = np.array([p[1] for p in route.points], dtype=np.int32)
            z_vals = z_grid[rows_arr, cols_arr] + z_offset

            axis.plot(
                cols_arr.astype(np.float64),
                rows_arr.astype(np.float64),
                z_vals,
                color=route.color,
                linewidth=route.linewidth,
                linestyle=route.linestyle,
                label=route.label,
                zorder=route.zorder,
                alpha=0.95,
            )

        axis.legend(
            loc="upper right",
            facecolor="black",
            edgecolor="white",
            labelcolor="white",
            fontsize=7.5,
            framealpha=0.85,
        )

    def plot_surface(
        self,
        elevation: np.ndarray,
        path: Optional[list[GridPoint]] = None,
        markers: Optional[list[SurfaceMarker]] = None,
        routes: Optional[list[RoutePath]] = None,
        z_exaggeration: float = 2.5,
        view_elev: float = 35.0,
        view_azim: float = 225.0,
        title: str = "Lunar DEM 3D Surface",
    ) -> Figure:
        """Plots a DEM tile as a 3D surface with optional path overlay."""

        if elevation.ndim != 2:
            raise ValueError("Elevation matrix must be 2-dimensional.")
        if z_exaggeration <= 0:
            raise ValueError("z_exaggeration must be a positive number.")

        x_grid, y_grid = self.build_xy_mesh(elevation.shape)
        z_grid = elevation * float(z_exaggeration)

        figure = plt.figure(figsize=(12, 9))
        axis: Axes3D = figure.add_subplot(111, projection="3d")
        surface = axis.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            cmap=self._surface_cmap,
            linewidth=0,
            antialiased=True,
            alpha=0.95,
        )
        figure.colorbar(surface, shrink=0.6, pad=0.08, label="Elevation (scaled)")

        if path:
            x_path, y_path, z_path = self._path_to_arrays(path, elevation)
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

        if routes:
            self._plot_routes(
                axis=axis,
                routes=routes,
                elevation=elevation,
                z_exaggeration=z_exaggeration,
            )

        if markers:
            for marker in markers:
                self._plot_surface_marker(
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

    def plot_heatmap(
        self,
        elevation: np.ndarray,
        path: Optional[list[GridPoint]] = None,
        title: str = "Lunar DEM Top View",
    ) -> tuple[Figure, Axes]:
        """Plots DEM as 2D heatmap with optional path overlay."""

        if elevation.ndim != 2:
            raise ValueError("Elevation matrix must be 2-dimensional.")

        figure, axis = plt.subplots(figsize=(9, 7))
        image = axis.imshow(elevation, cmap=self._heatmap_cmap, origin="upper")
        figure.colorbar(image, ax=axis, label="Elevation")

        if path:
            x_path, y_path, _ = self._path_to_arrays(path, elevation)
            axis.plot(x_path, y_path, color="crimson", linewidth=1.8)
            axis.scatter(x_path[0], y_path[0], color="limegreen", s=35)
            axis.scatter(x_path[-1], y_path[-1], color="black", s=35)

        axis.set_title(title)
        axis.set_xlabel("Column")
        axis.set_ylabel("Row")

        return figure, axis

    @staticmethod
    def show_all() -> None:
        """Displays all prepared matplotlib figures."""

        plt.tight_layout()
        plt.show()


_DEFAULT_VISUALIZER = DEMVisualizer()


def build_xy_mesh(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Builds meshgrid arrays for surface plotting."""

    return _DEFAULT_VISUALIZER.build_xy_mesh(shape)


def plot_dem_surface(
    elevation: np.ndarray,
    path: Optional[list[GridPoint]] = None,
    markers: Optional[list[SurfaceMarker]] = None,
    routes: Optional[list[RoutePath]] = None,
    z_exaggeration: float = 2.5,
    view_elev: float = 35.0,
    view_azim: float = 225.0,
    title: str = "Lunar DEM 3D Surface",
) -> Figure:
    """Plots a DEM tile as a 3D surface with optional path overlay."""

    return _DEFAULT_VISUALIZER.plot_surface(
        elevation=elevation,
        path=path,
        markers=markers,
        routes=routes,
        z_exaggeration=z_exaggeration,
        view_elev=view_elev,
        view_azim=view_azim,
        title=title,
    )


def plot_dem_heatmap(
    elevation: np.ndarray,
    path: Optional[list[GridPoint]] = None,
    title: str = "Lunar DEM Top View",
) -> tuple[Figure, Axes]:
    """Plots DEM as 2D heatmap with optional path overlay."""

    return _DEFAULT_VISUALIZER.plot_heatmap(
        elevation=elevation,
        path=path,
        title=title,
    )


def show_all() -> None:
    """Displays all prepared matplotlib figures."""

    _DEFAULT_VISUALIZER.show_all()
