import numpy as np


def gust_1minuscos(t: float, amplitude: float = 10.0, t0: float = 1.0, duration: float = 0.5) -> float:
    """Smooth '1-cos' wind gust profile.

    V_gust(t) = (A/2) * (1 - cos(2*pi*(t-t0)/T))  for t0 <= t <= t0+T

    Args:
        t: Current time (s)
        amplitude: Peak gust magnitude (m/s), default 10.0
        t0: Gust start time (s), default 1.0
        duration: Gust duration (s), default 0.5

    Returns:
        Vertical wind velocity (m/s, positive up)
    """
    if t < t0 or t > t0 + duration:
        return 0.0
    return (amplitude / 2.0) * (1.0 - np.cos(2.0 * np.pi * (t - t0) / duration))
