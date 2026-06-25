from __future__ import annotations
from pathlib import Path
import gmsh
import math

class MeshGenerator3D:
    """Generate 3D mesh by subtracting imported STEP wing from farfield box."""

    def __init__(self, mesh_density: float = 1.0, span_layers: int = 30):
        self.mesh_density = mesh_density
        self.span_layers = span_layers

    def generate(
        self,
        step_file: str | Path,
        output_su2: str | Path,
        quiet: bool = True,
    ) -> Path:
        step_file = Path(step_file)
        output_su2 = Path(output_su2)
        output_su2.parent.mkdir(parents=True, exist_ok=True)

        gmsh.initialize()
        if quiet:
            gmsh.option.setNumber("General.Terminal", 0)

        gmsh.model.add("wing_3d_cut")

        # 1. Import STEP wing
        imported = gmsh.model.occ.importShapes(str(step_file))
        gmsh.model.occ.synchronize()

        # Isolate the 3D solid volume
        wing_solid_entity = [e for e in imported if e[0] == 3][0]
        
        # 2. Get bounding box
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.occ.getBoundingBox(*wing_solid_entity)
        
        # 3. Create Farfield Box
        margin = 15.0
        farfield_box = gmsh.model.occ.addBox(xmin - margin, ymin, zmin - margin,
                                           (xmax - xmin) + 2*margin,
                                           (ymax - ymin),
                                           (zmax - zmin) + 2*margin)
        
        # 4. Boolean subtraction
        fluid_vol_res = gmsh.model.occ.cut([(3, farfield_box)], [wing_solid_entity], removeTool=True)
        gmsh.model.occ.synchronize()
        
        # 5. Define Physical Groups
        gmsh.model.addPhysicalGroup(3, [fluid_vol_res[0][0][1]], name="fluid")
        
        all_surfaces = gmsh.model.getEntities(2)
        wing_surfaces = []
        for dim, tag in all_surfaces:
            adj = gmsh.model.getAdjacencies(dim, tag)
            if wing_solid_entity[1] in adj[1]:
                wing_surfaces.append(tag)
        
        gmsh.model.addPhysicalGroup(2, wing_surfaces, name="airfoil")
        
        # 6. Mesh refinement
        dist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(dist, "SurfacesList", wing_surfaces)

        thresh = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(thresh, "InField", dist)
        gmsh.model.mesh.field.setNumber(thresh, "SizeMin", 0.02 * self.mesh_density)
        gmsh.model.mesh.field.setNumber(thresh, "SizeMax", 2.0 * self.mesh_density)
        gmsh.model.mesh.field.setNumber(thresh, "DistMin", 0.1)
        gmsh.model.mesh.field.setNumber(thresh, "DistMax", 5.0)
        gmsh.model.mesh.field.setAsBackgroundMesh(thresh)
        
        # 7. Generate mesh
        gmsh.option.setNumber("Mesh.Algorithm3D", 1) # Delaunay
        gmsh.model.mesh.generate(3)
        
        gmsh.model.mesh.createTopology()
        gmsh.write(str(output_su2))
        gmsh.finalize()
        
        return output_su2
