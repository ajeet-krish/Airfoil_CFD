from __future__ import annotations

from pathlib import Path
from typing import Optional

import gmsh
import numpy as np


class MeshGenerator:
    """Gmsh-based mesh generation for 2D airfoil C-grid meshes."""

    FARFIELD_RADIUS: float = 15.0
    DOWNSTREAM_LENGTH: float = 30.0

    def __init__(self, mesh_density: float = 1.0):
        self.mesh_density = mesh_density

    @staticmethod
    def _clean_coords(dat_file: str) -> np.ndarray:
        """Load and deduplicate airfoil coordinates from a .dat file."""
        coords = np.loadtxt(dat_file)
        if np.allclose(coords[0], coords[-1], atol=1e-5):
            return coords[:-1]
        return coords

    def generate(
        self,
        dat_file: str,
        output_su2: str,
        bl_first_layer: float = 2e-5,
        bl_ratio: float = 1.15,
        bl_thickness: float = 0.05,
        farfield_size: float = 1.2,
        airfoil_size: float = 0.003,
        quiet: bool = True,
    ) -> Path:
        """Generate a 2D C-grid mesh around an airfoil with structured boundary layer.

        Args:
            dat_file: Path to airfoil .dat coordinate file (Selig format)
            output_su2: Output path for .su2 mesh
            bl_first_layer: First boundary layer height (absolute)
            bl_ratio: Boundary layer geometric growth ratio
            bl_layers: Number of boundary layers
            bl_thickness: Total boundary layer thickness
            farfield_size: Max element size in farfield
            airfoil_size: Max element size on airfoil surface
            quiet: Suppress Gmsh terminal output
        """
        gmsh.initialize()
        if quiet:
            gmsh.option.setNumber("General.Terminal", 0)

        gmsh.model.add("airfoil_cgrid")

        # ── 1. Airfoil contour ──
        coords = self._clean_coords(dat_file)
        airfoil_points = []
        for x, y in coords:
            pid = gmsh.model.geo.addPoint(x, y, 0.0)
            airfoil_points.append(pid)

        # Spline through all points (closed contour)
        airfoil_tag = gmsh.model.geo.addSpline(airfoil_points + [airfoil_points[0]])

        # ── 2. C-shaped farfield boundary ──
        R = self.FARFIELD_RADIUS
        L = self.DOWNSTREAM_LENGTH

        # Semicircle centered at (0, 0) — airfoil leading edge
        p_bot = gmsh.model.geo.addPoint(0.0, -R, 0.0)
        p_ctr = gmsh.model.geo.addPoint(0.0, 0.0, 0.0)
        p_lef = gmsh.model.geo.addPoint(-R, 0.0, 0.0)
        p_top = gmsh.model.geo.addPoint(0.0, R, 0.0)

        # Downstream
        p_out_top = gmsh.model.geo.addPoint(L, R, 0.0)
        p_out_bot = gmsh.model.geo.addPoint(L, -R, 0.0)

        arc_bot = gmsh.model.geo.addCircleArc(p_bot, p_ctr, p_lef)
        arc_top = gmsh.model.geo.addCircleArc(p_lef, p_ctr, p_top)
        line_top = gmsh.model.geo.addLine(p_top, p_out_top)
        line_out = gmsh.model.geo.addLine(p_out_top, p_out_bot)
        line_bot = gmsh.model.geo.addLine(p_out_bot, p_bot)

        farfield_curves = [arc_bot, arc_top, line_top, line_out, line_bot]

        # ── 3. Curve loops and surface ──
        farfield_loop = gmsh.model.geo.addCurveLoop(farfield_curves)
        airfoil_loop = gmsh.model.geo.addCurveLoop([airfoil_tag])
        fluid_surf = gmsh.model.geo.addPlaneSurface([farfield_loop, airfoil_loop])

        gmsh.model.geo.synchronize()

        # ── 4. Physical groups ──
        gmsh.model.addPhysicalGroup(1, farfield_curves, name="farfield")
        gmsh.model.addPhysicalGroup(1, [airfoil_tag], name="airfoil")
        gmsh.model.addPhysicalGroup(2, [fluid_surf], name="fluid")

        # ── 5. Mesh refinement via fields ──
        # Distance from airfoil
        dist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(dist, "CurvesList", [airfoil_tag])

        # Threshold for smooth size transition
        thresh = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(thresh, "InField", dist)
        gmsh.model.mesh.field.setNumber(
            thresh, "SizeMin", airfoil_size * self.mesh_density
        )
        gmsh.model.mesh.field.setNumber(
            thresh, "SizeMax", farfield_size * self.mesh_density
        )
        gmsh.model.mesh.field.setNumber(thresh, "DistMin", 0.05)
        gmsh.model.mesh.field.setNumber(thresh, "DistMax", 2.5)

        # Boundary layer field for structured near-wall layers
        bl = gmsh.model.mesh.field.add("BoundaryLayer")
        gmsh.model.mesh.field.setNumbers(bl, "CurvesList", [airfoil_tag])
        gmsh.model.mesh.field.setNumber(bl, "Size", bl_first_layer)
        gmsh.model.mesh.field.setNumber(bl, "Ratio", bl_ratio)
        gmsh.model.mesh.field.setNumber(bl, "Thickness", bl_thickness)
        gmsh.model.mesh.field.setAsBoundaryLayer(bl)

        gmsh.model.mesh.field.setAsBackgroundMesh(thresh)

        # ── 6. Mesh controls ──
        gmsh.option.setNumber("Mesh.Algorithm", 6)  # Frontal-Delaunay
        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 0)
        gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 0)

        # ── 7. Generate 2D mesh ──
        gmsh.model.mesh.generate(2)

        # ── 8. Export to SU2 format ──
        # gmsh SU2 export needs createTopology() call to avoid empty mesh bug
        gmsh.model.mesh.createTopology()
        gmsh.write(output_su2)

        gmsh.finalize()
        return Path(output_su2)


# Convenience function for backward compatibility
def generate_su2_mesh(dat_file, output_su2, mesh_density=1.0):
    """Legacy wrapper."""
    gen = MeshGenerator(mesh_density=mesh_density)
    return gen.generate(dat_file, output_su2)
