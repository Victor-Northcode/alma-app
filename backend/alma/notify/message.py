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
in the *device’s* language, so a phone set to Italian gets Italian even if the
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

from ..i18n.placements import _base, placement
from .rules import Chosen
from .transport import CHANNEL_DAILY, Push

TITLE_KEY = "push.daily.title"

#: The headline, in seven languages, **composed here rather than resolved on
#: the device** — and that is a correction, not a preference.
#:
#: `docs/PUSH.md §1.6` says the title stays a `loc-key` so that a phone whose
#: language we guessed wrong still gets a correct headline. That argument
#: depends on the key existing in the app's **native** bundle, which is where
#: iOS looks: `UNNotificationContent` resolves `title-loc-key` against
#: `Localizable.strings` in the main bundle, and Android against `strings.xml`.
#: The product is one Flutter app now, its seven catalogues are `.arb` files
#: compiled into Dart, and there is no `Localizable.strings` in the tree at all
#: — `knownRegions` in the Xcode project is `(en, Base)`. So the key resolved
#: against nothing, and iOS renders an unresolved `title-loc-key` as **the raw
#: key**: every daily would have arrived headed `push.daily.title`.
#:
#: The words are the app's own — `pushDailyTitle` in `lib/l10n/app_*.arb`,
#: already written, already reviewed, already shipped in all seven. Nothing is
#: invented here (push copy across the seven locales is explicitly somebody
#: else's task — `SCREENS-V3.md` W7), and
#: `tests/test_notify_strings.py` asserts this table still equals theirs, the
#: same "one source, two mirrors" guard the placement names already have.
#:
#: **How to undo this**, because it should be undone rather than kept: when the
#: client ships a native catalogue carrying `push.daily.title` in seven
#: languages, drop the `title=` argument in `compose` below. The key is still
#: computed and still carried, precisely so that flip is one line — and the
#: senders already prefer a literal title over a key, so nothing else moves.
TITLES: dict[str, str] = {
    "en": "Exact today",
    "es": "Aspecto exacto hoy",
    "de": "Heute exakt",
    "it": "Esatto oggi",
    "fr": "Exact aujourd’hui",
    "pt-BR": "Aspecto exato hoje",
    "ru": "Точный аспект сегодня",
}

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
    # One English title, not two. This read "In your chart today" while the app
    # shipped "Exact today" in all seven languages — the server's own source set
    # and its two mirrors had quietly separated on the one string that reaches a
    # lock screen. The app's wins, for the reason `test_notify_strings.py`
    # already gives about the placement names: the words a person sees in the
    # notification and the words they see in the app have to be the same words.
    TITLE_KEY: TITLES["en"],
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
    """The exact instant, in the shape the reader’s language writes it.

    Twelve-hour for English and twenty-four for the other five. Not a
    preference: Spanish, German, Italian, French and Brazilian Portuguese all
    write 14:20, and English is the only one of our six whose largest market
    does not. This has to be decided here rather than on the device, because a
    `loc-arg` is substituted verbatim and the operating system will not format
    a string we hand it.
    """
    if (locale or "en").lower().startswith("en"):
        # "2:20 pm", not "02:20 PM" — a leading zero on a twelve-hour clock is
        # something no English speaker writes. "%-I" would say that directly,
        # but the minus flag is a glibc extension and does not exist in the
        # Windows C runtime, so the zero is stripped by hand instead.
        return moment.strftime("%I:%M %p").lstrip("0").lower()
    return moment.strftime("%H:%M")


def expires(local: datetime) -> datetime:
    """When this notification stops being worth delivering.

    Конец местных суток получателя. Раньше здесь стояло начало тихих часов
    (22:00) — и это убивало бы письмо человека, который сам выбрал 23:00
    (владелец, 25.08.2026: выбранный час — любой из 24). Полночь оставляет
    прежний смысл: строка про сегодня не доезжает до завтра — телефон,
    вернувшийся из самолёта в 00:40, не получит бодрую фразу про день,
    который уже кончился.
    """
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return day + timedelta(hours=24)


def compose(
    chosen: Chosen,
    *,
    zone: ZoneInfo,
    local: datetime,
    locale: str | None,
    teaser: str = "",
) -> Push:
    """One notification, ready for either vendor.

    `locale` is the **device’s** language where the client reported one at
    registration, and the account’s language otherwise. The device wins because
    that is what the operating system will resolve the key in, and an argument
    translated into the account’s language inside a sentence resolved into the
    phone’s would be the exact bug the whole `loc-key` design exists to avoid —
    only harder to see, because five of the six words would be right.

    `teaser` is the written piece’s own opening sentence, and when it is here
    it becomes the body. That is the merge of two designs that arrived at this
    from different sides: this module’s payload shape — keys, resolved by the
    operating system in the device’s language — with the daily package’s body,
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
        # The headline in the reader's language, because the key resolves
        # against a native bundle this product no longer has — see `TITLES`,
        # which also says how to take this line back out.
        title=TITLES[_base(locale)],
        body=(teaser or "").strip(),
        thread="daily",
        channel=CHANNEL_DAILY,
        collapse_id=f"daily-{local.date().isoformat()}",
        expires_at=expires(local),
        # **`type`, not `kind`, and that was a real disconnection.** The routing
        # key is whatever the app reads, and the app reads `type`:
        # `AppDelegate.swift` lifts the string fields of `userInfo` and
        # `main.dart` records `push_opened{type: payload['type']}`. This payload
        # said `kind`, so every tap on a daily was counted with a null type
        # while the pair push — written later, against the client rather than
        # against `docs/PUSH.md §1.6` — was counted correctly. One name, and it
        # is the one already on the phone; §1.6 has been corrected to match.
        data={"type": "daily", "date": local.date().isoformat()},
    )
