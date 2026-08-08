"""Astrocartography, verified against Skyfield's own topocentric machinery.

The lines here are built by hand from apparent right ascension, declination
and Greenwich sidereal time. Skyfield can answer the same question by a
completely different route — put an observer at a latitude and longitude and
ask for the body's hour angle and altitude — and that route shares no code
with the formulae under test. So the check is real rather than circular: on
an MC line the hour angle must be zero, and on an ASC or DESC line the
altitude must be zero.

A note on what is *not* asserted. A body on its MC line does not put its
ecliptic longitude on the chart's Midheaven; the Midheaven is where the
meridian cuts the ecliptic, the MC line is where it cuts the body, and the
two coincide only for a body with no ecliptic latitude. Testing that
equivalence would have been testing a false premise.

The other thing worth testing is the refusal. A circumpolar body has no
rising line at all, and the standard way these maps go wrong is to clamp the
arccosine and draw a line along the polar circle that means nothing.
"""

from __future__ import annotations

import pytest
from skyfield.api import wgs84

from alma.engine import astrocartography as ac
from alma.engine import ephemeris, natal
from alma.engine.timeutil import resolve

MILAN = dict(latitude=45.4642, longitude=9.19)


def _observed(chart, body: str, latitude: float, longitude: float):
    """Skyfield's own answer for a body seen from one place at one instant."""
    eph, _ts, _ = ephemeris._loaded()
    t = ephemeris._skyfield_time(chart.julian_day)
    place = eph["earth"] + wgs84.latlon(latitude, longitude)
    return place.at(t).observe(ephemeris._resolve(body)).apparent()


def _moment(**overrides):
    params = dict(year=1998, month=3, day=14, hour=4, minute=20, tz_name="Europe/Rome")
    params.update(overrides)
    return resolve(**params)


@pytest.fixture(scope="module")
def chart():
    return natal.compute(moment=_moment(), **MILAN)


@pytest.fixture(scope="module")
def amap(chart):
    return ac.compute(chart)


# ── the cross-check that matters ───────────────────────────────────────────

@pytest.mark.parametrize(
    "body", ["sun", "moon", "venus", "mars", "jupiter", "saturn", "pluto"]
)
def test_standing_on_an_mc_line_the_body_is_on_the_meridian(chart, amap, body):
    """Hour angle zero — the body is culminating directly overhead-ish.

    Parallax cannot spoil this one even for the Moon: on the meridian the
    observer's zenith is on the meridian too, so the whole displacement is in
    declination and none of it in hour angle.
    """
    line = next(l for l in amap.lines if l.body == body and l.angle == "MC")
    for latitude in (-40.0, 0.0, 20.0, 50.0):
        hour_angle, _dec, _dist = _observed(chart, body, latitude, line.meridian).hadec()
        offset = abs(ac._normalise_longitude(hour_angle._degrees))
        assert offset < 0.05, f"{body} is {offset:.4f}° off the meridian at {latitude}°"


@pytest.mark.parametrize("body", ["sun", "venus", "jupiter", "saturn"])
def test_standing_on_an_ic_line_the_body_is_on_the_lower_meridian(chart, amap, body):
    line = next(l for l in amap.lines if l.body == body and l.angle == "IC")
    hour_angle, _dec, _dist = _observed(chart, body, -10.0, line.meridian).hadec()
    offset = abs(abs(ac._normalise_longitude(hour_angle._degrees)) - 180.0)
    assert offset < 0.05


@pytest.mark.parametrize("body", ["sun", "mars", "saturn", "jupiter", "pluto"])
def test_standing_on_an_asc_line_the_body_is_on_the_horizon(chart, amap, body):
    """Altitude zero, and rising rather than setting — the eastern half."""
    line = next(l for l in amap.lines if l.body == body and l.angle == "ASC")
    for latitude, longitude in line.points[::7]:
        altitude, azimuth, _dist = _observed(chart, body, latitude, longitude).altaz()
        assert abs(altitude.degrees) < 0.1, (
            f"{body} is {altitude.degrees:.3f}° off the horizon at latitude {latitude}"
        )
        assert 0.0 <= azimuth.degrees <= 180.0, f"{body} is setting, not rising"


@pytest.mark.parametrize("body", ["sun", "venus", "saturn"])
def test_standing_on_a_desc_line_the_body_is_setting(chart, amap, body):
    line = next(l for l in amap.lines if l.body == body and l.angle == "DESC")
    for latitude, longitude in line.points[::7]:
        altitude, azimuth, _dist = _observed(chart, body, latitude, longitude).altaz()
        assert abs(altitude.degrees) < 0.1
        assert 180.0 <= azimuth.degrees <= 360.0, f"{body} is rising, not setting"


def test_the_moons_horizon_lines_are_geocentric_by_convention(chart, amap):
    """The Moon is the one body where the convention shows.

    Astrocartography draws geocentric lines, but an observer standing on the
    Moon's rising line sees it about a degree from the horizon because of
    lunar parallax. That gap is the convention, not an error, and it is worth
    pinning down so nobody 'fixes' it later.
    """
    line = next(l for l in amap.lines if l.body == "moon" and l.angle == "ASC")
    worst = max(
        abs(_observed(chart, "moon", lat, lon).altaz()[0].degrees)
        for lat, lon in line.points[::7]
    )
    assert 0.1 < worst < 1.2, f"lunar parallax on the rising line is {worst:.3f}°"


# ── the circumpolar refusal ────────────────────────────────────────────────

def test_a_circumpolar_body_has_no_rising_line_at_that_latitude():
    """cos H = −tan φ tan δ has no solution, and we must not invent one."""
    assert ac._hour_angle_at_horizon(declination=23.0, latitude=80.0) is None
    assert ac._hour_angle_at_horizon(declination=-23.0, latitude=80.0) is None
    assert ac._hour_angle_at_horizon(declination=23.0, latitude=45.0) is not None


def test_the_horizon_hour_angle_is_ninety_degrees_on_the_equator():
    """On the equator every body rises six hours before it culminates."""
    for declination in (-20.0, 0.0, 20.0):
        assert ac._hour_angle_at_horizon(declination, 0.0) == pytest.approx(90.0)


def test_rising_lines_stop_rather_than_bend_at_the_pole(amap):
    """A body with high declination must simply have fewer points."""
    for line in amap.lines:
        if line.angle in ("ASC", "DESC"):
            latitudes = [lat for lat, _ in line.points]
            assert latitudes == sorted(latitudes)
            assert all(abs(lat) <= ac.LATITUDE_LIMIT for lat in latitudes)


# ── structure ──────────────────────────────────────────────────────────────

def test_every_body_gets_four_lines(amap):
    by_body: dict[str, set[str]] = {}
    for line in amap.lines:
        by_body.setdefault(line.body, set()).add(line.angle)
    assert by_body
    for body, angles in by_body.items():
        assert angles == set(ac.ANGLES), f"{body} is missing {set(ac.ANGLES) - angles}"


def test_mc_and_ic_lines_are_exactly_opposite(amap):
    for body in {l.body for l in amap.lines}:
        mc = next(l for l in amap.lines if l.body == body and l.angle == "MC")
        ic = next(l for l in amap.lines if l.body == body and l.angle == "IC")
        gap = abs(ac._normalise_longitude(mc.meridian - ic.meridian))
        assert gap == pytest.approx(180.0, abs=1e-9)


def test_asc_and_desc_are_symmetric_about_the_meridian(amap):
    """Rising and setting sit equal distances either side of culmination."""
    for body in {l.body for l in amap.lines}:
        mc = next(l for l in amap.lines if l.body == body and l.angle == "MC")
        asc = next(l for l in amap.lines if l.body == body and l.angle == "ASC")
        desc = next(l for l in amap.lines if l.body == body and l.angle == "DESC")
        for (lat_a, lon_a), (lat_b, lon_b) in zip(asc.points, desc.points):
            assert lat_a == lat_b
            before = ac._normalise_longitude(mc.meridian - lon_a)
            after = ac._normalise_longitude(lon_b - mc.meridian)
            assert before == pytest.approx(after, abs=1e-9)


def test_all_longitudes_are_in_range(amap):
    for line in amap.lines:
        for _lat, lon in line.points:
            assert -180.0 <= lon <= 180.0


# ── reading a place ────────────────────────────────────────────────────────

def test_a_place_on_a_line_reports_that_line(chart, amap):
    line = next(l for l in amap.lines if l.body == "venus" and l.angle == "MC")
    reading = amap.read_place(30.0, line.meridian)
    assert any(body == "venus" and angle == "MC" for body, angle, _ in reading.influences)


def test_a_place_far_from_every_line_reports_nothing(amap):
    """Silence is a real answer — most of the globe is not under a line."""
    empty = [
        longitude
        for longitude in range(-180, 180, 3)
        if not amap.read_place(0.0, float(longitude)).influences
    ]
    assert empty, "every longitude on the equator is claimed by some line"


def test_influences_are_ordered_by_distance(amap):
    reading = amap.read_place(45.4642, 9.19)
    distances = [d for _b, _a, d in reading.influences]
    assert distances == sorted(distances)


# ── parans ─────────────────────────────────────────────────────────────────

def test_parans_are_a_coincidence_in_time_not_a_crossing_on_the_map(chart, amap):
    """At a paran latitude both bodies are angular within the same window."""
    assert amap.parans
    for paran in amap.parans[:15]:
        first = next(
            l for l in amap.lines if l.body == paran.first and l.angle == paran.first_angle
        )
        second = next(
            l for l in amap.lines if l.body == paran.second and l.angle == paran.second_angle
        )
        a = ac._longitude_at(first, paran.latitude)
        b = ac._longitude_at(second, paran.latitude)
        assert a is not None and b is not None
        assert abs(ac._normalise_longitude(a - b)) <= 7.5 + 1e-9


def test_a_paran_never_pairs_a_body_with_itself(amap):
    for paran in amap.parans:
        assert paran.first != paran.second


# ── the unknown-time refusal ───────────────────────────────────────────────

def test_the_map_is_refused_without_a_birth_time():
    """Sidereal time moves a degree every four minutes — a noon guess is a
    different continent."""
    timeless = natal.compute(moment=_moment(hour=None, minute=None), **MILAN)
    with pytest.raises(ValueError, match="birth time"):
        ac.compute(timeless)


# ── sensitivity ────────────────────────────────────────────────────────────

def test_four_minutes_of_birth_time_moves_every_line_one_degree():
    """The map is exactly as sensitive as sidereal time says it should be."""
    early = natal.compute(moment=_moment(hour=4, minute=20), **MILAN)
    later = natal.compute(moment=_moment(hour=4, minute=24), **MILAN)
    a = ac.lines_for("sun", early.julian_day)[0]
    b = ac.lines_for("sun", later.julian_day)[0]
    shift = abs(ac._normalise_longitude(a.meridian - b.meridian))
    assert 0.9 < shift < 1.1, f"four minutes moved the MC line {shift:.3f}°"
