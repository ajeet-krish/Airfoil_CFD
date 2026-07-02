from __future__ import annotations

import numpy as np

from physics.aero_surrogate import AeroSurrogate
from src.actuator import Actuator


class LongitudinalDynamics:
    """6-DoF longitudinal rigid-body dynamics model.

    State vector: [u, w, q, theta, x, z]
      u     forward velocity (body x, m/s)
      w     vertical velocity (body z, m/s, positive down)
      q     pitch rate (rad/s)
      theta pitch angle (rad)
      x     horizontal position (m)
      z     altitude (m, positive up)
    """

    def __init__(
        self,
        aero: AeroSurrogate,
        dt: float = 0.01,
        mass: float = 50.0,
        wing_area: float = 2.5,
        chord: float = 1.0,
        iyy: float = 2.0,
        rho: float = 1.225,
        g: float = 9.81,
        cm_q: float = -5.0,
        static_margin: float = -0.05,
        thrust: float = 0.0,
    ):
        self.aero = aero
        self.dt = dt
        self.mass = mass
        self.wing_area = wing_area
        self.chord = chord
        self.iyy = iyy
        self.rho = rho
        self.g = g
        self.cm_q = cm_q
        self.static_margin = static_margin
        self.thrust = thrust  # Constant propulsive thrust (N), positive forward  # (x_cg - x_ac)/c, negative for stable (default -0.05)

        self.actuator = Actuator(dt=dt)

        # State
        self.u = 50.0
        self.w = 0.0
        self.q = 0.0
        self.theta = 0.0
        self.x = 0.0
        self.z = 100.0

        self._log: list[dict] = []

    def set_state(self, u: float, w: float, q: float, theta: float, x: float, z: float) -> None:
        self.u = u
        self.w = w
        self.q = q
        self.theta = theta
        self.x = x
        self.z = z

    @property
    def aoa(self) -> float:
        return np.arctan2(self.w, self.u)

    @property
    def velocity(self) -> float:
        return np.sqrt(self.u**2 + self.w**2)

    @property
    def flight_path_angle(self) -> float:
        return self.theta - self.aoa

    @property
    def state(self) -> dict:
        return {
            "u": self.u,
            "w": self.w,
            "q": self.q,
            "theta": self.theta,
            "x": self.x,
            "z": self.z,
            "aoa": self.aoa,
            "V": self.velocity,
            "gamma": self.flight_path_angle,
        }

    def step(self, command: float = 0.0, wind_gust: float = 0.0) -> dict:
        delta = self.actuator.step(command)

        # Total velocity and AoA including gust
        # Wind gust is positive UPWARD; body Z is positive DOWN
        # Relative vertical velocity = w_aircraft + w_gust
        effective_w = self.w + wind_gust
        V = np.sqrt(self.u**2 + effective_w**2)
        aoa_val = np.arctan2(effective_w, self.u)

        # Get aerodynamic coefficients
        cl, cd, cm = self.aero.get_coefficients(
            np.degrees(aoa_val), delta
        )

        # Dynamic pressure
        qbar = 0.5 * self.rho * V**2

        # Forces in wind axes
        lift = qbar * self.wing_area * cl
        drag = qbar * self.wing_area * cd

        # Rotate from wind to body axes
        cos_a = np.cos(aoa_val)
        sin_a = np.sin(aoa_val)
        Fx = lift * sin_a - drag * cos_a + self.thrust
        Fz = -lift * cos_a - drag * sin_a

        # Pitching moment (acodynamic + static margin + pitch damping)
        # Static margin provides Cm = CL * static_margin (negative = stable)
        cm_static = cl * self.static_margin
        cm_damping = self.cm_q * self.q * self.chord / (2.0 * V + 1e-6)
        M = qbar * self.wing_area * self.chord * (cm + cm_static + cm_damping)

        # Newton-Euler integration
        du = -self.q * self.w - self.g * np.sin(self.theta) + Fx / self.mass
        dw = self.q * self.u + self.g * np.cos(self.theta) + Fz / self.mass
        dq = M / self.iyy
        dtheta = self.q
        dx = self.u * np.cos(self.theta) + self.w * np.sin(self.theta)
        dz = self.u * np.sin(self.theta) - self.w * np.cos(self.theta)

        self.u += du * self.dt
        self.w += dw * self.dt
        self.q += dq * self.dt
        self.theta += dtheta * self.dt
        self.x += dx * self.dt
        self.z += dz * self.dt

        result = {
            "t": 0.0,
            "u": self.u,
            "w": self.w,
            "q": self.q,
            "theta": self.theta,
            "x": self.x,
            "z": self.z,
            "aoa": np.degrees(aoa_val),
            "V": V,
            "gamma": np.degrees(self.flight_path_angle),
            "cl": cl,
            "cd": cd,
            "cm": cm,
            "delta": delta,
            "command": command,
            "wind_gust": wind_gust,
            "lift": lift,
            "drag": drag,
            "M": M,
        }
        self._log.append(result)
        return result

    def log(self) -> list[dict]:
        return self._log
