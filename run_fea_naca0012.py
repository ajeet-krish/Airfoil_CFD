from __future__ import annotations

from pathlib import Path

from physics.fea import FeaWingAnalysis

VTU_PATH = Path("output/cfd/naca0012/aoa_4/flow_results_4.vtu")
DAT_PATH = Path("output/cfd/naca0012/aoa_4/airfoil.dat")
OUTPUT_DIR = Path("output/fea/naca0012")


def main():
    fea = FeaWingAnalysis(
        vtu_path=str(VTU_PATH),
        dat_path=str(DAT_PATH),
        output_dir=str(OUTPUT_DIR),
    )
    results = fea.run()

    print()
    print("=== FEA Results (NACA 0012 @ 4deg) ===")
    print(f"  Max tip displacement: {results['max_disp'] * 1000:.3f} mm")
    print(f"  Peak von Mises stress: {results['max_stress']:.1f} MPa")
    print(f"  Factor of Safety:     {results['factor_of_safety']:.1f}")
    print(f"  VTU file:             {results['vtu_path']}")


if __name__ == "__main__":
    main()
