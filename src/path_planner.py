"""Path planning skeleton ready for user-defined multi-objective cost."""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import sqrt
from typing import Protocol

import numpy as np

GridPoint = tuple[int, int]


@dataclass(frozen=True)
class CostContext:
    """Context passed to custom cost evaluators.

    Attributes:
        current: Current grid cell as (row, col).
        neighbor: Neighbor grid cell as (row, col).
        distance: Euclidean distance between current and neighbor cells.
        local_slope: Local slope proxy computed from elevation delta.
        solar_penalty: Placeholder for solar shadow penalty.
    """

    current: GridPoint
    neighbor: GridPoint
    distance: float
    local_slope: float
    solar_penalty: float


class CostFunction(Protocol):
    """Protocol for user-defined dynamic cost functions."""

    def __call__(self, context: CostContext) -> float:
        """Computes transition cost from one grid cell to another."""

        ...


@dataclass(order=True)
class PrioritizedNode:
    """Priority queue node used in path search."""

    priority: float
    point: GridPoint = field(compare=False)


def neighbors_8(point: GridPoint, shape: tuple[int, int]) -> list[GridPoint]:
    """Returns valid 8-connected neighbors for a grid point.

    Args:
        point: Input grid point.
        shape: Grid shape as (rows, cols).

    Returns:
        List of neighboring grid points.
    """

    row, col = point
    rows, cols = shape
    result: list[GridPoint] = []

    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            n_row = row + d_row
            n_col = col + d_col
            if 0 <= n_row < rows and 0 <= n_col < cols:
                result.append((n_row, n_col))

    return result


def euclidean_distance(a: GridPoint, b: GridPoint) -> float:
    """Computes Euclidean distance between two grid points."""

    return float(sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


def estimate_local_slope(elevation: np.ndarray, current: GridPoint, neighbor: GridPoint) -> float:
    """Estimates slope proxy from normalized local elevation difference."""

    dz = float(elevation[neighbor] - elevation[current])
    distance = max(euclidean_distance(current, neighbor), 1e-6)
    return abs(dz) / distance


def estimate_solar_penalty(_current: GridPoint, _neighbor: GridPoint) -> float:
    """Placeholder solar penalty computation.

    Replace this with mission-specific illumination or shadow analysis.
    """

    return 0.0


def reconstruct_path(came_from: dict[GridPoint, GridPoint], goal: GridPoint) -> list[GridPoint]:
    """Reconstructs a path from predecessor map."""

    path: list[GridPoint] = [goal]
    cursor = goal
    while cursor in came_from:
        cursor = came_from[cursor]
        path.append(cursor)
    path.reverse()
    return path


def _validate_point(point: GridPoint, shape: tuple[int, int], name: str) -> None:
    """Validates a point against grid bounds."""

    row, col = point
    rows, cols = shape
    if not (0 <= row < rows and 0 <= col < cols):
        raise ValueError(f"{name} point {point} is outside grid bounds {shape}.")


@dataclass
class AStarPathPlanner:
    """Object-oriented A* planner with pluggable transition-cost strategy."""

    elevation: np.ndarray
    cost_function: CostFunction

    def __post_init__(self) -> None:
        if self.elevation.ndim != 2:
            raise ValueError("Elevation grid must be 2-dimensional.")

    def _build_cost_context(self, current: GridPoint, neighbor: GridPoint) -> CostContext:
        """Builds one transition context consumed by user-defined cost formulas."""

        return CostContext(
            current=current,
            neighbor=neighbor,
            distance=euclidean_distance(current, neighbor),
            local_slope=estimate_local_slope(self.elevation, current, neighbor),
            solar_penalty=estimate_solar_penalty(current, neighbor),
        )

    def plan(self, start: GridPoint, goal: GridPoint) -> list[GridPoint]:
        """Plans one path from start to goal over the elevation grid."""

        _validate_point(start, self.elevation.shape, "Start")
        _validate_point(goal, self.elevation.shape, "Goal")

        if start == goal:
            return [start]

        open_heap: list[PrioritizedNode] = []
        heappush(open_heap, PrioritizedNode(priority=0.0, point=start))

        came_from: dict[GridPoint, GridPoint] = {}
        g_score: dict[GridPoint, float] = {start: 0.0}

        while open_heap:
            current = heappop(open_heap).point
            if current == goal:
                return reconstruct_path(came_from, goal)

            for neighbor in neighbors_8(current, self.elevation.shape):
                context = self._build_cost_context(current, neighbor)
                step_cost = float(self.cost_function(context))

                if not np.isfinite(step_cost) or step_cost < 0:
                    continue

                tentative_g = g_score[current] + step_cost
                if tentative_g >= g_score.get(neighbor, np.inf):
                    continue

                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                priority = tentative_g + euclidean_distance(neighbor, goal)
                heappush(open_heap, PrioritizedNode(priority=priority, point=neighbor))

        raise RuntimeError("No feasible path found for the selected DEM window.")


def plan_path(
    elevation: np.ndarray,
    start: GridPoint,
    goal: GridPoint,
    cost_function: CostFunction,
) -> list[GridPoint]:
    """Plans a path using a pluggable search skeleton.

    This function keeps planning flow and cost modeling separated so the exact
    user-provided multi-objective equation can be injected without edits to
    graph traversal logic.

    Args:
        elevation: DEM matrix used for terrain-aware planning.
        start: Start grid point `(row, col)`.
        goal: Goal grid point `(row, col)`.
        cost_function: User-provided cost function callback.

    Returns:
        Ordered path from start to goal.

    Raises:
        ValueError: If input shapes or points are invalid.
        RuntimeError: If no path is found.
    """

    planner = AStarPathPlanner(elevation=elevation, cost_function=cost_function)
    return planner.plan(start=start, goal=goal)


def path_length(path: list[GridPoint]) -> float:
    """Computes total Euclidean length of a path."""

    if len(path) < 2:
        return 0.0

    return float(
        sum(euclidean_distance(path[idx], path[idx + 1]) for idx in range(len(path) - 1))
    )
