# OpenCode Instructions for CFD Airfoil Explorer

## Project Overview
Automated CFD analysis of NACA 4-digit airfoils across multiple angles of attack.
Generates C-grid meshes (Gmsh), solves RANS equations (SU2, Spalart-Allmaras),
and outputs a static Dracula-themed portfolio website with ParaView field
visualizations and matplotlib convergence/aggregate plots with experimental
validation.

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
- `post.py` - (placeholder) Field visualizations (velocity, pressure, mesh) created in ParaView
- `analysis.py` - Convergence plots, Cl/Cd curves, drag polar with experimental overlay
- `validate.py` - NACA 0012 experimental data (Ladson 1988, Abbott 1949)

### Workflow
`run_tunnel.py` orchestrates: geometry -> C-grid mesh -> SU2 solver -> convergence plots
-> aggregate plots. All images go directly to `docs/assets/images/` (no sync step).
`output/` contains only simulation artifacts and ParaView state files.

5 AoAs: [0, 4, 8, 12, 16] with regime labels
(Symmetric Baseline, Linear Lift, High Lift, Onset of Stall, Deep Stall)

### Entrypoint
```bash
uv run python run_tunnel.py
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
- Use `docs/paraview.html` for step-by-step recipes.
- ParaView state files are saved in `output/aoa_*/paraview_*.pvsm`.

### Code-Generated Plots (analysis.py)
- `plot_convergence()` - RMS residuals + Cl/Cd history per AoA
- `plot_cl_alpha()` - Lift curve vs angle of attack
- `plot_cd_alpha()` - Drag vs angle of attack
- `plot_drag_polar()` - Cl vs Cd with experimental overlay
- All output goes directly to `docs/assets/images/` (per-AoA in subfolders)

### Website (Multi-Page)
- `docs/index.html` - Home: project intro, CFD relevance (aviation/auto/energy), rapid iteration
- `docs/methodology.html` - Theory + Methodology + Mesh: NACA equations, flight regimes table, C-grid design, 3 mesh images, mesh stats table, sim parameters
- `docs/airfoils/naca0012.html` - Airfoil-specific results: summary table, aggregate plots, velocity/pressure galleries (5-up), per-AoA metric cards + visualizations
- `docs/implementation.html` - How to run, code architecture, SU2 config reference, 5 expandable source blocks
- `docs/paraview.html` - ParaView walkthrough with 11+ visualization recipes
- `paraview_recipes.md` - (project root, untracked) ParaView step-by-step in markdown
- All pages share `nav.top-nav` bar: **Home | Methodology | NACA 0012 | Implementation | ParaView**
- CSS is minimalist Dracula inspired by `/Users/ajeet/Projects/Digital\ CV`: `#21222c` card bg, `border-left` accent, no hover lift/shadow, no gradients, monospace throughout
- Images go directly to `docs/assets/images/` - no sync step needed
- `docs/` is the GitHub Pages root
- Adding a new airfoil: copy `docs/airfoils/naca0012.html` as template, update params

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

## Development Commands
```bash
uv sync                           # Install/update dependencies
uv run python run_tunnel.py       # Full pipeline (~30 min)
# No build step - static HTML hand-authored; edit files directly in docs/
open docs/index.html              # View portfolio site
```

## Recent Fixes (2026-06-24)
1. **post.py stripped**: Visualizer class removed - all field vis now done in ParaView
2. **Direct image output**: Pipeline writes convergence/aggregate plots directly to
   `docs/assets/images/` instead of `output/` with a separate sync step
3. **Velocity/Pressure galleries**: naca0012.html now has 5-up comparison grids
4. **Output folder clean**: `output/` contains only simulation files and ParaView states

## Color Scheme (Dracula)
- Background: `#282a36`
- Card Background: `#44475a`
- Text: `#f8f8f2`
- Accents: Pink `#ff79c6`, Purple `#bd93f9`, Cyan `#8be9fd`, Green `#50fa7b`
- Comment: `#6272a4`
