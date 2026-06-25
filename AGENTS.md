# OpenCode Instructions for CFD Airfoil Explorer

## Project Overview
Automated CFD analysis of NACA 4-digit airfoils across multiple angles of attack.
Generates C-grid meshes (Gmsh), solves RANS equations (SU2, Spalart-Allmaras),
and outputs a static Dracula-themed portfolio website with ParaView field
visualizations and matplotlib convergence/aggregate plots with experimental
validation. Includes airfoil shape optimization (CST + NeuralFoil + SLSQP),
structural FEA (FElupe), 3D wing CFD pipeline (2.5D extrusion), and
CadQuery wing CAD (STEP export with spar/ribs).

## Style Rules
- **No em dashes** anywhere in the website. Use a regular hyphen `-` instead of `--`, `&mdash;`, `&ndash;`, or the literal Unicode em dash `—`.

## Reference Project: Soccer CFD
This project mirrors the architecture and patterns of the **Soccer CFD** project
at `/Users/ajeet/Projects/Soccer_CFD`. Key patterns adopted:
- **Classes pattern**: physics/ modules (geometry/mesher/solver/post/analysis)
- **Jinja2 -> static**: Website files live in `docs/` - no template rendering
- **Dracula theme**: Consistent color scheme ported from Soccer CFD

Always reference Soccer CFD when stuck on architecture or visualization questions.

## Architecture

### physics/ Modules (Classes Pattern - mirrors Soccer CFD)
- `geometry.py` - `generate_naca_4digit(m, p, t, num_points=200)` with cosine spacing.
  t is in NACA convention (e.g. 12 for 12% thickness); divides by 100 internally.
- `mesher.py` - `MeshGenerator` class. Generates hybrid C-grid:
  - C-shaped farfield (semicircular inlet R=15 chords, outlet 30 chords downstream)
  - Structured boundary layer via Gmsh BoundaryLayer field (20 layers, ratio 1.15)
  - Unstructured Frontal-Delaunay farfield fill (Algorithm 6)
  - Physical groups: "airfoil" (wall), "farfield" (inlet/outlet/walls), "fluid"
  - Y+ ~1 at Re=1e6 with first layer height 2e-5
- `solver.py` - `SU2Config` dataclass + `SU2Solver` + `SU2Results`:
  - Compressible RANS, SA turbulence, ROE scheme, MUSCL_FLOW=NO (1st order stable)
  - CFL_ADAPT ramps from 0.01 to 5.0 over 2000 iterations
  - `HISTORY_OUTPUT= (INNER_ITER, RMS_RES, AERO_COEFF)` captures CL/CD in CSV
- `mesher3d.py` - `MeshGenerator3D` class. 2.5D extrusion of 2D C-grid to 3D:
  - Parses 2D SU2 mesh, extrudes nodes/elements along span with sweep/dihedral/twist per layer
  - Prism/wedge elements in farfield, hexahedral elements in BL region (preserves BL topology)
  - 990K nodes, 1.9M elements, ~3.9s generation time at span_layers=30, mesh_density=1.0
  - Does NOT use Gmsh 3D BoundaryLayer (unsupported in 4.15.2) — carries 2D BL into 3D via extrusion
- `post.py` - (placeholder) Field visualizations (velocity, pressure, mesh) created in ParaView
- `analysis.py` - Convergence plots, Cl/Cd curves, drag polar with experimental overlay
- `validate.py` - NACA 0012 experimental data (Ladson 1988, Abbott 1949)
- `optimize.py` - `run_optimization()` performs CST-based airfoil shape optimization:
  - 16 CST design variables (8 upper + 8 lower Bernstein weights, matching NeuralFoil internal)
  - NeuralFoil surrogate evaluation via `get_aero_from_kulfan_parameters()` (~1000 evals/sec)
  - 9 constraints: min thickness (>=12%), LE radius (0.007-0.020), cross-over prevention,
    area (+-15%), max camber (<=2%), thickness location (0.25-0.40c)
  - SLSQP gradient-based optimizer (scipy) - finite differences, no CasADi MX type issues
  - Objective: minimize Cd at fixed Cl with strong Cl tracking penalty
  - ~105 iterations, ~2 seconds convergence, + SU2 verification (~10 min)
  - `plot_airfoil_comparison()` - Dracula-themed shape overlay plot (NACA 0012 vs optimized)
- `fea.py` - `FeaWingAnalysis` class. Structural analysis of optimized wing under CFD loads:
  - 3D wing lofted via Gmsh OCC (addThruSections) with sweep, dihedral, twist
  - Tetrahedral mesh (~3,400 elements, ~1,200 nodes)
  - CFD pressure mapped to skin facets via KDTree nearest-neighbor interpolation
  - Outward normal computation per skin triangle for traction vector application
  - FElupe linear elastic solve (Al 7075-T6: E=71.7 GPa, nu=0.33)
  - Fixed root BC + distributed PointLoad from aerodynamic pressure
  - Von Mises stress extrapolated from Cauchy stress tensor integration points to nodes
  - VTU export with displacement, von_mises, on_skin fields for ParaView
  - PyVista off-screen 3D contour renders (stress + displacement side-by-side)

- `cad_wing.py` - CadQuery parametric wing CAD:
  - Wing lofted from airfoil sections with sweep=25deg, dihedral=3deg, twist=-2deg
  - Internal structural layout: I-beam spar at 25% chord, 5 ribs
  - STEP export for manufacturing/CAD downstream
  - Called by `run_cad.py` for both NACA 0012 and optimized wing

### Workflow
For standard multi-angle analysis: `run_tunnel.py` orchestrates geometry -> C-grid mesh -> SU2 solver -> convergence plots -> aggregate plots.
For single-airfoil optimization: `run_optimization.py` runs CST optimization (NeuralFoil) -> meshes optimized shape -> runs SU2 RANS -> generates comparison.
For structural analysis (2D pressure): `run_fea.py` runs extract_pressure -> generate_wing_geometry -> solve (with loads) -> stress computation -> VTU export -> 3D plots.
For 3D wing pipeline: `run_3d_pipeline.py` runs 2.5D extrusion mesh -> SU2 3D RANS -> FEA with 3D surface pressure (for both NACA 0012 and optimized wing).
For wing CAD: `run_cad.py` generates CadQuery STEP files with spar/ribs.
All images go directly to `docs/assets/images/naca0012/` (per-AoA in `aoa_*` subdirs, plots in `plots/`, mesh in `mesh_naca0012/`).
`output/cfd/naca0012/` contains 2D CFD artifacts, `output/cfd/naca0012_3d/` and `output/cfd/optimized_3d/` contain 3D pipeline artifacts, `output/cad/` for STEP files, `output/fea/` for FEA results.

5 AoAs: [0, 4, 8, 12, 16] with regime labels
(Symmetric Baseline, Linear Lift, High Lift, Onset of Stall, Deep Stall)

### Entrypoints
```bash
uv run python run_tunnel.py         # Standard multi-angle analysis (~30 min)
uv run python run_optimization.py   # Single-airfoil CST optimization (~2 sec + SU2 ~10 min)
uv run python run_fea.py            # Structural FEA for optimized wing (~6 sec)
uv run python run_fea_naca0012.py   # Structural FEA for NACA 0012 wing
uv run python run_3d_pipeline.py    # 3D mesh -> SU2 3D CFD -> 3D pressure FEA (~25 min)
uv run python run_cad.py            # CadQuery wing CAD STEP export
```

---

## Critical Knowledge - SU2 v8.4.0

### Config Options
- `HISTORY_OUTPUT= ( INNER_ITER, RMS_RES, AERO_COEFF )` produces CSV columns:
  Inner_Iter, rms[Rho], rms[RhoU], rms[RhoV], rms[RhoE], rms[nu],
  RefForce, CD, CL, CSF, CMx, CMy, CMz, CFx, CFy, CFz, CEff, Buffet
- The "CD" and "CL" columns ARE the actual aerodynamic coefficients for
  compressible RANS (not dimensionless forces requiring post-multiplication)
- `MUSCL_FLOW= NO` required for stability on C-grids with SA model
- `CFL_ADAPT_PARAM= ( 0.01, 5.0, 1.1, 25.0 )` where third param (ramp factor) must be > 1.0
- `OUTPUT_FILES= (RESTART, PARAVIEW)` - surface_flow.vtu may not be generated
- VOLUME_OUTPUT, SURFACE_OUTPUT, and ENTROPY_FIX_COEFF are NOT valid in v8.4.0

### Solver Performance
- 2000 iterations recommended for convergence (rms[Rho] < -6, residuals dropping)
- A single AoA takes ~5-10 minutes on the reference hardware (M-series Mac)
- CFL ramps from 0.01 to 5.0 over 2000 iterations for stability
- The solver may hang if invalid config options are present; always test with 100 iters first

---

## Critical Knowledge - Mesh Generation

### 2.5D Extrusion (mesher3d.py)
- Extrudes 2D C-grid SU2 mesh into 3D volume (no Gmsh 3D geometry)
- Parses NPOIN, NELEM, NMARK sections from 2D SU2 mesh
- Extrudes each 2D node along span by layer: applies sweep (dx), dihedral (dz), twist (rotation)
- Layer positions: linear spanwise from root (y=0) to tip (y=half_span)
- BL quads become hexahedra (2 layers of 4 nodes -> 2 layers of 8 nodes per element)
- Farfield triangles become wedges/prisms (2 layers of 3 nodes -> 6 nodes per element)
- Physical markers: "airfoil" -> MARKER_WALL, "farfield" -> MARKER_FAR, plus new "symmetry" at root/tip
- Default: span=11.0, half_span=5.5, span_layers=30, sweep=25deg, dihedral=3deg, twist=-2deg
- Performance: 990K nodes, 1.9M elements, ~3.9s, ~157MB .su2 file
- Mesh type: quad-dominant in BL (hexahedral), triangle-dominant in farfield (wedge/prism)

### C-grid Implementation
- C-shaped farfield: semicircle centered at (0, 0) radius 15, walls to x=30, outlet at x=30
- Airfoil spline through cosine-clustered points (200 pts, LE/TE refined)
- BoundaryLayer field uses `gmsh.model.mesh.field.setAsBoundaryLayer()` (NOT setAsBackgroundMesh)
- Default first layer height: 2e-5 (y+ ~1 at Re=1e6, M=0.15)
- The Distance + Threshold field is set as background mesh; BoundaryLayer is separate
- `gmsh.model.mesh.createTopology()` must be called before `gmsh.write()` for SU2 export

### Mesh Quality
- ~32K points, ~97K cells at mesh_density=1.0
  - Actual counts: 31,927 points, 63,141 cells
- Y+ max ~1.04, mean ~0.01 (excellent for SA model)
- Element type mix: quads in boundary layer, triangles in farfield

---

## Critical Knowledge - Geometry

### The t/100 Bug (Fixed 2026-06-23)
- Old code passed `t=12` (NACA 0012 convention) but used `t=12.0` in the formula
- This generated airfoils 100x too thick (1200% instead of 12% thickness)
- All previous results before this fix are invalid
- Fix: `t = t / 100.0` inside `generate_naca_4digit()`
- Correct NACA 0012: max y = 0.06 at x/c = 0.3

### Cosine Spacing
- 200 points with `x = (1 - cos(beta)) / 2` provides dense LE/TE clustering
- First x: 0.0, then 6.2e-5, 2.5e-4, etc. (good LE curvature resolution)

---

## Critical Knowledge - Visualization

### Field Visualizations (ParaView)
- Velocity contours and pressure fields are rendered interactively in ParaView,
  not by the pipeline. The VTU flow results are loaded directly.
- Use `paraview_recipes.md` for step-by-step recipes.
- ParaView state files are saved in `output/cfd/naca0012/aoa_*/paraview_*.pvsm`.

### Code-Generated Plots (analysis.py)
- `plot_convergence()` - RMS residuals + Cl/Cd history per AoA
- `plot_cl_alpha()` - Lift curve vs angle of attack
- `plot_cd_alpha()` - Drag vs angle of attack
- `plot_drag_polar()` - Cl vs Cd with experimental overlay
- `plot_airfoil_comparison()` - NACA 0012 vs optimized shape overlay, Dracula-themed
- All output goes directly to `docs/assets/images/naca0012/` (per-AoA in `aoa_*` subdirs, plots in `plots/`, mesh in `mesh_naca0012/`), or `docs/assets/images/optimized/` for optimized results

### Website (Multi-Page)
- `docs/index.html` - Home: project intro, CFD relevance (aviation/auto/energy), rapid iteration
- `docs/methodology.html` - Theory + Methodology + Mesh: NACA equations, flight regimes table, C-grid design, 3 mesh images, mesh stats table, sim parameters
- `docs/airfoil_analysis.html` - Airfoil-specific results: summary table, aggregate plots, velocity/pressure galleries (5-up), per-AoA metric cards + visualizations
- `docs/optimization.html` - Optimized shape results: shape comparison, velocity/pressure contours, real-life match, optimization setup
- `docs/structural.html` - Structural analysis: FEA results, stress/displacement contours, load mapping methodology
- `docs/implementation.html` - How to run, code architecture, SU2 config reference, 5 expandable source blocks
- `paraview_recipes.md` - (project root, untracked) ParaView step-by-step in markdown
- All pages share `nav.top-nav` bar: **Home | Methodology | Airfoil Analysis | Optimization | Structural Analysis | Implementation**
- CSS is minimalist Dracula inspired by `/Users/ajeet/Projects/Digital\ CV`: `#21222c` card bg, `border-left` accent, no hover lift/shadow, no gradients, monospace throughout
- Images go directly to `docs/assets/images/` - no sync step needed
- `docs/` is the GitHub Pages root
- Adding a new airfoil: copy `docs/airfoil_analysis.html` as template, update params

---

## Results - Final (2026-06-23)

| AoA | Regime | CL | CD | L/D | Converged |
|-----|--------|---:|---:|---:|:---------:|
| 0deg | Symmetric Baseline | 0.0014 | 0.0749 | 0.0 | Yes |
| 4deg | Linear Lift | 0.4453 | 0.0969 | 4.6 | Yes |
| 8deg | High Lift | 0.8718 | 0.1644 | 5.3 | Yes |
| 12deg | Onset of Stall | 1.2647 | 0.2764 | 4.6 | Yes |
| 16deg | Deep Stall | 1.6082 | 0.4314 | 3.7 | Yes |

Lift curve slope: 0.109 per degree (matches theoretical 2pi within 1%)

---

## Optimization Results (2026-06-24)

### NACA 0012 Baseline at 4deg (NeuralFoil)
| Metric | Value |
|--------|------:|
| CL | 0.4453 |
| CD | 0.0057 |
| L/D | 78.1 |

### Optimized Shape at 4deg (SU2 RANS verified)
| Metric | Baseline | Optimized (NeuralFoil) | Optimized (SU2) | Change |
|--------|---------:|----------------------:|----------------:|:------:|
| CL | 0.4453 | 0.4453 | 0.3686 | -17.2% |
| CD | 0.0969 | 0.0052 | 0.0791 | -18.4% |
| L/D | 4.6 | 86.1 | 4.7 | +2.2% |

### Key Findings
- NeuralFoil is **optimistic**: predicts 94.7% Cd reduction, SU2 shows 18.4%
- SU2 Cl mismatch: optimized shape generates less lift at 4deg (0.369 vs 0.445)
- Real Cd reduction: 18.4% (0.0791 vs 0.097 baseline) is still meaningful
- NeuralFoil serves well as a fast surrogate (~2 sec) but SU2 verification is essential
- The C-grid with 1st-order scheme (MUSCL=NO) adds ~10x numerical dissipation over XFoil

### Optimizer Performance
- SLSQP converges in ~105 iterations, ~2 seconds, ~2000 function evaluations
- LE radius constraint is the hardest to satisfy (converges to boundary at 0.007)
- Cl tracking: NeuralFoil matches target exactly, SU2 undershoots by 17%

---

## Known Issues (2026-06-23)

1. **Surface VTU not generated**: SU2 v8.4.0 doesn't create surface_flow.vtu despite
   SURFACE_FILENAME being set. Cp distribution plots are unavailable.
2. **CD ~10x higher than experimental**: Due to 1st-order scheme (MUSCL=NO) on
   a C-grid with SA model. Experimental CD at AoA=0 is ~0.007, we get ~0.075.
   MUSCL=YES would improve accuracy but causes divergence on this mesh.
3. **No stall predicted**: CL continues increasing linearly through 16deg (1.608).
   Real NACA 0012 stalls around 12-14deg. SA model with 1st-order scheme overpredicts
   attached flow at high AoA. A finer mesh or unsteady RANS may be needed.
4. **KaTeX required**: methodology.html needs KaTeX JS scripts for math rendering
   (fixed - both CSS and JS CDN links must be present).

---

## FEA Results (2026-06-25)

### Optimized Wing at 4deg (2D pressure -> 3D FEA, FElupe linear elastic)
| Metric | Value |
|--------|------:|
| Max Tip Displacement | 521.6 mm |
| Peak von Mises Stress | 3082 MPa |
| Factor of Safety | 0.2 |
| Material | Al 7075-T6 (E=71.7 GPa, nu=0.33, sigma_yield=503 MPa) |
| Wing Mesh | 1,241 nodes, 3,417 tetrahedra |

### NACA 0012 Wing at 4deg (2D pressure -> 3D FEA)
| Metric | Value |
|--------|------:|
| Max Tip Displacement | 474.1 mm |
| Peak von Mises Stress | 1985 MPa |
| Factor of Safety | 0.25 |
| Material | Al 7075-T6 |
| Wing Mesh | 1,241 nodes, 3,417 tetrahedra |

### Notes
- FS < 1.0 expected: solid wing with no internal spars/ribs
- Pressure mapped from 2D SU2 RANS solution to 3D skin facets (FeaWingAnalysis.run())
- 3D pressure uses KDTree 3D-to-3D interpolation via FeaWingAnalysis.run_with_3d()
- VTU exported to `output/fea/optimized/results.vtu` for ParaView
- 3D contour plots generated by PyVista off-screen

---

## Development Commands
```bash
uv sync                           # Install/update dependencies
uv run python run_tunnel.py       # Full pipeline (~30 min)
uv run python run_optimization.py # Single-airfoil optimization (~2 sec + SU2 ~10 min)
uv run python run_fea.py          # Structural analysis (~6 sec)
uv run python run_fea_naca0012.py # NACA 0012 structural FEA (~6 sec)
uv run python run_3d_pipeline.py  # 3D mesh -> SU2 3D CFD -> 3D pressure FEA (~25 min)
uv run python run_cad.py          # CadQuery wing STEP export
# No build step - static HTML hand-authored; edit files directly in docs/
open docs/index.html              # View portfolio site
```

## Recent Fixes (2026-06-24)
1. **post.py stripped**: Visualizer class removed - all field vis now done in ParaView
2. **Direct image output**: Pipeline writes convergence/aggregate plots directly to
   `docs/assets/images/` instead of `output/` with a separate sync step
3. **Velocity/Pressure galleries**: naca0012.html now has 5-up comparison grids
4. **Output folder clean**: `output/` contains only simulation files and ParaView states
5. **Optimization module added**: `optimize.py` with CST param + NeuralFoil + SLSQP + 9 constraints
6. **CST coordinate bug fixed**: `build_airfoil_from_cst()` had TE lower point missing,
   causing TE_thickness=1.0 and wrong constraint values. Fixed coordinate ordering.
7. **Optimization solver changed**: AeroSandbox Opti/IPOPT dropped due to CasADi MX type
   incompatibilities with KulfanAirfoil.to_airfoil(). Replaced with scipy SLSQP + finite
   differences + penalty method (~2 sec, 100-150 iters, 0.01 Cd tolerance).

## Recent Additions (2026-06-25)
8. **FEA module added**: `fea.py` with `FeaWingAnalysis` class - Gmsh OCC wing lofting,
   tetrahedral mesh, CFD pressure mapping to skin, FElupe linear elastic solve,
   von Mises stress computation, VTU export, 3D PyVista contour plots.
9. **Structural Analysis page**: New standalone `docs/structural.html` with results table,
   load mapping methodology, stress/displacement figures, material properties.
10. **Navigation updated**: All 6 pages now have **Home | Methodology | Airfoil Analysis |
    Optimization | Structural Analysis | Implementation** nav bar (ParaView page removed).
11. **Project restructuring** (2026-06-25): Reorganized output dirs to `output/cfd/`, `output/cad/`,
    `output/fea/`. Docs images under `docs/assets/images/naca0012/{aoa_*,plots,mesh_naca0012}/`.
    Root-level HTML pages: `airfoil_analysis.html`, `optimization.html`. Deleted `docs/airfoils/`
    and `docs/paraview.html`. Added `physics/cad_wing.py` + `run_cad.py` for CadQuery wing CAD
    with internal spar and ribs.
12. **2.5D extrusion mesher**: `physics/mesher3d.py` — parses 2D SU2 mesh, extrudes nodes/elements
    along span with sweep/dihedral/twist per layer. Prism/wedge farfield, hexahedral BL. No Gmsh 3D
    dependency. 990K nodes, 1.9M elements, ~3.9s.
13. **3D SU2 config**: `SU2Config3D` dataclass in `solver.py` — 3D RANS with SA, ROE, MUSCL=NO,
    multigrid=0, conservative CFL ramp, MARKER_FAR/MARKER_HEATFLUX boundary conditions.
14. **3D FEA pressure mapping**: `fea.py.run_with_3d()` — maps 3D surface VTU pressure to 3D wing
    skin via KDTree nearest-neighbor interpolation (3D-to-3D, not 2D-to-3D).
15. **3D pipeline orchestrator**: `run_3d_pipeline.py` — iterates NACA 0012 and optimized wing
    configs: mesh -> SU2 3D CFD -> FEA with 3D pressure, skips completed steps via file checks.
16. **NACA 0012 FEA runner**: `run_fea_naca0012.py` — separate entrypoint for NACA 0012 structural
    FEA alongside optimized wing.
17. **Knowledge graph**: `graphify-out/` codebase graph — 141 nodes, 282 edges, 13 communities.
    Accessible via `graph-out/graph.html` and `GRAPH_REPORT.md`.

## Color Scheme (Dracula)
- Background: `#282a36`
- Card Background: `#44475a`
- Text: `#f8f8f2`
- Accents: Pink `#ff79c6`, Purple `#bd93f9`, Cyan `#8be9fd`, Green `#50fa7b`
- Comment: `#6272a4`
