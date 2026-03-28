from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

GridPoint = Tuple[int, int]


@dataclass(frozen=True)
class AStarConfig:
    w_distance: float = 1.0
    w_slope: float = 4.0
    w_energy: float = 0.15
    max_slope_deg: float = 35.0
    traverse_energy_per_meter: float = 1.0
    ascent_energy_per_meter: float = 4.0
    descent_recovery: float = 0.25
    allow_diagonal: bool = True


@dataclass(frozen=True)
class PathResult:
    path: List[GridPoint]
    total_cost: float
    total_distance_m: float
    total_energy: float
    max_segment_slope_deg: float
    expanded_nodes: int


def _validate_point(point: GridPoint, shape: Tuple[int, int], name: str) -> None:
    row, col = point
    if row < 0 or row >= shape[0] or col < 0 or col >= shape[1]:
        raise ValueError(f"{name} point {point} is outside DEM bounds {shape}.")


def _neighbors(point: GridPoint, shape: Tuple[int, int], allow_diagonal: bool) -> List[GridPoint]:
    row, col = point
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if allow_diagonal:
        offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])

    result: List[GridPoint] = []
    for dr, dc in offsets:
        nr = row + dr
        nc = col + dc
        if 0 <= nr < shape[0] and 0 <= nc < shape[1]:
            result.append((nr, nc))
    return result


def _segment_metrics(
    dem: np.ndarray,
    current: GridPoint,
    neighbor: GridPoint,
    resolution: Tuple[float, float],
) -> Tuple[float, float, float]:
    r0, c0 = current
    r1, c1 = neighbor

    dz = float(dem[r1, c1] - dem[r0, c0])
    dx = float((c1 - c0) * resolution[0])
    dy = float((r1 - r0) * resolution[1])

    horizontal_distance = math.hypot(dx, dy)
    if horizontal_distance <= 0.0:
        return 0.0, 0.0, 0.0

    slope_deg = math.degrees(math.atan(abs(dz) / horizontal_distance))
    return horizontal_distance, dz, slope_deg


def _energy_cost(horizontal_distance: float, dz: float, cfg: AStarConfig) -> float:
    energy = horizontal_distance * cfg.traverse_energy_per_meter

    if dz > 0:
        energy += dz * cfg.ascent_energy_per_meter
    elif dz < 0:
        energy -= abs(dz) * cfg.ascent_energy_per_meter * cfg.descent_recovery

    minimum_energy = 0.1 * horizontal_distance * cfg.traverse_energy_per_meter
    return max(minimum_energy, energy)


def _movement_cost(
    horizontal_distance: float,
    slope_deg: float,
    energy: float,
    cfg: AStarConfig,
) -> float:
    slope_norm = slope_deg / max(cfg.max_slope_deg, 1e-9)
    slope_penalty = horizontal_distance * (slope_norm**2)

    return (
        cfg.w_distance * horizontal_distance
        + cfg.w_slope * slope_penalty
        + cfg.w_energy * energy
    )


def _heuristic(
    current: GridPoint,
    goal: GridPoint,
    resolution: Tuple[float, float],
    cfg: AStarConfig,
) -> float:
    dr = abs(goal[0] - current[0])
    dc = abs(goal[1] - current[1])
    distance = math.hypot(dr * resolution[1], dc * resolution[0])
    return cfg.w_distance * distance


def _reconstruct_path(came_from: Dict[GridPoint, GridPoint], goal: GridPoint) -> List[GridPoint]:
    path = [goal]
    current = goal
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def plan_path_astar(
    dem: np.ndarray,
    start: GridPoint,
    goal: GridPoint,
    resolution: Tuple[float, float] = (1.0, 1.0),
    config: AStarConfig | None = None,
) -> PathResult:
    """
    Plan a path on a DEM grid with A*.

    Cost model includes:
    - geometric distance,
    - slope penalty,
    - energy cost (traversal + climbing/descending).
    """
    cfg = config or AStarConfig()
    dem = np.asarray(dem, dtype=np.float32)

    if dem.ndim != 2:
        raise ValueError("DEM must be a 2D NumPy array.")
    if resolution[0] <= 0 or resolution[1] <= 0:
        raise ValueError("Resolution values must be positive.")

    _validate_point(start, dem.shape, "start")
    _validate_point(goal, dem.shape, "goal")

    if np.isnan(dem[start]):
        raise ValueError(f"Start point {start} is nodata/NaN.")
    if np.isnan(dem[goal]):
        raise ValueError(f"Goal point {goal} is nodata/NaN.")

    if start == goal:
        return PathResult(
            path=[start],
            total_cost=0.0,
            total_distance_m=0.0,
            total_energy=0.0,
            max_segment_slope_deg=0.0,
            expanded_nodes=0,
        )

    open_heap: List[Tuple[float, int, GridPoint]] = []
    tie = 0

    g_score: Dict[GridPoint, float] = {start: 0.0}
    energy_score: Dict[GridPoint, float] = {start: 0.0}
    max_slope_score: Dict[GridPoint, float] = {start: 0.0}
    came_from: Dict[GridPoint, GridPoint] = {}
    closed = set()

    heapq.heappush(open_heap, (_heuristic(start, goal, resolution, cfg), tie, start))

    expanded_nodes = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)

        if current in closed:
            continue

        expanded_nodes += 1
        if current == goal:
            break

        closed.add(current)

        for neighbor in _neighbors(current, dem.shape, cfg.allow_diagonal):
            if neighbor in closed:
                continue
            if np.isnan(dem[neighbor]):
                continue

            horizontal_distance, dz, slope_deg = _segment_metrics(dem, current, neighbor, resolution)

            if slope_deg > cfg.max_slope_deg:
                continue

            edge_energy = _energy_cost(horizontal_distance, dz, cfg)
            edge_cost = _movement_cost(horizontal_distance, slope_deg, edge_energy, cfg)
            tentative_g = g_score[current] + edge_cost

            if tentative_g < g_score.get(neighbor, math.inf):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                energy_score[neighbor] = energy_score[current] + edge_energy
                max_slope_score[neighbor] = max(max_slope_score[current], slope_deg)

                tie += 1
                f_score = tentative_g + _heuristic(neighbor, goal, resolution, cfg)
                heapq.heappush(open_heap, (f_score, tie, neighbor))

    if goal not in came_from:
        raise RuntimeError(
            "Path could not be found. Try a larger crop, different start/goal, "
            "or a less strict max_slope_deg."
        )

    path = _reconstruct_path(came_from, goal)

    total_distance = 0.0
    for i in range(1, len(path)):
        horizontal_distance, _, _ = _segment_metrics(dem, path[i - 1], path[i], resolution)
        total_distance += horizontal_distance

    return PathResult(
        path=path,
        total_cost=g_score[goal],
        total_distance_m=total_distance,
        total_energy=energy_score[goal],
        max_segment_slope_deg=max_slope_score[goal],
        expanded_nodes=expanded_nodes,
    )


def compute_slope_map(dem: np.ndarray, resolution: Tuple[float, float]) -> np.ndarray:
    """
    Compute per-cell slope map in degrees from a DEM array.
    """
    dem = np.asarray(dem, dtype=np.float32)
    if dem.ndim != 2:
        raise ValueError("DEM must be a 2D array.")
    if np.all(np.isnan(dem)):
        raise ValueError("DEM contains only NaN values.")

    filled = dem.copy()
    nan_mask = np.isnan(filled)
    if np.any(nan_mask):
        fill_value = float(np.nanmedian(filled))
        filled[nan_mask] = fill_value

    grad_y, grad_x = np.gradient(filled, resolution[1], resolution[0])
    slope = np.degrees(np.arctan(np.hypot(grad_x, grad_y))).astype(np.float32)

    if np.any(nan_mask):
        slope[nan_mask] = np.nan

    return slope
