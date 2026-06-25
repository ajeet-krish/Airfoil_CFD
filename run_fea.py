from __future__ import annotations

from pathlib import Path

from physics.fea import FeaWingAnalysis

VTU_PATH = Path("output_optimized/flow_results_optimized.vtu")
DAT_PATH = Path("output_optimized/optimized_airfoil.dat")
OUTPUT_DIR = Path("output_optimized")


def main():
    fea = FeaWingAnalysis(
        vtu_path=str(VTU_PATH),
        dat_path=str(DAT_PATH),
        output_dir=str(OUTPUT_DIR),
    )
    results = fea.run()

    print()
    print("=== FEA Results ===")
    print(f"  Max tip displacement: {results['max_disp'] * 1000:.3f} mm")
    print(f"  Peak von Mises stress: {results['max_stress']:.1f} MPa")
    print(f"  Factor of Safety:     {results['factor_of_safety']:.1f}")
    print(f"  VTU file:             {results['vtu_path']}")


if __name__ == "__main__":
    main()
