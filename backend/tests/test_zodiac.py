"""The interpretive layer, checked against its own rules.

Aspects, dignities and configurations are definitions rather than
measurements, so each test states the definition and asserts the code agrees
with it — including the cases that are easy to get subtly wrong: orb
weighting, the closest-aspect rule, dispositor loops, and phases at the
wrap-around.
"""

from __future__ import annotations

import pytest

from alma.engine import zodiac as Z


# ── signs and formatting ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "longitude,sign",
    [(0.0, "Aries"), (29.99, "Aries"), (30.0, "Taurus"), (185.0, "Libra"),
     (359.99, "Pisces"), (360.0, "Aries"), (-1.0, "Pisces")],
)
def test_sign_boundaries_including_the_wrap(longitude, sign):
    assert Z.sign_of(longitude) == sign


def test_position_formatting_rounds_without_producing_sixty_minutes():
    """59.999′ must roll into the next degree, not print as 60′."""
    text = Z.format_position(22.999999)
    assert "60′" not in text
    assert text.startswith("23°00′")


def test_element_and_modality_follow_the_zodiac_order():
    assert Z.element_of(0.0) == "fire" and Z.modality_of(0.0) == "cardinal"    # Aries
    assert Z.element_of(35.0) == "earth" and Z.modality_of(35.0) == "fixed"    # Taurus
    assert Z.element_of(65.0) == "air" and Z.modality_of(65.0) == "mutable"    # Gemini
    assert Z.element_of(95.0) == "water" and Z.modality_of(95.0) == "cardinal" # Cancer


def test_separation_is_never_more_than_half_a_circle():
    assert Z.separation(10.0, 350.0) == pytest.approx(20.0)
    assert Z.separation(0.0, 180.0) == pytest.approx(180.0)
    assert Z.separation(0.0, 181.0) == pytest.approx(179.0)


# ── aspects ────────────────────────────────────────────────────────────────

def test_exact_aspects_are_found_with_zero_orb():
    positions = {"sun": 0.0, "moon": 120.0, "mars": 180.0, "venus": 90.0, "jupiter": 60.0}
    by_pair = {frozenset((a.first, a.second)): a for a in Z.find_aspects(positions)}
    assert by_pair[frozenset(("sun", "moon"))].type == "trine"
    assert by_pair[frozenset(("sun", "mars"))].type == "opposition"
    assert by_pair[frozenset(("sun", "venus"))].type == "square"
    assert by_pair[frozenset(("sun", "jupiter"))].type == "sextile"
    assert all(a.orb == pytest.approx(0.0) for a in by_pair.values())


def test_an_aspect_outside_its_orb_is_not_reported():
    """A 100° gap is neither a square nor a trine."""
    aspects = Z.find_aspects({"a": 0.0, "b": 100.0})
    assert aspects == []


def test_only_the_closest_aspect_is_kept_for_a_pair():
    """44° is inside the semisquare orb; it must not also count as a sextile."""
    aspects = Z.find_aspects({"a": 0.0, "b": 44.0})
    assert len(aspects) == 1
    assert aspects[0].type == "semisquare"


def test_luminaries_get_a_wider_orb_than_outer_points():
    """A 9° conjunction holds for the Sun but not for two outer planets."""
    assert Z.find_aspects({"sun": 0.0, "mars": 9.0}), "the Sun's wider orb should catch this"
    assert not Z.find_aspects({"uranus": 0.0, "neptune": 9.0})


def test_points_like_chiron_get_a_tightened_orb():
    """A 6° conjunction to Chiron is out of orb even though 6 < 8."""
    assert not Z.find_aspects({"chiron": 0.0, "mars": 6.0})
    assert Z.find_aspects({"chiron": 0.0, "mars": 4.0})


def test_applying_requires_speeds_and_is_direction_aware():
    """The faster body closing on exactness is applying; separating is not."""
    positions = {"moon": 118.0, "sun": 0.0}
    applying = Z.find_aspects(positions, {"moon": 13.0, "sun": 1.0})
    assert applying[0].type == "trine" and applying[0].applying is True

    separating = Z.find_aspects({"moon": 122.0, "sun": 0.0}, {"moon": 13.0, "sun": 1.0})
    assert separating[0].applying is False


def test_applying_is_false_when_no_speeds_are_supplied():
    """We do not guess timing — no speeds means no claim."""
    aspects = Z.find_aspects({"moon": 118.0, "sun": 0.0})
    assert aspects[0].applying is False


def test_minor_aspects_can_be_excluded():
    positions = {"a": 0.0, "b": 150.0}
    assert Z.find_aspects(positions, include_minor=True)
    assert not Z.find_aspects(positions, include_minor=False)


def test_aspects_come_back_tightest_first():
    positions = {"a": 0.0, "b": 121.5, "c": 90.2, "d": 60.0}
    orbs = [a.orb for a in Z.find_aspects(positions)]
    assert orbs == sorted(orbs)


# ── dignities ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "planet,longitude,status",
    [
        ("mars", 5.0, "rulership"),      # Mars in Aries
        ("sun", 125.0, "rulership"),     # Sun in Leo
        ("sun", 5.0, "exaltation"),      # Sun exalted in Aries
        ("saturn", 185.0, "exaltation"), # Saturn exalted in Libra
        ("mars", 185.0, "detriment"),    # Mars opposite its own sign
        ("sun", 185.0, "fall"),          # Sun falls in Libra
        ("jupiter", 65.0, "detriment"),  # Jupiter in Gemini
        ("venus", 125.0, "peregrine"),   # Venus in Leo — no dignity
    ],
)
def test_essential_dignity(planet, longitude, status):
    assert Z.dignity_of(planet, longitude).status == status


def test_a_planet_in_its_own_sign_has_no_dispositor():
    assert Z.dignity_of("mars", 5.0).dispositor is None


def test_dispositor_points_at_the_sign_ruler():
    """Venus in Leo is disposed by the Sun."""
    assert Z.dignity_of("venus", 125.0).dispositor == "sun"


def test_modern_rulers_are_preferred_where_they_exist():
    """Scorpio disposes to Pluto, not Mars, in the modern scheme."""
    assert Z.dignity_of("venus", 215.0).dispositor == "pluto"


def test_final_dispositor_is_none_when_the_chain_loops():
    """Mutual reception has no final dispositor — saying 'none' is correct."""
    dignities = {
        "venus": Z.dignity_of("venus", 5.0),    # Venus in Aries → Mars
        "mars": Z.dignity_of("mars", 35.0),     # Mars in Taurus → Venus
    }
    assert Z.final_dispositor(dignities) is None


# ── balance and dominants ──────────────────────────────────────────────────

def test_balance_reports_missing_elements():
    longitudes = {"a": 5.0, "b": 125.0, "c": 245.0}  # all fire
    result = Z.balance(longitudes)
    assert result["dominant_element"] == "fire"
    assert set(result["missing_elements"]) == {"earth", "air", "water"}
    assert result["element_percent"]["fire"] == pytest.approx(100.0)


def test_dominants_reward_angular_placement():
    """The same body scores higher on an angle than buried in the twelfth."""
    longitudes = {"sun": 10.0, "mars": 40.0}
    angular = Z.dominants(longitudes, {"sun": 1, "mars": 12}, [])
    cadent = Z.dominants(longitudes, {"sun": 12, "mars": 12}, [])
    sun_angular = next(p["score"] for p in angular["planets"] if p["body"] == "sun")
    sun_cadent = next(p["score"] for p in cadent["planets"] if p["body"] == "sun")
    assert sun_angular > sun_cadent


# ── configurations ─────────────────────────────────────────────────────────

def test_grand_trine_is_detected():
    positions = {"sun": 0.0, "moon": 120.0, "mars": 240.0}
    names = {c.name for c in Z.find_configurations(positions, Z.find_aspects(positions))}
    assert "grand trine" in names


def test_t_square_is_detected_with_its_apex():
    positions = {"sun": 0.0, "mars": 180.0, "saturn": 90.0}
    configs = Z.find_configurations(positions, Z.find_aspects(positions))
    tsq = next(c for c in configs if c.name == "t-square")
    assert "saturn" in tsq.detail


def test_stellium_needs_three_bodies_in_one_sign():
    two = {"sun": 2.0, "mercury": 6.0}
    three = {"sun": 2.0, "mercury": 6.0, "venus": 11.0}
    assert not [c for c in Z.find_configurations(two, Z.find_aspects(two)) if c.name == "stellium"]
    assert [c for c in Z.find_configurations(three, Z.find_aspects(three)) if c.name == "stellium"]


def test_yod_is_detected():
    positions = {"a": 0.0, "b": 60.0, "c": 210.0}  # sextile, both quincunx c
    names = {c.name for c in Z.find_configurations(positions, Z.find_aspects(positions))}
    assert "yod" in names


def test_configurations_are_not_reported_twice():
    positions = {"sun": 0.0, "moon": 120.0, "mars": 240.0}
    configs = Z.find_configurations(positions, Z.find_aspects(positions))
    keys = [(c.name, tuple(sorted(c.members))) for c in configs]
    assert len(keys) == len(set(keys))


# ── fortune, phase, lunar day ──────────────────────────────────────────────

def test_part_of_fortune_swaps_by_day_and_night():
    day = Z.part_of_fortune(100.0, 10.0, 50.0, day_birth=True)
    night = Z.part_of_fortune(100.0, 10.0, 50.0, day_birth=False)
    assert day == pytest.approx(140.0)
    assert night == pytest.approx(60.0)
    assert day != night


@pytest.mark.parametrize(
    "elongation,phase",
    [(0.0, "new moon"), (90.0, "first quarter"), (180.0, "full moon"), (270.0, "last quarter")],
)
def test_moon_phase_at_the_quarters(elongation, phase):
    assert Z.moon_phase(0.0, elongation)["phase"] == phase


def test_moon_phase_illumination_matches_the_geometry():
    assert Z.moon_phase(0.0, 0.0)["illumination"] == pytest.approx(0.0, abs=1e-9)
    assert Z.moon_phase(0.0, 180.0)["illumination"] == pytest.approx(1.0, abs=1e-9)
    assert Z.moon_phase(0.0, 90.0)["illumination"] == pytest.approx(0.5, abs=1e-9)


def test_waxing_flag_flips_at_the_full_moon():
    assert Z.moon_phase(0.0, 90.0)["waxing"] is True
    assert Z.moon_phase(0.0, 200.0)["waxing"] is False


@pytest.mark.parametrize("elongation", [0.0, 45.0, 180.0, 359.9])
def test_lunar_day_stays_in_range(elongation):
    assert 1 <= Z.lunar_day(0.0, elongation) <= 30
