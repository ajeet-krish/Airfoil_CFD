from __future__ import annotations

from pathlib import Path

import numpy as np

from physics.aircraft import build_aircraft
from physics.geometry import generate_naca_4digit

OUTPUT_DIR = Path("output/cad")
OPTIMIZED_DAT = Path("output/cfd/optimized/optimized_airfoil.dat")


def main():
    if OPTIMIZED_DAT.exists():
        print("Loading optimized airfoil coordinates for wing/hstab...")
        coords = np.loadtxt(str(OPTIMIZED_DAT))
        print(f"  {len(coords)} points, t/c={coords[:,1].max() - coords[:,1].min():.3f}")
    else:
        print("Optimized airfoil not found, generating NACA 0012...")
        upper, lower = generate_naca_4digit(0, 0, 12)
        coords = np.vstack((upper[::-1], lower[1:]))

    print("Generating NACA 0012 coordinates for V-stab...")
    v_upper, v_lower = generate_naca_4digit(0, 0, 12)
    vstab_coords = np.vstack((v_upper[::-1], v_lower[1:]))

    step_path = OUTPUT_DIR / "aircraft.step"

    print("\nBuilding aircraft assembly...")
    assembly = build_aircraft(
        coords=coords,
        vstab_coords=vstab_coords,
        fuselage_length=10.0,
        filepath=str(step_path),
    )

    print(f"\nDone. STEP file: {step_path}")


if __name__ == "__main__":
    main()
