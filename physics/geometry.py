from __future__ import annotations

import numpy as np


def generate_naca_4digit(
    m: float, p: float, t: float, num_points: int = 200
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate upper and lower coordinates for a NACA 4-digit airfoil.

    Uses cosine spacing to cluster points at leading and trailing edges
    for better resolution of high-curvature regions.

    Args:
        m: Maximum camber (e.g., 0.02 for NACA 2412)
        p: Position of max camber (e.g., 0.4 for NACA 2412)
        t: Maximum thickness in percent (e.g., 12 for NACA 0012)
        num_points: Number of points along the chord
    Returns:
        (upper_coords, lower_coords) as Nx2 numpy arrays
    """
    t = t / 100.0

    # Cosine spacing for LE/TE clustering
    beta = np.linspace(0, np.pi, num_points)
    x = (1 - np.cos(beta)) / 2

    # Thickness distribution
    yt = (
        5
        * t
        * (
            0.2969 * np.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x**2
            + 0.2843 * x**3
            - 0.1015 * x**4
        )
    )

    # Camber line and slope
    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)

    if m > 0 and p > 0:
        forward = x < p
        backward = ~forward
        yc[forward] = (m / p**2) * (2 * p * x[forward] - x[forward] ** 2)
        dyc_dx[forward] = (2 * m / p**2) * (p - x[forward])
        yc[backward] = (m / (1 - p) ** 2) * (
            (1 - 2 * p) + 2 * p * x[backward] - x[backward] ** 2
        )
        dyc_dx[backward] = (2 * m / (1 - p) ** 2) * (p - x[backward])

    # Combine perpendicular to camber line
    theta = np.arctan(dyc_dx)

    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    upper_coords = np.column_stack((xu, yu))
    lower_coords = np.column_stack((xl, yl))

    return upper_coords, lower_coords


def save_dat_file(
    upper: np.ndarray, lower: np.ndarray, filename: str
) -> None:
    """
    Save airfoil coordinates in Selig format (closed loop from TE, over the top,
    around LE, and back to TE along bottom).
    """
    coords = np.vstack((upper[::-1], lower[1:]))
    np.savetxt(filename, coords, fmt="%f %f")
