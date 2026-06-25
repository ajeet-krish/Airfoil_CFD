from __future__ import annotations

from pathlib import Path

from physics.cad_wing import generate_wing, load_coordinates


def main():
    configs = [
        {
            "name": "NACA 0012 @ 4deg",
            "dat": Path("output/cfd/naca0012/aoa_4/airfoil.dat"),
            "step": Path("output/cad/naca0012_wing.step"),
        },
        {
            "name": "Optimized Wing @ 4deg",
            "dat": Path("output/cfd/optimized/optimized_airfoil.dat"),
            "step": Path("output/cad/optimized_wing.step"),
        },
    ]

    for cfg in configs:
        print(f"\n=== {cfg['name']} ===")
        coords = load_coordinates(cfg["dat"])
        print(f"  Loaded {len(coords)} coordinates from {cfg['dat']}")

        generate_wing(coords, filepath=cfg["step"])
        print(f"  STEP exported: {cfg['step']}")

    print("\nBoth wings generated.")


if __name__ == "__main__":
    main()
