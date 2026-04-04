"""AYAP-2 DEM Yükleme ve Maliyet Katmanı Hesaplama Modülü.

Bu modül:
  1. GeoTIFF (.tif) dosyasını `rasterio` ile okur.
  2. KESİNLİKLE agresif downsample yapmaz — min 120×120 çözünürlük korunur.
  3. Gerçek Z matrisinden E (eğim), S (sürtünme/regolit) ve G (gölge/termal)
     maliyet haritalarını türetir.

Lunar Physics Implementation:
    E (Slope): Gradient magnitude from DEM. Steep slopes drain battery
               (uphill) and risk tipping (both directions beyond θ_max).

    S (Soil/Friction): Lunar regolith varies in compaction. High local
               elevation variance indicates loose, unpacked material that
               increases wheel slip and traversal energy cost.

    G (Shadow/Thermal): Permanently shadowed regions (PSRs) near lunar
               poles can drop to -250°C. Rover electronics and batteries
               fail at these temperatures. This layer combines:
               - Hillshade from solar illumination angle
               - Depth below local mean (crater floors = cold traps)
               Uses SOFT avoidance (high cost, NOT infinite walls).

Hardware Constraint (RAD750):
    This module loads the full DEM into RAM. For flight hardware with
    ~128MB RAM limit, implement hierarchical sliding window:
    - Global layer: 50m/px coarse route planning
    - Local layer: 100×100px high-res window around rover position

Kullanım:
    from dem_loader import load_dem, build_cost_layers, CostLayers
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    from .config import PROJECT_CONFIG
except ImportError:
    from config import PROJECT_CONFIG

# ─────────────────────────────────────────────────
# Tip Tanımları
# ─────────────────────────────────────────────────
GridPoint = tuple[int, int]


# ─────────────────────────────────────────────────
# Veri Yapıları
# ─────────────────────────────────────────────────

@dataclass(frozen=True)
class CostLayers:
    """AYAP-2 4D maliyet denklemi için türetilmiş haritalar.

    These cost layers encode lunar terrain physics into numeric grids
    that the A* algorithm uses for path optimization.

    Attributes:
        z_norm: [0, 1] normalized elevation. Used for slope calculation
                during path transitions. Higher = peak, Lower = crater floor.
        e_map:  Slope intensity [0, 1]. Derived from terrain gradient.
                High values indicate steep terrain that drains battery
                (uphill) or risks instability (downhill beyond θ_max).
        s_map:  Surface friction / regolith roughness [0, 1]. Computed
                from local elevation variance. High values = loose soil
                that increases wheel slip and traversal energy.
        g_map:  Shadow/thermal risk [1.0, 50.0]. Composite of hillshade
                illumination and crater depth. High values = cold traps
                where electronics may fail. Uses soft avoidance, not
                infinite cost walls.
    """

    z_norm: np.ndarray
    e_map: np.ndarray
    s_map: np.ndarray
    g_map: np.ndarray


# ─────────────────────────────────────────────────
# İç Yardımcı Fonksiyonlar
# ─────────────────────────────────────────────────

def _normalize_01(values: np.ndarray) -> np.ndarray:
    """Sonlu matris değerlerini [0, 1] aralığına normalize eder."""
    v = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(v)
    if not np.any(finite):
        raise ValueError("Matris hiç sonlu değer içermiyor, normalizasyon başarısız.")
    v_min = float(np.nanmin(v[finite]))
    v_max = float(np.nanmax(v[finite]))
    span = max(v_max - v_min, 1e-9)
    out = (v - v_min) / span
    out[~finite] = 0.0
    return out


def _to_2d_float32(array: np.ndarray) -> np.ndarray:
    """Girdi dizisini sonlu değerlerle dolu 2D float32 DEM matrisine dönüştürür."""
    dem = np.asarray(array)
    if dem.ndim == 3:
        dem = dem[..., :3].mean(axis=2)
    if dem.ndim != 2:
        raise ValueError(f"DEM 2D olmalı, elde edilen boyut: {dem.shape}")
    dem = dem.astype(np.float32, copy=False)
    finite = np.isfinite(dem)
    if not np.any(finite):
        raise ValueError("DEM hiç sonlu değer içermiyor.")
    fill_value = float(np.nanmedian(dem[finite]))
    dem[~finite] = fill_value
    return dem


def _local_variance_3x3(field: np.ndarray) -> np.ndarray:
    """Computes 3×3 local variance map with edge padding.

    Lunar Physics Rationale:
        High local variance in elevation indicates heterogeneous terrain:
        - Rocky outcrops with varying boulder sizes
        - Loose regolith that hasn't been compacted by impacts
        - Crater rim rubble and ejecta deposits

        These areas increase wheel slip and traversal energy cost (S layer).
    """
    rows, cols = field.shape
    padded = np.pad(field, 1, mode="edge")
    sum_w = np.zeros((rows, cols), dtype=np.float64)
    sum_sq = np.zeros((rows, cols), dtype=np.float64)
    for dr in range(3):
        for dc in range(3):
            tile = padded[dr:dr + rows, dc:dc + cols]
            sum_w += tile
            sum_sq += tile * tile
    mean = sum_w / 9.0
    variance = (sum_sq / 9.0) - (mean * mean)
    return np.clip(variance, 0.0, None)


def _safe_downsample(
    raster_height: int,
    raster_width: int,
    requested_downsample: int,
) -> int:
    """Downsample faktörünü MIN_GRID_SIZE korumasıyla sınırlar.

    Asla min_grid_size'ın altına düşecek bir downsample faktörü döndürmez.
    """
    if requested_downsample < 1:
        return 1
    min_size = PROJECT_CONFIG.min_grid_size
    max_safe = max(1, min(raster_height, raster_width) // min_size)
    return min(requested_downsample, max_safe)


# ─────────────────────────────────────────────────
# DEM Yükleme
# ─────────────────────────────────────────────────

def load_dem(
    tif_path: str | Path,
    window_size: int | None = None,
    downsample: int | None = None,
) -> np.ndarray:
    """GeoTIFF DEM dosyasını okur ve 2D float32 matris döndürür.

    KESİN KURAL: Çıktı matrisi min 120×120 piksel olmalıdır.
    256×256 gibi küçük rasterlar hiç downsample edilmez.

    Args:
        tif_path: .tif dosyasının yolu.
        window_size: Opsiyonel merkez kırpma boyutu (piksel).
        downsample: Opsiyonel downsample faktörü. Güvenli sınırları aşamaz.

    Returns:
        2D float32 numpy matrisi (yükseklik değerleri).

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ModuleNotFoundError: rasterio yüklü değilse.
    """
    tif_path = Path(tif_path).expanduser().resolve()
    if not tif_path.exists():
        raise FileNotFoundError(f"GeoTIFF dosyası bulunamadı: {tif_path}")

    try:
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.windows import Window
    except ModuleNotFoundError as err:
        raise ModuleNotFoundError(
            "GeoTIFF yüklemek için 'rasterio' paketi gereklidir. "
            "pip install rasterio"
        ) from err

    ws = window_size if window_size is not None else PROJECT_CONFIG.tif_window_size
    ds_factor = downsample if downsample is not None else PROJECT_CONFIG.tif_downsample

    with rasterio.open(tif_path) as dataset:
        rw, rh = dataset.width, dataset.height

        # Merkez kırpma penceresi (window_size raster boyutunu aşarsa daralt)
        crop = min(ws, rw, rh)
        col_start = (rw - crop) // 2
        row_start = (rh - crop) // 2
        rio_window = Window(col_off=col_start, row_off=row_start,
                            width=crop, height=crop)

        # Güvenli downsample hesabı
        safe_ds = _safe_downsample(crop, crop, ds_factor)
        out_h = max(1, int(np.ceil(crop / safe_ds)))
        out_w = max(1, int(np.ceil(crop / safe_ds)))

        print(f"[DEM] Raster: {rw}×{rh} | Crop: {crop}×{crop} | "
              f"DS: ×{safe_ds} → Çıktı: {out_w}×{out_h}")

        elevation = dataset.read(
            1,
            window=rio_window,
            out_shape=(out_h, out_w),
            resampling=Resampling.bilinear,
        )

        # Nodata temizliği
        elevation = elevation.astype(np.float32, copy=False)
        if dataset.nodata is not None:
            nodata_mask = np.isclose(elevation, float(dataset.nodata))
            if np.any(nodata_mask):
                elevation[nodata_mask] = np.nan

    dem = _to_2d_float32(elevation)

    # Son güvenlik kontrolü
    if min(dem.shape) < PROJECT_CONFIG.min_grid_size:
        raise ValueError(
            f"DEM çözünürlüğü ({dem.shape}) minimum kabul ({PROJECT_CONFIG.min_grid_size}) "
            f"altına düştü. Downsample faktörünü düşürün."
        )

    return dem


# ─────────────────────────────────────────────────
# Maliyet Katmanları
# ─────────────────────────────────────────────────

def build_cost_layers(z_real: np.ndarray) -> CostLayers:
    """Derives AYAP-2 cost layers (E, S, G) from real DEM elevation data.

    D (distance) is computed dynamically per-transition, not stored as a map.

    Cost Layer Derivation:
        E (Slope Intensity):
            - Computed from terrain gradient magnitude (∂z/∂x, ∂z/∂y)
            - Normalized to [0, 1] range
            - High E = steep terrain that drains battery or risks tipping

        S (Soil Friction / Regolith Roughness):
            - Computed from local 3×3 elevation variance
            - Gated by inverse slope (flat + rough = slippery loose soil)
            - Formula: S = normalize(variance × (0.35 + 0.65 × (1 - E)))
            - High S = loose regolith that increases wheel slip

        G (Shadow / Thermal Risk):
            - Composite of hillshade illumination + crater depth
            - Hillshade: sun azimuth=315° (NW), elevation=15° (polar)
            - Depth proxy: cells below 40th percentile elevation
            - Formula: G = 1.0 + 49.0 × shadow_score^1.4
            - Range: [1.0, 50.0] — soft avoidance, NOT infinite walls
            - High G = permanently shadowed region (PSR) cold trap risk

    Args:
        z_real: 2D float32 elevation matrix (meters).

    Returns:
        CostLayers dataclass with z_norm, e_map, s_map, g_map.
    """
    z = _to_2d_float32(z_real)
    z_norm = _normalize_01(z)

    # ── E Map: Slope Intensity from terrain gradient ──
    grad_row, grad_col = np.gradient(z_norm)
    grad_mag = np.hypot(grad_row, grad_col)
    e_map = _normalize_01(grad_mag)

    # ── S Map: Soil Friction / Regolith Roughness ──
    # High local variance + low slope = loose, slippery material
    roughness = _normalize_01(_local_variance_3x3(z_norm))
    low_slope_gate = 1.0 - e_map
    s_map = _normalize_01(roughness * (0.35 + 0.65 * low_slope_gate))

    # ── G Map: Shadow / Thermal Risk ──
    # Sun position: NW direction at 15° elevation (polar illumination)
    sun_azimuth = np.deg2rad(315.0)      # Sun direction (NW)
    sun_elevation = np.deg2rad(15.0)     # Low sun angle (lunar polar)

    slope_angle = (np.pi / 2.0) - np.arctan(np.hypot(grad_col, grad_row))
    aspect = np.arctan2(-grad_row, grad_col + 1e-12)
    hillshade = (
        np.sin(sun_elevation) * np.sin(slope_angle)
        + np.cos(sun_elevation) * np.cos(slope_angle) * np.cos(sun_azimuth - aspect)
    )
    hillshade = _normalize_01(hillshade)

    # Crater depth proxy: cells below 40th percentile are "in shadow"
    p40 = float(np.percentile(z_norm, 40.0))
    lowland_depth = np.clip(
        (p40 - z_norm) / max(p40 - float(np.min(z_norm)), 1e-9),
        0.0,
        1.0,
    )

    # Composite shadow score: 72% depth + 28% shade
    shadow_score = _normalize_01(
        (0.72 * lowland_depth) + (0.28 * (1.0 - hillshade))
    )
    # Nonlinear scaling: 1.0 (safe) → 50.0 (high PSR risk)
    g_map = 1.0 + 49.0 * np.power(shadow_score, 1.4)

    return CostLayers(
        z_norm=z_norm.astype(np.float32),
        e_map=e_map.astype(np.float32),
        s_map=s_map.astype(np.float32),
        g_map=g_map.astype(np.float32),
    )
