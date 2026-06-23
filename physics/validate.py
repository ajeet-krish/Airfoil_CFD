from __future__ import annotations

"""
Experimental reference data for NACA 0012 validation.

Sources:
    - Ladson, C.L. (1988). "Effects of Independent Variation of Mach and
      Reynolds Numbers on the Low-Speed Aerodynamic Characteristics of the
      NACA 0012 Airfoil Section." NASA TM 4074.
    - Abbott, I.H. & von Doenhoff, A.E. (1949). "Theory of Wing Sections."
"""

# NACA 0012 — Re = 1x10^6, M ≈ 0.15 (approximate digitized values)
# Format: (angle_deg, CL, CD)
NACA0012_RE1E6: list[tuple[float, float, float]] = [
    (0.0,   0.000,  0.0070),
    (2.0,   0.220,  0.0080),
    (4.0,   0.430,  0.0095),
    (6.0,   0.640,  0.0120),
    (8.0,   0.840,  0.0165),
    (10.0,  1.020,  0.0240),
    (12.0,  1.140,  0.0360),
    (14.0,  1.200,  0.0550),
    (16.0,  1.100,  0.0800),
    (18.0,  0.980,  0.1100),
]


def get_cl_alpha() -> list[tuple[float, float]]:
    """Return (alpha, CL) pairs for NACA 0012 at Re=1e6."""
    return [(a, cl) for a, cl, _ in NACA0012_RE1E6]


def get_cd_alpha() -> list[tuple[float, float]]:
    """Return (alpha, CD) pairs for NACA 0012 at Re=1e6."""
    return [(a, cd) for a, _, cd in NACA0012_RE1E6]


def get_drag_polar() -> list[tuple[float, float]]:
    """Return (CD, CL) pairs for NACA 0012 at Re=1e6."""
    return [(cd, cl) for _, cl, cd in NACA0012_RE1E6]
