"""AYAP-2 A* Rota Planlama Motoru.

Bu modül `heapq` tabanlı gerçek 8-yönlü A* algoritmasını içerir.

Geçiş maliyeti formülü (AYAP-2 4D Cost Denklemi):
    C_toplam = [ (W_d × D) + (W_e × E) + (W_s × S) + (W_g × G) ] × 1000

Lunar Physics Implementation:
    D = Öklid mesafesi (kinematik enerji proxy'si)
    E = Asimetrik U-eğrili eğim maliyeti:
        • Düz (θ ≈ 0): Temel maliyet
        • Hafif iniş (θ < 0): Küçük ödül (rejeneratif frenleme)
        • Dik yokuş yukarı (θ >> 0): Üstel ceza
        • θ > θ_max: Maliyet = 10,000 (pratik sonsuz, geçilemez)
    S = Yüzey sürtünmesi / regolit pürüzlülük proxy'si
    G = Gölge / termal risk (YUMUŞAK kaçınma, sonsuz duvar DEĞİL)

Hardware Constraint (RAD750):
    The full-grid A* here assumes the DEM fits in RAM. For flight hardware,
    use hierarchical sliding window: coarse global plan + local 100x100 window.

Kullanım:
    from planner import astar_search, RouteResult
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from heapq import heappop, heappush
from math import atan2, sqrt

import numpy as np

try:
    from .config import (
        THETA_MAX_COST,
        THETA_MAX_RAD,
        RouteProfile,
        get_dynamic_wg,
    )
    from .dem_loader import CostLayers
except ImportError:
    from config import (
        THETA_MAX_COST,
        THETA_MAX_RAD,
        RouteProfile,
        get_dynamic_wg,
    )
    from dem_loader import CostLayers

# ─────────────────────────────────────────────────
# Logger Configuration
# ─────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────
# Tip Tanımları
# ─────────────────────────────────────────────────
GridPoint = tuple[int, int]

# 8 yönlü komşuluk ofsetleri
_NEIGHBOR_OFFSETS: tuple[tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1),
)


# ─────────────────────────────────────────────────
# Veri Yapıları
# ─────────────────────────────────────────────────

@dataclass(frozen=True)
class RouteResult:
    """Tek bir A* çalışmasının sonucu.

    Attributes:
        profile: Kullanılan rota profili.
        path: Başlangıçtan hedefe grid noktaları listesi.
        cumulative_cost: Toplam kümülatif maliyet.
    """

    profile: RouteProfile
    path: list[GridPoint]
    cumulative_cost: float


# ─────────────────────────────────────────────────
# Mesafe ve Maliyet Hesaplama
# ─────────────────────────────────────────────────

def _euclidean(a: GridPoint, b: GridPoint) -> float:
    """İki grid noktası arasındaki Öklid mesafesini hesaplar.

    Diagonal moves use √2 ≈ 1.414 for correct 8-connectivity cost.
    """
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _compute_slope_angle(
    current: GridPoint,
    neighbor: GridPoint,
    layers: CostLayers,
    cell_size: float = 1.0,
) -> float:
    """Computes the actual slope angle in radians between two cells.

    Lunar Physics:
        Slope angle determines rover stability. Angles beyond θ_max
        risk tipping the rover due to high center of gravity.

    Args:
        current: Source grid point.
        neighbor: Target grid point.
        layers: Cost layers containing normalized elevation.
        cell_size: Physical size of one grid cell in meters.

    Returns:
        Slope angle in radians (positive = uphill, negative = downhill).
    """
    z_cur = float(layers.z_norm[current])
    z_nbr = float(layers.z_norm[neighbor])

    # Horizontal distance in grid units (√2 for diagonals)
    horiz_dist = _euclidean(current, neighbor) * cell_size

    # Vertical change (normalized, so scale appropriately)
    # Note: z_norm is [0,1], representing full elevation range
    dz = z_nbr - z_cur

    # atan2 gives signed angle: positive = uphill, negative = downhill
    return atan2(dz, horiz_dist)


def _asymmetric_slope_cost(
    current: GridPoint,
    neighbor: GridPoint,
    distance: float,
    layers: CostLayers,
) -> float:
    """Asimetrik U-eğrili eğim maliyeti hesaplar.

    Lunar Physics Implementation:
        • Hafif iniş → küçük ödül (rejeneratif frenleme potansiyeli)
        • Dik yokuş yukarı → üstel ceza (motor yükü, enerji tüketimi)
        • Çok dik iniş → stabilite riski cezası
        • θ > θ_max → THETA_MAX_COST (pratik sonsuz, tipping riski)

    The asymmetric U-curve models:
        - Flat terrain: baseline traversal cost
        - Mild downhill: slight energy recovery (regenerative braking)
        - Steep uphill: exponential penalty (motor strain, battery drain)
        - Very steep downhill: stability penalty (rollover risk)
        - Beyond θ_max: effectively impassable (10,000 cost)
    """
    z_cur = float(layers.z_norm[current])
    z_nbr = float(layers.z_norm[neighbor])
    signed_grade = (z_nbr - z_cur) / max(distance, 1e-9)

    # Check θ_max threshold for tipping safety
    slope_angle = abs(atan2(z_nbr - z_cur, distance))
    if slope_angle > THETA_MAX_RAD:
        logger.debug(
            "Slope %.2f° exceeds θ_max at %s→%s, applying max cost",
            slope_angle * 180 / 3.14159,
            current,
            neighbor,
        )
        return THETA_MAX_COST

    uphill = max(signed_grade, 0.0)
    downhill = max(-signed_grade, 0.0)

    # Local gradient from precomputed E-map (average of both cells)
    local_grad = 0.5 * (
        float(layers.e_map[current]) + float(layers.e_map[neighbor])
    )

    # Exponential uphill penalty: motor load increases exponentially
    uphill_penalty = float(np.expm1(7.5 * uphill))

    # Mild downhill reward: regenerative braking opportunity
    # Gaussian centered at 5% grade, σ=3%
    mild_downhill_reward = float(
        -0.18 * np.exp(-((downhill - 0.05) ** 2) / (2.0 * 0.03 ** 2))
    )

    # Steep downhill penalty: stability risk beyond 18% grade
    steep_downhill_penalty = 4.0 * max(downhill - 0.18, 0.0) ** 2

    e_value = local_grad + uphill_penalty + steep_downhill_penalty + mild_downhill_reward
    return max(0.01, float(e_value))


def _transition_cost(
    current: GridPoint,
    neighbor: GridPoint,
    profile: RouteProfile,
    layers: CostLayers,
    battery_soc: float | None = None,
) -> float:
    """AYAP-2 4D geçiş maliyetini hesaplar.

    Full Cost Equation:
        C_total = (W_d×D + W_e×E + W_s×S + W_g×G) × 1000

    Args:
        current: Source grid point.
        neighbor: Target grid point.
        profile: Route profile with base weights.
        layers: Precomputed cost layers.
        battery_soc: Battery state-of-charge (0-100%) for dynamic W_g.
                     If None, uses profile's base wg (no survival override).

    Returns:
        Total transition cost (float).
    """
    d_val = _euclidean(current, neighbor)
    e_val = _asymmetric_slope_cost(current, neighbor, d_val, layers)

    # S and G use average of both cells (smooth transition)
    s_val = 0.5 * (float(layers.s_map[current]) + float(layers.s_map[neighbor]))
    g_val = 0.5 * (float(layers.g_map[current]) + float(layers.g_map[neighbor]))

    # Use profile's base W_g unless battery SoC triggers survival mode
    if battery_soc is not None:
        effective_wg = get_dynamic_wg(battery_soc, profile.wg)
    else:
        effective_wg = profile.wg

    total = (
        (profile.wd * d_val)
        + (profile.we * e_val)
        + (profile.ws * s_val)
        + (effective_wg * g_val)
    ) * 1000.0

    return float(total)


def _heuristic(point: GridPoint, goal: GridPoint, profile: RouteProfile) -> float:
    """A* için kabul edilebilir (admissible) sezgisel: ağırlıklı Öklid mesafesi.

    This heuristic is admissible because it only considers the distance
    component (D) which is the minimum possible cost to reach the goal.
    """
    return profile.wd * _euclidean(point, goal) * 1000.0


def _sliding_window_density(mask: np.ndarray, radius: int) -> np.ndarray:
    """Binary mask için kayar pencere doluluk oranı üretir.

    Bu fonksiyon, Hiyerarşik Kayar Pencere yaklaşımında her pikselin
    çevresindeki engel yoğunluğunu [0, 1] aralığında verir.

    Uses integral image for O(1) per-pixel computation regardless of radius.
    """
    binary = np.asarray(mask, dtype=np.float32)
    if binary.ndim != 2:
        raise ValueError(f"mask 2D olmalı, elde edilen boyut: {binary.shape}")

    if radius <= 0:
        return np.clip(binary, 0.0, 1.0)

    pad = int(radius)
    k = (2 * pad) + 1

    padded = np.pad(binary, ((pad, pad), (pad, pad)), mode="constant")
    integral = np.pad(padded, ((1, 0), (1, 0)), mode="constant")
    integral = integral.cumsum(axis=0).cumsum(axis=1)

    rows, cols = binary.shape
    # Integral image ile pencere toplamları
    window_sum = (
        integral[k:k + rows, k:k + cols]
        - integral[:rows, k:k + cols]
        - integral[k:k + rows, :cols]
        + integral[:rows, :cols]
    )
    area = float(k * k)
    return np.clip(window_sum / area, 0.0, 1.0).astype(np.float32)


def apply_rock_obstacle_penalty(
    layers: CostLayers,
    rock_mask: np.ndarray,
    *,
    target_layer: str = "s",
    direct_penalty: float = 35.0,
    near_penalty: float = 12.0,
    far_penalty: float = 4.0,
    near_radius: int = 2,
    far_radius: int = 5,
) -> CostLayers:
    """Kaya segmentasyon maskesini maliyet katmanlarına ceza olarak işler.

    Hiyerarşik Kayar Pencere mantığı:
      1) Kaya pikselinin kendisi: anında yüksek ceza (`direct_penalty`)
      2) Yakın pencere yoğunluğu: orta ceza (`near_penalty`)
      3) Uzak pencere yoğunluğu: düşük ceza (`far_penalty`)

    This creates a smooth gradient of avoidance around obstacles rather
    than hard binary walls, improving path quality and stability.
    """
    mask = np.asarray(rock_mask)
    if mask.ndim != 2:
        raise ValueError(f"rock_mask 2D olmalı, elde edilen boyut: {mask.shape}")
    if mask.shape != layers.s_map.shape:
        raise ValueError(
            "rock_mask ile maliyet katmanlarının şekli eşleşmiyor: "
            f"mask={mask.shape}, layers={layers.s_map.shape}"
        )

    mask_f = (mask > 0).astype(np.float32)

    near_density = _sliding_window_density(mask_f, radius=max(0, int(near_radius)))
    far_density = _sliding_window_density(mask_f, radius=max(0, int(far_radius)))

    penalty_map = (
        (direct_penalty * mask_f)
        + (near_penalty * near_density)
        + (far_penalty * far_density)
    ).astype(np.float32)

    target = target_layer.strip().lower()
    if target not in {"s", "e", "both"}:
        raise ValueError("target_layer yalnızca 's', 'e' veya 'both' olabilir.")

    new_s = layers.s_map.copy()
    new_e = layers.e_map.copy()

    if target in {"s", "both"}:
        new_s = new_s + penalty_map
    if target in {"e", "both"}:
        new_e = new_e + penalty_map

    return CostLayers(
        z_norm=layers.z_norm,
        e_map=new_e.astype(np.float32),
        s_map=new_s.astype(np.float32),
        g_map=layers.g_map,
    )


def _reconstruct_path(
    came_from: dict[GridPoint, GridPoint],
    goal: GridPoint,
) -> list[GridPoint]:
    """Öncül (predecessor) haritasından yolu geri oluşturur."""
    path: list[GridPoint] = [goal]
    cursor = goal
    while cursor in came_from:
        cursor = came_from[cursor]
        path.append(cursor)
    path.reverse()
    return path


# ─────────────────────────────────────────────────
# Ana A* Arama
# ─────────────────────────────────────────────────

def astar_search(
    shape: tuple[int, int],
    start: GridPoint,
    goal: GridPoint,
    profile: RouteProfile,
    layers: CostLayers,
    battery_soc: float | None = None,
) -> RouteResult:
    """8-yönlü heapq tabanlı A* araması çalıştırır.

    Implementation Details:
        - g(n): Full 4D cumulative cost from start to node n
        - h(n): Admissible heuristic (weighted Euclidean distance)
        - f(n) = g(n) + h(n): Total estimated cost through node n
        - 8-connectivity with √2 diagonal distance

    Lunar Physics Integration:
        - Asymmetric U-curve slope cost (E)
        - θ_max enforcement (tipping threshold)
        - Dynamic W_g based on battery SoC (survival mode)
        - Soft shadow avoidance (high cost, not infinite)

    Args:
        shape:   DEM matris boyutu (n_rows, n_cols).
        start:   Başlangıç grid noktası (row, col).
        goal:    Hedef grid noktası (row, col).
        profile: Maliyet ağırlıkları ve çizim stili.
        layers:  Türetilmiş maliyet katmanları.
        battery_soc: Battery state-of-charge (0-100%). If None, uses
                     profile's base wg (no survival mode override).

    Returns:
        RouteResult — yol, maliyet ve profil bilgisi.

    Raises:
        ValueError: Başlangıç/hedef sınır dışındaysa.
        RuntimeError: Geçerli yol bulunamazsa.
    """
    rows, cols = shape

    # ── Sınır Kontrolü ──
    for name, point in (("Başlangıç (A)", start), ("Hedef (B)", goal)):
        r, c = point
        if not (0 <= r < rows and 0 <= c < cols):
            raise ValueError(
                f"{name} noktası {point} DEM sınırları dışında: {shape}"
            )

    if start == goal:
        return RouteResult(profile=profile, path=[start], cumulative_cost=0.0)

    # ── A* Başlat ──
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
            path = _reconstruct_path(came_from, goal)
            return RouteResult(
                profile=profile,
                path=path,
                cumulative_cost=float(g_score[goal]),
            )

        closed.add(current)
        current_g = g_score[current]
        base_row, base_col = current

        for dr, dc in _NEIGHBOR_OFFSETS:
            nr, nc = base_row + dr, base_col + dc
            if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                continue

            neighbor: GridPoint = (nr, nc)
            if neighbor in closed:
                continue

            step_cost = _transition_cost(
                current, neighbor, profile, layers, battery_soc
            )
            tentative_g = current_g + step_cost

            if tentative_g >= g_score.get(neighbor, float("inf")):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            f_score = tentative_g + _heuristic(neighbor, goal, profile)
            heappush(open_heap, (f_score, neighbor))

    raise RuntimeError(
        f"A* araması başarısız: {start} → {goal} arasında geçerli yol bulunamadı."
    )
