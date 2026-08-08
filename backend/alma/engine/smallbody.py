"""Chiron, from sampled JPL states.

Chiron is a centaur and is not in DE440s, and the SPK that JPL Horizons emits
for small bodies is data type 21, which neither Skyfield nor jplephem can
read. Rather than guess at that binary format, we sample Horizons' own
barycentric state vectors on a fixed grid and interpolate between them.

The interpolation is exact enough to ignore. Chiron's orbital period is 50.4
years, so over a four-day step the cubic Hermite truncation error is of order
(ωh)⁴/384 ≈ 9e-15 of the radius — sub-millimetre on an 8–19 AU orbit. The
error that matters is JPL's own, and we inherit it unchanged.

Everything downstream — light-time, aberration, precession, nutation — is the
same code path the DE440s bodies take, so Chiron is not a special case in the
chart, only in where its numbers come from.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from skyfield.vectorlib import VectorFunction

#: NAIF-style id for asteroid 2060 Chiron. Nothing reads it but Skyfield's
#: position bookkeeping; it just has to be distinct from the DE440s targets.
CHIRON_ID = 2002060


class SampledSmallBody(VectorFunction):
    """A barycentric body defined by a table of states, Hermite-interpolated."""

    def __init__(self, name: str, target: int, jd_tdb, state) -> None:
        self.center = 0            # solar-system barycentre
        self.target = target
        self.center_name = "SSB"
        self.target_name = name
        self.ephemeris = None
        self._jd = np.asarray(jd_tdb, dtype=np.float64)
        self._pos = np.asarray(state, dtype=np.float64)[:, :3]
        self._vel = np.asarray(state, dtype=np.float64)[:, 3:]
        self.jd_start = float(self._jd[0])
        self.jd_end = float(self._jd[-1])

    def covers(self, jd_tdb: float) -> bool:
        return self.jd_start <= jd_tdb <= self.jd_end

    def _at(self, t):
        p, v = self._interpolate(np.atleast_1d(np.asarray(t.tdb, dtype=np.float64)))
        if getattr(t.tdb, "shape", ()) == ():
            return p[:, 0], v[:, 0], None, None
        return p, v, None, None

    def _interpolate(self, jd):
        if np.any(jd < self.jd_start) or np.any(jd > self.jd_end):
            raise ValueError(
                f"{self.target_name} is only tabulated between JD {self.jd_start} "
                f"and JD {self.jd_end}"
            )
        # searchsorted gives the sample at or before each time; clamp so the
        # final sample still has a segment to its right.
        i = np.clip(np.searchsorted(self._jd, jd, side="right") - 1, 0, len(self._jd) - 2)
        t0 = self._jd[i]
        h = self._jd[i + 1] - t0
        s = (jd - t0) / h

        p0, p1 = self._pos[i], self._pos[i + 1]
        v0, v1 = self._vel[i], self._vel[i + 1]

        s2, s3 = s * s, s * s * s
        h00 = (2 * s3 - 3 * s2 + 1)[:, None]
        h10 = (s3 - 2 * s2 + s)[:, None]
        h01 = (-2 * s3 + 3 * s2)[:, None]
        h11 = (s3 - s2)[:, None]
        hcol = h[:, None]
        position = h00 * p0 + h10 * hcol * v0 + h01 * p1 + h11 * hcol * v1

        d00 = (6 * s2 - 6 * s)[:, None]
        d10 = (3 * s2 - 4 * s + 1)[:, None]
        d01 = (-6 * s2 + 6 * s)[:, None]
        d11 = (3 * s2 - 2 * s)[:, None]
        velocity = (d00 * p0 + d01 * p1) / hcol + d10 * v0 + d11 * v1

        return position.T, velocity.T


def _table_path() -> Path:
    explicit = os.environ.get("ALMA_CHIRON_TABLE")
    if explicit:
        return Path(explicit)
    return Path(__file__).resolve().parents[2] / "data" / "chiron_2060.npz"


@lru_cache(maxsize=1)
def chiron_body() -> SampledSmallBody | None:
    """Chiron, or None when the table is not installed.

    None rather than an exception: a missing centaur must degrade to "Chiron
    unavailable" in the chart, never to a failed reading.
    """
    path = _table_path()
    if not path.exists():
        return None
    try:
        with np.load(path) as data:
            return SampledSmallBody("chiron", CHIRON_ID, data["jd_tdb"], data["state"])
    except Exception:  # a truncated or corrupt table must not break a reading
        return None
