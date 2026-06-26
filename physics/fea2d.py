from __future__ import annotations

from pathlib import Path

import felupe
import gmsh
import matplotlib
import meshio
import numpy as np
import pyvista as pv
from scipy.spatial import KDTree

BG_COLOR = "#282a36"
CARD_BG = "#44475a"
FG_COLOR = "#f8f8f2"
PINK = "#ff79c6"
PURPLE = "#bd93f9"
CYAN = "#8be9fd"
GREEN = "#50fa7b"
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


class Fea2dAnalysis:
    def __init__(
        self,
        vtu_path: str,
        dat_path: str,
        output_dir: str,
        label: str = "airfoil",
    ):
        self.vtu_path = Path(vtu_path)
        self.dat_path = Path(dat_path)
        self.output_dir = Path(output_dir)
        self.label = label

        self.E = 71.7e3
        self.nu = 0.33
        self.yield_stress = 503.0
        self.p_inf = 28994.36

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fea_dir = self.output_dir / "fea_2d"
        self.fea_dir.mkdir(parents=True, exist_ok=True)

        self.docs_img = Path("docs") / "assets" / "images" / ("naca0012" if "naca" in label.lower() else "optimized")
        self.docs_img.mkdir(parents=True, exist_ok=True)

    def extract_surface_pressure(self) -> tuple[np.ndarray, np.ndarray]:
        coords = np.loadtxt(self.dat_path)
        grid = pv.read(str(self.vtu_path))
        tree = KDTree(grid.points[:, :2])
        _, indices = tree.query(coords)
        p_surf = grid["Pressure"][indices]
        return coords, p_surf - self.p_inf

    def generate_2d_mesh(self, coords: np.ndarray) -> Path:
        gmsh.initialize()
        gmsh.model.add("airfoil_2d")

        pts = []
        for x, y in coords:
            pid = gmsh.model.geo.addPoint(x, y, 0.0)
            pts.append(pid)

        # Use individual lines between consecutive points so Gmsh
        # places mesh nodes at every .dat coordinate
        lines = []
        for i in range(len(pts)):
            lines.append(gmsh.model.geo.addLine(pts[i], pts[(i + 1) % len(pts)]))
        loop = gmsh.model.geo.addCurveLoop(lines)
        surf = gmsh.model.geo.addPlaneSurface([loop])

        gmsh.model.geo.synchronize()

        gmsh.model.addPhysicalGroup(1, lines, name="airfoil_boundary")
        gmsh.model.addPhysicalGroup(2, [surf], name="airfoil_interior")

        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 0.02)
        gmsh.model.mesh.generate(2)

        msh_path = self.fea_dir / "airfoil_2d.msh"
        gmsh.write(str(msh_path))
        gmsh.finalize()
        return msh_path

    def solve(self, mesh_path: Path, coords: np.ndarray, pressure: np.ndarray):
        m = meshio.read(str(mesh_path))
        points = m.points[:, :2]

        all_tri = [cb.data for cb in m.cells if cb.type == "triangle"]
        tri_cells = np.concatenate(all_tri, axis=0) if len(all_tri) > 1 else all_tri[0]

        mesh = felupe.Mesh(points=points, cells=tri_cells)
        region = felupe.RegionTriangle(mesh)
        field = felupe.FieldContainer([felupe.Field(region, dim=2)])

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
        from scipy.interpolate import interp1d
        cp_interp = interp1d(x_all[sort_idx], p_all[sort_idx], fill_value="extrapolate")

        all_line_segs = []
        for i, cb in enumerate(m.cells):
            if cb.type == "line":
                phys = m.cell_data["gmsh:physical"][i]
                mask = phys == 1
                if mask.any():
                    all_line_segs.append(cb.data[mask])

        if not all_line_segs:
            raise RuntimeError("No boundary lines (physical=1) found")

        line_cells = np.concatenate(all_line_segs, axis=0)

        forces = np.zeros((len(points), 2))
        boundary_node_ids = np.unique(line_cells.flatten())

        for seg in line_cells:
            p0, p1 = points[seg[0]], points[seg[1]]
            mid = (p0 + p1) / 2.0
            dp = float(cp_interp(mid[0]))
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            length = np.sqrt(dx * dx + dy * dy)
            normal = np.array([dy, -dx]) / length
            f_node = (-dp * length / 2.0) * normal
            for node_id in seg:
                forces[node_id] += f_node

        umat = felupe.LinearElasticPlaneStress(E=self.E, nu=self.nu)
        solid = felupe.SolidBody(umat, field)

        loaded_forces = forces[boundary_node_ids]
        load = felupe.PointLoad(field, boundary_node_ids.tolist(), values=loaded_forces)

        bounds = {
            "fixed": felupe.dof.Boundary(
                field[0],
                fx=lambda x: np.isclose(x, 1.0, atol=0.02),
                skip=(False, False),
            )
        }

        step = felupe.Step(items=[solid, load], boundaries=bounds)
        job = felupe.Job(steps=[step])
        job.evaluate()

        return field, solid, m

    def _compute_stress(self, solid, field, mesh_io):
        sigma = solid._cauchy_stress()
        s11, s22 = sigma[0, 0], sigma[1, 1]
        s12 = sigma[0, 1]
        s33 = self.nu * (s11 + s22)

        vm = np.sqrt(
            0.5 * ((s11 - s22) ** 2 + (s22 - s33) ** 2 + (s33 - s11) ** 2)
            + 3.0 * s12 ** 2
        )

        n_quad = vm.shape[0]
        n_elem = vm.shape[1]
        vm_elem = np.mean(vm, axis=0)

        all_tri = [cb.data for cb in mesh_io.cells if cb.type == "triangle"]
        tri_cells = np.concatenate(all_tri, axis=0) if len(all_tri) > 1 else all_tri[0]
        points = mesh_io.points[:, :2]
        n_nodes = len(points)

        vm_nodal = np.zeros(n_nodes)
        node_count = np.zeros(n_nodes)
        for e in range(n_elem):
            for nid in tri_cells[e]:
                vm_nodal[nid] += vm_elem[e]
                node_count[nid] += 1
        mask = node_count > 0
        vm_nodal[mask] /= node_count[mask]

        displacement = field[0].values
        max_disp = np.max(np.abs(displacement))
        max_stress = np.max(vm_nodal)
        fs = self.yield_stress / max_stress if max_stress > 0 else float("inf")

        return vm_nodal, max_disp, max_stress, fs

    def _export_vtu(self, mesh_io, field, von_mises):
        all_tri_export = [cb.data for cb in mesh_io.cells if cb.type == "triangle"]
        tri_cells = np.concatenate(all_tri_export, axis=0) if len(all_tri_export) > 1 else all_tri_export[0]
        points = mesh_io.points[:, :2].copy()
        displacement_3d = np.zeros((len(points), 3))
        displacement_3d[:, :2] = field[0].values

        cells_out = [("triangle", tri_cells)]

        point_data = {
            "displacement": displacement_3d,
            "von_mises": von_mises,
        }

        mesh_out = meshio.Mesh(
            points=np.column_stack([points, np.zeros(len(points))]),
            cells=cells_out,
            point_data=point_data,
        )
        vtu_path = self.fea_dir / "results_2d.vtu"
        meshio.write(str(vtu_path), mesh_out)
        return vtu_path

    def visualize(self, von_mises, pressure, coords):
        plt = _setup_matplotlib()
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        ax = axes[0]
        le_idx = int(np.argmin(coords[:, 0]))
        upper_coords = coords[: le_idx + 1]
        lower_coords = coords[le_idx:]
        ax.plot(upper_coords[:, 0], upper_coords[:, 1], color=CYAN, linewidth=1.5, label="Upper")
        ax.plot(lower_coords[:, 0], lower_coords[:, 1], color=PINK, linewidth=1.5, label="Lower")
        ax.fill_between(coords[:, 0], coords[:, 1], alpha=0.1, color=CYAN)
        ax.set_xlabel("x/c")
        ax.set_ylabel("y/c")
        ax.set_title(f"{self.label} Airfoil Shape")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.15)
        ax.legend()

        ax = axes[1]
        ax.plot(coords[: le_idx + 1, 0], pressure[: le_idx + 1], color=CYAN, linewidth=1.5, label="Upper")
        ax.plot(coords[le_idx:, 0], pressure[le_idx:], color=PINK, linewidth=1.5, label="Lower")
        ax.fill_between(coords[:, 0], pressure, alpha=0.1, color=PINK)
        ax.axhline(0, color=COMMENT, linewidth=0.5)
        ax.set_xlabel("x/c")
        ax.set_ylabel("Pressure (Pa)")
        ax.set_title("CFD Surface Pressure")
        ax.grid(True, alpha=0.15)
        ax.legend()

        fig.tight_layout()
        out = self.docs_img / "fea2d_pressure.png"
        fig.savefig(str(out), dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    def visualize_stress(self, vtu_path):
        grid = pv.read(str(vtu_path))
        plotter = pv.Plotter(window_size=(1200, 500), off_screen=True)
        plotter.add_mesh(
            grid,
            scalars="von_mises",
            cmap="magma",
            show_edges=True,
            scalar_bar_args={
                "title": "von Mises (MPa)",
                "color": FG_COLOR,
                "label_font_size": 10,
            },
        )
        plotter.add_title(f"{self.label} - 2D Plane Stress", color=PURPLE, font_size=12)
        plotter.view_xy()
        plotter.set_background(BG_COLOR)
        out_stress = self.docs_img / "fea2d_stress.png"
        plotter.screenshot(str(out_stress), scale=2)
        plotter.close()

        plotter2 = pv.Plotter(window_size=(1200, 500), off_screen=True)
        disp_mag = np.linalg.norm(grid["displacement"], axis=1)
        grid["disp_magnitude"] = disp_mag
        plotter2.add_mesh(
            grid,
            scalars="disp_magnitude",
            cmap="coolwarm",
            show_edges=True,
            scalar_bar_args={
                "title": "Disp (m)",
                "color": FG_COLOR,
                "label_font_size": 10,
            },
        )
        plotter2.add_title(f"{self.label} - Displacement", color=PURPLE, font_size=12)
        plotter2.view_xy()
        plotter2.set_background(BG_COLOR)
        out_disp = self.docs_img / "fea2d_displacement.png"
        plotter2.screenshot(str(out_disp), scale=2)
        plotter2.close()

        return out_stress, out_disp

    def run(self):
        print(f"  [{self.label}] [1/5] Extracting CFD pressure...")
        coords, pressure_dist = self.extract_surface_pressure()
        print(f"    Pressure range: [{pressure_dist.min():.1f}, {pressure_dist.max():.1f}] Pa")

        print(f"  [{self.label}] [2/5] Generating 2D triangle mesh (Gmsh)...")
        mesh_path = self.generate_2d_mesh(coords)

        print(f"  [{self.label}] [3/5] Running plane-stress FElupe solve...")
        field, solid, mesh_io = self.solve(mesh_path, coords, pressure_dist)

        print(f"  [{self.label}] [4/5] Computing stress and safety factor...")
        von_mises, max_disp, max_stress, fs = self._compute_stress(solid, field, mesh_io)
        print(f"    Max displacement: {max_disp * 1000:.3f} mm")
        print(f"    Peak von Mises:   {max_stress:.1f} MPa")
        print(f"    Factor of Safety: {fs:.1f}")

        print(f"  [{self.label}] [5/5] Exporting and visualizing...")
        vtu_path = self._export_vtu(mesh_io, field, von_mises)
        self.visualize(von_mises, pressure_dist, coords)
        self.visualize_stress(vtu_path)

        results = {
            "max_disp": max_disp,
            "max_stress": max_stress,
            "factor_of_safety": fs,
            "vtu_path": str(vtu_path),
        }
        print(f"  [{self.label}] 2D FEA complete.")
        return results
