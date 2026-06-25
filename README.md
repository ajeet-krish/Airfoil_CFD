# CFD Airfoil Explorer

Automated CFD analysis of NACA 4-digit airfoils across multiple angles of attack using SU2 RANS (Spalart-Allmaras) on high-quality C-grid meshes with structured boundary layers. Includes airfoil shape optimization via CST parameterization + NeuralFoil surrogate + SU2 verification, structural analysis of wings under CFD loads (FElupe FEA), 3D wing CFD+FEA pipeline via 2.5D extrusion, and CadQuery wing CAD with internal spars/ribs.

## Features

- **Modular Architecture**: Decoupled `physics/` modules for geometry, meshing, solving, post-processing, optimization, structural analysis, CAD, and 3D meshing
- **C-Grid Meshing**: Hybrid structured/unstructured mesh via Gmsh (20 BL layers, Y+~1, 32K points)
- **3D Wing Meshing**: 2.5D extrusion of 2D C-grid into 3D prism/wedge/hexahedral mesh (1.9M cells, ~3.9s)
- **SU2 RANS Solver**: Compressible 2D and 3D RANS with Spalart-Allmaras turbulence model (MUSCL=NO, CFL ramp)
- **Airfoil Optimization**: CST parameterization with 16 Bernstein weights, NeuralFoil surrogate evaluation, SLSQP gradient-based optimizer, SU2 RANS verification
- **Structural Analysis**: CFD pressure mapped to 3D FEA wing via KDTree interpolation, FElupe linear elastic solve, von Mises stress, safety factor
- **Wing CAD**: CadQuery parametric wing with sweep, dihedral, twist, internal spar + ribs, STEP export
- **ParaView Visualizations**: Velocity contours, pressure fields, and structural deformation rendered interactively
- **Code-Generated Plots**: Convergence history, Cl/Cd curves, drag polar, airfoil shape overlays with experimental validation
- **Knowledge Graph**: Codebase mapped via graphify with 141 nodes, 282 edges, 13 communities — query relationships between modules
- **Extensible**: Add new airfoils by running the same pipeline, each gets its own results page

## Results

### NACA 0012 (2D, Multi-AoA)

| AoA | Regime | CL | CD | L/D | Status |
|-----|--------|---:|---:|---:|:------|
| 0deg | Symmetric Baseline | 0.0014 | 0.0749 | 0.0 | Converged |
| 4deg | Linear Lift | 0.4453 | 0.0969 | 4.6 | Converged |
| 8deg | High Lift | 0.8718 | 0.1644 | 5.3 | Converged |
| 12deg | Onset of Stall | 1.2647 | 0.2764 | 4.6 | Converged |
| 16deg | Deep Stall | 1.6082 | 0.4314 | 3.7 | Converged |

### Optimization (NACA 0012 at 4deg)

| Metric | Baseline | Optimized (NeuralFoil) | Optimized (SU2) | Change |
|--------|---------:|----------------------:|----------------:|:------:|
| CL | 0.4453 | 0.4453 | 0.3686 | -17.2% |
| CD | 0.0969 | 0.0052 | 0.0791 | -18.4% |
| L/D | 4.6 | 86.1 | 4.7 | +2.2% |

### FEA (Optimized Wing at 4deg, 3D CFD loads)

| Metric | Value |
|--------|------:|
| Max Tip Displacement | 521.6 mm |
| Peak von Mises Stress | 3082 MPa |
| Factor of Safety | 0.2 (solid wing, no spars) |
| Material | Al 7075-T6 |
| Wing Mesh | 1,241 nodes, 3,417 tetrahedra |

## Requirements

- SU2 8.4.0 (`SU2_CFD` in PATH)
- Gmsh Python SDK
- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (package manager)

## Usage

```bash
# Install dependencies
uv sync

# Multi-angle 2D analysis (5 AoAs, ~30 min)
uv run python run_tunnel.py

# Single-airfoil CST optimization (~2 sec + SU2 ~10 min)
uv run python run_optimization.py

# Structural FEA (optimized wing, 2D pressure -> 3D FEA, ~6 sec)
uv run python run_fea.py

# Structural FEA (NACA 0012 wing)
uv run python run_fea_naca0012.py

# 3D wing pipeline: mesh -> SU2 3D CFD -> FEA with 3D pressure (~25 min)
uv run python run_3d_pipeline.py

# Wing CAD (CadQuery STEP export with spar/ribs)
uv run python run_cad.py

# View results
open docs/index.html
```

## Project Structure

```
.
├── physics/
│   ├── geometry.py       NACA 4-digit coordinates with cosine spacing
│   ├── mesher.py         MeshGenerator — hybrid C-grid via Gmsh
│   ├── mesher3d.py       MeshGenerator3D — 2.5D extrusion to 3D volume mesh
│   ├── solver.py         SU2Config/SU2Config3D + SU2Solver + SU2Results
│   ├── post.py           (placeholder — field vis done in ParaView)
│   ├── analysis.py       Convergence, Cl/Cd, drag polar with validation
│   ├── validate.py       NACA 0012 experimental data (Ladson 1988)
│   ├── optimize.py       CST optimization + NeuralFoil + SU2 verification
│   ├── fea.py            FeaWingAnalysis — FElupe FEA with 2D/3D CFD loads
│   └── cad_wing.py       CadQuery wing with sweep/dihedral/twist, spar/ribs
├── run_tunnel.py          2D multi-angle pipeline orchestrator
├── run_optimization.py    CST optimization pipeline
├── run_fea.py             FEA for optimized wing (2D->3D pressure)
├── run_fea_naca0012.py    FEA for NACA 0012 wing
├── run_3d_pipeline.py     3D mesh -> SU2 3D CFD -> 3D pressure FEA
├── run_cad.py             CadQuery wing CAD STEP export
├── docs/
│   ├── index.html              Home page
│   ├── methodology.html        Theory, methodology, mesh design
│   ├── airfoil_analysis.html   NACA 0012 results with galleries
│   ├── optimization.html       Optimized airfoil results
│   ├── structural.html         FEA structural analysis results
│   ├── implementation.html     Code architecture and source
│   ├── css/style.css           Dracula theme
│   └── assets/images/          All images (ParaView + code-generated)
│       ├── naca0012/
│       └── optimized/
├── output/                     Simulation artifacts (gitignored)
│   ├── cfd/                    CFD results (2D + 3D)
│   ├── cad/                    STEP files
│   └── fea/                    FEA VTU + results
└── graphify-out/               Knowledge graph outputs (gitignored)
```

## Adding a New Airfoil

1. Update `NACA_PARAMS` in `run_tunnel.py` (m, p, t values)
2. Run `uv run python run_tunnel.py`
3. Copy `docs/airfoil_analysis.html` as template, update parameters and image paths

## Known Issues

1. **Surface VTU not generated in 2D**: SU2 v8.4.0 doesn't create surface_flow.vtu despite SURFACE_FILENAME being set.
2. **CD ~10x higher than experimental**: 1st-order scheme (MUSCL=NO) on C-grid with SA model adds numerical dissipation.
3. **No stall predicted**: CL continues increasing through 16deg. SA + 1st-order overpredicts attached flow.
4. **NeuralFoil optimism**: NeuralFoil predicts 94.7% Cd reduction; SU2 verification shows 18.4%.
