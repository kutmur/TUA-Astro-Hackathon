"""AYAP-2 Matplotlib 3D/2D Görselleştirme Motoru.

Bu modül sadece çizim ve diske kaydetme işlemlerinden sorumludur.
Hiçbir veri işleme veya planlama mantığı içermez.

KESİN KURALLAR (Jury Requirements):
  • input.png: 3D DEM surface with A/B markers (no routes)
  • topview.png: 2D heatmap with elevation colorbar
  • output.png: 3D DEM with all 3 routes overlaid + legend

Visualization Standards:
  • Kamera açısı: view_init(elev=38, azim=228)
  • A/B noktaları "Bayrak Direği" formatında çizilir
  • Rota çizgileri Z-Offset ile yüzeyden kaldırılır
  • Elevation color scale: dark brown = peaks, dark blue = crater floors

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
    """AYAP-2 3D/2D DEM ve rota çizim sınıfı.

    Bu sınıf, jury-grade görselleştirme iş akışını destekler:
        • input.png: 3D surface + A/B markers
        • topview.png: 2D elevation heatmap
        • output.png: 3D surface + A/B markers + 3 routes + legend
    """

    def __init__(self, cfg: ProjectConfig | None = None) -> None:
        self.cfg = cfg if cfg is not None else PROJECT_CONFIG

    # ─────────────────────────────────────────────
    # Yüzey Çizimi
    # ─────────────────────────────────────────────

    def _create_base_surface(
        self,
        z_real: np.ndarray,
        title: str = "Lunar DEM 3D Surface — Haworth Crater",
    ) -> tuple[Figure, Axes3D]:
        """Temel 3D DEM yüzeyini oluşturur.

        Lunar terrain visualization with:
          - gist_earth colormap: dark brown peaks, dark blue crater floors
          - High alpha for solid surface appearance
          - Fixed camera angle for consistent jury presentation

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
        fig.colorbar(surface, shrink=0.60, pad=0.08, label="Elevation (m)")

        ax.set_title(
            title,
            fontsize=13,
            fontweight="bold",
            pad=12,
        )
        ax.set_xlabel("Column (Col)", fontsize=10)
        ax.set_ylabel("Row", fontsize=10)
        ax.set_zlabel("Elevation (m)", fontsize=10)

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

        Creates a "flagpole" marker that stands above the terrain surface,
        making start/end points clearly visible even in 3D views.

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

        # Siyah direk (vertical line from surface to marker)
        ax.plot(
            [x, x], [y, y], [z0, z1],
            color="black",
            linewidth=3.0,
            zorder=1000,
        )

        # Parlak marker at top of pole
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
            label="A (Start)",
            marker_color="red",
            marker_shape="v",
            pole_height=pole_height,
        )
        self._draw_flagpole(
            ax=ax,
            z_surface=z_real,
            point=goal,
            label="B (Goal)",
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
        """Rota çizgilerini Z-Offset ile yüzeyin üzerine çizer.

        Routes are lifted above the terrain surface to remain visible
        from all camera angles. The offset is proportional to terrain relief.
        """
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
            title="Cumulative Cost (C)",
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
    # 2D Heatmap (Top View)
    # ─────────────────────────────────────────────

    def _create_topview_heatmap(
        self,
        z_real: np.ndarray,
        title: str = "Lunar DEM Top View",
    ) -> Figure:
        """Creates 2D elevation heatmap (bird's eye view).

        This view is essential for understanding terrain layout and
        route planning context without 3D perspective distortion.

        Args:
            z_real: 2D elevation matrix.
            title: Plot title.

        Returns:
            Matplotlib Figure object.
        """
        fig, ax = plt.subplots(figsize=(12, 10))

        # Use gist_earth for consistency with 3D view
        im = ax.imshow(
            z_real,
            cmap=self.cfg.surface_cmap,
            origin="upper",
            aspect="equal",
        )

        cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label("Elevation (m)", fontsize=11)

        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("Column", fontsize=11)
        ax.set_ylabel("Row", fontsize=11)

        return fig

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
        print(f"  [SAVED] {path}")

    # ─────────────────────────────────────────────
    # Jury-Grade Output Functions (3 Required Files)
    # ─────────────────────────────────────────────

    def plot_input_png(
        self,
        z_real: np.ndarray,
        start: GridPoint,
        goal: GridPoint,
        save_path: Path,
    ) -> Path:
        """Generates input.png: 3D DEM with A/B markers (no routes).

        Jury Requirement:
            - 3D surface plot of the real DEM
            - Red marker pole at start point A (labeled)
            - Green marker pole at goal point B (labeled)
            - Elevation color scale: dark brown = peaks, dark blue = crater floors
            - Title: "Lunar DEM 3D Surface — Haworth Crater"

        Args:
            z_real: 2D elevation matrix.
            start: A point (row, col).
            goal: B point (row, col).
            save_path: Output path for input.png.

        Returns:
            Path to the saved PNG file.
        """
        fig, ax = self._create_base_surface(
            z_real,
            title="Lunar DEM 3D Surface — Haworth Crater",
        )
        self._add_markers(ax, z_real, start, goal)
        self._save_figure(fig, save_path)
        plt.close(fig)
        return save_path

    def plot_topview_png(
        self,
        z_real: np.ndarray,
        save_path: Path,
    ) -> Path:
        """Generates topview.png: 2D heatmap of DEM elevation.

        Jury Requirement:
            - 2D heatmap (plt.imshow) of DEM elevation
            - Labeled axes (Row / Column)
            - Colorbar with elevation values
            - Title: "Lunar DEM Top View"

        Args:
            z_real: 2D elevation matrix.
            save_path: Output path for topview.png.

        Returns:
            Path to the saved PNG file.
        """
        fig = self._create_topview_heatmap(
            z_real,
            title="Lunar DEM Top View",
        )
        self._save_figure(fig, save_path)
        plt.close(fig)
        return save_path

    def plot_output_png(
        self,
        z_real: np.ndarray,
        start: GridPoint,
        goal: GridPoint,
        routes: list[RouteResult],
        save_path: Path,
    ) -> Path:
        """Generates output.png: 3D DEM with all routes overlaid.

        Jury Requirement:
            - Same 3D surface as input.png
            - Three routes overlaid with z-lift (visible above terrain):
                Yellow solid line    → Balanced 4D   | C = ~590,502
                Cyan dashed line     → Shortest Dist | C = ~1,345,804
                Magenta dotted line  → Thermal Safe  | C = ~9,030,179
            - Legend showing profile names + cumulative costs
            - Title: "TUA AYAP-2 | Real DEM A* 4D Route Simulation"

        Args:
            z_real: 2D elevation matrix.
            start: A point (row, col).
            goal: B point (row, col).
            routes: List of RouteResult objects.
            save_path: Output path for output.png.

        Returns:
            Path to the saved PNG file.
        """
        fig, ax = self._create_base_surface(
            z_real,
            title="TUA AYAP-2 | Real DEM A* 4D Route Simulation",
        )
        self._add_markers(ax, z_real, start, goal)
        self._add_routes(ax, z_real, routes)
        self._add_legend(ax)
        self._save_figure(fig, save_path)
        plt.close(fig)
        return save_path

    # ─────────────────────────────────────────────
    # Legacy Step-by-Step Functions (Backward Compatibility)
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
