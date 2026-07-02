from __future__ import annotations

from pathlib import Path

import numpy as np

# Dracula theme
BG = "#282a36"
CARD = "#44475a"
FG = "#f8f8f2"
PINK = "#ff79c6"
PURPLE = "#bd93f9"
CYAN = "#8be9fd"
GREEN = "#50fa7b"
YELLOW = "#f1fa8c"
COMMENT = "#6272a4"


def _setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "axes.edgecolor": CARD,
        "axes.labelcolor": FG,
        "text.color": FG,
        "xtick.color": COMMENT,
        "ytick.color": COMMENT,
        "grid.alpha": 0.15,
        "grid.color": FG,
    })
    return plt


def plot_telemetry(log: list[dict], save_path: str = "docs/assets/images/dynamics/telemetry.png") -> str:
    """Dracula-themed dual-panel telemetry dashboard.

    Panel 1: Flight trajectory (altitude vs range) + AoA over time
    Panel 2: Actuator commanded vs actual deflection + load factor
    """
    plt = _setup()

    if not log:
        return ""

    t = np.array([entry["t"] for entry in log])
    x = np.array([entry["x"] for entry in log])
    z = np.array([entry["z"] for entry in log])
    aoa = np.array([entry["aoa"] for entry in log])
    delta = np.array([entry["delta"] for entry in log])
    command = np.array([entry["command"] for entry in log])
    lift = np.array([entry["lift"] for entry in log])
    mass = 50.0
    load_factor = lift / (mass * 9.81)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Panel 1: Flight trajectory + AoA
    color_traj = CYAN
    color_aoa = PINK
    ax1.plot(x, z, color=color_traj, linewidth=1.5, label="Flight Path")
    ax1.set_ylabel("Altitude (m)", color=color_traj)
    ax1.set_title("Flight Trajectory & Angle of Attack")
    ax1.grid(True, alpha=0.15)

    ax1b = ax1.twinx()
    ax1b.plot(t, aoa, color=color_aoa, linewidth=1.5, linestyle="--", label="AoA")
    ax1b.set_ylabel("Angle of Attack (deg)", color=color_aoa)
    ax1b.tick_params(axis="y", labelcolor=color_aoa)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines1b, labels1b = ax1b.get_legend_handles_labels()
    ax1.legend(lines1 + lines1b, labels1 + labels1b, facecolor=CARD, labelcolor=FG)

    # Panel 2: Actuator telemetry + load factor
    ax2.plot(t, command, color=GREEN, linewidth=1, linestyle=":", label="Commanded")
    ax2.plot(t, delta, color=PURPLE, linewidth=1.5, label="Actual Deflection")
    ax2.set_ylabel("Flap Deflection (deg)")
    ax2.set_xlabel("Time (s)")
    ax2.set_title("Actuator Response & Load Factor")
    ax2.grid(True, alpha=0.15)

    ax2b = ax2.twinx()
    ax2b.plot(t, load_factor, color=YELLOW, linewidth=1, linestyle="--", label="Load Factor (n)")
    ax2b.set_ylabel("Load Factor", color=YELLOW)
    ax2b.tick_params(axis="y", labelcolor=YELLOW)

    lines2, labels2 = ax2.get_legend_handles_labels()
    lines2b, labels2b = ax2b.get_legend_handles_labels()
    ax2.legend(lines2 + lines2b, labels2 + labels2b, facecolor=CARD, labelcolor=FG)

    fig.tight_layout()
    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)
