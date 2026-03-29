"""AYAP-2 4D Rota Optimizasyonu — Merkezi Konfigürasyon Modülü.

Bu dosya projenin tüm sabitlerini, A/B nokta oranlarını ve
üç farklı rota profili için AYAP-2 4D maliyet denklemi ağırlıklarını
(W_d, W_e, W_s, W_g) barındırır.

Kullanım:
    from config import PROJECT_CONFIG, ROUTE_PROFILES, START_UV, GOAL_UV
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ─────────────────────────────────────────────────
# A ve B Noktaları — Harita UV Oranları (0.0 – 1.0)
# ─────────────────────────────────────────────────
# UV oranları, harita matrisinin satır/sütun boyutuna
# çarpılarak gerçek grid indekslerine dönüştürülür.
#   row = int(UV_row * (n_rows - 1))
#   col = int(UV_col * (n_cols - 1))

START_UV: Final[tuple[float, float]] = (0.0, 0.99)   # Row = En Üst,  Col = En Sağ
GOAL_UV: Final[tuple[float, float]]  = (0.5, 0.05)   # Row = Orta,    Col = En Sol

# ─────────────────────────────────────────────────
# Kamera / Perception Tetikleyicisi
# ─────────────────────────────────────────────────

# RAD750 kısıtı simülasyonu:
# False iken segmentasyon modeli RAM'e yüklenmez.
CAMERA_CONNECTED: Final[bool] = False

# Mock kamera ayarları (OpenCV VideoCapture)
CAMERA_DEVICE_INDEX: Final[int] = 0
CAMERA_MAX_FRAMES: Final[int] = 45

# U-Net + VGG16 inference ayarları
SEGMENTATION_INPUT_SHAPE: Final[tuple[int, int, int]] = (500, 500, 3)
SEGMENTATION_MODEL_WEIGHTS: Final[str] = "model_TL_UNET.h5"
SEGMENTATION_VGG16_WEIGHTS: Final[str] = "imagenet"
ROCK_MASK_THRESHOLD: Final[float] = 0.55

# Planner entegrasyonu (Hiyerarşik Kayar Pencere ceza parametreleri)
ROCK_PENALTY_TARGET_LAYER: Final[str] = "s"  # "s", "e" veya "both"
ROCK_DIRECT_PENALTY: Final[float] = 35.0
ROCK_NEAR_PENALTY: Final[float] = 12.0
ROCK_FAR_PENALTY: Final[float] = 4.0
ROCK_NEAR_WINDOW_RADIUS: Final[int] = 2
ROCK_FAR_WINDOW_RADIUS: Final[int] = 5

# ─────────────────────────────────────────────────
# Rota Profili
# ─────────────────────────────────────────────────

@dataclass(frozen=True)
class RouteProfile:
    """Tek bir rota senaryosunun ağırlık ve çizim stilini tanımlar.

    Attributes:
        name: Profil adı (lejant etiketi).
        wd: Mesafe (Distance) ağırlığı.
        we: Eğim (Elevation/Slope) ağırlığı.
        ws: Sürtünme / Regolit (Soil) ağırlığı.
        wg: Gölge (Shadow / Thermal) ağırlığı.
        color: Matplotlib çizgi rengi.
        linestyle: Matplotlib çizgi stili.
        linewidth: Çizgi kalınlığı.
    """

    name: str
    wd: float
    we: float
    ws: float
    wg: float
    color: str
    linestyle: str = "-"
    linewidth: float = 3.0


# Üç standart AYAP-2 rota profili
ROUTE_PROFILES: Final[list[RouteProfile]] = [
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
        name="Shortest Distance",
        wd=9.5,
        we=0.25,
        ws=0.05,
        wg=0.01,
        color="cyan",
        linestyle="--",
        linewidth=2.5,
    ),
    RouteProfile(
        name="Thermal Safe",
        wd=0.9,
        we=1.2,
        ws=0.5,
        wg=6.5,
        color="magenta",
        linestyle=":",
        linewidth=2.5,
    ),
]

# ─────────────────────────────────────────────────
# Proje Geneli Sabitler
# ─────────────────────────────────────────────────

@dataclass(frozen=True)
class ProjectConfig:
    """Projenin çalışma zamanı ayarları."""

    # Varsayılan GeoTIFF yolu (proje kökünden göreli)
    default_tif_name: str = "haworth_crater_DEM_1m.tif"

    # DEM yükleme ayarları
    tif_window_size: int = 1500
    tif_downsample: int = 1          # 256×256 zaten küçük — downsample YAPMA

    # Minimum kabul edilebilir çözünürlük (agresif downsample'a karşı koruma)
    min_grid_size: int = 120

    # Görselleştirme sabitleri
    camera_elev: int = 38
    camera_azim: int = 228
    figure_size: tuple[int, int] = (16, 11)
    figure_dpi: int = 220
    surface_cmap: str = "gist_earth"
    surface_alpha: float = 0.96

    # Z-Offset: rotaların yüzeye gömülmesini engelleyen kaldırma oranı
    z_offset_ratio: float = 0.04     # Z_path = Z_surface + (Z_span * 0.04)

    # Bayrak direği yükseklik oranı
    pole_height_ratio: float = 0.18

    # Çıktı dosya isimleri
    output_step1: str = "01_base_surface.png"
    output_step2: str = "02_surface_with_markers.png"
    output_step3: str = "03_final_routes_analyzed.png"


PROJECT_CONFIG: Final[ProjectConfig] = ProjectConfig()


# ─────────────────────────────────────────────────
# Yardımcı Fonksiyonlar
# ─────────────────────────────────────────────────

GridPoint = tuple[int, int]


def uv_to_grid(
    uv: tuple[float, float],
    shape: tuple[int, int],
) -> GridPoint:
    """UV oranını (row_ratio, col_ratio) gerçek grid indeksine çevirir.

    Args:
        uv: (row_ratio, col_ratio) — her ikisi de [0.0, 1.0] aralığında.
        shape: (n_rows, n_cols) — DEM matris boyutu.

    Returns:
        (row, col) tam sayı grid indeksi.
    """
    n_rows, n_cols = shape
    row = int(round(uv[0] * (n_rows - 1)))
    col = int(round(uv[1] * (n_cols - 1)))
    # Sınır koruması
    row = max(0, min(row, n_rows - 1))
    col = max(0, min(col, n_cols - 1))
    return (row, col)


def resolve_default_tif() -> Path | None:
    """Proje dizin yapısında varsayılan GeoTIFF dosyasını bulur.

    Şu dizinlere sırasıyla bakar:
        1. ayap2_nav/data/
        2. <proje_kökü>/data/
        3. cwd/data/
    """
    base = Path(__file__).resolve()
    candidate_dirs = [
        base.parent / "data",
        base.parent.parent / "data",
        Path.cwd() / "data",
    ]
    for directory in candidate_dirs:
        if not directory.exists():
            continue
        candidates = sorted(directory.glob("*.tif")) + sorted(directory.glob("*.tiff"))
        if candidates:
            return candidates[0]
    return None
