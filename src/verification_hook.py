from __future__ import annotations

from pathlib import Path
from typing import Optional


class VerificationHook:
    """Event-driven SU2 CFD snapshot runner for flight dynamics verification.

    Monitors the simulation state stream and triggers verification events
    at key flight conditions (peak gust load, cruise recovery).
    """

    def __init__(self, workdir: str = "output/verification"):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._log: list[dict] = []
        self._peak_gust_triggered = False
        self._cruise_recovery_triggered = False
        self._prev_wind = 0.0
        self._near_trim_count = 0
        self._trim_aoa: Optional[float] = None

    def set_trim_aoa(self, aoa_deg: float) -> None:
        self._trim_aoa = aoa_deg

    def monitor(self, t: float, state: dict) -> Optional[dict]:
        """Monitor the simulation state at each time step.

        Args:
            t: Current simulation time (s)
            state: Dictionary with keys: aoa, V, delta, cl, cd, wind_gust, ...

        Returns:
            Event dict if a verification trigger fires, else None.
        """
        result = None

        # --- Peak gust detection ---
        if not self._peak_gust_triggered and state.get("wind_gust", 0.0) > 1.0:
            if state["wind_gust"] < self._prev_wind:
                self._peak_gust_triggered = True
                result = {
                    "event": "peak_gust",
                    "time": t,
                    "state": state,
                    "aoa": state.get("aoa", 0.0),
                    "V": state.get("V", 0.0),
                    "delta": state.get("delta", 0.0),
                }
                self._log.append(result)

        # --- Cruise recovery detection ---
        # Fire only after the gust has ended and AoA is near trim
        if self._peak_gust_triggered and not self._cruise_recovery_triggered:
            wind = state.get("wind_gust", 0.0)
            aoa = state.get("aoa", 0.0)
            gust_ended = wind < 0.01
            near_trim = (
                self._trim_aoa is not None and abs(aoa - self._trim_aoa) < 0.5
            )

            if gust_ended and near_trim:
                self._near_trim_count += 1
                # Require 20 consecutive steps (~0.1s) near trim
                if self._near_trim_count >= 20:
                    self._cruise_recovery_triggered = True
                    result = {
                        "event": "cruise_recovery",
                        "time": t,
                        "state": state,
                        "aoa": aoa,
                        "V": state.get("V", 0.0),
                        "delta": state.get("delta", 0.0),
                    }
                    self._log.append(result)
            else:
                self._near_trim_count = 0

        self._prev_wind = state.get("wind_gust", 0.0)

        return result

    def reset(self) -> None:
        self._peak_gust_triggered = False
        self._cruise_recovery_triggered = False
        self._prev_wind = 0.0
        self._near_trim_count = 0

    @property
    def events(self) -> list[dict]:
        return self._log

    @property
    def has_fired(self) -> bool:
        return len(self._log) > 0
