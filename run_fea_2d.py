from __future__ import annotations

from pathlib import Path

from physics.fea2d import Fea2dAnalysis


def main():
    configs = [
        {
            "label": "NACA 0012",
            "vtu": "output/cfd/naca0012/aoa_4/flow_results_4.vtu",
            "dat": "output/cfd/naca0012/aoa_4/airfoil.dat",
            "out": "output/fea/naca0012",
        },
        {
            "label": "Optimized",
            "vtu": "output/cfd/optimized/flow_results_optimized.vtu",
            "dat": "output/cfd/optimized/optimized_airfoil.dat",
            "out": "output/fea/optimized_2d",
        },
    ]

    all_results = {}
    for cfg in configs:
        print(f"\n{'='*60}")
        print(f"  2D FEA: {cfg['label']} at 4deg")
        print(f"{'='*60}")
        fea = Fea2dAnalysis(
            vtu_path=cfg["vtu"],
            dat_path=cfg["dat"],
            output_dir=cfg["out"],
            label=cfg["label"],
        )
        results = fea.run()
        all_results[cfg["label"]] = results

    print(f"\n{'='*60}")
    print("  2D FEA Summary")
    print(f"{'='*60}")
    for label, r in all_results.items():
        print(f"  {label}:")
        print(f"    Max displacement: {r['max_disp'] * 1000:.3f} mm")
        print(f"    Peak von Mises:   {r['max_stress']:.1f} MPa")
        print(f"    Factor of Safety: {r['factor_of_safety']:.1f}")
    print("  Done.")


if __name__ == "__main__":
    main()
