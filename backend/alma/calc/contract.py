"""The CalcResult contract — the single source of facts for everything above.

Every system produces one of these, and nothing downstream is allowed to
compute astrology of its own. The API serialises it, the cache stores it, and
the AI layer is given it whole and told that `factors` is the complete list of
things it may assert. That last rule is only enforceable because the shape is
uniform: a validator can check a generated paragraph against `factors` without
knowing which system it came from.

Three properties are load-bearing and are tested as such:

* **JSON-safe.** No numpy scalars, no dataclasses, no tuples-as-keys. A
  numpy float survives every local test and then fails in production at the
  encoder, at the worst possible moment.
* **Complete.** `factors` lists everything the reading may lean on. If a fact
  is not in there, the AI inventing it is our bug, not the model's.
* **Honest.** `unavailable` says what could not be computed and why, in
  language a reader could be shown. An empty chart section with no reason is
  how a product loses trust.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, is_dataclass, asdict
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

#: Bumped whenever a change would alter a number. Every cache key carries it,
#: so a bump silently invalidates every stored result rather than serving a
#: reading computed by yesterday's arithmetic.
ENGINE_VERSION = "1.0.0"

SYSTEMS: tuple[str, ...] = (
    "natal",
    "numerology",
    "birth-card",
    "transits",
    "solar-return",
    "compatibility",
    "astrocartography",
    "synthesis",
)


class HouseSystem(str, Enum):
    placidus = "placidus"
    whole_sign = "whole_sign"
    porphyry = "porphyry"


@dataclass(frozen=True, slots=True)
class BirthData:
    """Everything a chart needs about one person, and nothing more.

    `time` is optional and its absence is a first-class state rather than a
    missing field to be filled in with noon. Every system that depends on the
    horizon checks `time_known` and refuses rather than guessing.
    """

    date: date
    latitude: float
    longitude: float
    timezone: str
    time: str | None = None            # "HH:MM", local wall clock
    place_label: str | None = None
    name: str | None = None
    on_ambiguous: str = "raise"        # "raise" | "earlier" | "later"

    @property
    def time_known(self) -> bool:
        return self.time is not None

    @property
    def hour_minute(self) -> tuple[int | None, int | None]:
        if self.time is None:
            return None, None
        hour, minute = self.time.split(":")[:2]
        return int(hour), int(minute)

    def fingerprint(self) -> str:
        """A stable identity for caching — same birth, same string."""
        payload = "|".join(
            str(part)
            for part in (
                self.date.isoformat(),
                self.time or "-",
                f"{self.latitude:.6f}",
                f"{self.longitude:.6f}",
                self.timezone,
                self.name or "-",
                self.on_ambiguous,
            )
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def as_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "time": self.time,
            "time_known": self.time_known,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "place": self.place_label,
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class CalcResult:
    """One system's answer, in the shape everything above it expects."""

    system: str
    engine_version: str
    subject: dict
    data: dict
    factors: tuple[str, ...]
    unavailable: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    provenance: dict = field(default_factory=dict)
    computed_at: str = ""

    def as_dict(self) -> dict:
        return {
            "system": self.system,
            "engine_version": self.engine_version,
            "computed_at": self.computed_at,
            "subject": self.subject,
            "data": self.data,
            "factors": list(self.factors),
            "unavailable": list(self.unavailable),
            "notes": list(self.notes),
            "provenance": self.provenance,
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, **kwargs)

    def cites(self, text: str) -> bool:
        """Whether a piece of generated prose leans only on known factors.

        Deliberately weak on its own — real validation lives in the AI layer,
        which knows what a citation looks like. This is the cheap structural
        check that a factor was referenced at all.
        """
        lowered = text.lower()
        return any(factor.lower() in lowered for factor in self.factors)


def build(
    *,
    system: str,
    birth: BirthData,
    data: dict,
    factors: list[str] | tuple[str, ...],
    unavailable: list[str] | tuple[str, ...] = (),
    notes: list[str] | tuple[str, ...] = (),
    provenance: dict | None = None,
) -> CalcResult:
    """Assemble a result, forcing it through the JSON-safety conversion."""
    if system not in SYSTEMS:
        raise ValueError(f"unknown system: {system}")

    return CalcResult(
        system=system,
        engine_version=ENGINE_VERSION,
        subject=json_safe(birth.as_dict()),
        data=json_safe(data),
        factors=tuple(str(f) for f in factors),
        unavailable=tuple(str(u) for u in unavailable),
        notes=tuple(str(n) for n in notes),
        provenance=json_safe(provenance or {}),
        computed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def json_safe(value: Any) -> Any:
    """Convert anything the engine produces into something json can encode.

    Numpy scalars are the reason this exists. They compare equal to floats,
    print like floats, pass every assertion, and then raise at the encoder in
    production. Converting once at the boundary is cheaper than auditing every
    arithmetic path forever.
    """
    if value is None:
        return None

    # Exact types only. `isinstance(x, float)` is true for numpy.float64,
    # which would let the very thing this function exists to remove pass
    # straight through — and it would keep working, right up until a
    # numpy.float32 (which is *not* a float subclass) reaches the encoder.
    kind = type(value)
    if kind is bool or kind is int or kind is float or kind is str:
        return value

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(v) for v in value]

    # numpy scalars and anything else that knows how to become a Python one.
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return json_safe(item())
        except (TypeError, ValueError):  # pragma: no cover - defensive
            pass

    # A subclass of a primitive with no .item() — coerce to the plain type.
    # bool before int: bool is a subclass of int and must stay a bool.
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return str(value)
    return str(value)


def cache_key(system: str, birth: BirthData, **options: Any) -> str:
    """Content address for a computed result.

    Includes the engine version so a change to the arithmetic invalidates
    everything, and the options so a Placidus chart and a whole-sign chart of
    the same birth never collide.
    """
    parts = [ENGINE_VERSION, system, birth.fingerprint()]
    for key in sorted(options):
        parts.append(f"{key}={options[key]}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
