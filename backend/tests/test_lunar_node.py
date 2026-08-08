"""The lunar node, verified against physics rather than against a library.

When the Moon's ecliptic latitude crosses zero going north, the Moon *is* in
the ascending node — so the node's longitude must equal the Moon's at that
instant. That identity holds for any correct implementation, which makes it a
better oracle than another program's output: it cannot drift, and we are
allowed to use it.

This test exists because the first implementation passed every eyeball check
while being ~70" wrong. Skyfield returns ICRS vectors; rotating them with the
obliquity of date mixes two frames and displaces the node by roughly the
accumulated precession. The error was smooth and plausible — exactly the kind
that ships.
"""

from __future__ import annotations

import pytest

from alma.engine import ephemeris as E


def _moon_latitude(jd: float) -> float:
    return E.position("moon", jd).latitude


def _refine_crossing(low: float, high: float) -> float:
    """Bisect to the instant the Moon's latitude passes through zero."""
    for _ in range(80):
        mid = (low + high) / 2.0
        if _moon_latitude(low) * _moon_latitude(mid) <= 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2.0


def _ascending_crossings(start_jd: float, count: int) -> list[float]:
    found: list[float] = []
    jd = start_jd
    previous = _moon_latitude(jd)
    while len(found) < count and jd < start_jd + 40 * count:
        jd += 0.25
        current = _moon_latitude(jd)
        if previous < 0 <= current:
            found.append(_refine_crossing(jd - 0.25, jd))
        previous = current
    return found


# Spread across the DE440s span so a frame error cannot hide in one epoch:
# the ICRS-versus-of-date discrepancy grows with distance from J2000.
@pytest.mark.parametrize("start_jd", [2415021.0, 2450800.0, 2469808.0], ids=["1900", "1997", "2050"])
def test_true_node_equals_moon_longitude_at_the_crossing(start_jd):
    for jd in _ascending_crossings(start_jd, 2):
        moon = E.position("moon", jd).longitude
        node = E.lunar_node(jd, true_node=True).longitude
        separation = abs(moon - node) % 360.0
        separation = min(separation, 360.0 - separation)
        assert separation * 3600.0 < 1.0, (
            f"at JD {jd:.4f} the Moon is at the node by construction, but the node "
            f"sits {separation * 3600.0:.1f}\" away — check the reference frame"
        )


def test_mean_node_oscillation_is_the_expected_physical_size():
    """The true node swings around the mean one; the mean node is not wrong.

    Guards against 'fixing' the mean node to track the true one, which would
    destroy the quantity astrologers actually asked for.
    """
    deviations = []
    for jd in _ascending_crossings(2450800.0, 4):
        mean = E.lunar_node(jd, true_node=False).longitude
        true = E.lunar_node(jd, true_node=True).longitude
        gap = abs(mean - true) % 360.0
        deviations.append(min(gap, 360.0 - gap))

    assert max(deviations) < 2.0, "the true/mean gap should never exceed ~1.6°"
    assert max(deviations) > 0.2, "a mean node that tracks the true node is not a mean node"


def test_the_node_moves_backwards():
    """Both nodes are retrograde — roughly one full circuit every 18.6 years."""
    jd = 2450800.0
    for true_node in (True, False):
        node = E.lunar_node(jd, true_node=true_node)
        assert node.speed_longitude < 0.0
        # 360° / 18.6 years ≈ 0.053°/day. The true node wobbles around that.
        assert abs(node.speed_longitude) < 0.5
