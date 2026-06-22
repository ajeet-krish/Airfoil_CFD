import pyvista as pv
import os
import numpy as np

# Dracula Theme Constants
BG_COLOR = "#282a36"
CMAP = ["#bd93f9", "#ff79c6", "#f1fa8c"]  # Purple -> Pink -> Yellow

def export_visuals(vtu_file, save_path):
    """Generates Dracula-themed visual assets using PyVista."""
    if not os.path.exists(vtu_file):
        print(f"VTU file not found: {vtu_file}")
        return

    mesh = pv.read(vtu_file)
    
    # 1. Velocity Plot with Dense Streamlines
    plotter_vel = pv.Plotter(off_screen=True, window_size=[1000, 800])
    plotter_vel.set_background(BG_COLOR)
    
    # Compute velocity magnitude
    mesh["Velocity_Mag"] = np.linalg.norm(mesh["Velocity"], axis=1)

    # Add contours
    plotter_vel.add_mesh(mesh, scalars="Velocity_Mag", cmap=CMAP, show_scalar_bar=False)
    
    # Dense Streamlines for separation
    streamlines = mesh.streamlines(vectors="Velocity", n_points=300)
    plotter_vel.add_mesh(streamlines, color="white", line_width=1.5, opacity=0.6)
    
    plotter_vel.view_xy()
    plotter_vel.screenshot(f"{save_path}/velocity.png")
    plotter_vel.close()
    
    # 2. Pressure Plot
    plotter_pres = pv.Plotter(off_screen=True, window_size=[1000, 800])
    plotter_pres.set_background(BG_COLOR)
    
    # Add Pressure contours
    plotter_pres.add_mesh(mesh, scalars="Pressure", cmap=CMAP, show_scalar_bar=False)
    plotter_pres.view_xy()
    plotter_pres.screenshot(f"{save_path}/pressure.png")
    plotter_pres.close()
    print(f"Screenshots saved in {save_path}")

if __name__ == "__main__":
    export_visuals("output/aoa_0/flow_results.vtu", "output/aoa_0")
