"""Turning one occasion into one short piece, through the writer that exists.

**The daily goes through `alma/ai/writer.py` or it is not Alma writing.** That
is not a style preference. `validator.py` is the only reason this product is
distinguishable from an app that asks a model for a horoscope: every paragraph
carries the factor strings it was read from, and a paragraph naming a placement
this chart does not contain is refused after three attempts rather than
shipped. A daily generated on a shortcut around that would be the one piece of
prose in the product with no citation check — and it is also the one that
arrives uninvited, on a lock screen, with no chapter around it to give it
context. It needs the check more than a chapter does, not less.

So nothing here generates. This module builds the brief and hands it over.

**Why the brief is one event and not the whole day.** `docs/THE-DAILY.md §2.1`
measured both shapes: a whole-day brief has to carry the complete natal factor
list so the validator has something to check against, and that list alone is
~2.3 kB; a one-event brief is 167 characters at the median. The input is 14×
smaller and the input is most of the bill at these output lengths. But the
better reason is editorial. Given everything in orb, a model writes about the
day; given one contact, it writes about the contact. §1.2 measured 6.4–10.7
contacts in orb on an average day, and a piece that mentions eight of them is
the horoscope this product exists not to be.

**Not in `chapters.BY_SYSTEM`.** The daily has a `Chapter` because that is what
the writer takes, but it is built here, per locale, and never registered. A
41st entry in `BY_SYSTEM` would appear in the table of contents, in the
paywall's chapter count, in `writer.preview`, and in `tests/test_locales.py`'s
comparison of all six catalogue files — four places that would each be
asserting something false about a piece nobody buys and nobody browses to.
`writer.build_prompt` asks the chapter object for its own title and question,
so building it locally from `words.py` is the whole mechanism required.
"""

from __future__ import annotations

import logging

from ..ai import writer
from ..ai.chapters import Chapter
from ..ai.provider import Provider
from ..calc.contract import BirthData, CalcResult, build
from ..engine import ephemeris, transits, zodiac
from ..engine.natal import NatalChart
from . import clock
from .selection import DELIVERY_HOUR, ENTERS, Occasion
from .words import words_for

log = logging.getLogger("alma.daily.writing")

#: 80–130 words, one or two paragraphs. Shorter than every chapter in
#: `chapters.py` by a factor of two, because this is read first on a lock
#: screen and then in the app, and because there is exactly one fact in it. A
#: chapter answers a question about a life; this names a contact and says what
#: it tends to feel like. Anything longer is padding, and padding in a daily is
#: how a subscription starts to feel like a newsletter.
WORDS = (80, 130)
PARAGRAPHS = (1, 2)

#: What the model must cite. `Hit.describe()` begins with "transiting ", so
#: this selects the contact and leaves the natal placement it touches in the
#: "rest of the chart" section of the prompt — context it *may* cite rather
#: than the thing it must. That is the right split: the piece is about the
#: transit, and the natal degree is why the transit lands where it does.
#:
#: `_moving_line` below is also written to begin with "transiting", so the
#: moving body's own degree is offered rather than merely available. See
#: `brief` for why that line had to exist at all.
READS = ("transiting",)

#: How far apart the two points are, per aspect, in degrees. Straight off
#: `transits.ASPECT_TARGETS` — the same numbers, deduplicated and made positive,
#: because a trine is two crossings at ±120° and the prompt only cares that it
#: is 120°. Derived rather than retyped so that an aspect added to the engine
#: cannot acquire a second, disagreeing angle here.
ASPECT_DEGREES: dict[str, float] = {
    name: abs(offset) for name, offset in transits.ASPECT_TARGETS
}


def chapter_for(locale: str) -> Chapter:
    """The daily's `Chapter`, in the reader's language.

    Localised for the same reason `writer.build_prompt` localises a chapter's
    question: it is the one line of the prompt that is a piece of the *product*
    rather than an instruction, and asking the question in English while
    demanding an answer in German asks the model to translate the brief before
    it starts.
    """
    words = words_for(locale)
    return Chapter(
        slug="daily",
        numeral="·",
        index=0,
        title=words.title,
        question=words.question,
        reads=READS,
        free=False,
        # False on purpose. A chart without a birth time loses the Ascendant
        # and Midheaven and is measurably thinner — 65 empty days a year
        # against 0–20 (§1.2, §7) — but the daily still works for it, and the
        # honest response is the `unavailable` note carried in the brief below
        # rather than refusing to write anything.
        time_dependent=False,
        words=WORDS,
        paragraphs=PARAGRAPHS,
        # No "what to do with it" line. `voice.DAILY_TIER` forbids exactly that
        # sentence and the schema was asking for it anyway — 7 of 8 live
        # generations obliged, every one of them with the banned content. See
        # `chapters.Chapter.advice`.
        advice=False,
    )


def natal_lines(chart: NatalChart, name: str) -> list[str]:
    """The natal placement this transit is touching, as the chart prints it.

    Spelled exactly as `NatalChart.factors()` spells it. Not similarly — the
    validator normalises punctuation but not wording, and a natal line the
    reader could compare against their own chart page and find worded
    differently is a small crack in the one thing this product sells.
    """
    placement = chart.placements.get(name)
    if placement is not None:
        return [placement.describe()]
    if chart.angles is not None and name in ("ascendant", "midheaven"):
        return [f"{name} {zodiac.format_position(getattr(chart.angles, name))}"]
    return []


def natal_longitude(chart: NatalChart, name: str) -> float | None:
    """The degree `natal_lines` prints, as a number. Same two sources, in order."""
    placement = chart.placements.get(name)
    if placement is not None:
        return float(placement.longitude)
    if chart.angles is not None and name in ("ascendant", "midheaven"):
        return float(getattr(chart.angles, name))
    return None


def moving_longitude(occasion: Occasion) -> float | None:
    """Where the transiting body actually is at the instant being written about.

    From the ephemeris, at `occasion.at` — not inferred as
    `natal + target_offset`, which is exact only for a `PERFECTS` occasion and
    off by an orb's width in an unknown direction for an `ENTERS` one. One
    ephemeris call against a model call is free, and a number that is right for
    one of the two kinds is the kind of almost-right that put this defect here
    in the first place.

    Returns `None` rather than raising when the body is not one the ephemeris
    can place — Chiron outside its kernel's range is the real case — because
    the piece is still writable without the degree, and losing a daily over a
    missing supplementary fact would be the fix costing more than the bug.
    """
    try:
        value = ephemeris.longitudes(
            occasion.hit.transiting, [clock.to_jd(occasion.at)]
        )
        return float(value[0]) % 360.0
    except Exception:  # pragma: no cover - kernel range and loader faults
        log.warning(
            "no ephemeris position for transiting %s at %s; the daily brief "
            "will carry the aspect in words but not the moving degree",
            occasion.hit.transiting, occasion.at,
        )
        return None


def _moving_line(occasion: Occasion, longitude: float) -> str:
    """The moving body's own position, spelled so it is offered and checkable.

    Begins with "transiting" so `READS` puts it in the prompt's *cite these*
    list rather than its context list, and formats the degree with
    `zodiac.format_position` — the same function `natal_lines` uses — so the
    two ends of the aspect are printed in one notation and the difference
    between them is visible at a glance.
    """
    motion = " retrograde" if occasion.hit.retrograde else ""
    return (
        f"transiting {occasion.hit.transiting}{motion} at "
        f"{zodiac.format_position(longitude)}"
    )


def _geometry(occasion: Occasion, *, moving: float | None, natal: float | None) -> str:
    """The one note that stops a piece inventing where the moving body is.

    **This is the fix for a reading that shipped a false astronomical fact.** A
    live generation for a Kraków chart on 2026-08-31 — occasion
    `pluto:sextile:ascendant` — wrote *"transiting Pluto reaches your Ascendant
    at 3°31′ Aries exactly, orb 0.00°"*. Pluto was at 3°31′ **Aquarius**, 300°
    away, and will not reach that Ascendant for about two centuries. The
    validator passed it on the first attempt, and it was right to: it compares
    cited factor strings against the allowed set and never reads the prose, so
    this class of error is structurally outside what it can catch.

    The prompt caused it, and in two ways that compounded. The aspect reached
    the model **only as a glyph** — `Hit.describe()` renders "⚹" and the word
    "sextile" appeared nowhere in the prompt — and, worse, the prompt carried
    **no position for the moving body at all**, so the single degree anywhere
    in it was the Ascendant's. Given "orb 0.00°", one degree, and no other
    candidate, "Pluto is at 3°31′ Aries" is the inference the prompt invited.

    So this note names the aspect in words, states the separation in degrees,
    prints both positions next to each other, and forbids the specific sentence
    that was written. It is a note rather than a factor because none of it is a
    placement: the validator cannot check "60° apart", and pretending otherwise
    by dressing it as a citable string would be a fact that looks checked and
    is not. What *is* checkable — the moving body's degree — is a factor, above.
    """
    aspect = occasion.hit.aspect
    apart = ASPECT_DEGREES.get(aspect)
    said = f"the aspect is a {aspect}"
    if apart is not None:
        said += f": the two points are {apart:g}° apart"

    if moving is not None and natal is not None:
        said += (
            f". Transiting {occasion.hit.transiting} is at "
            f"{zodiac.format_position(moving)} and natal {occasion.hit.natal} "
            f"is at {zodiac.format_position(natal)}"
        )

    if aspect == "conjunction":
        return said + (
            ". They are at the same degree of the zodiac, which is what makes "
            "this a conjunction."
        )

    body, point = occasion.hit.transiting, occasion.hit.natal
    said += (
        f". They are in DIFFERENT SIGNS and are NOT in the same place. Do not "
        f"write that the transiting {body} is on, at, reaching, meeting or "
        f"sitting on the natal {point}, and never put the transiting {body} in "
        f"the natal {point}'s sign."
    )
    # The sign, not the degree, and the distinction is the whole point. Every
    # aspect angle here is a multiple of 30°, so the two ends always share the
    # same degree *within* their signs — 3°37′ Aquarius and 3°37′ Aries is a
    # correct sextile, and an instruction to avoid "the natal degree" would be
    # asking the model not to write the true sentence. What can never be shared
    # outside a conjunction is the sign.
    if apart is not None:
        said += (
            f" An orb of 0° here means the {apart:g}° angle is exact — not "
            "that the two are in the same place."
        )
    return said


def brief(
    occasion: Occasion,
    *,
    chart: NatalChart,
    birth: BirthData,
) -> CalcResult:
    """The one-event brief, as a `CalcResult` so the writer needs no new shape.

    `factors` is the complete world the piece may assert from: the contact,
    **both ends of it as degrees**, and the natal line it lands on. `notes`
    carries the timing and the geometry, neither of which is a placement and
    therefore neither of which the validator can check — they are labelled
    clearly and given verbatim, which is how `transits_result` already handles
    a window.

    The timing lines are the point of the whole feature. *"Saturn squares your
    Sun"* is a horoscope; *"Saturn squares your Sun at 14:20 today, and it has
    been in orb since 20 July"* is a calendar entry, and the difference is
    entirely in these two strings.

    **Both degrees are here because one of them was missing and a piece lied.**
    See `_geometry` for the reading that shipped and what it claimed. The short
    version: the brief used to contain exactly one position — the natal one —
    and an orb of 0.00°, and a model asked to write about a contact under those
    conditions will put the moving body on the only degree it has been given.
    """
    moving = moving_longitude(occasion)
    natal = natal_longitude(chart, occasion.hit.natal)

    words = [occasion.factor]
    if moving is not None:
        words.append(_moving_line(occasion, moving))
    words += natal_lines(chart, occasion.hit.natal)

    notes = [
        _geometry(occasion, moving=moving, natal=natal),
        _timing(occasion),
        _window(occasion),
    ]
    if occasion.hit.retrograde:
        notes.append(
            f"the transiting {occasion.hit.transiting} is retrograde at the "
            "moment this perfects, so this is a return over ground it has "
            "already covered rather than a first pass"
        )
    if occasion.valve:
        # The condition §4.3 attaches to the valve: the piece must read as the
        # quiet week it is. `voice.DAILY_TIER` instructs on that; this is what
        # tells it which week it is looking at.
        notes.append(
            "THE WEEK IS QUIET. Nothing in this chart has been pressing for "
            "three weeks and this contact is the strongest thing still moving. "
            "Write the quiet week honestly — say that nothing is pressing and "
            "name this as what is still in motion. Do not inflate it."
        )

    unavailable = list(chart.unavailable)
    if not chart.time_known:
        # §7: do not silently serve a thinner product. A chart without a birth
        # time has no Ascendant and no Midheaven — two of the five natal points
        # carrying NATAL_WEIGHT 1.0 — and the reader is entitled to know that
        # is why their daily is quieter than a friend's.
        unavailable.append(
            "transits to the ascendant and midheaven: the birth time is unknown"
        )

    return build(
        system="transits",
        birth=birth,
        data={
            "daily": True,
            "date": occasion.on.isoformat(),
            "kind": occasion.kind,
            "kernel": occasion.kernel,
            "valve": occasion.valve,
            "timezone": occasion.zone,
            "at": occasion.at.isoformat(timespec="minutes"),
            "orb": occasion.orb,
            "weight": occasion.hit.weight,
            "settled_days": occasion.settled_days,
        },
        factors=words,
        unavailable=unavailable,
        notes=[n for n in notes if n] + list(chart.notes),
        provenance={"selection": "alma.daily.selection", "kernel": occasion.kernel},
    )


def _timing(occasion: Occasion, *, read_at: int = DELIVERY_HOUR) -> str:
    """When this happens, and — the part that was missing — when it is read.

    A daily is delivered at `DELIVERY_HOUR`, 08:00 local. Simulated over six
    charts and a full year, **39% of exact-hit occasions perfect before 08:00**:
    Seoul on 2026-08-17 at 00:04, Auckland on 2026-09-21 at 01:16, Buenos Aires
    on 2026-10-03 at 00:02. The note used to say "this aspect perfects at 00:04
    … Name that time in the piece" in the present tense and never mentioned
    that the reader would meet it eight hours later, so the prose followed the
    tense it was given and pointed at a peak that was already gone.

    The model was inconsistent about it rather than uniformly wrong — one of
    the generated pieces did write "at 03:42 this morning" unprompted — and
    intermittent is worse than uniform, because a reader who is pointed at a
    time that has passed once stops treating the time as information at all.

    `read_at` is a parameter and not a constant so that a caller delivering at
    another hour gets an honest note rather than this module's assumption. The
    matching half of this fix is in `notification._compose`, which picks a
    past-tense template for the same case.
    """
    when = clock.format_time(occasion.at)
    day = occasion.on.isoformat()
    if occasion.kind == ENTERS:
        return (
            f"this contact enters orb today, {day}, in {occasion.zone} — it has "
            "not been live before today"
        )

    note = (
        f"this aspect perfects at {when} on {day}, local time in "
        f"{occasion.zone}. Name that time in the piece."
    )
    if occasion.at.hour < read_at:
        note += (
            f" IMPORTANT: this piece is read at {read_at:02d}:00, so by the time"
            f" it is read {when} has already passed. Write it in the past tense"
            " — it peaked earlier today, it is not coming. Do not tell the"
            " reader to expect or watch for something that has been and gone."
        )
    return note


def _window(occasion: Occasion) -> str:
    opened = occasion.enters_at.date().isoformat() if occasion.enters_at else None
    closes = occasion.leaves_at.date().isoformat() if occasion.leaves_at else None
    if opened and closes:
        settled = occasion.settled_days
        so_far = f", {settled} day(s) ago" if settled else ""
        return f"in orb from {opened}{so_far} until {closes}"
    if closes:
        return f"already in orb when this chart's window opened; it closes {closes}"
    if opened:
        return f"in orb from {opened}; it is still open at the end of the scan"
    return "the orb window runs past both ends of the scanned year"


async def write(
    occasion: Occasion,
    *,
    chart: NatalChart,
    birth: BirthData,
    provider: Provider,
    model: str,
    locale: str = "en",
    ledger=None,
) -> writer.Written:
    """One daily piece, validated exactly as a paid chapter is.

    `paid=False` and `register="daily"` together, which is what
    `voice.system_prompt`'s `register` argument was added for. The two used to
    be one boolean and the daily wants opposite answers from them:

    * **the register** is its own — 80 to 130 words whose first sentence has to
      survive a lock screen is not `PAID_TIER`'s "go deeper, let length serve
      the content", and it is not the free sample either;
    * **the ceiling** is the tight one. `cost.guard(paid=False)` refuses
      anything over `free_user_budget`, $0.05. §2.2 *modelled* a one-event
      daily at $0.0105; **fourteen live generations on `claude-sonnet-5`
      measured $0.0143 at the mean and $0.0175 at the worst**, read back off
      the spend ledger rather than added up from what the calls claimed. So the
      headroom is 2.9×, not the order of magnitude that used to be claimed
      here — still ample, and still the property that makes the ceiling worth
      keeping tight. This is the one generation in the product that can happen
      every day for every subscriber, so it is the one where a prompt that
      quietly grew should stop being affordable long before the invoice
      notices. Re-measure with `tools/daily/a_real_week.py`; past $0.025
      something got longer.
    """
    return await writer.write(
        result=brief(occasion, chart=chart, birth=birth),
        chapter=chapter_for(locale),
        provider=provider,
        model=model,
        locale=locale,
        paid=False,
        register="daily",
        ledger=ledger,
    )
