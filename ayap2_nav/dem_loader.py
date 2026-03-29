"""AYAP-2 DEM Yükleme ve Maliyet Katmanı Hesaplama Modülü.

Bu modül:
  1. GeoTIFF (.tif) dosyasını `rasterio` ile okur.
  2. KESİNLİKLE agresif downsample yapmaz — min 120×120 çözünürlük korunur.
  3. Gerçek Z matrisinden E (eğim), S (sürtünme/regolit) ve G (gölge/termal)
     maliyet haritalarını türetir.

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

    Attributes:
        z_norm: [0, 1] aralığına normalize edilmiş yükseklik matrisi.
        e_map:  Eğim (slope) yoğunluk haritası [0, 1].
        s_map:  Sürtünme / regolit pürüzlülük haritası [0, 1].
        g_map:  Gölge / termal risk haritası (düşük=güvenli, yüksek=riskli).
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
    """3×3 pencere ile lokal varyans haritası hesaplar (kenar dolgusu ile)."""
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
    """Gerçek DEM'den AYAP-2 maliyet katmanlarını (E, S, G) türetir.

    D (mesafe) her geçişte dinamik hesaplandığı için harita olarak tutulmaz.

    Katman Açıklamaları:
        E – Eğim Haritası: Yüzey gradyan büyüklüğünün [0, 1] normalizasyonu.
        S – Sürtünme / Regolit: Pürüzlülük × ters eğim (düz ama pürüzlü = yüksek S).
        G – Gölge / Termal: Hillshade + çukur derinliği → gölgede kalma riski.

    Args:
        z_real: 2D float32 yükseklik matrisi.

    Returns:
        CostLayers dataclass'ı.
    """
    z = _to_2d_float32(z_real)
    z_norm = _normalize_01(z)

    # ── E Haritası: Eğim Yoğunluğu ──
    grad_row, grad_col = np.gradient(z_norm)
    grad_mag = np.hypot(grad_row, grad_col)
    e_map = _normalize_01(grad_mag)

    # ── S Haritası: Sürtünme / Regolit Pürüzlülüğü ──
    # Yüksek lokal varyans + düşük eğim = kaygan/kumlu zemin
    roughness = _normalize_01(_local_variance_3x3(z_norm))
    low_slope_gate = 1.0 - e_map
    s_map = _normalize_01(roughness * (0.35 + 0.65 * low_slope_gate))

    # ── G Haritası: Gölge / Termal Risk ──
    # Güneş açısı ile hillshade hesabı + çukur derinliği proxy'si
    sun_azimuth = np.deg2rad(315.0)      # Güneş yönü (NW)
    sun_elevation = np.deg2rad(15.0)     # Düşük güneş açısı (ay yüzeyinde)

    slope_angle = (np.pi / 2.0) - np.arctan(np.hypot(grad_col, grad_row))
    aspect = np.arctan2(-grad_row, grad_col + 1e-12)
    hillshade = (
        np.sin(sun_elevation) * np.sin(slope_angle)
        + np.cos(sun_elevation) * np.cos(slope_angle) * np.cos(sun_azimuth - aspect)
    )
    hillshade = _normalize_01(hillshade)

    # Çukur derinliği: 40. yüzdelik altında kalanlar daha gölgeli
    p40 = float(np.percentile(z_norm, 40.0))
    lowland_depth = np.clip(
        (p40 - z_norm) / max(p40 - float(np.min(z_norm)), 1e-9),
        0.0,
        1.0,
    )

    shadow_score = _normalize_01(
        (0.72 * lowland_depth) + (0.28 * (1.0 - hillshade))
    )
    # 1.0 (güvenli) → 50.0 (çok riskli gölge) arası doğrusal olmayan ölçek
    g_map = 1.0 + 49.0 * np.power(shadow_score, 1.4)

    return CostLayers(
        z_norm=z_norm.astype(np.float32),
        e_map=e_map.astype(np.float32),
        s_map=s_map.astype(np.float32),
        g_map=g_map.astype(np.float32),
    )
