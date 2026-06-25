from __future__ import annotations

import math
import re
import tempfile
from pathlib import Path

import numpy as np

from physics.mesher import MeshGenerator


def _parse_su2_2d(path: Path) -> tuple:
    nodes: list[tuple[float, float]] = []
    elements: list[tuple[int, list[int], int]] = []
    boundaries: list[tuple[str, list]] = []

    text = path.read_text()

    npoint_match = re.search(r"NPOIN=\s*(\d+)", text)
    nelem_match = re.search(r"NELEM=\s*(\d+)", text)
    npoint = int(npoint_match.group(1)) if npoint_match else 0
    nelem = int(nelem_match.group(1)) if nelem_match else 0

    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line.startswith("NPOIN="):
            i += 1
            for _ in range(npoint):
                parts = lines[i].strip().split()
                nodes.append((float(parts[0]), float(parts[1])))
                i += 1
            continue

        if line.startswith("NELEM="):
            i += 1
            for _ in range(nelem):
                parts = lines[i].strip().split()
                etype = int(parts[0])
                enodes = [int(p) for p in parts[1:-1]]
                etag = int(parts[-1])
                elements.append((etype, enodes, etag))
                i += 1
            continue

        if line.startswith("MARKER_TAG="):
            mname = line.split("=", 1)[1].strip()
            i += 1
            subline = lines[i].strip()
            mcount = int(subline.split("=")[1])
            i += 1
            belem: list[tuple[int, list[int]]] = []
            for _ in range(mcount):
                parts = lines[i].strip().split()
                btype = int(parts[0])
                bnodes = [int(p) for p in parts[1:]]
                belem.append((btype, bnodes))
                i += 1
            boundaries.append((mname, belem))
            continue

        i += 1

    return np.array(nodes), elements, boundaries


def _write_su2_3d(
    path: Path,
    nodes_3d: list[tuple[float, float, float]],
    elems_3d: list[tuple[int, list[int], int]],
    boundaries_3d: list[tuple[str, list[tuple[int, list[int]]]]],
):
    lines: list[str] = []
    lines.append("NDIME= 3")
    lines.append(f"NELEM= {len(elems_3d)}")
    for etype, enodes, etag in elems_3d:
        lines.append(f"{etype} " + " ".join(str(n) for n in enodes) + f" {etag}")
    lines.append(f"NPOIN= {len(nodes_3d)}")
    for x, y, z in nodes_3d:
        lines.append(f"{x:.15e} {y:.15e} {z:.15e}")
    lines.append(f"NMARK= {len(boundaries_3d)}")
    for mname, belems in boundaries_3d:
        lines.append(f"MARKER_TAG= {mname}")
        lines.append(f"MARKER_ELEMS= {len(belems)}")
        for btype, bnodes in belems:
            lines.append(f"{btype} " + " ".join(str(n) for n in bnodes))
    path.write_text("\n".join(lines) + "\n")


class MeshGenerator3D:
    """Generate 3D mesh by extruding a 2D C-grid in the spanwise direction."""

    # SU2 element types
    TRI_2D = 5
    QUAD_2D = 9
    LINE_2D = 3
    PRISM_3D = 13
    HEX_3D = 12
    TRI_3D = 5

    def __init__(self, mesh_density: float = 1.0, span_layers: int = 30):
        self.mesh_density = mesh_density
        self.span_layers = span_layers

    def generate(
        self,
        dat_file: str | Path,
        output_su2: str | Path,
        root_chord: float = 2.5,
        tip_chord: float = 0.75,
        half_span: float = 5.5,
        sweep_angle: float = 25.0,
        dihedral_angle: float = 3.0,
        twist_angle: float = -2.0,
        quiet: bool = True,
    ) -> Path:
        dat_file = Path(dat_file)
        output_su2 = Path(output_su2)
        output_su2.parent.mkdir(parents=True, exist_ok=True)

        span = 2.0 * half_span

        print("  [1/3] Generating 2D C-grid mesh with boundary layers...")
        tmp_dir = Path(tempfile.mkdtemp())
        mesh_2d_path = tmp_dir / "mesh_2d.su2"
        mesher = MeshGenerator(mesh_density=self.mesh_density)
        mesher.generate(str(dat_file), str(mesh_2d_path), quiet=quiet)

        print("  [2/3] Parsing 2D mesh and extruding to 3D...")
        nodes_2d, elems_2d, boundaries_2d = _parse_su2_2d(mesh_2d_path)
        n2d = len(nodes_2d)
        print(f"    2D nodes: {n2d}, elements: {len(elems_2d)}, boundaries: {len(boundaries_2d)}")

        sweep_off = span * math.tan(math.radians(sweep_angle))
        dihedral_off = span * math.tan(math.radians(dihedral_angle))

        nodes_3d: list[tuple[float, float, float]] = []
        for layer in range(self.span_layers + 1):
            z = layer * (span / self.span_layers)
            s = z / span
            sw = s * sweep_off
            dh = s * dihedral_off
            tw = math.radians(s * twist_angle)
            ct, st = math.cos(tw), math.sin(tw)
            for x_2d, y_2d in nodes_2d:
                xx = x_2d * ct - y_2d * st + sw
                yy = x_2d * st + y_2d * ct + dh
                nodes_3d.append((xx, yy, z))

        def nid(layer: int, i: int) -> int:
            return i + layer * n2d

        elems_3d: list[tuple[int, list[int], int]] = []
        for etype, enodes, etag in elems_2d:
            if etype == self.TRI_2D:
                a, b, c = enodes
                for L in range(self.span_layers):
                    elems_3d.append((
                        self.PRISM_3D,
                        [nid(L, a), nid(L, b), nid(L, c),
                         nid(L + 1, a), nid(L + 1, b), nid(L + 1, c)],
                        etag,
                    ))
            elif etype == self.QUAD_2D:
                a, b, c, d = enodes
                for L in range(self.span_layers):
                    elems_3d.append((
                        self.HEX_3D,
                        [nid(L, a), nid(L, b), nid(L, c), nid(L, d),
                         nid(L + 1, a), nid(L + 1, b), nid(L + 1, c), nid(L + 1, d)],
                        etag,
                    ))

        wing_marker_name = "wing"
        farfield_marker_name = "farfield"
        marker_map = {
            "airfoil": wing_marker_name,
            "farfield": farfield_marker_name,
        }

        side_boundaries: dict[str, list[tuple[int, list[int]]]] = {}
        for marker_name, belems in boundaries_2d:
            mapped = marker_map.get(marker_name, marker_name)
            if mapped not in side_boundaries:
                side_boundaries[mapped] = []
            for btype, bnodes in belems:
                if btype == self.LINE_2D:
                    a, b = bnodes
                    for L in range(self.span_layers):
                        side_boundaries[mapped].append((
                            self.TRI_3D,
                            [nid(L, a), nid(L, b), nid(L + 1, a)],
                        ))
                        side_boundaries[mapped].append((
                            self.TRI_3D,
                            [nid(L, b), nid(L + 1, b), nid(L + 1, a)],
                        ))

        if farfield_marker_name not in side_boundaries:
            side_boundaries[farfield_marker_name] = []

        cap_boundaries: list[tuple[int, list[int]]] = []
        for etype, enodes, etag in elems_2d:
            if etype == self.TRI_2D:
                a, b, c = enodes
                cap_boundaries.append((self.TRI_3D, [nid(0, a), nid(0, b), nid(0, c)]))
                cap_boundaries.append((self.TRI_3D, [nid(self.span_layers, a), nid(self.span_layers, b), nid(self.span_layers, c)]))

        boundaries_3d: list[tuple[str, list]] = []
        boundaries_3d.append((wing_marker_name, side_boundaries.get(wing_marker_name, [])))

        farfield_all = side_boundaries.get(farfield_marker_name, []) + cap_boundaries
        boundaries_3d.append((farfield_marker_name, farfield_all))

        print(f"    3D nodes: {len(nodes_3d)}, elements: {len(elems_3d)}")
        print(f"    Boundaries: wing={len(boundaries_3d[0][1])} tris, farfield={len(boundaries_3d[1][1])} tris")

        print("  [3/3] Writing 3D SU2 mesh...")
        _write_su2_3d(output_su2, nodes_3d, elems_3d, boundaries_3d)

        print(f"    Mesh exported: {output_su2}")
        return output_su2
