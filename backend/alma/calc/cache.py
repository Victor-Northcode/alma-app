"""Caching for computed results.

A natal chart for a given birth is the same forever, so recomputing it is
pure waste — and a year of transits takes over a second, which is far too
long to spend on every page view. Both are content-addressed by
`contract.cache_key`, which folds in the engine version: bump the version and
every stored result becomes unreachable rather than stale.

Two rules keep this from becoming a source of wrong answers.

*A key carries exactly what the answer moves with — no less and no more.*
No less, or January's transits are served in June. No more, or the key drifts
under a result that has not changed and the calculation is redone for nothing.
`TIME_SCOPE` below is the table of what each of the eight systems actually
depends on, read out of the builders in `service.py`.

This is a cache key and not a *reading* key, and the two are different
questions that were once the same string. A key here covers a whole system's
answer; what identifies a written chapter is the facts that chapter was
written from, which `api/routers/readings._reading_key` derives. Conflating
them meant every chapter of a daily system was rewritten, and paid for, every
midnight.

*A cache miss must never be distinguishable from a hit.* The stored value is
the serialised CalcResult and nothing else — no partial objects, no
post-processing that only runs on the miss path. There is a second half to
that rule which lives in the callers: a system stamped at day resolution has
to be *asked* at day resolution too, or the answer is finer than its own key
and whichever worker computed it first decides what everybody sees. Both
routes now pass midnight for a transit scan for exactly that reason.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import date, datetime, timezone
from typing import Any, Protocol

from .contract import CalcResult, BirthData, cache_key


class ResultCache(Protocol):
    """What the service needs from a cache, and nothing more."""

    def get(self, key: str) -> CalcResult | None: ...

    def put(self, key: str, result: CalcResult) -> None: ...


def _revive(payload: dict) -> CalcResult:
    return CalcResult(
        system=payload["system"],
        engine_version=payload["engine_version"],
        subject=payload["subject"],
        data=payload["data"],
        factors=tuple(payload["factors"]),
        unavailable=tuple(payload.get("unavailable", ())),
        notes=tuple(payload.get("notes", ())),
        provenance=payload.get("provenance", {}),
        computed_at=payload.get("computed_at", ""),
    )


class MemoryCache:
    """A bounded in-process cache — the default for a single worker.

    Stores the serialised form rather than the object so that a bug which
    mutates a returned result cannot poison the next reader. Charts are read
    far more often than they are computed, and a shared mutable dict handed
    out repeatedly is the kind of thing that produces one wrong reading in a
    thousand and is never reproducible.
    """

    def __init__(self, capacity: int = 512) -> None:
        self.capacity = capacity
        self._entries: OrderedDict[str, str] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> CalcResult | None:
        blob = self._entries.get(key)
        if blob is None:
            self.misses += 1
            return None
        self._entries.move_to_end(key)
        self.hits += 1
        return _revive(json.loads(blob))

    def put(self, key: str, result: CalcResult) -> None:
        self._entries[key] = result.to_json()
        self._entries.move_to_end(key)
        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
        self.hits = self.misses = 0

    @property
    def size(self) -> int:
        return len(self._entries)


class NullCache:
    """Caches nothing. Useful in tests and when correctness is being chased."""

    def get(self, key: str) -> CalcResult | None:
        return None

    def put(self, key: str, result: CalcResult) -> None:
        return None


#: What each system's answer moves with, and at what resolution. Every entry
#: was read out of the matching builder in `service.py`; the three systems
#: absent from the table — natal, compatibility, astrocartography — never
#: consult a clock at all, so their keys carry no stamp and their chapters are
#: written once and found again forever.
#:
#: This replaces a boolean set that listed numerology, birth-card and
#: synthesis alongside transits and stamped all five with *today's date*. A
#: Birth Card is fixed from one birthday to the next and a synthesis moves at
#: most twice a year, so their keys drifted every midnight and the calculation
#: was redone for an answer that had not changed. Naming the *scope* rather
#: than a yes/no is what stops that from coming back: adding a system here
#: cannot be done without answering "moves with what?".
TIME_SCOPE: dict[str, str] = {
    # Bodies move continuously, so this is the one genuinely daily system.
    # Day resolution is a deliberate rounding — see `_reference_day`.
    "transits": "day",
    # The life path is fixed at birth, but the builder also computes a
    # personal *day* — month chained off year, day chained off month — and
    # puts all three in `factors`, where the AI may assert them. While a
    # personal day is citable, the result is a day's result.
    "numerology": "day",
    # `solar_return.compute(year=...)`: one return per calendar year, and the
    # builder's default is the current calendar year rather than the birthday
    # year, so this rolls on 1 January.
    "solar-return": "calendar-year",
    # `arcana.year_card` reads the reference date for one purpose only —
    # deciding which birthday-to-birthday period it falls in. Every day inside
    # a period yields the identical card, so every day inside a period is one
    # cache entry.
    "birth-card": "birthday-year",
    # Both boundaries at once, because the synthesis reads two clocks: the
    # Year Card (moves on the birthday) and the personal year (moves on
    # 1 January). Stamping only one of them would serve a stale axis for up to
    # a year.
    "synthesis": "calendar-and-birthday-year",
}

#: Kept as a name because "does this system consult a clock" is still worth
#: asking; derived so it can never fall out of step with the table above.
TIME_DEPENDENT = frozenset(TIME_SCOPE)

#: Options that name *when* the call is being made rather than a property of
#: the answer. For a scoped system they are consumed and replaced by the
#: stamp, never left alongside it: a caller passing `year=2026` and a caller
#: passing nothing during 2026 are asking the identical question and must land
#: on one entry.
#:
#: Public because the reading key in `api/routers/readings` drops exactly this
#: set for exactly this reason, and two lists of the same three strings is one
#: list that will be wrong the day a fourth is added.
MOMENT_OPTIONS: tuple[str, ...] = ("reference", "start", "year")


def _reference_day(system: str, options: dict) -> date:
    """The day a call is being made for, at day resolution.

    This is the only place the file rounds. Transits are computed from an
    instant and two scans an hour apart genuinely differ, but a scan costs
    over a second and the page is opened many times a day, so a key that
    moved with the clock would mean the cache never hit at all. A caller that
    needs a particular instant asks for it with an explicit `start` and shares
    an entry with the rest of that day.

    An unparseable reference raises rather than falling back to `now()`: the
    fallback is what turns "the caller passed an ISO string" into the daily
    key drift this module exists to prevent, and it does it silently.
    """
    for name in ("reference", "start"):
        value = options.get(name)
        if value is None:
            continue
        if isinstance(value, datetime):   # before `date` — datetime subclasses it
            return value.date()
        if isinstance(value, date):
            return value
        raise TypeError(
            f"{system}: `{name}` must be a date or datetime, "
            f"got {type(value).__name__}"
        )
    return datetime.now(timezone.utc).date()


def _birthday_year(birth: BirthData, on: date) -> int:
    """Which birthday-to-birthday period `on` falls in, labelled by its start.

    Deliberately the same comparison `arcana.year_card` makes, down to the
    tuple compare that decides a 29 February birth's period in a common year.
    If the two ever disagreed the key would change on a day the Year Card does
    not — or, far worse, hold still on the day it changes.
    """
    had_birthday = (on.month, on.day) >= (birth.date.month, birth.date.day)
    return on.year if had_birthday else on.year - 1


def _stamp(system: str, birth: BirthData, options: dict) -> dict[str, Any]:
    """The part of the key that says when — exactly as wide as the scope."""
    scope = TIME_SCOPE.get(system)
    if scope is None:
        return {}

    day = _reference_day(system, options)
    if scope == "day":
        return {"as_of_day": day.isoformat()}
    if scope == "calendar-year":
        asked = options.get("year")
        return {"as_of_year": int(asked) if asked is not None else day.year}
    if scope == "birthday-year":
        return {"as_of_birthday_year": _birthday_year(birth, day)}
    if scope == "calendar-and-birthday-year":
        return {
            "as_of_year": day.year,
            "as_of_birthday_year": _birthday_year(birth, day),
        }
    raise ValueError(f"unknown time scope for {system}: {scope}")


def key_for(system: str, birth: BirthData, options: dict) -> str:
    """The cache key for one call: the birth, the options, and the time scope.

    Every option that only names the moment is consumed here and replaced by
    the stamp `TIME_SCOPE` says the answer actually moves with, so two callers
    asking the same question on the same day — or in the same year, for a
    system that only moves yearly — land on the same entry.
    """
    parts = dict(options)
    stamp = _stamp(system, birth, options)
    if stamp:
        for name in MOMENT_OPTIONS:
            parts.pop(name, None)
        parts.update(stamp)

    if "other" in parts and isinstance(parts["other"], BirthData):
        parts["other"] = parts["other"].fingerprint()

    return cache_key(system, birth, **parts)


def compute_cached(
    system: str,
    birth: BirthData,
    *,
    cache: ResultCache,
    **options,
) -> CalcResult:
    """Compute a system, reusing a stored answer when there is one."""
    from .service import compute

    key = key_for(system, birth, options)
    found = cache.get(key)
    if found is not None:
        return found

    result = compute(system, birth, **options)
    cache.put(key, result)
    return result
