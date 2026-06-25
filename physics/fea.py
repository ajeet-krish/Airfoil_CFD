from __future__ import annotations

from pathlib import Path

import felupe
import gmsh
import matplotlib
import meshio
import numpy as np
import pyvista as pv
from scipy.interpolate import interp1d
from scipy.spatial import KDTree

BG_COLOR = "#282a36"
CARD_BG = "#44475a"
FG_COLOR = "#f8f8f2"
PINK = "#ff79c6"
PURPLE = "#bd93f9"
CYAN = "#8be9fd"
GREEN = "#50fa7b"
YELLOW = "#f1fa8c"
COMMENT = "#6272a4"


def _setup_matplotlib():
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": BG_COLOR,
        "axes.edgecolor": CARD_BG,
        "axes.labelcolor": FG_COLOR,
        "text.color": FG_COLOR,
        "xtick.color": COMMENT,
        "ytick.color": COMMENT,
        "grid.alpha": 0.15,
        "grid.color": FG_COLOR,
        "legend.facecolor": CARD_BG,
        "legend.labelcolor": FG_COLOR,
    })
    return plt


def _thick_camber(coords: np.ndarray, x_frac: float) -> tuple[float, float]:
    le_idx = int(np.argmin(coords[:, 0]))
    u = coords[: le_idx + 1]
    l = coords[le_idx:][::-1]
    u = u[np.argsort(u[:, 0])]
    l = l[np.argsort(l[:, 0])]
    yu = float(np.interp(x_frac, u[:, 0], u[:, 1]))
    yl = float(np.interp(x_frac, l[:, 0], l[:, 1]))
    return yu - yl, (yu + yl) / 2


def _downsample(coords: np.ndarray, target: int) -> np.ndarray:
    n = len(coords)
    if n <= target:
        return coords.copy()
    indices = np.linspace(0, n - 1, target, dtype=int)
    return coords[indices]


class FeaWingAnalysis:
    def __init__(
        self,
        vtu_path: str,
        dat_path: str,
        output_dir: str,
        surface_vtu_3d_path: str | None = None,
    ):
        self.vtu_path = Path(vtu_path) if vtu_path else None
        self.dat_path = Path(dat_path)
        self.output_dir = Path(output_dir)
        self.surface_vtu_3d_path = Path(surface_vtu_3d_path) if surface_vtu_3d_path else None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fea_dir = self.output_dir / "fea"
        self.fea_dir.mkdir(parents=True, exist_ok=True)

        self.root_chord = 2.5
        self.tip_chord = 0.75
        self.half_span = 5.5
        self.sweep_angle = 25.0
        self.dihedral_angle = 3.0
        self.twist_angle = -2.0
        self.spar_chord_frac = 0.3
        self.spar_width = 0.05
        self.rib_thickness = 0.01
        self.rib_count = 6

        self.E = 71.7e3
        self.nu = 0.33
        self.yield_stress = 503.0
        self.p_inf = 28994.36
        self.q_inf = 456.7
        self.rho_air = 0.35053

    def extract_surface_pressure(self) -> tuple[np.ndarray, np.ndarray]:
        coords = np.loadtxt(self.dat_path)
        grid = pv.read(str(self.vtu_path))
        tree = KDTree(grid.points[:, :2])
        _, indices = tree.query(coords)
        p_surf = grid["Pressure"][indices]
        return coords, p_surf - self.p_inf

    def extract_surface_pressure_3d(self) -> tuple[np.ndarray, np.ndarray]:
        grid = pv.read(str(self.surface_vtu_3d_path))
        points = grid.points
        pressure = np.asarray(grid["Pressure"]).ravel() - self.p_inf
        return points, pressure

    def _make_airfoil_wire(self, coords, y, chord, sweep, dihedral, twist):
        tr = np.radians(twist)
        ct, st = np.cos(tr), np.sin(tr)
        pts = []
        for x, z in coords:
            vx, vz = x * chord, z * chord
            tx = vx * ct + vz * st + sweep
            tz = -vx * st + vz * ct + dihedral
            pts.append(gmsh.model.occ.addPoint(tx, y, tz))
        pts.append(pts[0])
        spline = gmsh.model.occ.addBSpline(pts)
        return gmsh.model.occ.addWire([spline])

    def generate_wing_geometry(self) -> Path:
        gmsh.initialize()
        gmsh.model.add("wing_assembly")

        coords = np.loadtxt(self.dat_path)

        sweep_off = self.half_span * np.tan(np.radians(self.sweep_angle))
        dihedral_off = self.half_span * np.tan(np.radians(self.dihedral_angle))

        root_wire = self._make_airfoil_wire(coords, 0.0, self.root_chord, 0.0, 0.0, 0.0)
        tip_wire = self._make_airfoil_wire(
            coords, self.half_span, self.tip_chord, sweep_off, dihedral_off, self.twist_angle
        )
        wing_solid = gmsh.model.occ.addThruSections([root_wire, tip_wire], makeSolid=True)[0][1]

        gmsh.model.occ.synchronize()

        all_vols = gmsh.model.getEntities(3)
        wing_vol_tags = [tag for _, tag in all_vols]

        gmsh.model.addPhysicalGroup(3, wing_vol_tags, 1, name="WING")

        root_faces, tip_faces, skin_faces = [], [], []
        for dim, tag in gmsh.model.getEntities(2):
            adj = gmsh.model.getAdjacencies(dim, tag)
            volumes = adj[0]
            c = gmsh.model.occ.getCenterOfMass(dim, tag)
            if np.isclose(c[1], 0.0, atol=0.05):
                root_faces.append(tag)
            elif np.isclose(c[1], self.half_span, atol=0.05):
                tip_faces.append(tag)
            elif len(volumes) == 1:
                skin_faces.append(tag)

        print(f"    Faces: {len(root_faces)} root (y≈0), {len(tip_faces)} tip (y≈{self.half_span}), {len(skin_faces)} skin")
        for t in root_faces:
            c = gmsh.model.occ.getCenterOfMass(2, t)
            print(f"      root face tag={t}  CoM=({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f})")
        for t in tip_faces:
            c = gmsh.model.occ.getCenterOfMass(2, t)
            print(f"      tip  face tag={t}  CoM=({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f})")
        for t in skin_faces:
            c = gmsh.model.occ.getCenterOfMass(2, t)
            print(f"      skin face tag={t}  CoM=({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f})")

        gmsh.model.addPhysicalGroup(2, root_faces, 10, name="ROOT_BC")
        gmsh.model.addPhysicalGroup(2, skin_faces, 11, name="SKIN_BC")

        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.3)
        gmsh.model.mesh.generate(3)

        msh_path = self.fea_dir / "wing.msh"
        gmsh.write(str(msh_path))
        gmsh.finalize()
        print(f"  Mesh: {msh_path} ({len(wing_vol_tags)} volumes)")
        return msh_path

    def _build_cp_interpolator(self, coords: np.ndarray, pressure: np.ndarray):
        le_idx = int(np.argmin(coords[:, 0]))
        upper = coords[: le_idx + 1][::-1]
        lower = coords[le_idx:]
        upper = upper[np.argsort(upper[:, 0])]
        lower = lower[np.argsort(lower[:, 0])]
        p_upper = pressure[: le_idx + 1][::-1]
        p_lower = pressure[le_idx:]
        p_upper = p_upper[np.argsort(upper[:, 0])]
        p_lower = p_lower[np.argsort(lower[:, 0])]
        x_all = np.concatenate([upper[:, 0], lower[:, 0]])
        p_all = np.concatenate([p_upper, p_lower])
        sort_idx = np.argsort(x_all)
        return interp1d(
            x_all[sort_idx], p_all[sort_idx], fill_value="extrapolate"
        )

    def _compute_skin_forces(
        self, mesh_io, cp_interp
    ) -> tuple[np.ndarray, np.ndarray]:
        points = mesh_io.points

        skin_block = None
        for i, cb in enumerate(mesh_io.cells):
            if cb.type == "triangle":
                phys = mesh_io.cell_data["gmsh:physical"][i]
                if 11 in phys:
                    skin_block = i
                    break

        if skin_block is None:
            raise RuntimeError("No skin triangles (physical=11) found in mesh")

        skin_tris = mesh_io.cells[skin_block].data
        skin_phys = mesh_io.cell_data["gmsh:physical"][skin_block]
        skin_mask = skin_phys == 11
        skin_tris = skin_tris[skin_mask]

        skin_node_ids = np.unique(skin_tris.flatten())
        forces = np.zeros((len(points), 3))
        node_id_map = {nid: i for i, nid in enumerate(skin_node_ids)}

        for tri in skin_tris:
            p0, p1, p2 = points[tri[0]], points[tri[1]], points[tri[2]]
            v1 = p1 - p0
            v2 = p2 - p0
            cross = np.cross(v1, v2)
            area = 0.5 * np.linalg.norm(cross)
            normal = cross / (2.0 * area)

            centroid = (p0 + p1 + p2) / 3.0
            y_pos = centroid[1]
            span_frac = y_pos / self.half_span
            local_chord = self.root_chord + (self.tip_chord - self.root_chord) * span_frac
            sweep_offset = y_pos * np.tan(np.radians(self.sweep_angle))
            x_airfoil = (centroid[0] - sweep_offset) / local_chord
            x_airfoil = np.clip(x_airfoil, 0.001, 0.999)

            dp = float(cp_interp(x_airfoil))

            f_node = (dp * area / 3.0) * normal

            for node_id in tri:
                forces[node_id] += f_node

        loaded_forces = forces[skin_node_ids]
        return skin_node_ids, loaded_forces

    def solve(self, mesh_path: Path, pressure_coords: np.ndarray, pressure_dist: np.ndarray):
        mesh_io = meshio.read(str(mesh_path))
        points = mesh_io.points
        tetra_cells = np.array([cb.data for cb in mesh_io.cells if cb.type == "tetra"][0])

        mesh = felupe.Mesh(points=points, cells=tetra_cells)
        region = felupe.RegionTetra(mesh)
        field = felupe.FieldContainer([felupe.Field(region, dim=3)])

        cp_interp = self._build_cp_interpolator(pressure_coords, pressure_dist)

        skin_node_ids, loaded_forces = self._compute_skin_forces(mesh_io, cp_interp)

        umat = felupe.LinearElastic(E=self.E, nu=self.nu)
        solid = felupe.SolidBody(umat, field)

        load = felupe.PointLoad(field, skin_node_ids.tolist(), values=loaded_forces)

        bounds = {
            "fixed": felupe.dof.Boundary(
                field[0],
                fy=lambda y: np.isclose(y, 0.0, atol=0.05),
            )
        }

        step = felupe.Step(items=[solid, load], boundaries=bounds)
        job = felupe.Job(steps=[step])
        job.evaluate()

        return field, solid, mesh_io

    def _compute_stress(self, solid, field, mesh_io):
        sigma = solid._cauchy_stress()
        s11, s22, s33 = sigma[0, 0], sigma[1, 1], sigma[2, 2]
        s12, s23, s13 = sigma[0, 1], sigma[1, 2], sigma[0, 2]
        vm = np.sqrt(
            0.5 * ((s11 - s22) ** 2 + (s22 - s33) ** 2 + (s33 - s11) ** 2)
            + 3.0 * (s12 ** 2 + s23 ** 2 + s13 ** 2)
        )

        n_quad = vm.shape[0]
        n_elem = vm.shape[1]
        vm_elem = np.mean(vm, axis=0)

        points = mesh_io.points
        tetra_cells = np.array([cb.data for cb in mesh_io.cells if cb.type == "tetra"][0])
        n_nodes = len(points)

        vm_nodal = np.zeros(n_nodes)
        node_count = np.zeros(n_nodes)
        for e in range(n_elem):
            for nid in tetra_cells[e]:
                vm_nodal[nid] += vm_elem[e]
                node_count[nid] += 1
        mask = node_count > 0
        vm_nodal[mask] /= node_count[mask]

        displacement = field[0].values
        max_disp = np.max(np.abs(displacement))
        max_stress = np.max(vm_nodal)
        fs = self.yield_stress / max_stress if max_stress > 0 else float("inf")

        return vm_nodal, max_disp, max_stress, fs

    def _export_vtu(self, mesh_io, field, von_mises, skin_node_ids):
        tetra_cells = np.array([cb.data for cb in mesh_io.cells if cb.type == "tetra"][0])
        points = mesh_io.points.copy()
        displacement = field[0].values

        deformed_points = points.copy()
        deformed_points += displacement

        cells_out = [("tetra", tetra_cells)]

        skin_mask = np.zeros(len(points), dtype=bool)
        skin_mask[skin_node_ids] = True

        point_data = {
            "displacement": displacement,
            "von_mises": von_mises,
            "on_skin": skin_mask.astype(np.float64),
        }

        mesh_out = meshio.Mesh(
            points=deformed_points,
            cells=cells_out,
            point_data=point_data,
        )
        vtu_path = self.fea_dir / "results.vtu"
        meshio.write(str(vtu_path), mesh_out)
        print(f"  VTU exported: {vtu_path}")
        return vtu_path

    def visualize(self, pressure_dist, coords):
        plt = _setup_matplotlib()
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        ax = axes[0]
        le_idx = int(np.argmin(coords[:, 0]))
        upper_coords = coords[:le_idx + 1]
        lower_coords = coords[le_idx:]
        ax.plot(upper_coords[:, 0], upper_coords[:, 1], color=CYAN, linewidth=1.5, label="Upper surface")
        ax.plot(lower_coords[:, 0], lower_coords[:, 1], color=PINK, linewidth=1.5, label="Lower surface")
        ax.fill_between(coords[:, 0], coords[:, 1], alpha=0.1, color=CYAN)
        ax.set_xlabel("x/c")
        ax.set_ylabel("y/c")
        ax.set_title("Optimized Airfoil Shape")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.15)
        ax.legend()

        ax = axes[1]
        ax.plot(coords[:le_idx + 1, 0], pressure_dist[:le_idx + 1], color=CYAN, linewidth=1.5, label="Upper surface")
        ax.plot(coords[le_idx:, 0], pressure_dist[le_idx:], color=PINK, linewidth=1.5, label="Lower surface")
        ax.fill_between(coords[:, 0], pressure_dist, alpha=0.1, color=PINK)
        ax.axhline(0, color=COMMENT, linewidth=0.5)
        ax.set_xlabel("x/c")
        ax.set_ylabel("Pressure (Pa)")
        ax.set_title("CFD Surface Pressure (Aerodynamic Load)")
        ax.grid(True, alpha=0.15)
        ax.legend()

        fig.tight_layout()
        out = str(self.output_dir / "fea_pressure_distribution.png")
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: {out}")
        return out

    def visualize_3d(self, vtu_path: Path):
        grid = pv.read(str(vtu_path))

        plotter = pv.Plotter(
            shape=(1, 2),
            window_size=(1600, 600),
            off_screen=True,
        )

        plotter.subplot(0, 0)
        plotter.add_mesh(
            grid,
            scalars="von_mises",
            cmap="magma",
            show_edges=False,
            scalar_bar_args={
                "title": "von Mises (MPa)",
                "color": FG_COLOR,
                "label_font_size": 10,
            },
        )
        plotter.add_title("Von Mises Stress", color=PURPLE, font_size=12)
        plotter.view_isometric()
        plotter.enable_parallel_projection()

        plotter.subplot(0, 1)
        disp_mag = np.linalg.norm(grid["displacement"], axis=1)
        grid["disp_magnitude"] = disp_mag
        plotter.add_mesh(
            grid,
            scalars="disp_magnitude",
            cmap="coolwarm",
            show_edges=False,
            scalar_bar_args={
                "title": "Displacement (m)",
                "color": FG_COLOR,
                "label_font_size": 10,
            },
        )
        plotter.add_title("Displacement Magnitude", color=PURPLE, font_size=12)
        plotter.view_isometric()
        plotter.enable_parallel_projection()

        plotter.set_background(BG_COLOR)
        plotter.link_views()

        docs_img = Path("docs") / "assets" / "images" / "optimized"
        out_stress = str(docs_img / "fea_stress.png")
        out_disp = str(docs_img / "fea_displacement.png")

        plotter.screenshot(out_stress, scale=2)
        print(f"  Saved: {out_stress}")

        plotter.close()

        plotter2 = pv.Plotter(window_size=(800, 600), off_screen=True)
        plotter2.add_mesh(
            grid,
            scalars="disp_magnitude",
            cmap="coolwarm",
            show_edges=False,
            scalar_bar_args={
                "title": "Displacement (m)",
                "color": FG_COLOR,
                "label_font_size": 10,
            },
        )
        plotter2.add_title("Wing Deformation Under CFD Loads", color=PURPLE, font_size=12)
        plotter2.view_isometric()
        plotter2.enable_parallel_projection()
        plotter2.set_background(BG_COLOR)
        plotter2.screenshot(out_disp, scale=2)
        plotter2.close()
        print(f"  Saved: {out_disp}")

        return out_stress, out_disp

    def run(self):
        print("  [1/6] Extracting CFD pressure...")
        coords, pressure_dist = self.extract_surface_pressure()
        print(f"    Pressure range: [{pressure_dist.min():.1f}, {pressure_dist.max():.1f}] Pa")

        print("  [2/6] Building 3D wing geometry (Gmsh OCC)...")
        mesh_path = self.generate_wing_geometry()

        print("  [3/6] Computing aerodynamic loads on skin...")
        field, solid, mesh_io = self.solve(mesh_path, coords, pressure_dist)

        print("  [4/6] Computing stress and safety factor...")
        von_mises, max_disp, max_stress, fs = self._compute_stress(solid, field, mesh_io)
        print(f"    Max displacement: {max_disp:.6f} m ({max_disp * 1000:.3f} mm)")
        print(f"    Peak von Mises:   {max_stress:.1f} MPa")
        print(f"    Factor of Safety: {fs:.1f}")

        print("  [5/6] Exporting VTU for ParaView...")
        skin_node_ids = np.unique(
            np.array([cb.data for cb in mesh_io.cells if cb.type == "triangle"][0]).flatten()
        )
        vtu_path = self._export_vtu(mesh_io, field, von_mises, skin_node_ids)

        print("  [6/6] Generating plots...")
        self.visualize(pressure_dist, coords)
        self.visualize_3d(vtu_path)

        results = {
            "max_disp": max_disp,
            "max_stress": max_stress,
            "factor_of_safety": fs,
            "von_mises": von_mises,
            "vtu_path": str(vtu_path),
        }

        print("  FEA pipeline complete.")
        return results

    def _compute_skin_forces_3d(
        self, mesh_io, pressure_pts_3d: np.ndarray, pressure_vals_3d: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        points = mesh_io.points
        tree_3d = KDTree(pressure_pts_3d)

        skin_block = None
        for i, cb in enumerate(mesh_io.cells):
            if cb.type == "triangle":
                phys = mesh_io.cell_data["gmsh:physical"][i]
                if 11 in phys:
                    skin_block = i
                    break

        if skin_block is None:
            raise RuntimeError("No skin triangles (physical=11) found in mesh")

        skin_tris = mesh_io.cells[skin_block].data
        skin_phys = mesh_io.cell_data["gmsh:physical"][skin_block]
        skin_mask = skin_phys == 11
        skin_tris = skin_tris[skin_mask]

        skin_node_ids = np.unique(skin_tris.flatten())
        forces = np.zeros((len(points), 3))

        for tri in skin_tris:
            p0, p1, p2 = points[tri[0]], points[tri[1]], points[tri[2]]
            v1 = p1 - p0
            v2 = p2 - p0
            cross = np.cross(v1, v2)
            area = 0.5 * np.linalg.norm(cross)
            normal = cross / (2.0 * area)

            centroid = (p0 + p1 + p2) / 3.0
            _, idx = tree_3d.query(centroid)
            dp = float(pressure_vals_3d[idx])

            f_node = (dp * area / 3.0) * normal
            for node_id in tri:
                forces[node_id] += f_node

        return skin_node_ids, forces[skin_node_ids]

    def run_with_3d(self):
        print("  [1/6] Extracting 3D CFD surface pressure...")
        pressure_pts, pressure_vals = self.extract_surface_pressure_3d()
        print(f"    Points: {len(pressure_pts)}, range: [{pressure_vals.min():.1f}, {pressure_vals.max():.1f}] Pa")

        print("  [2/6] Building 3D wing geometry (Gmsh OCC)...")
        mesh_path = self.generate_wing_geometry()

        print("  [3/6] Computing aerodynamic loads from 3D pressure...")
        mesh_io = meshio.read(str(mesh_path))
        points = mesh_io.points
        tetra_cells = np.array([cb.data for cb in mesh_io.cells if cb.type == "tetra"][0])

        mesh = felupe.Mesh(points=points, cells=tetra_cells)
        region = felupe.RegionTetra(mesh)
        field = felupe.FieldContainer([felupe.Field(region, dim=3)])

        skin_node_ids, loaded_forces = self._compute_skin_forces_3d(mesh_io, pressure_pts, pressure_vals)

        umat = felupe.LinearElastic(E=self.E, nu=self.nu)
        solid = felupe.SolidBody(umat, field)
        load = felupe.PointLoad(field, skin_node_ids.tolist(), values=loaded_forces)

        bounds = {
            "fixed": felupe.dof.Boundary(
                field[0],
                fy=lambda y: np.isclose(y, 0.0, atol=0.05),
            )
        }
        step = felupe.Step(items=[solid, load], boundaries=bounds)
        job = felupe.Job(steps=[step])
        job.evaluate()

        print("  [4/6] Computing stress and safety factor...")
        von_mises, max_disp, max_stress, fs = self._compute_stress(solid, field, mesh_io)

        print("  [5/6] Exporting VTU for ParaView...")
        vtu_path = self._export_vtu(mesh_io, field, von_mises, skin_node_ids)

        print("  [6/6] Generating 3D contour plots...")
        self.visualize_3d(vtu_path)

        results = {
            "max_disp": max_disp,
            "max_stress": max_stress,
            "factor_of_safety": fs,
            "von_mises": von_mises,
            "vtu_path": str(vtu_path),
        }

        print("  3D FEA pipeline complete.")
        return results
