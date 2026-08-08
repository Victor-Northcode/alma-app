"""How wide a grant is, and the one grant that must stay narrow.

A one-time purchase and an annual plan are easy: you bought a thing, you keep
it. A recurring plan is not, and the difference is the whole reason `scope`
exists. Somebody paying monthly is paying for the part of the reading that
changes with the date — where the planets are now, what this birthday's chart
says, how two charts sit together today. If that plan also handed over the
natal chart, the rational customer subscribes for one month, reads the chart
that is true forever, and cancels. The recurring revenue would not recur.

`covers` is pure, so these tests build entitlements in memory and assert the
rule directly. What is being checked is not that the code does what it does —
it is that a live grant reaches exactly the time-dependent systems, that a
scope never outranks an expiry, and that a row written before `scope` existed
still means what it meant then.
"""

from __future__ import annotations

from datetime import timedelta

from alma.billing.catalogue import LIVING_SYSTEMS
from alma.db.models import Entitlement, EntitlementKind, utcnow


def _grant(*, kind: str = EntitlementKind.annual.value, **kwargs) -> Entitlement:
    """An entitlement as it exists before any INSERT.

    Column defaults are applied by the database, not the constructor, so
    anything not named here is `None` — which is exactly the state a row
    written before a column existed comes back in.
    """
    return Entitlement(user_id="u", kind=kind, **kwargs)


# ── the live scope ─────────────────────────────────────────────────────────

def test_the_living_systems_are_the_ones_that_change_with_the_date():
    """The definition, asserted rather than inferred from the code that reads it."""
    assert LIVING_SYSTEMS == frozenset({"transits", "solar-return", "compatibility"})


def test_a_live_plan_covers_what_it_is_renting():
    grant = _grant(system="*", scope="live")
    for system in ("transits", "solar-return", "compatibility"):
        assert grant.covers(system), f"a live plan must cover {system}"


def test_a_live_plan_does_not_hand_over_the_chart_that_never_changes():
    """Otherwise the plan is bought once, read once, and cancelled."""
    grant = _grant(system="*", scope="live")
    assert not grant.covers("natal")
    assert not grant.covers("astrocartography")
    assert not grant.covers("synthesis")


def test_a_live_plan_covers_every_chapter_of_what_it_covers():
    """It is a system-wide rental, not a chapter one — asking for a chapter
    inside a living system must not narrow it, and asking for a chapter inside
    a dead one must not widen it."""
    grant = _grant(system="*", scope="live")
    assert grant.covers("transits", chapter="the-year-ahead")
    assert not grant.covers("natal", chapter="core")


def test_an_expired_live_plan_covers_nothing_at_all():
    """Scope decides *what* a grant reaches, never *whether* it still reaches.

    The ordering inside `covers` is load-bearing: if the scope branch ran
    first, a cancelled subscription would keep working forever.
    """
    lapsed = _grant(system="*", scope="live", expires_at=utcnow() - timedelta(days=1))
    assert not lapsed.covers("transits")

    revoked = _grant(system="*", scope="live", revoked_at=utcnow())
    assert not revoked.covers("transits")


# ── the other scopes ───────────────────────────────────────────────────────

def test_an_all_scope_covers_everything_including_what_is_not_for_sale_yet():
    grant = _grant(system="natal", scope="all")
    assert grant.covers("natal")
    assert grant.covers("transits")
    assert grant.covers("something-we-have-not-built")


def test_a_row_written_before_scope_existed_still_means_what_it_meant():
    """`scope` is defaulted at INSERT, so old rows and unflushed ones read as
    None. None has to keep the original behaviour or every existing purchase
    silently changes meaning the day the column ships."""
    everything = _grant(system="*")
    one_system = _grant(system="natal", kind=EntitlementKind.one_time.value)
    one_chapter = _grant(system="natal:core", kind=EntitlementKind.one_time.value)

    assert everything.scope is None
    assert everything.covers("natal")
    assert one_system.covers("natal") and not one_system.covers("transits")
    assert one_chapter.covers("natal", chapter="core")
    assert not one_chapter.covers("natal", chapter="relationships")
    assert not one_chapter.covers("natal")


def test_a_system_scope_is_still_bounded_by_the_system_it_names():
    grant = _grant(system="natal", scope="system", kind=EntitlementKind.one_time.value)
    assert grant.covers("natal")
    assert not grant.covers("transits")


# ── what was removed ───────────────────────────────────────────────────────

def test_there_is_no_trial_kind():
    """A kind nothing issues is a feature the next reader believes in.

    If this test is failing because somebody added `trial` back, the thing to
    check is that something also *expires* it — a granted, time-limited,
    revocable state with no code to revoke it is permanent free access.
    """
    assert not hasattr(EntitlementKind, "trial")


def test_the_enum_names_exactly_the_kinds_the_catalogue_sells():
    """The list of kinds is read against what is on sale, not written twice.

    Kinds are stored as free strings, so an enum that is missing one does not
    fail — it just stops being the list of kinds. It listed `one_time` and
    `annual` while the catalogue was already pricing a monthly plan, and
    nothing anywhere said so.
    """
    from alma.billing.catalogue import PRODUCTS

    assert {kind.value for kind in EntitlementKind} == {
        item.kind for item in PRODUCTS.values()
    }
