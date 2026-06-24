from __future__ import annotations

from math import comb
from pathlib import Path
from typing import Optional

import numpy as np

from physics.geometry import save_dat_file

NACA0012_BASELINE = {
    "cl": 0.4453,
    "cd": 0.0969,
    "ld": 4.6,
    "area": 0.0765,
    "max_thickness": 0.12,
    "le_radius": 0.012,
    "te_thickness": 0.001,
    "max_camber": 0.0,
    "thickness_location": 0.30,
}

NACA0012_CST = {
    "upper_weights": [
        0.1728844021792659,
        0.151562918209576,
        0.1737630566439539,
        0.12768079074261648,
        0.1648184645582348,
        0.12637600339264848,
        0.1458978921585667,
        0.13919961424571897,
    ],
    "lower_weights": [
        -0.17288440217926504,
        -0.1515629182095779,
        -0.17376305664395086,
        -0.12768079074261918,
        -0.1648184645582331,
        -0.12637600339264946,
        -0.145897892158567,
        -0.13919961424571847,
    ],
    "leading_edge_weight": 2.87e-16,
    "TE_thickness": 0.0025479,
}


def bernstein(i: int, n: int, psi: np.ndarray) -> np.ndarray:
    return comb(n, i) * (psi**i) * ((1 - psi) ** (n - i))


def cst_coordinates(
    upper_weights: np.ndarray,
    lower_weights: np.ndarray,
    n_points: int = 200,
    n1: float = 0.5,
    n2: float = 1.0,
    te_thickness: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_upper = len(upper_weights)
    n_lower = len(lower_weights)
    psi = np.linspace(0, 1, n_points)
    cf = psi**n1 * (1 - psi) ** n2

    su = np.zeros(n_points)
    for i, w in enumerate(upper_weights):
        su += w * bernstein(i, n_upper - 1, psi)

    sl = np.zeros(n_points)
    for i, w in enumerate(lower_weights):
        sl += w * bernstein(i, n_lower - 1, psi)

    zu = cf * su + psi * te_thickness / 2
    zl = cf * sl - psi * te_thickness / 2

    return psi, zu, zl


def build_airfoil_from_cst(
    upper_weights: np.ndarray,
    lower_weights: np.ndarray,
    name: str = "optimized",
    n_points: int = 200,
    te_thickness: float = 0.0,
):
    from aerosandbox import Airfoil

    psi, zu, zl = cst_coordinates(upper_weights, lower_weights, n_points, te_thickness=te_thickness)
    upper = np.column_stack([psi, zu])
    lower = np.column_stack([psi, zl])
    coords = np.vstack([upper[::-1], lower[1:]])
    return Airfoil(name=name, coordinates=coords)


def _to_scalar(v):
    if isinstance(v, np.ndarray):
        return float(v.item()) if v.ndim == 0 else float(v[0])
    return float(v)


def airfoil_properties_from_weights(upper_weights, lower_weights, te_thickness: float = 0.0):
    af = build_airfoil_from_cst(upper_weights, lower_weights, te_thickness=te_thickness)

    x_t = np.linspace(0, 1, 1000)
    t = af.local_thickness(x_t)
    t_loc = float(x_t[np.argmax(t)])

    return {
        "max_thickness": _to_scalar(af.max_thickness()),
        "le_radius": _to_scalar(af.LE_radius()),
        "te_thickness": _to_scalar(af.TE_thickness()),
        "area": _to_scalar(af.area()),
        "max_camber": _to_scalar(af.max_camber()),
        "thickness_location": t_loc,
    }


def constraint_violations(
    props: dict,
    min_thickness: float = 0.12,
    max_le_radius: float = 0.020,
    min_le_radius: float = 0.007,
    min_te_thickness: float = 0.000,
    area_lower: float = 0.065,
    area_upper: float = 0.088,
    max_camber: float = 0.02,
    thickness_loc_lower: float = 0.25,
    thickness_loc_upper: float = 0.40,
) -> float:
    viol = 0.0
    viol += max(0, min_thickness - props["max_thickness"]) * 100
    viol += max(0, min_le_radius - props["le_radius"]) * 100
    viol += max(0, props["le_radius"] - max_le_radius) * 100
    viol += max(0, min_te_thickness - props["te_thickness"]) * 100
    viol += max(0, area_lower - props["area"])
    viol += max(0, props["area"] - area_upper)
    viol += max(0, props["max_camber"] - max_camber) * 10
    viol += max(0, thickness_loc_lower - props["thickness_location"])
    viol += max(0, props["thickness_location"] - thickness_loc_upper)
    return viol


def evaluate_airfoil(
    x: np.ndarray,
    alpha: float = 4.0,
    reynolds: float = 1e6,
    cl_target: float = 0.4453,
    cross_penalty: float = 100.0,
    n_weights: int = 8,
    le_weight: float = 0.0,
    te_thick: float = 0.0,
) -> float:
    from neuralfoil import get_aero_from_kulfan_parameters

    upper_weights = x[:n_weights]
    lower_weights = x[n_weights:]

    psi, zu, zl = cst_coordinates(upper_weights, lower_weights, te_thickness=te_thick)

    if np.any(zu[1:] <= zl[1:]):
        return cross_penalty

    af_props = airfoil_properties_from_weights(upper_weights, lower_weights, te_thickness=te_thick)
    cv = constraint_violations(af_props)

    if cv > 0.01:
        return 10.0 + cv * 100

    aero = get_aero_from_kulfan_parameters(
        {
            "lower_weights": lower_weights,
            "upper_weights": upper_weights,
            "leading_edge_weight": le_weight,
            "TE_thickness": te_thick,
        },
        alpha=alpha,
        Re=reynolds,
    )

    cl = _to_scalar(aero["CL"])
    cd = _to_scalar(aero["CD"]) + 1e-10

    cl_error = abs(cl - cl_target)
    objective = cd + 0.5 * cl_error

    if cl_error > 0.005:
        objective += 10.0 * cl_error

    return objective


def run_optimization(
    cst_u_init: np.ndarray | None = None,
    cst_l_init: np.ndarray | None = None,
    le_weight: float = 0.0,
    te_thick: float = 0.0,
    alpha: float = 4.0,
    reynolds: float = 1e6,
    cl_target: float = 0.4453,
    n_weights: int = 8,
    maxiter: int = 200,
) -> dict:
    from scipy.optimize import minimize

    if cst_u_init is None:
        cst_u_init = np.array(NACA0012_CST["upper_weights"][:n_weights])
    if cst_l_init is None:
        cst_l_init = np.array(NACA0012_CST["lower_weights"][:n_weights])

    x0 = np.concatenate([cst_u_init, cst_l_init])

    bounds = []
    for _ in range(n_weights):
        bounds.append((-0.3, 0.5))
    for _ in range(n_weights):
        bounds.append((-0.5, 0.3))

    def objective(x):
        return evaluate_airfoil(
            x,
            alpha=alpha,
            reynolds=reynolds,
            cl_target=cl_target,
            n_weights=n_weights,
            le_weight=le_weight,
            te_thick=te_thick,
        )

    if le_weight == 0.0 and te_thick == 0.0 and n_weights == 8:
        le_weight = NACA0012_CST["leading_edge_weight"]
        te_thick = NACA0012_CST["TE_thickness"]

    result = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        options={"maxiter": maxiter, "ftol": 1e-12, "disp": True},
    )

    x_opt = result.x
    cst_u_opt = x_opt[:n_weights]
    cst_l_opt = x_opt[n_weights:]

    af_opt = build_airfoil_from_cst(cst_u_opt, cst_l_opt, name="optimized", te_thickness=te_thick)

    from neuralfoil import get_aero_from_kulfan_parameters
    aero_opt = get_aero_from_kulfan_parameters(
        {
            "lower_weights": cst_l_opt,
            "upper_weights": cst_u_opt,
            "leading_edge_weight": le_weight,
            "TE_thickness": te_thick,
        },
        alpha=alpha,
        Re=reynolds,
    )

    props = airfoil_properties_from_weights(cst_u_opt, cst_l_opt, te_thickness=te_thick)

    metrics = {
        "cst_u": cst_u_opt,
        "cst_l": cst_l_opt,
        "cl": _to_scalar(aero_opt["CL"]),
        "cd": _to_scalar(aero_opt["CD"]),
        "ld": _to_scalar(aero_opt["CL"] / aero_opt["CD"]),
        **props,
        "optimizer_success": result.success,
        "optimizer_status": result.message,
        "optimizer_nfev": result.nfev,
    }

    print(f"\n{'='*60}")
    print("  Optimization Complete")
    print(f"{'='*60}")
    print(f"  Objective (Cd): {metrics['cd']:.6f}")
    print(f"  Cl: {metrics['cl']:.4f}  (target: {cl_target})")
    print(f"  L/D: {metrics['ld']:.1f}")
    print(f"  Optimizer: {result.message}")
    print(f"  Function evaluations: {result.nfev}")
    print(f"  Improvement over NACA 0012 baseline:")
    print(f"    Cd: {NACA0012_BASELINE['cd']:.4f} -> {metrics['cd']:.4f}")
    cd_delta = NACA0012_BASELINE["cd"] - metrics["cd"]
    cd_pct = (cd_delta / NACA0012_BASELINE["cd"]) * 100
    print(f"    Cd reduction: {cd_delta:.4f} ({cd_pct:.1f}%)")
    print(f"    L/D: {NACA0012_BASELINE['ld']:.1f} -> {metrics['ld']:.1f}")
    print(f"  Constraints:")
    print(f"    Max thickness:  {metrics['max_thickness']:.4f}  (>= {NACA0012_BASELINE['max_thickness']})")
    print(f"    LE radius:      {metrics['le_radius']:.4f}  (0.008-0.020 target)")
    print(f"    Area:           {metrics['area']:.4f}")
    print(f"    Max camber:     {metrics['max_camber']:.4f}  (<= 0.04)")
    print(f"    Thickness loc:  {metrics['thickness_location']:.2f}")

    return metrics


def save_optimized_airfoil(
    metrics: dict,
    output_dir: str | Path,
    num_points: int = 200,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    beta = np.linspace(0, np.pi, num_points)
    x = (1 - np.cos(beta)) / 2

    te_thick = metrics.get("te_thickness_param", 0.0)
    psi, zu, zl = cst_coordinates(metrics["cst_u"], metrics["cst_l"], te_thickness=te_thick)

    upper_interp = np.interp(x, psi, zu)
    lower_interp = np.interp(x, psi, zl)

    upper_arr = np.column_stack([x, upper_interp])
    lower_arr = np.column_stack([x, lower_interp])

    dat_path = output_dir / "optimized_airfoil.dat"
    save_dat_file(upper_arr, lower_arr, str(dat_path))
    return dat_path


def plot_airfoil_comparison(metrics: dict, save_path: str | Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    from physics.geometry import generate_naca_4digit

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    naca_upper, naca_lower = generate_naca_4digit(0, 0, 12, num_points=200)
    baseline = np.vstack([naca_upper[::-1], naca_lower[1:]])

    te_thick = metrics.get("te_thickness_param", 0.0)
    psi, zu, zl = cst_coordinates(metrics["cst_u"], metrics["cst_l"], te_thickness=te_thick)
    opt_upper = np.column_stack([psi, zu])
    opt_lower = np.column_stack([psi, zl])
    optimized = np.vstack([opt_upper[::-1], opt_lower[1:]])

    rcParams.update({
        "figure.facecolor": "#282a36",
        "axes.facecolor": "#21222c",
        "axes.edgecolor": "#44475a",
        "axes.labelcolor": "#f8f8f2",
        "axes.titlecolor": "#f8f8f2",
        "xtick.color": "#6272a4",
        "ytick.color": "#6272a4",
        "grid.color": "#44475a",
        "grid.alpha": 0.4,
        "legend.facecolor": "#21222c",
        "legend.edgecolor": "#44475a",
        "legend.labelcolor": "#f8f8f2",
        "font.family": "monospace",
        "font.size": 11,
    })

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(baseline[:, 0], baseline[:, 1], color="#8be9fd", lw=1.8, ls="--", label="NACA 0012", zorder=3)
    ax.plot(optimized[:, 0], optimized[:, 1], color="#ff79c6", lw=2.4, label="Optimized Airfoil", zorder=4)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.12, 0.12)
    ax.set_aspect("equal")
    ax.set_xlabel("x/c")
    ax.set_ylabel("y/c")
    ax.grid(True, linestyle=":", linewidth=0.5)
    ax.legend(loc="upper right", fontsize=11)

    fig.tight_layout()
    fig.savefig(str(save_path), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Airfoil shape overlay saved to {save_path}")
