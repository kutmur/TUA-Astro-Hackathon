"""AYAP-2 real DEM A* simulator with 4D mission cost model.

This module runs a true 8-direction A* search over a real DEM matrix and
plots three route strategies on a 3D surface:
- Balanced 4D mission path
- Distance-priority path
- Shadow/thermal safe path
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from heapq import heappop, heappush
from math import sqrt
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - keeps 3D projection registered

from visualization import build_xy_mesh

GridPoint = tuple[int, int]

# Keep A/B points stable across different DEM sizes using normalized UV coordinates.
REQUESTED_START_UV: tuple[float, float] = (0.0, 0.99)
# Target B is aligned to the same approximate region as image0/image1
# (about Row=31, Col=0 when grid is ~121x121).
REQUESTED_GOAL_UV: tuple[float, float] = (0.258, 0.0)

_NEIGHBOR_OFFSETS: tuple[tuple[int, int], ...] = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


@dataclass(frozen=True)
class RouteProfile:
    """Weight configuration and style for one A* run."""

    name: str
    wd: float
    we: float
    ws: float
    wg: float
    color: str
    linestyle: str
    linewidth: float


@dataclass(frozen=True)
class RouteResult:
    """A* output for one route profile."""

    profile: RouteProfile
    path: list[GridPoint]
    cumulative_cost: float


@dataclass(frozen=True)
class CostLayers:
    """Terrain-derived cost maps used by the AYAP-2 equation."""

    z_norm: np.ndarray
    e_map: np.ndarray
    s_map: np.ndarray
    g_map: np.ndarray


def normalize_01(values: np.ndarray) -> np.ndarray:
    """Normalizes a matrix into [0, 1]."""

    v_min = float(np.nanmin(values))
    v_max = float(np.nanmax(values))
    span = max(v_max - v_min, 1e-9)
    return (values - v_min) / span


def _dummy_dem() -> np.ndarray:
    """Deterministic temporary DEM fallback for architecture tests.

    This fallback is used only if external DEM loading fails and
    --allow-dummy is enabled.
    """

    rows = 90
    cols = 140
    row_axis = np.arange(rows, dtype=np.float32)[:, None]
    col_axis = np.arange(cols, dtype=np.float32)[None, :]
    dem = (0.7 * row_axis) - (0.25 * col_axis)

    terrace = np.zeros_like(dem)
    terrace[rows // 3 : rows // 2, cols // 4 : cols // 2] = 9.0
    terrace[rows // 2 : (rows * 3) // 4, (cols * 2) // 3 :] = -7.5

    return (dem + terrace).astype(np.float32)


def _to_2d_float32(array: np.ndarray) -> np.ndarray:
    """Converts input to a finite 2D float32 DEM matrix."""

    dem = np.asarray(array)
    if dem.ndim == 3:
        dem = dem[..., :3].mean(axis=2)
    if dem.ndim != 2:
        raise ValueError(f"DEM must be 2D after conversion, got shape {dem.shape}.")

    dem = dem.astype(np.float32)
    finite_mask = np.isfinite(dem)
    if not np.any(finite_mask):
        raise ValueError("DEM has no finite values.")

    median = float(np.nanmedian(dem[finite_mask]))
    dem[~finite_mask] = median
    return dem


def _load_dem_from_npy(path: Path) -> np.ndarray:
    """Loads a DEM matrix from a .npy/.npz file."""

    loaded = np.load(path, allow_pickle=False)

    if isinstance(loaded, np.lib.npyio.NpzFile):
        if not loaded.files:
            raise ValueError(f"NPZ file has no arrays: {path}")
        first_key = loaded.files[0]
        return _to_2d_float32(loaded[first_key])

    return _to_2d_float32(loaded)


def _load_dem_from_image(path: Path) -> np.ndarray:
    """Loads DEM-like grayscale heights from an image file.

    Preferred reader is cv2.imread(path, 0). If OpenCV is not available,
    matplotlib image reader is used.
    """

    try:
        import cv2  # type: ignore

        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"Could not read DEM image with cv2: {path}")
        return _to_2d_float32(image)
    except ModuleNotFoundError:
        image = plt.imread(path)
        return _to_2d_float32(image)


def _load_dem_from_tif(path: Path, window_size: int, downsample: int) -> np.ndarray:
    """Loads real DEM data from GeoTIFF using project loader utilities."""

    try:
        from data_processing import load_dem_window
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "GeoTIFF loading requires rasterio and project data_processing module."
        ) from error

    tile = load_dem_window(
        tif_path=path,
        pixel_window=None,
        bbox=None,
        window_size=window_size,
        downsample=max(1, downsample),
        fill_nan=True,
    )
    return _to_2d_float32(tile.elevation)


def _auto_default_tif() -> Path | None:
    """Finds first TIFF in project data directory."""

    data_dir = Path(__file__).resolve().parent.parent / "data"
    if not data_dir.exists():
        return None

    candidates = sorted(data_dir.glob("*.tif")) + sorted(data_dir.glob("*.tiff"))
    if not candidates:
        return None
    return candidates[0]


def load_real_dem(
    dem_npy: str | None = None,
    dem_image: str | None = None,
    dem_tif: str | None = None,
    tif_window_size: int = 1200,
    tif_downsample: int = 2,
    allow_dummy: bool = False,
) -> np.ndarray:
    """Loads real DEM from external input sources.

    Priority order:
      1) dem_npy -> 2D numpy matrix file
      2) dem_tif -> real GeoTIFF DEM
      3) dem_image -> grayscale heightmap image
      4) auto-detected TIFF in project data/
      5) deterministic dummy DEM (only if allow_dummy=True)
    """

    selected_sources = [
        dem_npy is not None,
        dem_image is not None,
        dem_tif is not None,
    ]
    if sum(selected_sources) > 1:
        raise ValueError("Use only one source: --dem-npy, --dem-image, or --dem-tif.")

    if dem_npy is not None:
        npy_path = Path(dem_npy).expanduser().resolve()
        if not npy_path.exists():
            raise FileNotFoundError(f"DEM npy/npz file does not exist: {npy_path}")
        print(f"[INFO] Loading real DEM from npy/npz: {npy_path}")
        return _load_dem_from_npy(npy_path)

    if dem_tif is not None:
        tif_path = Path(dem_tif).expanduser().resolve()
        if not tif_path.exists():
            raise FileNotFoundError(f"DEM GeoTIFF does not exist: {tif_path}")
        print(f"[INFO] Loading real DEM from GeoTIFF: {tif_path}")
        return _load_dem_from_tif(tif_path, window_size=tif_window_size, downsample=tif_downsample)

    if dem_image is not None:
        image_path = Path(dem_image).expanduser().resolve()
        if not image_path.exists():
            raise FileNotFoundError(f"DEM image does not exist: {image_path}")
        print(f"[INFO] Loading DEM-like heights from image: {image_path}")
        return _load_dem_from_image(image_path)

    auto_tif = _auto_default_tif()
    if auto_tif is not None:
        print(f"[INFO] Loading default project DEM: {auto_tif}")
        return _load_dem_from_tif(auto_tif, window_size=tif_window_size, downsample=tif_downsample)

    if allow_dummy:
        print("[WARN] No external DEM source found. Using temporary dummy DEM.")
        return _dummy_dem()

    raise FileNotFoundError(
        "No DEM source found. Provide --dem-npy, --dem-image, --dem-tif, or set --allow-dummy."
    )


def _local_variance_3x3(field: np.ndarray) -> np.ndarray:
    """Computes 3x3 local variance map with edge padding."""

    rows, cols = field.shape
    padded = np.pad(field, 1, mode="edge")
    sum_window = np.zeros_like(field, dtype=np.float64)
    sum_sq_window = np.zeros_like(field, dtype=np.float64)

    for d_row in range(3):
        for d_col in range(3):
            tile = padded[d_row : d_row + rows, d_col : d_col + cols]
            sum_window += tile
            sum_sq_window += tile * tile

    mean_window = sum_window / 9.0
    variance = np.clip((sum_sq_window / 9.0) - (mean_window * mean_window), 0.0, None)
    return variance


def build_cost_layers(z_real: np.ndarray) -> CostLayers:
    """Builds AYAP-2 E, S, G cost maps from real DEM matrix.

    D is dynamic per edge (grid/euclidean distance), so it is not stored as a map.
    """

    z_norm = normalize_01(z_real.astype(np.float64))
    grad_row, grad_col = np.gradient(z_norm)
    grad_mag = np.hypot(grad_row, grad_col)

    # E map base: global slope intensity from real DEM gradients.
    e_map = normalize_01(grad_mag)

    # S map: high friction where roughness is high and slope is still low.
    roughness = normalize_01(_local_variance_3x3(z_norm))
    low_slope = 1.0 - normalize_01(grad_mag)
    s_map = normalize_01(roughness * (0.35 + 0.65 * low_slope))

    # G map: lowland + shading proxy. 1=safe, 50=high soft-avoid cost.
    sun_azimuth = np.deg2rad(315.0)
    sun_elevation = np.deg2rad(15.0)

    slope_angle = np.pi / 2.0 - np.arctan(np.hypot(grad_col, grad_row))
    aspect = np.arctan2(-grad_row, grad_col + 1e-12)
    hillshade = (
        np.sin(sun_elevation) * np.sin(slope_angle)
        + np.cos(sun_elevation) * np.cos(slope_angle) * np.cos(sun_azimuth - aspect)
    )
    hillshade = normalize_01(hillshade)

    p40 = float(np.percentile(z_norm, 40.0))
    lowland_depth = np.clip(
        (p40 - z_norm) / max(p40 - float(np.min(z_norm)), 1e-9),
        0.0,
        1.0,
    )

    shadow_score = normalize_01((0.72 * lowland_depth) + (0.28 * (1.0 - hillshade)))
    g_map = 1.0 + 49.0 * np.power(shadow_score, 1.4)

    return CostLayers(
        z_norm=z_norm.astype(np.float32),
        e_map=e_map.astype(np.float32),
        s_map=s_map.astype(np.float32),
        g_map=g_map.astype(np.float32),
    )


def euclidean(a: GridPoint, b: GridPoint) -> float:
    """Computes euclidean distance between two grid points."""

    return float(sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


def _asymmetric_e_cost(
    current: GridPoint,
    neighbor: GridPoint,
    distance: float,
    layers: CostLayers,
) -> float:
    """Computes asymmetric U-curve slope cost from real DEM gradients.

    - Mild downhill gets a small reward (lower cost)
    - Steep uphill gets exponential penalty
    - Very steep downhill also gets penalty for stability risk
    """

    z_current = float(layers.z_norm[current])
    z_neighbor = float(layers.z_norm[neighbor])
    signed_grade = (z_neighbor - z_current) / max(distance, 1e-9)

    uphill = max(signed_grade, 0.0)
    downhill = max(-signed_grade, 0.0)
    local_grad = 0.5 * (float(layers.e_map[current]) + float(layers.e_map[neighbor]))

    uphill_penalty = float(np.expm1(7.5 * uphill))
    mild_downhill_reward = float(-0.18 * np.exp(-((downhill - 0.05) ** 2) / (2.0 * 0.03**2)))
    steep_downhill_penalty = 4.0 * max(downhill - 0.18, 0.0) ** 2

    e_value = local_grad + uphill_penalty + steep_downhill_penalty + mild_downhill_reward
    return max(0.01, float(e_value))


def _transition_cost(
    current: GridPoint,
    neighbor: GridPoint,
    profile: RouteProfile,
    layers: CostLayers,
) -> float:
    """Computes one transition cost with AYAP-2 4D equation.

    C_total = [Wd*D + We*E + Ws*S + Wg*G] * 1000
    """

    d_value = euclidean(current, neighbor)
    e_value = _asymmetric_e_cost(current=current, neighbor=neighbor, distance=d_value, layers=layers)
    s_value = 0.5 * (float(layers.s_map[current]) + float(layers.s_map[neighbor]))
    g_value = 0.5 * (float(layers.g_map[current]) + float(layers.g_map[neighbor]))

    total_cost = (
        (profile.wd * d_value)
        + (profile.we * e_value)
        + (profile.ws * s_value)
        + (profile.wg * g_value)
    ) * 1000.0
    return float(total_cost)


def _heuristic(point: GridPoint, goal: GridPoint, profile: RouteProfile) -> float:
    """Admissible heuristic using distance term only."""

    return profile.wd * euclidean(point, goal) * 1000.0


def _reconstruct_path(came_from: dict[GridPoint, GridPoint], goal: GridPoint) -> list[GridPoint]:
    """Reconstructs path from predecessor map."""

    path = [goal]
    cursor = goal
    while cursor in came_from:
        cursor = came_from[cursor]
        path.append(cursor)
    path.reverse()
    return path


def astar_8_connected(
    z_real: np.ndarray,
    start: GridPoint,
    goal: GridPoint,
    profile: RouteProfile,
    layers: CostLayers,
) -> tuple[list[GridPoint], float]:
    """Runs heapq-based 8-direction true A* on DEM grid."""

    rows, cols = z_real.shape

    for name, point in (("Start", start), ("Goal", goal)):
        row, col = point
        if not (0 <= row < rows and 0 <= col < cols):
            raise ValueError(f"{name} point {point} is outside DEM bounds {z_real.shape}.")

    if start == goal:
        return [start], 0.0

    open_heap: list[tuple[float, GridPoint]] = []
    heappush(open_heap, (_heuristic(start, goal, profile), start))

    came_from: dict[GridPoint, GridPoint] = {}
    g_score: dict[GridPoint, float] = {start: 0.0}
    closed: set[GridPoint] = set()

    while open_heap:
        _, current = heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            return _reconstruct_path(came_from, goal), float(g_score[goal])

        closed.add(current)
        current_g = g_score[current]
        base_row, base_col = current

        for d_row, d_col in _NEIGHBOR_OFFSETS:
            n_row = base_row + d_row
            n_col = base_col + d_col
            if n_row < 0 or n_row >= rows or n_col < 0 or n_col >= cols:
                continue

            neighbor = (n_row, n_col)
            if neighbor in closed:
                continue

            step_cost = _transition_cost(current=current, neighbor=neighbor, profile=profile, layers=layers)
            tentative_g = current_g + step_cost

            if tentative_g >= g_score.get(neighbor, float("inf")):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            f_score = tentative_g + _heuristic(neighbor, goal, profile)
            heappush(open_heap, (f_score, neighbor))

    raise RuntimeError("No feasible path found between start and goal.")


def _uv_to_grid(uv_point: tuple[float, float], shape: tuple[int, int]) -> GridPoint:
    """Converts normalized UV point to DEM grid index with clamping."""

    rows, cols = shape
    if rows <= 0 or cols <= 0:
        raise ValueError(f"Invalid DEM shape: {shape}")

    u = float(np.clip(uv_point[0], 0.0, 1.0))
    v = float(np.clip(uv_point[1], 0.0, 1.0))
    row = int(round(u * (rows - 1)))
    col = int(round(v * (cols - 1)))
    return (row, col)


def resolve_start_goal(shape: tuple[int, int]) -> tuple[GridPoint, GridPoint, bool]:
    """Resolves requested start/goal from UV coordinates."""

    rows, cols = shape
    if rows <= 0 or cols <= 0:
        raise ValueError(f"Invalid DEM shape: {shape}")

    start = _uv_to_grid(REQUESTED_START_UV, shape)
    goal = _uv_to_grid(REQUESTED_GOAL_UV, shape)

    if start == goal and (rows > 1 or cols > 1):
        goal = (rows - 1, 0)

    # True when rounding/clamping changes exact floating-point projection.
    scaled = (
        REQUESTED_START_UV[0] * (rows - 1) != float(start[0])
        or REQUESTED_START_UV[1] * (cols - 1) != float(start[1])
        or REQUESTED_GOAL_UV[0] * (rows - 1) != float(goal[0])
        or REQUESTED_GOAL_UV[1] * (cols - 1) != float(goal[1])
    )
    return start, goal, scaled


def _plot_flagpole(
    axis: Axes3D,
    z_surface: np.ndarray,
    point: GridPoint,
    label: str,
    marker_color: str,
    marker_style: str,
    pole_height: float,
) -> None:
    """Draws one vertical pin and marker above terrain."""

    row, col = point
    x = float(col)
    y = float(row)
    z0 = float(z_surface[row, col])
    z1 = z0 + pole_height

    axis.plot(
        [x, x],
        [y, y],
        [z0, z1],
        color="black",
        linewidth=3.0,
        zorder=1000,
    )
    axis.scatter(
        [x],
        [y],
        [z1],
        s=190,
        c=marker_color,
        marker=marker_style,
        edgecolors="black",
        linewidths=1.6,
        depthshade=False,
        zorder=1000,
    )
    axis.text(
        x + 2.0,
        y + 2.0,
        z1 + (0.06 * pole_height),
        label,
        color="black",
        fontsize=10,
        fontweight="bold",
        bbox={"facecolor": "white", "edgecolor": "black", "alpha": 0.93},
        zorder=1000,
    )


def plot_routes_3d(
    z_real: np.ndarray,
    start: GridPoint,
    goal: GridPoint,
    route_results: list[RouteResult],
    save_path: Path | None = None,
    z_exaggeration: float = 2.5,
    view_elev: float = 35.0,
    view_azim: float = 225.0,
    save_dpi: int = 300,
    surface_cmap: str = "terrain",
) -> None:
    """Plots real DEM surface and route overlays (matches ``plot.py`` / ``plot_dem_surface`` style).

    Planning uses raw ``z_real``; only the figure applies ``z_exaggeration`` for display,
    consistent with ``src/visualization.py`` DEMVisualizer defaults.
    """

    x_grid, y_grid = build_xy_mesh(z_real.shape)
    z_grid = z_real.astype(np.float64) * float(z_exaggeration)

    figure = plt.figure(figsize=(12, 9))
    axis: Axes3D = figure.add_subplot(111, projection="3d")
    surface = axis.plot_surface(
        x_grid,
        y_grid,
        z_grid,
        cmap=surface_cmap,
        linewidth=0,
        antialiased=True,
        alpha=0.95,
        zorder=1,
    )
    figure.colorbar(surface, shrink=0.63, pad=0.08, label="Elevation (scaled)")

    z_span = float(np.nanmax(z_grid) - np.nanmin(z_grid))
    path_offset = max(0.025 * z_span, 0.08)
    pole_height = max(0.18 * z_span, path_offset * 4.0, 1.0)

    for result in route_results:
        if not result.path:
            continue

        row_array = np.array([point[0] for point in result.path], dtype=np.int32)
        col_array = np.array([point[1] for point in result.path], dtype=np.int32)
        path_z = z_grid[row_array, col_array] + path_offset

        label = f"{result.profile.name} | C={result.cumulative_cost:,.0f}"
        axis.plot(
            col_array.astype(np.float64),
            row_array.astype(np.float64),
            path_z.astype(np.float64),
            color=result.profile.color,
            linestyle=result.profile.linestyle,
            linewidth=result.profile.linewidth,
            alpha=0.98,
            label=label,
            zorder=500,
        )

    _plot_flagpole(
        axis=axis,
        z_surface=z_grid,
        point=start,
        label="A",
        marker_color="red",
        marker_style="v",
        pole_height=pole_height,
    )
    _plot_flagpole(
        axis=axis,
        z_surface=z_grid,
        point=goal,
        label="B",
        marker_color="lime",
        marker_style="D",
        pole_height=pole_height,
    )

    legend = axis.legend(
        loc="upper right",
        title="Gercek Kumulatif Maliyet",
        facecolor="black",
        edgecolor="white",
        framealpha=0.9,
        fontsize=9,
    )
    legend.get_title().set_color("white")
    for text in legend.get_texts():
        text.set_color("white")

    axis.set_title("TUA AYAP-2 | Real DEM Uzerinde A* 4D Rota Simulasyonu")
    axis.set_xlabel("Column")
    axis.set_ylabel("Row")
    axis.set_zlabel("Elevation (scaled)")
    axis.view_init(elev=float(view_elev), azim=float(view_azim))

    figure.tight_layout()

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(save_path, dpi=int(save_dpi), bbox_inches="tight")


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for source selection and plotting."""

    parser = argparse.ArgumentParser(
        description="AYAP-2 A* 4D route planner over real DEM data."
    )
    parser.add_argument("--dem-npy", type=str, default=None, help="Path to .npy/.npz DEM matrix.")
    parser.add_argument("--dem-image", type=str, default=None, help="Path to grayscale DEM image.")
    parser.add_argument("--dem-tif", type=str, default=None, help="Path to real DEM GeoTIFF.")
    parser.add_argument(
        "--tif-window-size",
        type=int,
        default=1200,
        help="Center crop window size for GeoTIFF loading (match src/plot.py for consistent visuals).",
    )
    parser.add_argument(
        "--tif-downsample",
        type=int,
        default=2,
        help="GeoTIFF downsample factor; higher is faster but coarser (default matches src/plot.py).",
    )
    parser.add_argument(
        "--z-exaggeration",
        type=float,
        default=2.5,
        help="Vertical scale for 3D display only (same default as src/plot.py).",
    )
    parser.add_argument(
        "--view-elev",
        type=float,
        default=35.0,
        help="3D camera elevation (degrees).",
    )
    parser.add_argument(
        "--view-azim",
        type=float,
        default=225.0,
        help="3D camera azimuth (degrees).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI when saving the output figure.",
    )
    parser.add_argument(
        "--allow-dummy",
        action="store_true",
        help="Allow deterministic dummy DEM fallback when real source is unavailable.",
    )
    parser.add_argument(
        "--save",
        type=str,
        default="routes_output.png",
        help="Output image path for 3D plot.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Create figure and save it without opening a GUI window.",
    )
    return parser.parse_args()


def run() -> int:
    """Executes full AYAP-2 route simulation pipeline."""

    args = parse_args()

    z_real = load_real_dem(
        dem_npy=args.dem_npy,
        dem_image=args.dem_image,
        dem_tif=args.dem_tif,
        tif_window_size=args.tif_window_size,
        tif_downsample=args.tif_downsample,
        allow_dummy=args.allow_dummy,
    )

    layers = build_cost_layers(z_real)
    start, goal, scaled = resolve_start_goal(z_real.shape)

    profiles = [
        RouteProfile(
            name="Optimal Path (Balanced 4D)",
            wd=1.4,
            we=4.0,
            ws=1.6,
            wg=0.22,
            color="gold",
            linestyle="-",
            linewidth=3.0,
        ),
        RouteProfile(
            name="Shortest Distance (High Slope)",
            wd=9.5,
            we=0.25,
            ws=0.05,
            wg=0.01,
            color="cyan",
            linestyle="--",
            linewidth=2.2,
        ),
        RouteProfile(
            name="Shadow/Thermal Safe",
            wd=0.9,
            we=1.2,
            ws=0.5,
            wg=6.5,
            color="magenta",
            linestyle=":",
            linewidth=2.2,
        ),
    ]

    route_results: list[RouteResult] = []
    for profile in profiles:
        path, cumulative_cost = astar_8_connected(
            z_real=z_real,
            start=start,
            goal=goal,
            profile=profile,
            layers=layers,
        )
        route_results.append(
            RouteResult(
                profile=profile,
                path=path,
                cumulative_cost=cumulative_cost,
            )
        )

    save_path = Path(args.save).expanduser().resolve() if args.save else None
    plot_routes_3d(
        z_real=z_real,
        start=start,
        goal=goal,
        route_results=route_results,
        save_path=save_path,
        z_exaggeration=float(args.z_exaggeration),
        view_elev=float(args.view_elev),
        view_azim=float(args.view_azim),
        save_dpi=int(args.dpi),
    )

    print(f"DEM shape: {z_real.shape}")
    print(f"Requested A (UV): {REQUESTED_START_UV} -> Used A: {start}")
    print(f"Requested B (UV): {REQUESTED_GOAL_UV} -> Used B: {goal}")
    if scaled:
        print("[INFO] Start/goal coordinates were scaled to fit DEM bounds.")

    for result in route_results:
        print(
            f"{result.profile.name}: "
            f"steps={len(result.path)}, cumulative_cost={result.cumulative_cost:.3f}"
        )

    if save_path is not None:
        print(f"Saved figure: {save_path}")

    if args.no_show:
        plt.close("all")
    else:
        plt.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
