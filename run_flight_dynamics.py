from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from physics.aero_surrogate import AeroSurrogate
from src.dynamics import LongitudinalDynamics
from src.gust_profile import gust_1minuscos
from src.verification_hook import VerificationHook
from src.plot_telemetry import plot_telemetry


def main():
    print("=" * 60)
    print("  Flight Dynamics Simulation with SU2 Verification")
    print("=" * 60)

    # Build surrogate from SU2 tunnel data (fall back to mock if unavailable)
    # Extend to negative AoA for symmetric NACA 0012 behavior
    try:
        base_aero = AeroSurrogate.from_su2_tunnel("output/cfd/naca0012")
        # Zero out CM (NACA 0012 symmetric -> Cm_AC = 0)
        zero_cm = [0.0] * len(base_aero.angles)
        base_zero_cm = AeroSurrogate(base_aero.angles, base_aero._cl_raw, base_aero._cd_raw, zero_cm)
        aero = base_zero_cm.extend_symmetric()
        print(f"  [OK] Surrogate from SU2 tunnel data, extended to {-max(base_aero.angles)} deg (CM zeroed)")
    except (FileNotFoundError, ValueError) as exc:
        print(f"  [WARN] No SU2 tunnel data found ({exc}), using mock data")
        # NACA 0012 symmetric -> extend to negative AoA
        # CL(-alpha) = -CL(alpha), CD(-alpha) = CD(alpha), CM(-alpha) = -CM(alpha)
        pos_angles = [0.0, 4.0, 8.0, 12.0, 16.0]
        pos_cl = [0.0014, 0.4453, 0.8718, 1.2647, 1.6082]
        pos_cd = [0.0749, 0.0969, 0.1644, 0.2764, 0.4314]
        # CM with static stability: Cm_alpha ~ -0.08/deg (CG fwd of AC by ~4% chord)
        cm_alpha = -0.08  # per degree
        pos_cm = [cm_alpha * a for a in pos_angles]

        angles = pos_angles + [-a for a in pos_angles[:0:-1]]
        cl_vals = pos_cl + [-c for c in pos_cl[:0:-1]]
        cd_vals = pos_cd + list(reversed(pos_cd[:-1]))
        cm_vals = pos_cm + [-c for c in pos_cm[:0:-1]]

        aero = AeroSurrogate(angles, cl_vals, cd_vals, cm_vals)
        print(f"  [OK] Mock surrogate built ({len(angles)} AoA points, -16 to +16 deg)")

    # Initialize dynamics
    sim = LongitudinalDynamics(
        aero=aero,
        dt=0.005,
        mass=50.0,
        wing_area=2.5,
        chord=1.0,
        iyy=16.7,
    )

    # Trim at cruise: compute AoA for level flight (L = W)
    V = 50.0
    m = 50.0
    S = 2.5
    rho = 1.225
    g = 9.81
    CL_needed = 2.0 * m * g / (rho * V**2 * S)
    # Scan surrogate to find AoA that gives CL_needed
    for test_aoa in np.linspace(0.1, 10.0, 200):
        cl, cd, _ = aero.get_coefficients(test_aoa, 0.0)
        if cl >= CL_needed:
            trim_aoa = test_aoa
            break
    else:
        trim_aoa = 4.0

    # Compute thrust to balance drag at trim
    qbar = 0.5 * rho * V**2
    _, cd_trim, _ = aero.get_coefficients(trim_aoa, 0.0)
    drag_trim = qbar * S * cd_trim
    sim.thrust = drag_trim

    aoa_rad = np.radians(trim_aoa)
    u = V * np.cos(aoa_rad)
    w = V * np.sin(aoa_rad)
    sim.set_state(u=u, w=w, q=0.0, theta=aoa_rad, x=0.0, z=100.0)
    print(f"  Trim: V={V} m/s, AoA={trim_aoa:.2f} deg, CL_needed={CL_needed:.4f}, thrust={drag_trim:.1f} N")

    # Setup verification hook
    hook = VerificationHook()
    hook.set_trim_aoa(trim_aoa)

    # Run simulation
    t_end = 10.0
    dt = sim.dt
    n_steps = int(t_end / dt)
    command = 0.0  # No active flap command during gust test

    print(f"  Simulating {t_end}s at {int(1/dt)} Hz...")
    for i in range(n_steps):
        t = i * dt
        wind = gust_1minuscos(t, amplitude=5.0, t0=1.0, duration=0.5)

        # Step dynamics
        state = sim.step(command=command, wind_gust=wind)
        state["t"] = t  # Tag time

        # Verification hook monitors for events
        event = hook.monitor(t, state)
        if event:
            msg = f"  [VERIFICATION] {event['event']} at t={t:.2f}s: "
            msg += f"AoA={event['aoa']:.2f}deg, V={event['V']:.2f}m/s"
            print(msg)

    # Summary
    print(f"\n  Simulation complete: {n_steps} steps, {sim.log()[-1]['t']:.2f}s final time")
    print(f"  Max AoA: {max(e['aoa'] for e in sim.log()):.2f} deg")
    print(f"  Max load factor: {max(abs(e['lift'] / (50*9.81)) for e in sim.log()):.2f} g")

    if hook.events:
        print(f"\n  Verification Events:")
        for ev in hook.events:
            print(f"    - {ev['event']} @ t={ev['time']:.2f}s: "
                  f"AoA={ev['aoa']:.2f}deg V={ev['V']:.1f}m/s")

    # Export JSON data for web interactive playback
    json_path = Path("docs/assets/data/flight_dynamics.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # Convert numpy values to native Python types for JSON serialization
    def _convert(v):
        if isinstance(v, (np.floating, np.integer)):
            return v.item()
        return v
    log_clean = [{k: _convert(v) for k, v in entry.items()} for entry in sim.log()]
    with open(json_path, "w") as f:
        json.dump(log_clean, f, indent=2)
    print(f"  JSON data: {json_path} ({len(log_clean)} frames)")

    # Generate telemetry plot
    out = plot_telemetry(sim.log())
    print(f"\n  Telemetry dashboard: {out}")

    print(f"\n  Done. Run 'open docs/assets/images/dynamics/telemetry.png' to view.")
    print("=" * 60)


if __name__ == "__main__":
    main()
