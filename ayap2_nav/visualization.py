"""AYAP-2 Matplotlib 3D Görselleştirme Motoru.

Bu modül sadece çizim ve diske kaydetme işlemlerinden sorumludur.
Hiçbir veri işleme veya planlama mantığı içermez.

KESİN KURALLAR:
  • Kamera açısı: view_init(elev=38, azim=228)
  • A/B noktaları "Bayrak Direği" formatında çizilir
  • Rota çizgileri Z-Offset ile yüzeyden kaldırılır: Z_path = Z_surface + (Z_span × 0.04)
  • Rota çizgi kalınlığı ≥ 3

Kullanım:
    from visualization import DEMVisualizer
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # GUI olmadan çalış

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

try:
    from .config import PROJECT_CONFIG, ProjectConfig
    from .planner import RouteResult
except ImportError:
    from config import PROJECT_CONFIG, ProjectConfig
    from planner import RouteResult

# ─────────────────────────────────────────────────
# Tip Tanımları
# ─────────────────────────────────────────────────
GridPoint = tuple[int, int]


class DEMVisualizer:
    """AYAP-2 3D DEM ve rota çizim sınıfı.

    Bu sınıf, kademeli (3 aşamalı) görselleştirme iş akışını destekler:
        1. Çıplak 3D yüzey
        2. Yüzey + A/B bayrak direkleri
        3. Yüzey + Noktalar + Rotalar + Lejant
    """

    def __init__(self, cfg: ProjectConfig | None = None) -> None:
        self.cfg = cfg if cfg is not None else PROJECT_CONFIG

    # ─────────────────────────────────────────────
    # Yüzey Çizimi
    # ─────────────────────────────────────────────

    def _create_base_surface(
        self,
        z_real: np.ndarray,
    ) -> tuple[Figure, Axes3D]:
        """Temel 3D DEM yüzeyini oluşturur.

        Returns:
            (figure, axes3d) tuple'ı.
        """
        rows, cols = z_real.shape
        x_grid, y_grid = np.meshgrid(np.arange(cols), np.arange(rows))

        fig = plt.figure(figsize=self.cfg.figure_size)
        ax: Axes3D = fig.add_subplot(111, projection="3d")

        surface = ax.plot_surface(
            x_grid,
            y_grid,
            z_real,
            cmap=self.cfg.surface_cmap,
            linewidth=0,
            antialiased=True,
            alpha=self.cfg.surface_alpha,
            zorder=1,
        )
        fig.colorbar(surface, shrink=0.60, pad=0.08, label="Yükseklik (m)")

        ax.set_title(
            "TUA AYAP-2 | Haworth Krateri DEM — 4D A* Rota Simülasyonu",
            fontsize=13,
            fontweight="bold",
            pad=12,
        )
        ax.set_xlabel("Sütun (Col)", fontsize=10)
        ax.set_ylabel("Satır (Row)", fontsize=10)
        ax.set_zlabel("Yükseklik", fontsize=10)

        # KESİN KURAL: Sabit kamera açısı
        ax.view_init(elev=self.cfg.camera_elev, azim=self.cfg.camera_azim)

        return fig, ax

    # ─────────────────────────────────────────────
    # Bayrak Direği Çizimi
    # ─────────────────────────────────────────────

    def _draw_flagpole(
        self,
        ax: Axes3D,
        z_surface: np.ndarray,
        point: GridPoint,
        label: str,
        marker_color: str,
        marker_shape: str,
        pole_height: float,
    ) -> None:
        """Yüzeyden yukarı doğru siyah direk + parlak marker + etiket çizer.

        Args:
            ax: Matplotlib 3D ekseni.
            z_surface: Gerçek yükseklik matrisi (Z değerini almak için).
            point: (row, col) grid noktası.
            label: Marker üstündeki metin etiketi (ör. "A", "B").
            marker_color: Marker rengi.
            marker_shape: Matplotlib marker tipi (ör. "v", "D").
            pole_height: Direğin yüksekliği (Z birimi).
        """
        row, col = point
        x = float(col)
        y = float(row)
        z0 = float(z_surface[row, col])
        z1 = z0 + pole_height

        # Siyah direk
        ax.plot(
            [x, x], [y, y], [z0, z1],
            color="black",
            linewidth=3.0,
            zorder=1000,
        )

        # Parlak marker
        ax.scatter(
            [x], [y], [z1],
            s=200,
            c=marker_color,
            marker=marker_shape,
            edgecolors="black",
            linewidths=1.6,
            depthshade=False,
            zorder=1001,
        )

        # Metin etiketi (bbox ile arka plan)
        ax.text(
            x + 2.5,
            y + 2.5,
            z1 + (0.06 * pole_height),
            label,
            fontsize=11,
            fontweight="bold",
            color="black",
            bbox={
                "facecolor": "white",
                "edgecolor": "black",
                "alpha": 0.93,
                "boxstyle": "round,pad=0.3",
            },
            zorder=1002,
        )

    def _add_markers(
        self,
        ax: Axes3D,
        z_real: np.ndarray,
        start: GridPoint,
        goal: GridPoint,
    ) -> None:
        """A ve B bayrak direklerini yüzeye ekler."""
        z_span = float(np.max(z_real) - np.min(z_real))
        pole_height = max(
            self.cfg.pole_height_ratio * z_span,
            z_span * self.cfg.z_offset_ratio * 4.0,
            1.0,
        )

        self._draw_flagpole(
            ax=ax,
            z_surface=z_real,
            point=start,
            label="A (Başlangıç)",
            marker_color="red",
            marker_shape="v",
            pole_height=pole_height,
        )
        self._draw_flagpole(
            ax=ax,
            z_surface=z_real,
            point=goal,
            label="B (Hedef)",
            marker_color="lime",
            marker_shape="D",
            pole_height=pole_height,
        )

    # ─────────────────────────────────────────────
    # Rota Çizimi
    # ─────────────────────────────────────────────

    def _add_routes(
        self,
        ax: Axes3D,
        z_real: np.ndarray,
        routes: list[RouteResult],
    ) -> None:
        """Rota çizgilerini Z-Offset ile yüzeyin üzerine çizer."""
        z_span = float(np.max(z_real) - np.min(z_real))
        z_offset = z_span * self.cfg.z_offset_ratio  # KESİN KURAL

        for route in routes:
            if not route.path:
                continue

            row_arr = np.array([p[0] for p in route.path], dtype=np.int32)
            col_arr = np.array([p[1] for p in route.path], dtype=np.int32)
            z_path = z_real[row_arr, col_arr].astype(np.float64) + z_offset

            cost_str = f"{route.cumulative_cost:,.0f}"
            label = f"{route.profile.name} | C={cost_str}"

            ax.plot(
                col_arr.astype(np.float64),
                row_arr.astype(np.float64),
                z_path,
                color=route.profile.color,
                linestyle=route.profile.linestyle,
                linewidth=max(route.profile.linewidth, 3.0),
                alpha=0.98,
                label=label,
                zorder=500,
            )

    def _add_legend(self, ax: Axes3D) -> None:
        """Sağ üst köşeye siyah arka planlı profesyonel lejant ekler."""
        legend = ax.legend(
            loc="upper right",
            title="Kümülatif Maliyet (C)",
            facecolor="black",
            edgecolor="white",
            framealpha=0.92,
            fontsize=9,
            title_fontsize=10,
        )
        legend.get_title().set_color("white")
        for text in legend.get_texts():
            text.set_color("white")

    # ─────────────────────────────────────────────
    # Diske Kaydetme
    # ─────────────────────────────────────────────

    @staticmethod
    def _save_figure(fig: Figure, path: Path) -> None:
        """Figure'ı yüksek çözünürlükte PNG olarak kaydeder."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(
            path,
            dpi=PROJECT_CONFIG.figure_dpi,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        print(f"[KAYIT] {path}")

    # ─────────────────────────────────────────────
    # Kademeli (3 Adım) Genel Çizim Fonksiyonları
    # ─────────────────────────────────────────────

    def plot_step1_base_surface(
        self,
        z_real: np.ndarray,
        save_path: Path,
    ) -> tuple[Figure, Axes3D]:
        """ADIM 1: Çıplak 3D DEM yüzeyi → diske kaydet.

        Args:
            z_real: 2D yükseklik matrisi.
            save_path: Çıktı PNG yolu.

        Returns:
            (figure, axes3d) — sonraki adımda tekrar kullanılabilir.
        """
        fig, ax = self._create_base_surface(z_real)
        self._save_figure(fig, save_path)
        plt.close(fig)
        return fig, ax

    def plot_step2_with_markers(
        self,
        z_real: np.ndarray,
        start: GridPoint,
        goal: GridPoint,
        save_path: Path,
    ) -> tuple[Figure, Axes3D]:
        """ADIM 2: Yüzey + A/B bayrak direkleri → diske kaydet.

        Args:
            z_real: 2D yükseklik matrisi.
            start: A noktası grid indeksi.
            goal: B noktası grid indeksi.
            save_path: Çıktı PNG yolu.

        Returns:
            (figure, axes3d)
        """
        fig, ax = self._create_base_surface(z_real)
        self._add_markers(ax, z_real, start, goal)
        self._save_figure(fig, save_path)
        plt.close(fig)
        return fig, ax

    def plot_step3_final(
        self,
        z_real: np.ndarray,
        start: GridPoint,
        goal: GridPoint,
        routes: list[RouteResult],
        save_path: Path,
    ) -> Figure:
        """ADIM 3: Yüzey + Noktalar + Rotalar + Lejant → diske kaydet.

        Args:
            z_real: 2D yükseklik matrisi.
            start: A noktası grid indeksi.
            goal: B noktası grid indeksi.
            routes: Tamamlanmış RouteResult listesi.
            save_path: Çıktı PNG yolu.

        Returns:
            Final matplotlib Figure.
        """
        fig, ax = self._create_base_surface(z_real)
        self._add_markers(ax, z_real, start, goal)
        self._add_routes(ax, z_real, routes)
        self._add_legend(ax)
        self._save_figure(fig, save_path)
        plt.close(fig)
        return fig
