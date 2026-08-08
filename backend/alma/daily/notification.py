"""The one line that makes somebody open the app, and why it is not generated.

The notification is not the piece. It is a single line on a lock screen, and
the brief for it is exact: *"Mars reaches your Ascendant at 14:20"* rather than
*"Something is happening today"*. There were two ways to produce it and the
choice is worth writing down, because both are defensible and the reasons are
not obvious.

**Generated.** A second, tiny call to the model — a headline for the piece it
just wrote. It reads like a person wrote it, it can be surprising, and it costs
$0.014 measured live (§2.2), which §2.3 establishes is affordable at any cadence.

**Assembled.** Composed from the occasion and the six-language table in
`words.py`. Exact by construction, free, instant, and identical every time.

**It is assembled, and the argument that settles it is the validator.**
`alma/ai/validator.py` checks a generated paragraph against the factor list
character by character. It cannot check *"at 14:20"*, because a time is not a
placement and there is no factor to compare it to. So a generated notification
line would be the only user-facing string in this entire product with no
citation check on it — and it would be the string that arrives uninvited, is
read by everybody including the people who never open the piece, and is the one
quoted back to us when it is wrong. The place where the product's guarantee is
weakest is the last place to spend a generation.

Two supporting reasons. A generated line can *drift* from the piece behind it:
the piece says a transit is applying, the headline says it perfects, and the
reader sees only the headline. And the second call would sit outside the stored
piece, so the same day fetched twice could produce two different notifications
— which is the exact failure `Reading` exists to prevent one layer down.

**The known cost of assembling: it can read mechanically.** That is real and it
is answered rather than denied. The composed line is the *title* only, where
mechanical is the correct register — a title is a label. The **body** of the
notification is the piece's `teaser`, which was generated, is in the reader's
language, and went through the validator with the rest of the piece. So the
notification is exact where exactness matters and alive where life matters, and
neither half required a second generation.

**No piece, no push.** `compose` requires a teaser and there is no code path
that invents one. A notification can therefore never claim anything the
validated piece behind it does not.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import clock
from .selection import DELIVERY_HOUR, ENTERS, Occasion
from .words import words_for

#: The four shapes a daily notification comes in, named as localisation keys
#: so a client that would rather compose the line itself can. See `payload`.
KEY_EXACT = "daily.push.exact"

#: The same fact, delivered after it happened. Its own key rather than a tense
#: the client is expected to infer: `loc-args` substitute verbatim and the
#: operating system will not conjugate anything, so a past reading has to be a
#: different string in the bundle. See `words.DailyWords.line_exact_past` for
#: how often this fires — 39% of exact hits — and why the grammar of it is not
#: as simple as adding "was".
KEY_EXACT_PAST = "daily.push.exact_past"

KEY_ENTERING = "daily.push.entering"
KEY_QUIET = "daily.push.quiet"


@dataclass(frozen=True, slots=True)
class Notification:
    """One line, in one language, about one contact."""

    #: The composed line. Exact, assembled, never generated.
    title: str
    #: The piece's own first sentence — generated, cited, validated.
    body: str
    locale: str
    key: str
    #: Already localised into `locale`, in the order the key's format string
    #: expects. See `payload` for why they are pre-localised rather than raw.
    args: tuple[str, ...]
    #: The instant in ISO-8601 with offset, so a client that knows the device's
    #: real *region* — which the server never does, only its language — can
    #: print "2:20 PM" where `clock.format_time` printed "14:20".
    at: str
    on: str
    kernel: str

    def payload(self) -> dict:
        """The transport-neutral shape both senders need.

        `docs/PUSH.md §3` designs the APNs and FCM payloads around
        `loc-key`/`loc-args` and `body_loc_key`/`body_loc_args`, so that the
        translations live in the app bundles and the payload carries a key
        rather than a statement about somebody's chart. That is the right
        instinct and it is honoured here for the title, which is assembled and
        therefore *can* be a key.

        It cannot be honoured for the body, and it is worth being clear why
        rather than leaving the next person to discover it: the body is a
        sentence a model wrote about this person's chart. There is no key for
        it and there never will be. The payload therefore already carries text
        in the reader's language, which means the server already had to know
        the language — it wrote the piece in it. Given that, pre-localising
        `args` into the same language costs nothing and removes the one failure
        `PUSH.md` itself flagged: `loc-args` are substituted **verbatim**, so a
        client holding an English "Ascendant" would drop it into the middle of
        an Italian sentence. Here the argument arrives as "il tuo Ascendente"
        and the client's format string only has to know where the blanks go.

        `title` is included composed as well, so a client with no format string
        for this key — an old build, a platform that has not shipped the
        strings yet — has something true to display instead of a key.
        """
        return {
            "title": self.title,
            "body": self.body,
            "loc_key": self.key,
            "loc_args": list(self.args),
            "locale": self.locale,
            "date": self.on,
            "at": self.at,
            "kernel": self.kernel,
        }


def line(
    occasion: Occasion, *, locale: str = "en", read_at: int = DELIVERY_HOUR
) -> str:
    """The composed title on its own — for logs, tests and fallbacks."""
    return _compose(occasion, locale=locale, read_at=read_at)[0]


def compose(
    occasion: Occasion,
    *,
    teaser: str,
    locale: str = "en",
    read_at: int = DELIVERY_HOUR,
) -> Notification:
    """The notification for one occasion, given the piece already written.

    `teaser` is `Written.teaser` — the one sentence the schema asks every
    generation for, described in `writer.CHAPTER_SCHEMA` as "one sentence,
    always visible, that names what this chapter found". For a chapter that is
    a summary line on a hub. For the daily it is the notification body, which
    is why `voice.DAILY_TIER` tells the model that its first sentence is the
    whole piece for most readers.

    Raises rather than defaulting when the teaser is empty. A notification with
    a fabricated body would be the product asserting something no validator
    approved, and the correct behaviour when a piece has no teaser is to send
    nothing — silence is already a supported state of this feature (§1.6).

    `read_at` is the hour this will be *delivered*, which is a different fact
    from the hour the aspect perfects and is what decides the tense. It is
    threaded rather than assumed so that a caller delivering at another hour —
    a person who moved their delivery time, a catch-up run — still gets a line
    that is true when it lands.
    """
    text = (teaser or "").strip()
    if not text:
        raise ValueError(
            "a daily notification needs the written piece's teaser as its body; "
            "there is no path that invents one, because the line on a lock "
            "screen must not claim more than the validated piece behind it"
        )

    title, key, args = _compose(occasion, locale=locale, read_at=read_at)
    return Notification(
        title=title,
        # Deliberately not truncated. Both platforms elide a long body at the
        # right place for their own screen and font size, and a server-side cut
        # is a second place to get it wrong — in six languages, where the same
        # sentence is 30% longer in German than in English.
        body=text,
        locale=words_for(locale).locale,
        key=key,
        args=args,
        at=occasion.at.isoformat(timespec="minutes"),
        on=occasion.on.isoformat(),
        kernel=occasion.kernel,
    )


def _compose(
    occasion: Occasion, *, locale: str, read_at: int = DELIVERY_HOUR
) -> tuple[str, str, tuple[str, ...]]:
    words = words_for(locale)
    hit = occasion.hit
    contact = words.contact(
        body=hit.transiting, aspect=hit.aspect, point=hit.natal
    )

    # The valve check comes first: a piece admitted only because three weeks
    # were silent must not be announced with the same sentence as a Saturn
    # square that cleared the floor on its own. §4.3 makes that a condition of
    # the valve existing at all.
    if occasion.valve:
        return words.line_quiet.format(contact=contact), KEY_QUIET, (contact,)
    if occasion.kind == ENTERS:
        return words.line_entering.format(contact=contact), KEY_ENTERING, (contact,)

    when = clock.format_time(occasion.at)

    # The tense. An exact hit before the delivery hour has already happened by
    # the time the phone buzzes — 39% of them do, and the untensed line told
    # every one of those readers to look forward to a moment that was gone.
    # Compared against the hour rather than against "now" on purpose: this line
    # is composed once and stored with the piece, and a title that changed
    # meaning depending on when somebody happened to re-fetch it would be a
    # second, harder version of the same bug.
    if occasion.at.hour < read_at:
        return (
            words.line_exact_past.format(contact=contact, time=when),
            KEY_EXACT_PAST,
            (contact, when),
        )

    return (
        words.line_exact.format(contact=contact, time=when),
        KEY_EXACT,
        (contact, when),
    )
