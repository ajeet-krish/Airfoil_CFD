from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.interpolate import interp1d


class AeroSurrogate:
    """Aerodynamic coefficient surrogate anchored by SU2 RANS data.

    Provides fast CL, CD, CM interpolation for flight dynamics simulation.
    Can be serialized to/from JSON for caching.
    """

    def __init__(
        self,
        angles: list[float],
        cl_vals: list[float],
        cd_vals: list[float],
        cm_vals: Optional[list[float]] = None,
    ):
        data = sorted(zip(angles, cl_vals, cd_vals, cm_vals or [0.0] * len(angles)),
                      key=lambda x: x[0])
        angles_s, cl_s, cd_s, cm_s = zip(*data)

        self.angles = list(angles_s)
        self._cl_raw = list(cl_s)
        self._cd_raw = list(cd_s)
        self._cm_raw = list(cm_s)
        self.aoa_min = min(self.angles)
        self.aoa_max = max(self.angles)
        self.cl_interp = interp1d(angles_s, cl_s, kind='linear', fill_value='extrapolate')
        self.cd_interp = interp1d(angles_s, cd_s, kind='linear', fill_value='extrapolate')
        if cm_vals:
            self.cm_interp = interp1d(angles_s, cm_s, kind='linear', fill_value='extrapolate')
        else:
            self.cm_interp = lambda aoa: 0.0

        # Flap effect derivatives (placeholder, can be tuned)
        self.dcl_ddelta = 0.05
        self.dcd_ddelta = 0.01
        self.dcm_ddelta = -0.02

    @classmethod
    def from_su2_tunnel(cls, tunnel_dir: str) -> AeroSurrogate:
        """Read SU2 output directories and build surrogate from history CSVs."""
        base = Path(tunnel_dir)
        angles: list[float] = []
        cl_vals: list[float] = []
        cd_vals: list[float] = []
        cm_vals: list[float] = []

        for aoa_dir in sorted(base.iterdir()):
            if not aoa_dir.is_dir() or not aoa_dir.name.startswith("aoa_"):
                continue
            try:
                aoa = float(aoa_dir.name.split("_")[1])
            except (IndexError, ValueError):
                continue
            hist_file = aoa_dir / "history.csv"
            if not hist_file.exists():
                continue
            lines = hist_file.read_text().strip().split("\n")
            if len(lines) < 2:
                continue
            vals = lines[-1].split(",")
            # SU2 history.csv columns: Inner_Iter, rms[Rho], ..., RefForce, CD, CL, CSF, CMx, ...
            # Parse column indices from header
            header = lines[0].lower()
            cols = header.split(",")
            col_map = {c.strip().strip('"'): i for i, c in enumerate(cols)}
            cd_idx = col_map.get("cd", col_map.get("drag", 8))
            cl_idx = col_map.get("cl", col_map.get("lift", 9))
            cm_idx = col_map.get("cmz", col_map.get("cmy", 11))

            cd = float(vals[cd_idx])
            cl = float(vals[cl_idx])
            cm = float(vals[cm_idx]) if cm_idx < len(vals) else 0.0
            angles.append(aoa)
            cl_vals.append(cl)
            cd_vals.append(cd)
            cm_vals.append(cm)

        if not angles:
            raise ValueError(f"No valid SU2 results found in {tunnel_dir}")

        return cls(angles, cl_vals, cd_vals, cm_vals)

    def get_coefficients(self, aoa_deg: float, delta_flap: float = 0.0) -> tuple[float, float, float]:
        """Return (CL, CD, CM) for a given angle of attack and flap deflection.
        AoA is clipped to the valid data range to prevent extrapolation artifacts.
        """
        aoa_clipped = np.clip(aoa_deg, self.aoa_min, self.aoa_max)
        cl = float(self.cl_interp(aoa_clipped)) + self.dcl_ddelta * delta_flap
        cd = float(self.cd_interp(aoa_clipped)) + self.dcd_ddelta * abs(delta_flap)
        cm = float(self.cm_interp(aoa_clipped)) + self.dcm_ddelta * delta_flap
        return cl, cd, cm

    def verify(self, su2_cl: float, su2_cd: float, su2_cm: float,
               aoa_deg: float, delta_flap: float = 0.0) -> dict:
        """Compare surrogate prediction against a SU2 snapshot result.

        Returns a dict with absolute and relative errors.
        """
        surf_cl, surf_cd, surf_cm = self.get_coefficients(aoa_deg, delta_flap)
        return {
            "aoa": aoa_deg,
            "delta": delta_flap,
            "surrogate": {"CL": surf_cl, "CD": surf_cd, "CM": surf_cm},
            "su2": {"CL": su2_cl, "CD": su2_cd, "CM": su2_cm},
            "error": {
                "CL": surf_cl - su2_cl,
                "CD": surf_cd - su2_cd,
                "CM": surf_cm - su2_cm,
                "CL_pct": (surf_cl - su2_cl) / su2_cl * 100 if su2_cl != 0 else 0,
                "CD_pct": (surf_cd - su2_cd) / su2_cd * 100 if su2_cd != 0 else 0,
            },
        }

    def save(self, path: str | Path) -> None:
        """Serialize surrogate to JSON for caching."""
        data = {
            "angles": self.angles,
            "cl": [float(self.cl_interp(a)) for a in self.angles],
            "cd": [float(self.cd_interp(a)) for a in self.angles],
            "cm": [float(self.cm_interp(a)) for a in self.angles],
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> AeroSurrogate:
        """Load surrogate from JSON cache."""
        data = json.loads(Path(path).read_text())
        return cls(data["angles"], data["cl"], data["cd"], data["cm"])

    def extend_symmetric(self) -> AeroSurrogate:
        """Extend to negative AoA for symmetric airfoil (CL(-a) = -CL(a), CD(-a)=CD(a))."""
        pos_mask = [a > 0 for a in self.angles]
        neg_angles = [-self.angles[i] for i in range(len(self.angles)) if pos_mask[i]]
        neg_angles.reverse()
        neg_cl = [-self._cl_raw[i] for i in range(len(self.angles)) if pos_mask[i]]
        neg_cl.reverse()
        neg_cd = [self._cd_raw[i] for i in range(len(self.angles)) if pos_mask[i]]
        neg_cd.reverse()
        neg_cm = [-self._cm_raw[i] for i in range(len(self.angles)) if pos_mask[i]]
        neg_cm.reverse()
        all_a = neg_angles + list(self.angles)
        all_cl = neg_cl + list(self._cl_raw)
        all_cd = neg_cd + list(self._cd_raw)
        all_cm = neg_cm + list(self._cm_raw)
        return AeroSurrogate(all_a, all_cl, all_cd, all_cm)
