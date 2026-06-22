import os
import subprocess

def run_su2(template_cfg, mesh_file, aoa, output_dir):
    """
    Modifies the base SU2 config template for a specific AoA and runs the solver.
    
    Parameters:
        template_cfg (str): Path to the template configuration file.
        mesh_file (str): Path to the generated mesh file (.su2).
        aoa (float): Angle of attack in degrees.
        output_dir (str): Directory where the simulation will run.
    """
    # 1. Read the template
    with open(template_cfg, 'r') as f:
        config_content = f.read()
    
    # 2. Dynamically update key-value pairs using simple string replacement
    # Ensure mesh filename uses absolute path or correct relative path
    abs_mesh_path = os.path.abspath(mesh_file)
    
    config_content = config_content.replace("{{AOA}}", str(aoa))
    config_content = config_content.replace("{{MESH_FILENAME}}", abs_mesh_path)
    
    # 3. Write local config
    local_cfg = os.path.join(output_dir, "config.cfg")
    with open(local_cfg, 'w') as f:
        f.write(config_content)
    
    # 4. Execute SU2 solver
    # Run from inside the output_dir so output files are created locally
    print(f"Executing SU2_CFD for AoA={aoa}...")
    try:
        subprocess.run(["SU2_CFD", "config.cfg"], cwd=output_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing SU2_CFD: {e}")
        raise
    
    print(f"Simulation completed for AoA={aoa}.")
