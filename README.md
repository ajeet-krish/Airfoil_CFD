# Airfoil CFD Pipeline

This project implements a modular computational fluid dynamics (CFD) pipeline to analyze NACA 4-digit airfoils across various angles of attack (AoA). It automates geometry generation, mesh creation (via Gmsh), solver execution (via SU2), and visual post-processing (via PyVista), outputting a static, Dracula-themed HTML report.

## Features
- **Modular Architecture**: Decoupled physics, meshing, and solving modules.
- **Automated Workflow**: Orchestrates the entire simulation sweep via `run_tunnel.py`.
- **Aesthetic Visualization**: Dracula-themed plots with dense streamline analysis for turbulent separation.
- **Portfolio-Ready Output**: Automatically generates a professional HTML dashboard.

## Requirements
- `SU2` (must be in system PATH)
- `gmsh` Python SDK
- Python 3.14+
- `uv` (Use for all dependency and environment management)

## Usage
1. Configure `run_tunnel.py` parameters.
2. Run `uv run python run_tunnel.py`.
3. View results in `output/index.html`.
