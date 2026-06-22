import gmsh
import numpy as np

def generate_su2_mesh(dat_file, output_su2, mesh_density=1.0):
    """
    Generates a high-quality 2D unstructured mesh with boundary layer refinement 
    around the airfoil using the Gmsh Python API and exports it in SU2 format.
    
    Parameters:
        dat_file (str): Path to the .dat coordinates file
        output_su2 (str): Output path for the .su2 mesh file
        mesh_density (float): Density multiplier (lower values make mesh finer)
    """
    gmsh.initialize()
    # Suppress verbose terminal output from Gmsh to keep logging clean
    gmsh.option.setNumber("General.Terminal", 0)
    
    gmsh.model.add("airfoil_mesh")
    
    # 1. Load airfoil coordinates
    coords = np.loadtxt(dat_file)
    
    # Filter out duplicate first/last point if any to ensure clean loops
    if np.allclose(coords[0], coords[-1], atol=1e-5):
        coords_to_mesh = coords[:-1]
    else:
        coords_to_mesh = coords
        
    # Add points to geometry kernel
    airfoil_points = []
    for x, y in coords_to_mesh:
        pt_id = gmsh.model.geo.addPoint(x, y, 0.0)
        airfoil_points.append(pt_id)
        
    # Connect points sequentially with lines to represent the exact contour
    airfoil_lines = []
    num_pts = len(airfoil_points)
    for i in range(num_pts):
        p1 = airfoil_points[i]
        p2 = airfoil_points[(i + 1) % num_pts]
        line_id = gmsh.model.geo.addLine(p1, p2)
        airfoil_lines.append(line_id)
        
    # Form the inner boundary loop
    airfoil_loop = gmsh.model.geo.addCurveLoop(airfoil_lines)
    
    # 2. Define the circular Farfield Boundary
    # A circle centered at the chord midpoint (0.5, 0.0) with radius 15.0
    cx, cy = 0.5, 0.0
    r = 15.0
    p_center = gmsh.model.geo.addPoint(cx, cy, 0.0)
    p_right = gmsh.model.geo.addPoint(cx + r, cy, 0.0)
    p_top = gmsh.model.geo.addPoint(cx, cy + r, 0.0)
    p_left = gmsh.model.geo.addPoint(cx - r, cy, 0.0)
    p_bottom = gmsh.model.geo.addPoint(cx, cy - r, 0.0)
    
    # Define circular arcs (Gmsh requires arcs < 180 degrees)
    arc1 = gmsh.model.geo.addCircleArc(p_right, p_center, p_top)
    arc2 = gmsh.model.geo.addCircleArc(p_top, p_center, p_left)
    arc3 = gmsh.model.geo.addCircleArc(p_left, p_center, p_bottom)
    arc4 = gmsh.model.geo.addCircleArc(p_bottom, p_center, p_right)
    
    # Form the outer boundary loop
    farfield_loop = gmsh.model.geo.addCurveLoop([arc1, arc2, arc3, arc4])
    
    # 3. Create the 2D fluid surface domain (outer loop boundary containing inner airfoil hole)
    fluid_surface = gmsh.model.geo.addPlaneSurface([farfield_loop, airfoil_loop])
    
    # Synchronize to geometry kernel
    gmsh.model.geo.synchronize()
    
    # 4. Define Physical Groups
    # SU2 relies on the physical curve names to apply farfield/viscous wall boundaries!
    gmsh.model.addPhysicalGroup(1, [arc1, arc2, arc3, arc4], name="farfield")
    gmsh.model.addPhysicalGroup(1, airfoil_lines, name="airfoil")
    gmsh.model.addPhysicalGroup(2, [fluid_surface], name="fluid")
    
    # 5. Local Mesh Refinement using Fields
    # Field 1: Distance from airfoil boundaries
    dist_field = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(dist_field, "CurvesList", airfoil_lines)
    
    # Field 2: Threshold to scale cell size gradually away from the airfoil
    thresh_field = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(thresh_field, "InField", dist_field)
    gmsh.model.mesh.field.setNumber(thresh_field, "SizeMin", 0.003 * mesh_density)  # Super-refined BL cell size
    gmsh.model.mesh.field.setNumber(thresh_field, "SizeMax", 1.2 * mesh_density)    # Standard size for farfield
    gmsh.model.mesh.field.setNumber(thresh_field, "DistMin", 0.05)                  # Radius of high refinement
    gmsh.model.mesh.field.setNumber(thresh_field, "DistMax", 2.5)                   # Transition radius
    
    # Set background mesh size field
    gmsh.model.mesh.field.setAsBackgroundMesh(thresh_field)
    
    # Set 2D mesh algorithm to Frontal-Delaunay for cleaner transition zones
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    
    # 6. Generate 2D mesh
    gmsh.model.mesh.generate(2)
    
    # 7. Write and close
    gmsh.write(output_su2)
    gmsh.finalize()
