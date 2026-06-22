# OpenCode Instructions for Airfoil CFD Pipeline

## Project Overview
This repository implements a modular computational fluid dynamics (CFD) pipeline to analyze NACA 4-digit airfoils across various angles of attack (AoA). It automates geometry generation, mesh creation (via Gmsh), solver execution (via SU2), and visual post-processing (via PyVista), outputting a static HTML report.

## Pipeline Orchestration & Workflow
- **Main Entrypoint**: Run `python run_tunnel.py`. It loops through `ANGLES_OF_ATTACK`, orchestrating `physics/` modules and rendering visualizations.
- **Directories**: 
  - `physics/`: Contains core logic.
    - `geometry.py`: NACA 4-digit math and coordinate generation.
    - `mesher.py`: Gmsh API wrapper for mesh generation.
    - `solver.py`: SU2 configuration management and execution.
  - `templates/`: Input configurations (`su2_template.cfg`) and presentation layout (`report_base.html`).
  - `output/`: Auto-generated on run. Stores per-AoA subfolders and `index.html`.
- **Note**: The pipeline is designed to be fully modular and decoupled.

## Toolchain & Quirks
- **Gmsh SDK**:
  - Requires `gmsh` Python bindings.
  - Mandatory: Always call `gmsh.initialize()` at the start and `gmsh.finalize()` at the end of `physics/mesher.py`.
  - SU2 format writer relies on physical groups. Ensure the airfoil surface is a physical curve named `airfoil` and the outer boundary is `farfield`.
- **SU2 Solver**:
  - `SU2_CFD` executable must be in the system path.
  - `physics/solver.py` reads `templates/su2_template.cfg` and injects `AOA` and `MESH_FILENAME`.
- **PyVista**:
  - Plots require `off_screen=True` in `Plotter`.
  - On headless systems, `pv.start_xvfb()` is necessary.

## Visual Design & Aesthetics ("Dracula Theme")
Strict adherence to the Dracula color scheme is required for portfolio cohesion.
- **Color Constants**:
  - Background: `#282a36`
  - Card Background: `#44475a`
  - Text/Foreground: `#f8f8f2`
  - Accents: Pink `#ff79c6`, Purple `#bd93f9`, Cyan `#8be9fd`, Green `#50fa7b`, Yellow `#f1fa8c`
- **PyVista Scalar Map Style**: Use custom colormap interpolating between Dracula colors or `magma`.
- **Streamline High Density Design**: For separation at high AoA ($12^\circ, 16^\circ$), use `mesh.streamlines_evenly_spaced_2D` with high `n_points` and transparency.

## Simulation Execution & Verification
- **Prerequisites**: Ensure `SU2_CFD` is in the system `PATH` and all Python dependencies (`uv sync`) are installed.
- **Execution**: Run `uv run python run_tunnel.py`.
- **Pipeline Workflow**:
  - The script iterates through `ANGLES_OF_ATTACK = [0, 4, 8, 12, 16]`.
  - For each angle, it:
    1. Generates coordinates (`physics/geometry.py`).
    2. Builds a mesh (`physics/mesher.py`).
    3. Executes the SU2 solver (`physics/solver.py`) using `templates/su2_template.cfg`.
    4. Renders Dracula-themed visuals (`pyvista`) and exports them to `output/aoa_<angle>/`.
  - Finally, it compiles all results into `output/index.html`.
- **Troubleshooting**: 
  - If `ModuleNotFoundError` occurs, verify that `uv sync` completed successfully. 
  - If the solver fails, check the `output/aoa_<angle>/config.cfg` file for correct mesh file paths and verify the SU2 configuration options are compatible with your installed version of SU2.
  - If the solver times out, the simulation is likely progressing, but consider increasing the `timeout` parameter if executing via a wrapper.

## AI Agent Interaction Guidelines
- **Modifications**: When modifying any physics logic, verify mesh generation and SU2 solver convergence.
- **Formatting**: Maintain the modular structure of `physics/`.
- **Aesthetic**: All new plots or UI components MUST follow the Dracula color scheme.
- **Tooling**: Use `uv` for all environment management, dependency installation, and script execution (e.g., `uv run python ...`). Never use standard `pip` or `python` directly for package management.
- **Style Constraint**: Do NOT use em dashes ( - ) anywhere in the project documentation or code comments. Use hyphen-spaces ( - ) or en dashes instead.

