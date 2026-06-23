from __future__ import annotations

import shutil
from pathlib import Path

from physics.geometry import generate_naca_4digit, save_dat_file
from physics.mesher import MeshGenerator
from physics.solver import SU2Config, SU2Solver
from physics.post import Visualizer
from physics.analysis import (
    plot_convergence,
    plot_cl_alpha,
    plot_cd_alpha,
    plot_drag_polar,
)
from physics.validate import get_cl_alpha, get_cd_alpha, get_drag_polar

# --- Parameters ---
NACA_NAME = "NACA 0012"
NACA_PARAMS = (0, 0, 12)  # m, p, t
ANGLES_OF_ATTACK = [0, 4, 8, 12, 16]
BASE_DIR = Path("./output")

REGIME_LABELS = {
    0: "Symmetric Baseline",
    4: "Linear Lift",
    8: "High Lift",
    12: "Onset of Stall",
    16: "Deep Stall",
}


def main():
    if BASE_DIR.exists():
        shutil.rmtree(BASE_DIR)
    BASE_DIR.mkdir(parents=True)

    solver = SU2Solver()
    mesher = MeshGenerator(mesh_density=1.0)
    viz = Visualizer()

    all_results: list[tuple[float, SU2Results]] = []

    for aoa in ANGLES_OF_ATTACK:
        print(f"\n{'='*60}")
        print(f"  AoA = {aoa}° — {REGIME_LABELS[aoa]}")
        print(f"{'='*60}")

        aoa_dir = BASE_DIR / f"aoa_{aoa}"
        aoa_dir.mkdir(parents=True, exist_ok=True)

        # ── Step 1: Geometry ──
        print("  [1/4] Generating geometry...")
        upper, lower = generate_naca_4digit(*NACA_PARAMS)
        dat_path = aoa_dir / "airfoil.dat"
        save_dat_file(upper, lower, str(dat_path))

        # ── Step 2: Mesh ──
        print("  [2/4] Generating C-grid mesh with boundary layers...")
        mesh_path = aoa_dir / "mesh.su2"
        mesher.generate(str(dat_path), str(mesh_path))

        # ── Step 3: Run SU2 ──
        print("  [3/4] Running SU2 CFD solver...")
        config = SU2Config(angle_of_attack=aoa)

        results = solver.run(config, mesh_path, aoa_dir, timeout=600)

        if results.history:
            print(
                f"    Iterations: {results.iterations}"
                f"  CL={results.cl:.6f}  CD={results.cd:.6f}"
                f"  Converged: {results.converged}"
            )
        else:
            print("    WARNING: No convergence history parsed")

        all_results.append((aoa, results))

        # ── Step 4: Visualizations ──
        print("  [4/4] Rendering visualizations...")
        vtu_file = aoa_dir / f"flow_results_{aoa}.vtu"
        surface_vtu = aoa_dir / f"surface_flow_{aoa}.vtu"

        viz.export_velocity(str(vtu_file), str(aoa_dir), aoa=aoa)
        viz.export_pressure(str(vtu_file), str(aoa_dir), aoa=aoa)
        viz.export_mesh_visual(str(vtu_file), str(aoa_dir), aoa=aoa)
        viz.export_surface_cp(str(surface_vtu), str(aoa_dir), aoa=aoa)
        plot_convergence(results.history, str(aoa_dir), aoa=aoa)

    # ── Aggregate plots ──
    print(f"\n{'='*60}")
    print("  Generating aggregate Cl/Cd curves...")
    print(f"{'='*60}")

    experimental_cl = get_cl_alpha()
    experimental_cd = get_cd_alpha()
    experimental_polar = get_drag_polar()

    plot_cl_alpha(all_results, str(BASE_DIR), experimental=experimental_cl)
    plot_cd_alpha(all_results, str(BASE_DIR), experimental=experimental_cd)
    plot_drag_polar(all_results, str(BASE_DIR), experimental=experimental_polar)

    # ── Sync images to docs/assets/images/ ──
    print(f"\n{'='*60}")
    print("  Syncing images to docs/assets/images/...")
    print(f"{'='*60}")

    docs_img = Path("./docs/assets/images")
    docs_img.mkdir(parents=True, exist_ok=True)

    # Aggregate plots
    for f in BASE_DIR.glob("*.png"):
        shutil.copy2(f, docs_img / f.name)

    # Per-AoA images
    for aoa in ANGLES_OF_ATTACK:
        aoa_src = BASE_DIR / f"aoa_{aoa}"
        aoa_dst = docs_img / f"aoa_{aoa}"
        aoa_dst.mkdir(parents=True, exist_ok=True)
        for f in aoa_src.glob("*.png"):
            shutil.copy2(f, aoa_dst / f.name)

    print(f"\n  Done. Open docs/index.html in your browser.")


if __name__ == "__main__":
    main()
