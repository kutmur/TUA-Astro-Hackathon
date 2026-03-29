"""AYAP-2 A* Rota Planlama Motoru.

Bu modül `heapq` tabanlı gerçek 8-yönlü A* algoritmasını içerir.

Geçiş maliyeti formülü (AYAP-2 4D Cost Denklemi):
    C_toplam = [ (W_d × D) + (W_e × E) + (W_s × S) + (W_g × G) ] × 1000

Burada:
    D = Öklid mesafesi (grid biriminde)
    E = Asimetrik eğim maliyeti (yokuş yukarı ceza, hafif iniş ödül)
    S = Sürtünme / regolit maliyeti (komşu ortalaması)
    G = Gölge / termal risk maliyeti (komşu ortalaması)

Kullanım:
    from planner import astar_search, RouteResult
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import sqrt

import numpy as np

try:
    from .config import RouteProfile
    from .dem_loader import CostLayers
except ImportError:
    from config import RouteProfile
    from dem_loader import CostLayers

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
    """İki grid noktası arasındaki Öklid mesafesini hesaplar."""
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _asymmetric_slope_cost(
    current: GridPoint,
    neighbor: GridPoint,
    distance: float,
    layers: CostLayers,
) -> float:
    """Asimetrik U-eğrili eğim maliyeti.

    Davranış:
      • Hafif iniş → küçük ödül (düşük maliyet)
      • Dik yokuş yukarı → üstel ceza
      • Çok dik iniş → stabilite riski cezası
    """
    z_cur = float(layers.z_norm[current])
    z_nbr = float(layers.z_norm[neighbor])
    signed_grade = (z_nbr - z_cur) / max(distance, 1e-9)

    uphill = max(signed_grade, 0.0)
    downhill = max(-signed_grade, 0.0)

    local_grad = 0.5 * (
        float(layers.e_map[current]) + float(layers.e_map[neighbor])
    )

    uphill_penalty = float(np.expm1(7.5 * uphill))
    mild_downhill_reward = float(
        -0.18 * np.exp(-((downhill - 0.05) ** 2) / (2.0 * 0.03 ** 2))
    )
    steep_downhill_penalty = 4.0 * max(downhill - 0.18, 0.0) ** 2

    e_value = local_grad + uphill_penalty + steep_downhill_penalty + mild_downhill_reward
    return max(0.01, float(e_value))


def _transition_cost(
    current: GridPoint,
    neighbor: GridPoint,
    profile: RouteProfile,
    layers: CostLayers,
) -> float:
    """AYAP-2 4D geçiş maliyetini hesaplar.

    C_toplam = (W_d×D + W_e×E + W_s×S + W_g×G) × 1000
    """
    d_val = _euclidean(current, neighbor)
    e_val = _asymmetric_slope_cost(current, neighbor, d_val, layers)
    s_val = 0.5 * (float(layers.s_map[current]) + float(layers.s_map[neighbor]))
    g_val = 0.5 * (float(layers.g_map[current]) + float(layers.g_map[neighbor]))

    total = (
        (profile.wd * d_val)
        + (profile.we * e_val)
        + (profile.ws * s_val)
        + (profile.wg * g_val)
    ) * 1000.0

    return float(total)


def _heuristic(point: GridPoint, goal: GridPoint, profile: RouteProfile) -> float:
    """A* için kabul edilebilir (admissible) sezgisel: ağırlıklı Öklid mesafesi."""
    return profile.wd * _euclidean(point, goal) * 1000.0


def _sliding_window_density(mask: np.ndarray, radius: int) -> np.ndarray:
    """Binary mask için kayar pencere doluluk oranı üretir.

    Bu fonksiyon, Hiyerarşik Kayar Pencere yaklaşımında her pikselin
    çevresindeki engel yoğunluğunu [0, 1] aralığında verir.
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

    Böylece A* geçiş maliyeti kaya bölgelerinden dinamik şekilde uzaklaştırılır.
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
) -> RouteResult:
    """8-yönlü heapq tabanlı A* araması çalıştırır.

    Args:
        shape:   DEM matris boyutu (n_rows, n_cols).
        start:   Başlangıç grid noktası (row, col).
        goal:    Hedef grid noktası (row, col).
        profile: Maliyet ağırlıkları ve çizim stili.
        layers:  Türetilmiş maliyet katmanları.

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

            step_cost = _transition_cost(current, neighbor, profile, layers)
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
