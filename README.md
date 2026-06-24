# CFD Airfoil Explorer

Automated CFD analysis of NACA 4-digit airfoils across multiple angles of attack using SU2 RANS (Spalart-Allmaras) on high-quality C-grid meshes with structured boundary layers. Field visualizations rendered in ParaView; convergence and aggregate plots generated via matplotlib. Static multi-page Dracula-themed portfolio website.

## Features

- **Modular Architecture**: Decoupled `physics/` modules — geometry, meshing, solving, post-processing
- **C-Grid Meshing**: Hybrid structured/unstructured mesh via Gmsh (20 BL layers, Y+~1, 32K points)
- **SU2 RANS Solver**: Compressible RANS with Spalart-Allmaras turbulence model
- **ParaView Visualizations**: Velocity contours and pressure fields rendered interactively
- **Code-Generated Plots**: Convergence history, Cl/Cd curves, drag polar with experimental validation
- **Extensible**: Add new airfoils by running the same pipeline — each gets its own results page

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
│   ├── post.py          (placeholder — field vis done in ParaView)
│   ├── analysis.py      Convergence, Cl/Cd, drag polar with validation
│   └── validate.py      NACA 0012 experimental data (Ladson 1988)
├── run_tunnel.py        Main pipeline orchestrator
├── docs/
│   ├── index.html              Home page
│   ├── methodology.html        Theory, methodology, mesh design
│   ├── implementation.html     Code architecture and source
│   ├── paraview.html           ParaView walkthrough
│   ├── airfoils/
│   │   └── naca0012.html       NACA 0012 results
│   ├── css/style.css           Dracula theme
│   └── assets/images/          All images (ParaView renders + code-generated plots)
└── output/                     Simulation artifacts only (gitignored)
```

## Adding a New Airfoil

1. Update `NACA_PARAMS` in `run_tunnel.py` (m, p, t values)
2. Run the pipeline
3. Copy `docs/airfoils/naca0012.html` as template, update parameters and image paths

## GitHub Pages

The website lives in `docs/` and can be hosted via [GitHub Pages](https://ajeet.github.io/Airfoil_CFD). After running the pipeline:

```bash
git add docs/ && git commit -m "Update results" && git push
```

## License

MIT
