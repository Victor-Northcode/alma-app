"""Turning one chosen transit into one notification, without writing a sentence.

Nothing here calls a model. The lock-screen line is **assembled** from a key
and two or three nouns, which buys three things at once: the push costs
nothing, it cannot hallucinate, and — because it is a localisation key — it
goes through the same six-language gate as every other string in the product.
That is the reason not to ask a model to write a lock-screen sentence, and it
is a different decision from the *reading* behind the notification, which is a
generation and is priced properly in `docs/THE-DAILY.md §2`.

**The keys live in the app bundles; only their English source lives here.**
`STRINGS` below is what a translator is given and what a reviewer reads. The
actual `Localizable.strings` and `strings.xml` entries are the clients', which
is the whole point of the `loc-key` design: the operating system resolves them
in the *device's* language, so a phone set to Italian gets Italian even if the
account was created in English.

**The aspect is in the key, the placements are in the arguments.** "Squares"
is a verb: its form changes with the language, and in three of our six it
changes with what follows it. Putting it in the arguments would be asking a
server to conjugate. Putting it in the key puts it in a file a translator
opens, next to the word order it belongs to — and leaves the arguments as
single nouns from the closed set in `alma/i18n/placements.py`.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..i18n.placements import placement
from .rules import QUIET_START, Chosen
from .transport import Push

TITLE_KEY = "push.daily.title"

#: The English source set, and the whole of it. Eleven body strings plus a
#: title: five aspects × two doors, and the valve.
#:
#: The placeholders are written in Apple's `%1$@` form; Android's `%1$s` is the
#: same three arguments in the same order, and each client writes its own
#: format for its own platform. The **order** is fixed by this table and is the
#: one thing a translator may not change: transiting body, natal point, time.
#:
#: The valve line is the one `THE-DAILY.md §7` left open — it recommended the
#: 21-day starvation valve *on condition* that the resulting notification reads
#: as the quiet week it is rather than as an announcement, and observed that
#: nobody had drafted one. This is that draft. It names the quiet outright
#: before it names the transit, it uses "still" rather than a verb of arrival,
#: and it carries no time because a valve piece is not about a moment. If it
#: cannot survive translation into all six with that character intact, the
#: valve should be dropped and the 60-day silence accepted — that is the honest
#: failure and a manufactured piece is not.
STRINGS: dict[str, str] = {
    TITLE_KEY: "In your chart today",
    "push.daily.exact.conjunction": "%1$@ meets your %2$@ exactly at %3$@.",
    "push.daily.exact.opposition": "%1$@ opposes your %2$@ exactly at %3$@.",
    "push.daily.exact.square": "%1$@ squares your %2$@ exactly at %3$@.",
    "push.daily.exact.trine": "%1$@ trines your %2$@ exactly at %3$@.",
    "push.daily.exact.sextile": "%1$@ sextiles your %2$@ exactly at %3$@.",
    "push.daily.entering.conjunction": "%1$@ comes into range of your %2$@ today.",
    "push.daily.entering.opposition": "%1$@ moves into opposition with your %2$@ today.",
    "push.daily.entering.square": "%1$@ moves into square with your %2$@ today.",
    "push.daily.entering.trine": "%1$@ moves into trine with your %2$@ today.",
    "push.daily.entering.sextile": "%1$@ moves into sextile with your %2$@ today.",
    "push.daily.quiet": "A quiet week. The one thing still moving: %1$@ on your %2$@.",
}


def body_key(chosen: Chosen) -> str:
    """Which string this notification uses.

    The valve has one key for all five aspects, on purpose. A quiet-week line
    that named the aspect would be reaching for precision to make a small
    thing sound larger, which is exactly the failure mode the valve was
    conditionally approved against.
    """
    if chosen.door == "valve":
        return "push.daily.quiet"
    return f"push.daily.{chosen.door}.{chosen.candidate.aspect}"


def clock(moment: datetime, locale: str | None) -> str:
    """The exact instant, in the shape the reader's language writes it.

    Twelve-hour for English and twenty-four for the other five. Not a
    preference: Spanish, German, Italian, French and Brazilian Portuguese all
    write 14:20, and English is the only one of our six whose largest market
    does not. This has to be decided here rather than on the device, because a
    `loc-arg` is substituted verbatim and the operating system will not format
    a string we hand it.
    """
    if (locale or "en").lower().startswith("en"):
        # "2:20 pm", not "02:20 PM" — a leading zero on a twelve-hour clock is
        # something no English speaker writes.
        return moment.strftime("%-I:%M %p").lower()
    return moment.strftime("%H:%M")


def expires(local: datetime) -> datetime:
    """When this notification stops being worth delivering.

    The start of the recipient's quiet hours on the same local day, not
    midnight. A phone that was off all day and comes back at 23:40 should not
    receive a cheerful line about a morning that has been and gone — and the
    vendor holding it until then would be the delivery layer quietly
    overriding the product's own rule that a late daily is dropped rather than
    deferred.
    """
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return day + timedelta(hours=QUIET_START)


def compose(
    chosen: Chosen,
    *,
    zone: ZoneInfo,
    local: datetime,
    locale: str | None,
    teaser: str = "",
) -> Push:
    """One notification, ready for either vendor.

    `locale` is the **device's** language where the client reported one at
    registration, and the account's language otherwise. The device wins because
    that is what the operating system will resolve the key in, and an argument
    translated into the account's language inside a sentence resolved into the
    phone's would be the exact bug the whole `loc-key` design exists to avoid —
    only harder to see, because five of the six words would be right.

    `teaser` is the written piece's own opening sentence, and when it is here
    it becomes the body. That is the merge of two designs that arrived at this
    from different sides: this module's payload shape — keys, resolved by the
    operating system in the device's language — with the daily package's body,
    which went through `validator.check` with the paragraph it belongs to.
    Assembling a body from a key was never *false*, but it pointed at a reading
    that was not being written; a teaser cannot exist without one.

    The key is still computed and still carried. A push with no piece behind it
    is not sent at all (see `daily.run`), so in practice the key is the shape
    tests and any future silent-push path use — but a payload that can degrade
    to a true sentence is better than one that cannot.
    """
    exact_local = chosen.candidate.exact_at.astimezone(zone)
    args = [
        placement(chosen.candidate.transiting, locale or "en"),
        placement(chosen.candidate.natal, locale or "en"),
    ]
    if chosen.door == "exact":
        args.append(clock(exact_local, locale))

    return Push(
        title_key=TITLE_KEY,
        body_key=body_key(chosen),
        args=tuple(args),
        body=(teaser or "").strip(),
        thread="daily",
        collapse_id=f"daily-{local.date().isoformat()}",
        expires_at=expires(local),
        data={"kind": "daily", "date": local.date().isoformat()},
    )
