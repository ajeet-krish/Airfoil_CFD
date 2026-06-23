from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
import numpy as np
import pyvista as pv
from scipy.interpolate import griddata

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Dracula theme
BG_COLOR = "#282a36"
CARD_BG = "#44475a"
TEXT_COLOR = "#f8f8f2"
ACCENT_PINK = "#ff79c6"
ACCENT_PURPLE = "#bd93f9"
ACCENT_CYAN = "#8be9fd"
ACCENT_GREEN = "#50fa7b"
COMMENT = "#6272a4"
CMAP_VEL = plt.cm.colors.LinearSegmentedColormap.from_list(
    "dracula_vel", ["#bd93f9", "#ff79c6", "#f1fa8c"], N=256
)
CMAP_PRE = "magma"
CMAP_CP = "coolwarm"


class Visualizer:
    """PyVista/matplotlib-based visualization pipeline for airfoil CFD results."""

    def __init__(
        self,
        window_size: tuple[int, int] = (1000, 800),
        off_screen: bool = True,
    ):
        self.window_size = window_size
        self.off_screen = off_screen
        self._grid_nx = 600
        self._grid_ny = 400
        self._xlim = (-2.0, 5.0)
        self._ylim = (-3.0, 3.0)

    def _make_regular_grid(self):
        xs = np.linspace(self._xlim[0], self._xlim[1], self._grid_nx)
        ys = np.linspace(self._ylim[0], self._ylim[1], self._grid_ny)
        return np.meshgrid(xs, ys)

    def _interp_to_grid(self, x, y, values, Xg, Yg):
        pts = np.column_stack([x, y])
        return griddata(pts, values, (Xg, Yg), method="linear")

    def _apply_dracula_style(self, ax):
        ax.set_facecolor(BG_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color(CARD_BG)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TEXT_COLOR)

    def export_velocity(
        self,
        vtu_file: str,
        save_path: str,
        aoa: int = 0,
        streamlines: bool = True,
    ) -> Optional[str]:
        """Velocity contour + streamline plot via matplotlib (Soccer CFD pattern)."""
        vtu_path = Path(vtu_file)
        if not vtu_path.exists():
            print(f"  VTU not found: {vtu_file}")
            return None

        mesh = pv.read(vtu_file)
        if "Velocity" not in mesh.point_data:
            print(f"  No Velocity field in {vtu_file}")
            return None

        pts = mesh.points
        vel = mesh["Velocity"]
        vel_mag = np.linalg.norm(vel, axis=1)
        vel_mag_max = np.percentile(vel_mag, 98)

        Xg, Yg = self._make_regular_grid()
        Vg = self._interp_to_grid(pts[:, 0], pts[:, 1], vel_mag, Xg, Yg)
        Ug = self._interp_to_grid(pts[:, 0], pts[:, 1], vel[:, 0], Xg, Yg)
        Vv = self._interp_to_grid(pts[:, 0], pts[:, 1], vel[:, 1], Xg, Yg)

        fig, ax = plt.subplots(figsize=(10, 6.5), facecolor=BG_COLOR)
        self._apply_dracula_style(ax)

        contour = ax.contourf(
            Xg, Yg, Vg,
            levels=50,
            cmap=CMAP_VEL,
            vmin=0,
            vmax=vel_mag_max,
            extend="max",
        )

        if streamlines:
            try:
                stride = 3
                ax.streamplot(
                    Xg[::stride, ::stride],
                    Yg[::stride, ::stride],
                    Ug[::stride, ::stride],
                    Vv[::stride, ::stride],
                    color="white",
                    linewidth=0.6,
                    density=0.8,
                    arrowsize=0.6,
                )
            except Exception as e:
                print(f"  Streamline generation failed: {e}")

        cbar = fig.colorbar(contour, ax=ax, pad=0.02)
        cbar.set_label("Velocity Magnitude", color=TEXT_COLOR)
        cbar.ax.yaxis.label.set_color(TEXT_COLOR)
        cbar.ax.tick_params(colors=TEXT_COLOR)

        ax.set_xlabel("x/c")
        ax.set_ylabel("y/c")
        ax.set_title("Velocity Field with Streamlines", color=TEXT_COLOR)
        ax.set_aspect("equal")

        out = f"{save_path}/velocity_{aoa}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
        plt.close(fig)
        return out

    def export_pressure(
        self,
        vtu_file: str,
        save_path: str,
        aoa: int = 0,
    ) -> Optional[str]:
        """Pressure contour plot via matplotlib (griddata pattern)."""
        vtu_path = Path(vtu_file)
        if not vtu_path.exists():
            print(f"  VTU not found: {vtu_file}")
            return None

        mesh = pv.read(vtu_file)
        if "Pressure" not in mesh.point_data:
            print(f"  No Pressure field in {vtu_file}")
            return None

        pts = mesh.points
        pressure = mesh["Pressure"]
        p_min, p_max = np.percentile(pressure, [2, 98])

        Xg, Yg = self._make_regular_grid()
        Pg = self._interp_to_grid(pts[:, 0], pts[:, 1], pressure, Xg, Yg)

        fig, ax = plt.subplots(figsize=(10, 6.5), facecolor=BG_COLOR)
        self._apply_dracula_style(ax)

        contour = ax.contourf(
            Xg, Yg, Pg,
            levels=50,
            cmap=CMAP_PRE,
            vmin=p_min,
            vmax=p_max,
            extend="both",
        )

        cbar = fig.colorbar(contour, ax=ax, pad=0.02)
        cbar.set_label("Pressure", color=TEXT_COLOR)
        cbar.ax.yaxis.label.set_color(TEXT_COLOR)
        cbar.ax.tick_params(colors=TEXT_COLOR)

        ax.set_xlabel("x/c")
        ax.set_ylabel("y/c")
        ax.set_title("Pressure Field", color=TEXT_COLOR)
        ax.set_aspect("equal")

        out = f"{save_path}/pressure_{aoa}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
        plt.close(fig)
        return out

    def export_surface_cp(
        self,
        surface_vtu: str,
        save_path: str,
        aoa: int = 0,
    ) -> Optional[str]:
        """Extract Cp distribution along the airfoil surface and plot."""
        if not Path(surface_vtu).exists():
            print(f"  Surface VTU not found: {surface_vtu}")
            return None

        mesh = pv.read(surface_vtu)
        if "Pressure_Coefficient" not in mesh.point_data:
            print(f"  No Pressure_Coefficient in {surface_vtu}")
            return None

        points = mesh.points
        cp = mesh["Pressure_Coefficient"]

        sort_idx = np.argsort(points[:, 0])
        x = points[sort_idx, 0]
        cp_sorted = cp[sort_idx]

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(facecolor=BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        ax.plot(x, cp_sorted, color="#ff79c6", linewidth=2, label=f"AoA={aoa}°")
        ax.invert_yaxis()
        ax.set_xlabel("x/c", color="#f8f8f2")
        ax.set_ylabel("$C_p$", color="#f8f8f2")
        ax.set_title(
            f"Pressure Coefficient Distribution — AoA = {aoa}°",
            color="#f8f8f2",
        )
        ax.tick_params(colors="#f8f8f2")
        for spine in ax.spines.values():
            spine.set_color("#44475a")
        ax.legend(facecolor="#44475a", labelcolor="#f8f8f2")
        ax.grid(True, alpha=0.15)

        out = f"{save_path}/cp_distribution_{aoa}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
        plt.close(fig)
        return out
