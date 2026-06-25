from __future__ import annotations

import json
from pathlib import Path

from physics.fea import FeaWingAnalysis
from physics.mesher3d import MeshGenerator3D
from physics.solver import SU2Config3D, SU2Solver

CONFIGS = [
    {
        "name": "NACA 0012 @ 4deg",
        "dat": Path("output/cfd/naca0012/aoa_4/airfoil.dat"),
        "output_dir": Path("output/cfd/naca0012_3d"),
        "fea_output_dir": Path("output/fea/naca0012_3d"),
        "docs_prefix": "naca0012",
    },
    {
        "name": "Optimized Wing @ 4deg",
        "dat": Path("output/cfd/optimized/optimized_airfoil.dat"),
        "output_dir": Path("output/cfd/optimized_3d"),
        "fea_output_dir": Path("output/fea/optimized_3d"),
        "docs_prefix": "optimized",
    },
]


def main():
    for cfg in CONFIGS:
        name = cfg["name"]
        dat_path = cfg["dat"]
        output_dir = cfg["output_dir"]
        fea_output_dir = cfg["fea_output_dir"]

        print(f"\n{'='*60}")
        print(f"  3D Pipeline: {name}")
        print(f"{'='*60}")

        if not dat_path.exists():
            print(f"  SKIP: {dat_path} not found. Run run_tunnel.py or run_optimization.py first.")
            continue

        output_dir.mkdir(parents=True, exist_ok=True)

        mesh_path = output_dir / "mesh_3d.su2"
        if not mesh_path.exists():
            print("  [1/3] Generating 3D volume mesh...")
            mesher = MeshGenerator3D(mesh_density=1.0, span_layers=30)
            mesher.generate(
                dat_file=str(dat_path),
                output_su2=str(mesh_path),
            )
        else:
            print("  [1/3] Mesh already exists, skipping...")

        surf_vtu_path = output_dir / "surface_3d_4.vtu"
        flow_vtu_path = output_dir / "flow_3d_4.vtu"
        if not surf_vtu_path.exists():
            print("  [2/3] Running SU2 3D CFD...")
            solver = SU2Solver()
            config = SU2Config3D(angle_of_attack=4.0, iterations=2000)
            solver.run(config, mesh_path, output_dir, timeout=3600)

            if not surf_vtu_path.exists():
                print("  WARNING: surface_3d_4.vtu not generated. SU2 may not have converged.")
                fallback = list(output_dir.glob("surface_*.vtu"))
                if fallback:
                    surf_vtu_path = fallback[0]
                    print(f"  Using fallback: {surf_vtu_path}")
                else:
                    print("  SKIP: No surface VTU available for FEA.")
                    continue
        else:
            print("  [2/3] SU2 results already exist, skipping...")

        fea_output_dir.mkdir(parents=True, exist_ok=True)
        fea_json = fea_output_dir / "fea_results.json"

        if not fea_json.exists():
            print("  [3/3] Running FEA with 3D surface pressure...")
            fea = FeaWingAnalysis(
                vtu_path="",
                dat_path=str(dat_path),
                output_dir=str(fea_output_dir),
                surface_vtu_3d_path=str(surf_vtu_path),
            )
            results = fea.run_with_3d()

            (fea_output_dir / "fea_results.json").write_text(
                json.dumps(results, indent=2, default=str)
            )

            print()
            print(f"  === {name} FEA Results ===")
            print(f"    Max tip displacement: {results['max_disp'] * 1000:.3f} mm")
            print(f"    Peak von Mises stress: {results['max_stress']:.1f} MPa")
            print(f"    Factor of Safety:     {results['factor_of_safety']:.1f}")
        else:
            print("  [3/3] FEA results already exist, skipping...")

    print(f"\n{'='*60}")
    print("  3D pipeline complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
