from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from physics.solver import SU2Results

# Dracula theme
BG_COLOR = "#282a36"
CARD_BG = "#44475a"
FG_COLOR = "#f8f8f2"
PINK = "#ff79c6"
PURPLE = "#bd93f9"
CYAN = "#8be9fd"
GREEN = "#50fa7b"
YELLOW = "#f1fa8c"
COMMENT = "#6272a4"


def _setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": BG_COLOR,
        "axes.edgecolor": CARD_BG,
        "axes.labelcolor": FG_COLOR,
        "text.color": FG_COLOR,
        "xtick.color": COMMENT,
        "ytick.color": COMMENT,
        "grid.alpha": 0.15,
        "grid.color": FG_COLOR,
        "legend.facecolor": CARD_BG,
        "legend.labelcolor": FG_COLOR,
    })
    return plt


def plot_convergence(
    history: list[dict],
    save_path: str,
    aoa: int = 0,
) -> Optional[str]:
    """Plot convergence history: RMS residuals and CL/CD."""
    if not history:
        return None

    import matplotlib.pyplot as plt

    _setup_matplotlib()

    n = len(history)
    iters = np.arange(1, n + 1)

    # Parse residuals
    rho_res, rhoU_res, rhoV_res, nu_res = [], [], [], []
    cl_hist, cd_hist = [], []
    for entry in history:
        rho_res.append(float(entry.get("rms[Rho]", float("nan"))))
        rhoU_res.append(float(entry.get("rms[RhoU]", float("nan"))))
        rhoV_res.append(float(entry.get("rms[RhoV]", float("nan"))))
        nu_res.append(float(entry.get("rms[nu]", float("nan"))))
        cl_hist.append(float(entry.get("LIFT", float("nan"))))
        cd_hist.append(float(entry.get("DRAG", float("nan"))))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Residuals
    ax1.plot(iters, rho_res, label="RMS Density", color=CYAN, linewidth=1)
    ax1.plot(iters, rhoU_res, label="RMS RhoU", color=PINK, linewidth=1)
    ax1.plot(iters, rhoV_res, label="RMS RhoV", color=GREEN, linewidth=1)
    ax1.plot(iters, nu_res, label="RMS nu", color=YELLOW, linewidth=1)
    ax1.set_ylabel("Log10(Residual)")
    ax1.set_title("Convergence History — RMS Residuals")
    ax1.legend()
    ax1.grid(True, alpha=0.15)

    # CL/CD
    ax2.plot(iters, cl_hist, label="$C_l$", color=PURPLE, linewidth=1.5)
    ax2.plot(iters, cd_hist, label="$C_d$", color=PINK, linewidth=1.5)
    ax2.set_xlabel("Iteration")
    ax2.set_ylabel("Coefficient")
    ax2.set_title("Force Coefficient Convergence")
    ax2.legend()
    ax2.grid(True, alpha=0.15)

    fig.tight_layout()
    out = f"{save_path}/convergence_{aoa}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_cl_alpha(
    results: list[tuple[float, SU2Results]],
    save_path: str,
    experimental: Optional[list[tuple[float, float]]] = None,
) -> Optional[str]:
    """Lift curve: CL vs angle of attack."""
    if not results:
        return None

    import matplotlib.pyplot as plt

    _setup_matplotlib()

    angles = [r[0] for r in results]
    cl_vals = [r[1].cl for r in results]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(angles, cl_vals, "o-", color=PURPLE, linewidth=2, markersize=8, label="SU2 RANS (SA)")

    if experimental:
        exp_angles, exp_cl = zip(*experimental)
        ax.plot(exp_angles, exp_cl, "s--", color=COMMENT, linewidth=1.5, markersize=5, label="Experimental")

    ax.set_xlabel("Angle of Attack (deg)")
    ax.set_ylabel("Lift Coefficient $C_l$")
    ax.set_title("Lift Curve — NACA 0012, Re = 1×10⁶, M = 0.15")
    ax.legend()
    ax.grid(True, alpha=0.15)

    fig.tight_layout()
    out = f"{save_path}/cl_vs_alpha.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_cd_alpha(
    results: list[tuple[float, SU2Results]],
    save_path: str,
    experimental: Optional[list[tuple[float, float]]] = None,
) -> Optional[str]:
    """Drag polar: Cd vs angle of attack."""
    if not results:
        return None

    import matplotlib.pyplot as plt

    _setup_matplotlib()

    angles = [r[0] for r in results]
    cd_vals = [r[1].cd for r in results]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(angles, cd_vals, "o-", color=PINK, linewidth=2, markersize=8, label="SU2 RANS (SA)")

    if experimental:
        exp_angles, exp_cd = zip(*experimental)
        ax.plot(exp_angles, exp_cd, "s--", color=COMMENT, linewidth=1.5, markersize=5, label="Experimental")

    ax.set_xlabel("Angle of Attack (deg)")
    ax.set_ylabel("Drag Coefficient $C_d$")
    ax.set_title("Drag Polar — NACA 0012, Re = 1×10⁶, M = 0.15")
    ax.legend()
    ax.grid(True, alpha=0.15)

    fig.tight_layout()
    out = f"{save_path}/cd_vs_alpha.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_drag_polar(
    results: list[tuple[float, SU2Results]],
    save_path: str,
    experimental: Optional[list[tuple[float, float]]] = None,
) -> Optional[str]:
    """Drag polar: CL vs Cd."""
    if not results:
        return None

    import matplotlib.pyplot as plt

    _setup_matplotlib()

    cl_vals = [r[1].cl for r in results]
    cd_vals = [r[1].cd for r in results]
    angles = [r[0] for r in results]

    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(cd_vals, cl_vals, c=angles, cmap="coolwarm", s=100, zorder=5)
    ax.plot(cd_vals, cl_vals, color=COMMENT, linewidth=1, alpha=0.5, zorder=3)
    cbar = fig.colorbar(sc, ax=ax, label="AoA (deg)")

    if experimental:
        exp_cd, exp_cl = zip(*experimental)
        ax.plot(exp_cd, exp_cl, "s--", color=COMMENT, linewidth=1.5, markersize=5, label="Experimental")

    for cd, cl, aoa in zip(cd_vals, cl_vals, angles):
        ax.annotate(f"{aoa}°", (cd, cl), xytext=(5, 5),
                    textcoords="offset points", color=FG_COLOR, fontsize=9)

    ax.set_xlabel("Drag Coefficient $C_d$")
    ax.set_ylabel("Lift Coefficient $C_l$")
    ax.set_title("Drag Polar — NACA 0012, Re = 1×10⁶, M = 0.15")
    ax.legend()
    ax.grid(True, alpha=0.15)

    fig.tight_layout()
    out = f"{save_path}/drag_polar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out
