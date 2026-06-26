from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
import numpy as np


def _airfoil_points(
    coords: np.ndarray,
    chord: float,
    sweep: float,
    dihedral: float,
    twist: float,
) -> list[tuple[float, float]]:
    pts = []
    for x_norm, y_norm in coords:
        vx = float(x_norm) * chord
        vz = float(y_norm) * chord
        tr = math.radians(twist)
        ct, st = math.cos(tr), math.sin(tr)
        x = vx * ct + vz * st + sweep
        z = -vx * st + vz * ct + dihedral
        pts.append((x, z))
    return pts


def _make_half_wing(
    coords: np.ndarray,
    root_chord: float,
    tip_chord: float,
    half_span: float,
    sweep_angle: float,
    dihedral_angle: float,
    twist: float,
) -> cq.Workplane:
    sweep_off = half_span * math.tan(math.radians(sweep_angle))
    dihedral_off = half_span * math.tan(math.radians(dihedral_angle))

    root_pts = _airfoil_points(coords, root_chord, 0.0, 0.0, 0.0)
    tip_pts = _airfoil_points(coords, tip_chord, sweep_off, dihedral_off, twist)

    wing = (
        cq.Workplane("YZ")
        .spline([(z, x) for x, z in root_pts])
        .close()
        .workplane(offset=half_span)
        .spline([(z, x) for x, z in tip_pts])
        .close()
        .loft()
    )
    return wing


def _fuselage_y_radius(z: float, length: float, max_height: float) -> float:
    h2 = max_height / 2
    secs = [
        (0.0, 0.005),
        (0.05 * length, h2 * 0.08),
        (0.1 * length, h2 * 0.18),
        (0.15 * length, h2 * 0.30),
        (0.2 * length, h2 * 0.42),
        (0.25 * length, h2 * 0.54),
        (0.3 * length, h2 * 0.65),
        (0.35 * length, h2 * 0.75),
        (0.4 * length, h2 * 0.83),
        (0.45 * length, h2 * 0.90),
        (0.5 * length, h2 * 0.95),
        (0.55 * length, h2 * 0.98),
        (0.6 * length, h2),
        (0.65 * length, h2),
        (0.85 * length, h2 * 0.7),
        (0.95 * length, h2 * 0.3),
        (length, 0.04),
    ]
    if z <= secs[0][0]:
        return secs[0][1]
    if z >= secs[-1][0]:
        return secs[-1][1]
    for i in range(len(secs) - 1):
        z1, r1 = secs[i]
        z2, r2 = secs[i + 1]
        if z1 <= z <= z2:
            t = (z - z1) / (z2 - z1) if z2 > z1 else 0
            return r1 + t * (r2 - r1)
    return 0.04


def _make_fuselage(
    length: float = 10.0,
    max_width: float = 1.2,
    max_height: float = 0.8,
) -> cq.Workplane:
    w2 = max_width / 2
    h2 = max_height / 2

    sections = [
        (0.0, 0.005, 0.005),
        (0.05 * length, w2 * 0.08, h2 * 0.08),
        (0.1 * length, w2 * 0.18, h2 * 0.18),
        (0.15 * length, w2 * 0.30, h2 * 0.30),
        (0.2 * length, w2 * 0.42, h2 * 0.42),
        (0.25 * length, w2 * 0.54, h2 * 0.54),
        (0.3 * length, w2 * 0.65, h2 * 0.65),
        (0.35 * length, w2 * 0.75, h2 * 0.75),
        (0.4 * length, w2 * 0.83, h2 * 0.83),
        (0.45 * length, w2 * 0.90, h2 * 0.90),
        (0.5 * length, w2 * 0.95, h2 * 0.95),
        (0.55 * length, w2 * 0.98, h2 * 0.98),
        (0.6 * length, w2, h2),
        (0.65 * length, w2, h2),
        (0.85 * length, w2 * 0.7, h2 * 0.7),
        (0.95 * length, w2 * 0.3, h2 * 0.3),
        (length, 0.04, 0.04),
    ]

    wp = cq.Workplane("XY")
    for i, (z, rx, ry) in enumerate(sections):
        if i == 0:
            wp = wp.center(0, 0).ellipse(rx, ry)
        else:
            wp = wp.workplane(offset=z - sections[i - 1][0]).center(0, 0).ellipse(rx, ry)

    return wp.loft()


def _make_hstab(
    coords: np.ndarray,
    span: float = 2.0,
    root_chord: float = 0.8,
    tip_chord: float = 0.4,
    sweep_angle: float = 15.0,
    z_offset: float = 7.5,
    y_offset: float = 0.0,
) -> cq.Workplane:
    sweep_off = span * math.tan(math.radians(sweep_angle))

    root_pts = _airfoil_points(coords, root_chord, 0.0, 0.0, 0.0)
    tip_pts = _airfoil_points(coords, tip_chord, sweep_off, 0.0, 0.0)

    hstab = (
        cq.Workplane("YZ")
        .spline([(z, x) for x, z in root_pts])
        .close()
        .workplane(offset=span)
        .spline([(z, x) for x, z in tip_pts])
        .close()
        .loft()
    )
    hstab = hstab.translate(cq.Vector(0, y_offset, z_offset))
    return hstab


def _make_vstab(
    coords: np.ndarray,
    span: float = 1.5,
    root_chord: float = 1.2,
    tip_chord: float = 0.3,
    sweep_angle: float = 30.0,
    z_offset: float = 7.5,
    y_offset: float = 0.0,
) -> cq.Workplane:
    sweep_off = span * math.tan(math.radians(sweep_angle))

    root_pts = _airfoil_points(coords, root_chord, 0.0, 0.0, 0.0)
    tip_pts = _airfoil_points(coords, tip_chord, sweep_off, 0.0, 0.0)

    vstab = (
        cq.Workplane("XZ")
        .spline([(z, x) for x, z in root_pts])
        .close()
        .workplane(offset=-span)
        .spline([(z, x) for x, z in tip_pts])
        .close()
        .loft()
    )
    vstab = vstab.translate(cq.Vector(0, y_offset, z_offset))
    return vstab


def build_aircraft(
    coords: np.ndarray,
    fuselage_length: float = 10.0,
    fuselage_width: float = 1.2,
    fuselage_height: float = 0.8,
    wing_root_chord: float = 2.5,
    wing_tip_chord: float = 0.75,
    wing_half_span: float = 5.5,
    wing_sweep: float = 25.0,
    wing_dihedral: float = 3.0,
    wing_twist: float = -2.0,
    wing_z_pos: float = 3.5,
    hstab_span: float = 2.0,
    hstab_root_chord: float = 0.8,
    hstab_tip_chord: float = 0.4,
    hstab_sweep: float = 15.0,
    hstab_z_pos: float = 8.5,
    hstab_y_pos: float = 0.0,
    vstab_coords: np.ndarray | None = None,
    vstab_span: float = 1.5,
    vstab_root_chord: float = 1.2,
    vstab_tip_chord: float = 0.3,
    vstab_sweep: float = 30.0,
    vstab_z_pos: float = 8.5,
    filepath: str | Path | None = None,
) -> cq.Compound:
    print("  Building fuselage...")
    fuselage = _make_fuselage(fuselage_length, fuselage_width, fuselage_height)

    print("  Building right wing...")
    right_wing = _make_half_wing(
        coords, wing_root_chord, wing_tip_chord, wing_half_span,
        wing_sweep, wing_dihedral, wing_twist,
    ).translate(cq.Vector(0, 0, wing_z_pos))

    print("  Building left wing (mirror)...")
    left_wing = _make_half_wing(
        coords, wing_root_chord, wing_tip_chord, wing_half_span,
        wing_sweep, wing_dihedral, wing_twist,
    ).translate(cq.Vector(0, 0, wing_z_pos)).mirror(mirrorPlane="YZ")

    print("  Building horizontal stabilizer...")
    hstab = _make_hstab(
        coords, hstab_span, hstab_root_chord, hstab_tip_chord,
        hstab_sweep, hstab_z_pos, hstab_y_pos,
    )
    hstab_right = hstab
    hstab_left = hstab.mirror(mirrorPlane="YZ")

    print("  Building vertical stabilizer...")
    vstab_airfoil = vstab_coords if vstab_coords is not None else coords
    vstab = _make_vstab(
        vstab_airfoil, vstab_span, vstab_root_chord, vstab_tip_chord,
        vstab_sweep, vstab_z_pos, 0.0,
    )

    bodies = [
        fuselage.val(),
        right_wing.val(),
        left_wing.val(),
        hstab_right.val(),
        hstab_left.val(),
        vstab.val(),
    ]

    assembly = cq.Compound.makeCompound(bodies)
    print(f"  Assembly: {len(assembly.Solids())} bodies")

    if filepath is not None:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(assembly, str(filepath), "STEP")
        print(f"  STEP exported: {filepath}")

    return assembly
