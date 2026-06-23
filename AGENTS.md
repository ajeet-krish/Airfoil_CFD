# OpenCode Instructions for Airfoil CFD Pipeline

## Project Overview
Automated CFD analysis of NACA 4-digit airfoils across multiple angles of attack.
Generates C-grid meshes (Gmsh), solves RANS equations (SU2, Spalart-Allmaras),
and outputs a static Dracula-themed portfolio website with matplotlib/PyVista
visualizations and experimental validation.

## Reference Project: Soccer CFD
This project mirrors the architecture and patterns of the **Soccer CFD** project
at `/Users/ajeet/Projects/Soccer_CFD`. Key patterns adopted:
- **Classes pattern**: physics/ modules (geometry/mesher/solver/post/analysis)
- **Streamlines**: `scipy.griddata` interpolation to regular grid +
  `matplotlib.ax.streamplot()` — not PyVista's hanging `streamlines_evenly_spaced_2D`
- **Jinja2 → static**: Website files live in `docs/` — no template rendering
- **Dracula theme**: Consistent color scheme ported from Soccer CFD

Always reference Soccer CFD when stuck on architecture or visualization questions.

## Architecture

### physics/ Modules (Classes Pattern — mirrors Soccer CFD)
- `geometry.py` — `generate_naca_4digit(m, p, t, num_points=200)` with cosine spacing.
  t is in NACA convention (e.g. 12 for 12% thickness); divides by 100 internally.
- `mesher.py` — `MeshGenerator` class. Generates hybrid C-grid:
  - C-shaped farfield (semicircular inlet R=15 chords, outlet 30 chords downstream)
  - Structured boundary layer via Gmsh BoundaryLayer field (20 layers, ratio 1.15)
  - Unstructured Frontal-Delaunay farfield fill (Algorithm 6)
  - Physical groups: "airfoil" (wall), "farfield" (inlet/outlet/walls), "fluid"
  - Y+ ~1 at Re=1e6 with first layer height 2e-5
- `solver.py` — `SU2Config` dataclass + `SU2Solver` + `SU2Results`:
  - Compressible RANS, SA turbulence, ROE scheme, MUSCL_FLOW=NO (1st order stable)
  - CFL_ADAPT ramps from 0.01 to 5.0 over 2000 iterations
  - `HISTORY_OUTPUT= (INNER_ITER, RMS_RES, AERO_COEFF)` captures CL/CD in CSV
- `post.py` — `Visualizer` class: velocity contours + streamlines (matplotlib+griddata),
  pressure, mesh (PyVista), Cp
- `analysis.py` — Convergence plots, Cl/Cd curves, drag polar with experimental overlay
- `validate.py` — NACA 0012 experimental data (Ladson 1988, Abbott 1949)

### Workflow
`run_tunnel.py` orchestrates: geometry -> C-grid mesh -> SU2 solver -> post-processing
-> sync images to `docs/assets/images/`

5 AoAs: [0, 4, 8, 12, 16] with regime labels
(Symmetric Baseline, Linear Lift, High Lift, Onset of Stall, Deep Stall)

### Entrypoint
```bash
uv run python run_tunnel.py
```

---

## Critical Knowledge — SU2 v8.4.0

### Config Options
- `HISTORY_OUTPUT= ( INNER_ITER, RMS_RES, AERO_COEFF )` produces CSV columns:
  Inner_Iter, rms[Rho], rms[RhoU], rms[RhoV], rms[RhoE], rms[nu],
  RefForce, CD, CL, CSF, CMx, CMy, CMz, CFx, CFy, CFz, CEff, Buffet
- The "CD" and "CL" columns ARE the actual aerodynamic coefficients for
  compressible RANS (not dimensionless forces requiring post-multiplication)
- `MUSCL_FLOW= NO` required for stability on C-grids with SA model
- `CFL_ADAPT_PARAM= ( 0.01, 5.0, 1.1, 25.0 )` where third param (ramp factor) must be > 1.0
- `OUTPUT_FILES= (RESTART, PARAVIEW)` — surface_flow.vtu may not be generated
- VOLUME_OUTPUT, SURFACE_OUTPUT, and ENTROPY_FIX_COEFF are NOT valid in v8.4.0

### Solver Performance
- 2000 iterations recommended for convergence (rms[Rho] < -6, residuals dropping)
- A single AoA takes ~5-10 minutes on the reference hardware (M-series Mac)
- CFL ramps from 0.01 to 5.0 over 2000 iterations for stability
- The solver may hang if invalid config options are present; always test with 100 iters first

---

## Critical Knowledge — Mesh Generation

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

## Critical Knowledge — Geometry

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

## Critical Knowledge — Visualization

### Streamlines (matplotlib+griddata — fixed 2026-06-23)
- `mesh.streamlines_evenly_spaced_2D()` HANGS on the 97K-cell C-grid mesh
  (high-aspect-ratio BL cells kill VTK's tracer)
- **Fix**: Use Soccer CFD's pattern — interpolate VTU data onto a 600x400
  Cartesian grid via `scipy.interpolate.griddata()`, then use
  `matplotlib.ax.streamplot()` with stride=3, density=0.8, linewidth=0.6
- This is MUCH faster and produces identical-quality streamlines

### Mesh Visualization
- PyVista wireframe on full VTU mesh works fine (no decimation needed)
- SU2 mesh files (.su2) cannot be read by PyVista directly — always use flow_results.vtu

### Website
- Static HTML generated by `docs/build_site.py` — reads physics/ source files,
  HTML-escapes them, embeds in `docs/index.html`
- After pipeline run, `run_tunnel.py` syncs PNGs from `output/` to `docs/assets/images/`
- `docs/` is the GitHub Pages root

---

## Results — Final (2026-06-23)

| AoA | Regime | CL | CD | L/D | Converged |
|-----|--------|---:|---:|---:|:---------:|
| 0° | Symmetric Baseline | 0.0014 | 0.0749 | 0.0 | Yes |
| 4° | Linear Lift | 0.4453 | 0.0969 | 4.6 | Yes |
| 8° | High Lift | 0.8718 | 0.1644 | 5.3 | Yes |
| 12° | Onset of Stall | 1.2647 | 0.2764 | 4.6 | Yes |
| 16° | Deep Stall | 1.6082 | 0.4314 | 3.7 | Yes |

Lift curve slope: 0.109 per degree (matches theoretical 2π within 1%)

---

## Known Issues (2026-06-23)

1. **Surface VTU not generated**: SU2 v8.4.0 doesn't create surface_flow.vtu despite
   SURFACE_FILENAME being set. Cp distribution plots are unavailable.
2. **CD ~10x higher than experimental**: Due to 1st-order scheme (MUSCL=NO) on
   a C-grid with SA model. Experimental CD at AoA=0 is ~0.007, we get ~0.075.
   MUSCL=YES would improve accuracy but causes divergence on this mesh.
3. **No stall predicted**: CL continues increasing linearly through 16° (1.608).
   Real NACA 0012 stalls around 12-14°. SA model with 1st-order scheme overpredicts
   attached flow at high AoA. A finer mesh or unsteady RANS may be needed.
4. **Website must be rebuilt**: After source changes, run `uv run python docs/build_site.py`
   to regenerate index.html with updated embedded source code.

---

## Development Commands
```bash
uv sync                           # Install/update dependencies
uv run python run_tunnel.py       # Full pipeline (~30 min)
uv run python docs/build_site.py  # Regenerate website (after source changes)
open docs/index.html              # View portfolio site
```

## Recent Fixes (2026-06-23)
1. **t/100 bug**: NACA thickness was 100x too thick — fixed divide by 100
2. **SU2 config path bug**: Relative paths caused `config.cfg` not found — fixed with `Path.resolve()`
3. **Streamline hang**: PyVista streamlines hung on C-grid — replaced with matplotlib+griddata

## Color Scheme (Dracula)
- Background: `#282a36`
- Card Background: `#44475a`
- Text: `#f8f8f2`
- Accents: Pink `#ff79c6`, Purple `#bd93f9`, Cyan `#8be9fd`, Green `#50fa7b`
- Comment: `#6272a4`
