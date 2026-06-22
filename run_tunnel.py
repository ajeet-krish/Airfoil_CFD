import os
import shutil
import pyvista as pv
from jinja2 import Template
import numpy as np

from physics.geometry import generate_naca_4digit, save_dat_file
from physics.mesher import generate_su2_mesh
from physics.solver import run_su2

# --- Parameters ---
NACA_NAME = "NACA 0012"
NACA_PARAMS = (0, 0, 12)  # m, p, t
ANGLES_OF_ATTACK = [0, 4, 8, 12, 16]
BASE_DIR = "./output"
TEMPLATE_CFG = "./templates/su2_template.cfg"
REPORT_TEMPLATE = "./templates/report_base.html"

# Dracula Theme Constants
BG_COLOR = "#282a36"
CMAP = ["#bd93f9", "#ff79c6", "#f1fa8c"]  # Purple -> Pink -> Yellow

def export_visuals(vtu_file, save_path, aoa):
    """Generates Dracula-themed visual assets using PyVista."""
    if not os.path.exists(vtu_file):
        print(f"VTU file not found: {vtu_file}")
        return

    mesh = pv.read(vtu_file)
    
    # 1. Velocity Plot with Dense Streamlines
    plotter_vel = pv.Plotter(off_screen=True, window_size=[1000, 800])
    plotter_vel.set_background(BG_COLOR)
    
    # Add contours
    plotter_vel.add_mesh(mesh, scalars="Velocity_Magnitude", cmap=CMAP, show_scalar_bar=False)
    
    # Dense Streamlines for separation
    streamlines = mesh.streamlines_evenly_spaced_2D(
        vectors="Velocity",
        start_x=0.0, start_y=-2.0, end_x=0.0, end_y=2.0,
        n_points=300
    )
    plotter_vel.add_mesh(streamlines, color="white", line_width=1.5, opacity=0.6)
    
    plotter_vel.view_xy()
    plotter_vel.screenshot(f"{save_path}/velocity.png")
    plotter_vel.close()
    
    # 2. Pressure Plot
    plotter_pres = pv.Plotter(off_screen=True, window_size=[1000, 800])
    plotter_pres.set_background(BG_COLOR)
    plotter_pres.add_mesh(mesh, scalars="Pressure", cmap=CMAP, show_scalar_bar=False)
    plotter_pres.view_xy()
    plotter_pres.screenshot(f"{save_path}/pressure.png")
    plotter_pres.close()

def main():
    # Setup Output
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    os.makedirs(BASE_DIR)
    
    results_data = []

    for aoa in ANGLES_OF_ATTACK:
        print(f"\n--- Processing AoA = {aoa} degrees ---")
        aoa_dir = os.path.join(BASE_DIR, f"aoa_{aoa}")
        os.makedirs(aoa_dir, exist_ok=True)
        
        # Step 1: Geometry
        upper, lower = generate_naca_4digit(*NACA_PARAMS)
        dat_path = f"{aoa_dir}/airfoil.dat"
        save_dat_file(upper, lower, dat_path)
        
        # Step 2: Mesh
        mesh_path = f"{aoa_dir}/mesh.su2"
        generate_su2_mesh(dat_path, mesh_path, mesh_density=1.0)
        
        # Step 3: Run SU2
        run_su2(TEMPLATE_CFG, mesh_path, aoa, aoa_dir)
        
        # Step 4: Post-Process (Assuming SU2 writes flow_results.vtu)
        vtu_file = os.path.join(aoa_dir, "flow_results.vtu")
        export_visuals(vtu_file, aoa_dir, aoa)
        
        # Add metadata for HTML
        results_data.append({
            "aoa": aoa,
            "regime": "Symmetric Baseline" if aoa == 0 else "Linear Lift" if aoa == 4 else "High Lift" if aoa == 8 else "Onset of Stall" if aoa == 12 else "Deep Stall",
            "cl": "0.00", # Placeholder
            "cd": "0.00", # Placeholder
            "cl_cd": "0.00" # Placeholder
        })

    # Step 5: Compile HTML
    print("\nCompiling HTML report...")
    with open(REPORT_TEMPLATE, 'r') as f:
        template = Template(f.read())
    
    html_output = template.render(naca_name=NACA_NAME, results=results_data)
    
    with open(os.path.join(BASE_DIR, "index.html"), 'w') as f:
        f.write(html_output)
    
    print("Wind tunnel run complete. Report available at output/index.html")

if __name__ == "__main__":
    main()
