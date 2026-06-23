# Airfoil CFD Pipeline

Automated CFD analysis of NACA 4-digit airfoils across multiple angles of attack using SU2 RANS (Spalart-Allmaras) on high-quality C-grid meshes with structured boundary layers. Generates Dracula-themed visualizations and a static portfolio website.

## Features

- **Modular Architecture**: Decoupled `physics/` modules — geometry, meshing, solving, post-processing
- **C-Grid Meshing**: Hybrid structured/unstructured mesh via Gmsh (20 BL layers, Y+~1, 32K points)
- **SU2 RANS Solver**: Compressible RANS with Spalart-Allmaras turbulence model
- **Rich Visualizations**: Velocity contours with streamlines, pressure field, mesh topology, convergence history
- **Experimental Validation**: Lift curve, drag polar with Ladson (1988) overlay
- **Portfolio Website**: Static Dracula-themed HTML with expandable source code

## Results — NACA 0012

| AoA | Regime | CL | CD | L/D | Status |
|-----|--------|---:|---:|---:|:------|
| 0° | Symmetric Baseline | 0.0014 | 0.0749 | 0.0 | Converged |
| 4° | Linear Lift | 0.4453 | 0.0969 | 4.6 | Converged |
| 8° | High Lift | 0.8718 | 0.1644 | 5.3 | Converged |
| 12° | Onset of Stall | 1.2647 | 0.2764 | 4.6 | Converged |
| 16° | Deep Stall | 1.6082 | 0.4314 | 3.7 | Converged |

## Requirements

- SU2 8.4.0 (`SU2_CFD` in PATH)
- Gmsh Python SDK
- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (package manager)

## Usage

```bash
# Install dependencies
uv sync

# Run the full pipeline (5 AoAs, ~30 min)
uv run python run_tunnel.py

# View results
open docs/index.html
```

## Project Structure

```
.
├── physics/
│   ├── geometry.py      NACA 4-digit coordinates with cosine spacing
│   ├── mesher.py        MeshGenerator — hybrid C-grid via Gmsh
│   ├── solver.py        SU2Config + SU2Solver + SU2Results
│   ├── post.py          Visualizer — matplotlib velocity/pressure/mesh
│   ├── analysis.py      Convergence, Cl/Cd, drag polar with validation
│   └── validate.py      NACA 0012 experimental data (Ladson 1988)
├── run_tunnel.py        Main pipeline orchestrator
├── docs/
│   ├── index.html       Static portfolio website
│   ├── css/style.css    Dracula theme
│   ├── assets/images/   Synced visualization PNGs
│   └── build_site.py    HTML generator (regenerates index.html from source)
└── output/              Generated results (gitignored)
```

## GitHub Pages

The website lives in `docs/` and can be hosted via [GitHub Pages](https://ajeet.github.io/Airfoil_CFD). After running the pipeline:

```bash
# Sync images (automatic in run_tunnel.py)
# Then commit and push
git add docs/ && git commit -m "Update results" && git push
```

## License

MIT
