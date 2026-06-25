from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
import numpy as np


def load_coordinates(filepath: str | Path) -> np.ndarray:
    return np.loadtxt(filepath)


def _airfoil_points(
    coords: np.ndarray,
    chord: float,
    sweep: float,
    dihedral: float,
    twist: float,
) -> list[tuple[float, float]]:
    points = []
    for x_norm, y_norm in coords:
        vx = float(x_norm) * chord
        vz = float(y_norm) * chord
        tr = math.radians(twist)
        ct, st = math.cos(tr), math.sin(tr)
        x = vx * ct + vz * st + sweep
        z = -vx * st + vz * ct + dihedral
        points.append((x, z))
    return points


def _thick_camber(coords: np.ndarray, x_frac: float) -> tuple[float, float]:
    le_idx = int(np.argmin(coords[:, 0]))
    u = coords[: le_idx + 1]
    l = coords[le_idx:][::-1]
    u = u[np.argsort(u[:, 0])]
    l = l[np.argsort(l[:, 0])]
    yu = float(np.interp(x_frac, u[:, 0], u[:, 1]))
    yl = float(np.interp(x_frac, l[:, 0], l[:, 1]))
    return yu - yl, (yu + yl) / 2


def generate_wing(
    coords: np.ndarray,
    root_chord: float = 2.5,
    tip_chord: float = 0.75,
    half_span: float = 5.5,
    sweep_angle: float = 25.0,
    dihedral_angle: float = 3.0,
    twist: float = -2.0,
    spar_chord_fraction: float = 0.3,
    spar_width: float = 0.05,
    n_ribs: int = 10,
    rib_thickness: float = 0.003,
    filepath: str | Path | None = None,
) -> cq.Compound:
    sweep_off = half_span * math.tan(math.radians(sweep_angle))
    dihedral_off = half_span * math.tan(math.radians(dihedral_angle))

    root_pts = _airfoil_points(coords, root_chord, 0.0, 0.0, 0.0)
    tip_pts = _airfoil_points(coords, tip_chord, sweep_off, dihedral_off, twist)

    wing_wp = (
        cq.Workplane("XZ")
        .spline(root_pts)
        .close()
        .workplane(offset=half_span)
        .spline(tip_pts)
        .close()
        .loft()
    )
    wing = wing_wp.solids().val()
    print(f"  Wing solid:         {wing.Volume():.4f} m^3")

    t_root, cam_root = _thick_camber(coords, spar_chord_fraction)
    t_tip, cam_tip = _thick_camber(coords, spar_chord_fraction)
    sh_root = t_root * root_chord * 0.15
    sh_tip = t_tip * tip_chord * 0.15

    sx_root = spar_chord_fraction * root_chord
    sz_root = cam_root * root_chord
    sx_tip = spar_chord_fraction * tip_chord + sweep_off
    sz_tip = cam_tip * tip_chord + dihedral_off

    root_spar_pts = [
        cq.Vector(sx_root - spar_width / 2, 0.0, sz_root - sh_root / 2),
        cq.Vector(sx_root + spar_width / 2, 0.0, sz_root - sh_root / 2),
        cq.Vector(sx_root + spar_width / 2, 0.0, sz_root + sh_root / 2),
        cq.Vector(sx_root - spar_width / 2, 0.0, sz_root + sh_root / 2),
    ]
    tip_spar_pts = [
        cq.Vector(sx_tip - spar_width / 2, -half_span, sz_tip - sh_tip / 2),
        cq.Vector(sx_tip + spar_width / 2, -half_span, sz_tip - sh_tip / 2),
        cq.Vector(sx_tip + spar_width / 2, -half_span, sz_tip + sh_tip / 2),
        cq.Vector(sx_tip - spar_width / 2, -half_span, sz_tip + sh_tip / 2),
    ]

    root_spar_wire = cq.Wire.makePolygon(root_spar_pts, close=True)
    tip_spar_wire = cq.Wire.makePolygon(tip_spar_pts, close=True)
    spar = cq.Solid.makeLoft([root_spar_wire, tip_spar_wire])
    print(f"  Spar:               {spar.Volume():.6f} m^3")

    ribs = []
    n_inner = n_ribs - 2
    for i in range(1, n_inner + 1):
        f = i / (n_ribs - 1)

        rib_chord = root_chord + f * (tip_chord - root_chord)
        rib_sweep = f * sweep_off
        rib_dihedral = f * dihedral_off
        rib_twist = f * twist
        y_pos = -f * half_span

        rib_xy = _airfoil_points(coords, rib_chord, rib_sweep, rib_dihedral, rib_twist)
        rib_wire = cq.Workplane("XZ").spline(rib_xy).close().wires().val()
        rib = cq.Solid.extrudeLinear(rib_wire, [], cq.Vector(0, rib_thickness, 0))
        rib = rib.translate(cq.Vector(0, y_pos - rib_thickness / 2, 0))
        ribs.append(rib)

    print(f"  Ribs:               {len(ribs)} ribs created")
    if ribs:
        total_rib_vol = sum(r.Volume() for r in ribs)
        print(f"  Total ribs volume:  {total_rib_vol:.6f} m^3")

    assembly = cq.Compound.makeCompound([wing, spar] + ribs)
    print(f"  Assembly:           {len(assembly.Solids())} bodies")

    if filepath is not None:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(assembly, str(filepath), "STEP")

    return assembly
