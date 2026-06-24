from __future__ import annotations

import shutil
from pathlib import Path

from physics.analysis import plot_convergence
from physics.mesher import MeshGenerator
from physics.optimize import (
    NACA0012_BASELINE,
    run_optimization,
    save_optimized_airfoil,
    plot_airfoil_comparison,
)
from physics.solver import SU2Config, SU2Solver

AOI = 4
RE = 1e6
MACH = 0.15
BASE_DIR = Path("./output_optimized")
DOCS_IMG = Path("./docs/assets/images/optimized")


def main():
    if BASE_DIR.exists():
        shutil.rmtree(BASE_DIR)
    BASE_DIR.mkdir(parents=True)

    # ── Step 1: Optimize ──
    print(f"\n{'='*60}")
    print(f"  Optimizing NACA 0012 for AoA={AOI}deg, Re={RE:.0e}, M={MACH}")
    print(f"{'='*60}")

    metrics = run_optimization(
        alpha=AOI,
        reynolds=RE,
        cl_target=NACA0012_BASELINE["cl"],
    )

    # ── Step 2: Save optimized airfoil coordinates ──
    print(f"\n{'='*60}")
    print("  Saving optimized airfoil geometry...")
    print(f"{'='*60}")
    dat_path = save_optimized_airfoil(metrics, str(BASE_DIR))

    # ── Step 2.5: Airfoil shape overlay plot ──
    print(f"\n{'='*60}")
    print("  Rendering airfoil shape comparison plot...")
    print(f"{'='*60}")
    plot_airfoil_comparison(metrics, str(DOCS_IMG / "airfoil_shape_overlay.png"))

    # ── Step 3: Mesh ──
    print(f"\n{'='*60}")
    print("  Generating C-grid mesh for optimized airfoil...")
    print(f"{'='*60}")
    mesher = MeshGenerator(mesh_density=1.0)
    mesh_path = BASE_DIR / "mesh.su2"
    mesher.generate(str(dat_path), str(mesh_path))

    # ── Step 4: Run SU2 ──
    print(f"\n{'='*60}")
    print("  Running SU2 CFD solver on optimized airfoil...")
    print(f"{'='*60}")
    solver = SU2Solver()
    config = SU2Config(angle_of_attack=AOI)
    results = solver.run(config, mesh_path, BASE_DIR, timeout=600)

    if results.history:
        print(
            f"  Iterations: {results.iterations}"
            f"  CL={results.cl:.6f}  CD={results.cd:.6f}"
            f"  Converged: {results.converged}"
        )
    else:
        print("  WARNING: No convergence history parsed")

    # ── Step 5: Convergence plot ──
    print(f"\n{'='*60}")
    print("  Rendering convergence plot...")
    print(f"{'='*60}")
    DOCS_IMG.mkdir(parents=True, exist_ok=True)
    plot_convergence(results.history, str(DOCS_IMG), aoa=AOI)

    # ── Step 6: Print comparison ──
    print(f"\n{'='*60}")
    print("  Comparison: NACA 0012 vs Optimized at 4deg")
    print(f"{'='*60}")
    print(f"  {'Metric':<20} {'Baseline':<16} {'Optimized (NeuralFoil)':<24} {'Optimized (SU2)':<16}")
    print(f"  {'-'*20} {'-'*16} {'-'*24} {'-'*16}")
    print(f"  {'CL':<20} {NACA0012_BASELINE['cl']:<16.4f} {metrics['cl']:<24.4f} {results.cl:<16.6f}")
    print(f"  {'CD':<20} {NACA0012_BASELINE['cd']:<16.4f} {metrics['cd']:<24.4f} {results.cd:<16.6f}")
    if results.cd > 0:
        ld_su2 = results.cl / results.cd
    else:
        ld_su2 = 0
    print(f"  {'L/D':<20} {NACA0012_BASELINE['ld']:<16.1f} {metrics['ld']:<24.1f} {ld_su2:<16.1f}")

    print(f"\n  Results saved to {DOCS_IMG}/")
    print(f"  VTU flow file: {BASE_DIR}/flow_results_{AOI}.vtu")
    print(f"  Open in ParaView to render velocity and pressure contours.")

    print(f"\n  To add a new airfoil results page:")
    print(f"    cp docs/airfoils/naca0012_optimized.html docs/airfoils/your_airfoil.html")
    print(f"    # Update parameters and image paths")


if __name__ == "__main__":
    main()
