class Actuator:
    """Second-order transfer function for control surface response."""
    def __init__(self, zeta: float = 0.7, omega_n: float = 10.0, dt: float = 0.01):
        self.zeta = zeta
        self.omega_n = omega_n
        self.dt = dt
        self.state = 0.0
        self.velocity = 0.0

    def step(self, command: float) -> float:
        """Advance actuator state using discretized second-order ODE."""
        # Acceleration = omega^2 * (command - state) - 2 * zeta * omega * velocity
        accel = (self.omega_n**2) * (command - self.state) - (2 * self.zeta * self.omega_n * self.velocity)
        self.velocity += accel * self.dt
        self.state += self.velocity * self.dt
        return self.state
