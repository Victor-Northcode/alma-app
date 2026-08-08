"""The nine stages a person passes through, and how many fell out between them.

There has been an `event` table since the first migration and nothing has ever
written a row to it. Every conversion number the pricing work rests on is
therefore an assumption someone typed, which is why that analysis says plainly
that no advertising money should be spent until this table has thirty days of
real data in it. This module is the smallest thing that produces that data
honestly, plus the query that makes it worth having — a table nobody can ask a
question of is a table nobody will look at.

Six decisions, and the reasons they went this way rather than the obvious way.

**The stage names are a closed set.** An analytics endpoint that accepts any
string is an analytics table that fills with `offer_view`, `offerView`,
`offer-view` and `offer_veiw`, and the funnel query that reads it answers a
confident, wrong number for months. The rejected alternative — take anything,
tidy it up later — cannot work: by the time the typo is noticed the rows it
should have been are gone. A refusal costs one 422 in development and nothing
in production, because the client hard-codes its eight — `STAGES` below is
spelt to match `src/lib/track.ts` for exactly that reason, and the ninth name
is the one only this server may write.

**Somebody who has told us nothing counts, and does not become a row in the
`user` table for it.** That sentence used to read "a guest counts", and it was
paid for in a way nobody had costed: `POST /v1/events` minted an account for
any caller without a token, the landing fired `landing_view` on mount, and so a
browser that loaded the page and touched nothing left an account behind. The
dev database showed 143 users against 46 profiles — two thirds of the rows were
page views wearing an account's clothes, and every per-account number computed
over them (how many accounts exist, how many convert, what an account costs)
was measuring the wrong population.

So the top of the funnel is recorded against an **anonymous id**: a random
string the client keeps, sent in `X-Alma-Anon`, which is not an account and
grants nothing. The account is minted at the first act that gives us something
to keep — a birth saved, or a sign-in — and `deps.current_user` claims the
anonymous id for it at that moment.

**Which is the whole reason `AnonymousVisitor` exists, and it is not
bookkeeping.** Without the claim, the stages before the account and the stages
after it are two identities belonging to one person, and "of the people who saw
the landing, how many finished the journey" — the number the pricing model
rests on — reads as zero on data that looks perfectly healthy. That is the same
failure the old code had, arriving from the other direction. The join is
therefore written at the one moment it is a *fact* rather than an inference,
which is the moment the account is created out of that browser's request.

The rejected alternative was to infer the join at read time from rows that
carry both ids. It needs no extra table and it is wrong in a way that cannot be
seen: a shared browser where a second person signs in would silently move the
first person's landing view onto the second person's account.

Attribution is one of those two ids and nothing else: no IP address, no user
agent, no device fingerprint, no address.

**A purchase is not the browser's word for it.** The browser knows an overlay
closed; the processor's signed webhook knows money moved, and it already writes
a `Purchase` row with `completed_at` on it. So the purchase stage is read from
the money trail rather than from this table, and `POST /v1/events` refuses the
name outright. Anything else means the number that decides how much is spent on
advertising is a number anybody with a terminal can inflate.

**What follows a checkout are three siblings, not three steps.** Opening one
has exactly three known endings, and each is measured against
`checkout_opened` rather than against the one printed above it:
`purchase_completed` is the overlay reporting that it ran to the end,
`purchase` is money that actually arrived, and `offer_declined` is the overlay
being closed. Chained instead, `offer_declined` would count the people who
declined *among the people who bought* — nobody, a zero indistinguishable from
a broken beacon — and `purchase` would count only buyers whose browser also
sent a beacon, so every customer with Do Not Track set would vanish out of the
revenue line. The gap between the middle two is worth watching on its own: an
overlay that finished with no payment behind it is a webhook that did not
arrive, and that is a person who paid and got nothing.

**Merges are folded when the funnel is read**, and it is worth being exact
about which rows need it, because the obvious answer is wrong. `accounts.merge`
*does* know about this table — `Event` is in the list of tables it re-points,
and it says why — so a guest's rows that carry a user id follow the guest into
the account they merged into, and those need no folding at all. What it cannot
move is the rows written **before** the account existed, because those carry
only an anonymous id and there is no user id on them to re-point. Those are
resolved through the claim instead, and the claim names the guest — the row that
existed when the browser handed its id over — so the merge pointer has to be
followed *after* the claim rather than instead of it. Read-time folding also
fixes rows already written, which a backfill would not.

**What must never be stored.** The privacy page names every field Alma holds
and promises that nothing is collected to build a profile for anyone else. A
birth date, a birth time, a place, a name, an email address, an IP address, a
user agent, a referrer or a full URL in this table would each make that page
false — and a free-form `properties` bag is exactly how one arrives, one
well-meaning `{"birthDate": …}` at a time. Hence `PROPERTIES`: a short
allowlist of words that describe the *product*, never the person, with short
values, and silence for anything else — see `clean_properties` for why an
unwanted label is dropped where an unwanted stage name is refused.

**An anonymous id is still an identifier, and it gets an identifier's rules.**
It is not a user row, but it is a string in somebody's browser that ties their
visits together, so: it is random and carries nothing derived from the person
or the device; it is refused unless it looks like one we would have issued, so
this table cannot be used to store somebody's address in a header; every row
carrying it dies with the account that claimed it, in `forget`; and none of them
outlives `PURGE_AFTER_DAYS`, which `purge` enforces and the privacy page
states. The retention deletes *every* row past the cutoff rather than only the
anonymous ones, and that is the deliberate choice: deleting the unattributed
top of an old funnel while leaving the conversions below it intact would make
every historical rate wrong in the direction that flatters us.

There is no HTTP route for the read side, on purpose. The funnel is the
business's own numbers, an unauthenticated endpoint publishes them to
competitors, and an authenticated one needs an operator credential that this
service does not have. So it is a module and a `__main__`, run as
`python -m alma.funnel --days 30`, the same shape as the renewal notices.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .db.models import AnonymousVisitor, Event, Purchase, User, as_utc, utcnow

log = logging.getLogger("alma.funnel")


class UnknownStage(ValueError):
    """A stage name outside the closed set. See `STAGES` for why that is fatal."""


class Unattributed(ValueError):
    """An event with neither an account nor an anonymous id behind it.

    Refused rather than written as a row with two nulls in it. Such a row can
    never be counted — the funnel counts distinct identities — but it *would*
    be counted in a `SELECT count(*)`, so it is exactly the kind of row that
    makes a table disagree with itself depending on who queries it.
    """


class TooManyEvents(RuntimeError):
    """This caller has written as many events today as it is allowed to."""


@dataclass(frozen=True)
class Stage:
    """One rung of the funnel.

    `after` is the stage this one's rate is measured against, which is usually
    but not always the one printed above it — see the note about the three
    endings of a checkout.
    `server_known` marks a stage the browser is not permitted to report,
    because something on our side knows it for certain.
    """

    name: str
    after: str | None
    server_known: bool = False


#: The whole funnel, in order. Adding a stage here is the only way to add one:
#: the endpoint validates against this tuple and the query walks it.
#:
#: The names are the ones `src/lib/track.ts` sends, down to the spelling. The
#: brief for this work called the last two "purchase" and "declined"; the
#: shipped client says `purchase_completed` and `offer_declined`, and since a
#: beacon swallows its own failures, a server that insisted on the other
#: spelling would refuse every event in production without anybody finding out
#: for a month.
STAGES: tuple[Stage, ...] = (
    Stage("landing_view", None),
    Stage("quiz_start", "landing_view"),
    Stage("quiz_complete", "quiz_start"),
    Stage("portrait_view", "quiz_complete"),
    Stage("offer_view", "portrait_view"),
    Stage("checkout_opened", "offer_view"),
    # The browser's own view of the overlay closing successfully. Kept
    # deliberately separate from the money below rather than treated as the
    # same fact: the client's own comment concedes that where the two
    # disagree, the webhook is right.
    Stage("purchase_completed", "checkout_opened"),
    # Read from the `Purchase` row the webhook writes, never from a client.
    # Measured against the checkout rather than against the beacon above it,
    # so that a buyer whose browser sent nothing is still a sale.
    Stage("purchase", "checkout_opened", server_known=True),
    # The third ending, not a step beyond buying.
    Stage("offer_declined", "checkout_opened"),

    # ── the daily ──────────────────────────────────────────────────────────
    #
    # Not part of the acquisition funnel above and deliberately at the end of
    # it: these two measure what happens *after* somebody is already paying,
    # which is retention rather than conversion. They are here because this
    # tuple is the only way to add a stage — the endpoint validates against it
    # and the query walks it — and because until they existed the daily was
    # unmeasured. `alma/notify/daily.py::FUNNEL_STAGES` names both and
    # `_measure` already calls `record`; it was logging a warning and dropping
    # the event.
    #
    # `THE-DAILY.md §6.3` makes the ratio of Off to Occasionally after thirty
    # days the only metric that measures what the owner actually asked for —
    # "not annoying" — and `daily_opened / daily_sent` is the other half of
    # it: a notification people open is one they wanted.
    #
    # `daily_sent` is `server_known` for the same reason `purchase` is. The
    # job knows it accepted a vendor's receipt; a browser cannot report it and
    # must not be allowed to. `daily_opened` is the client's, because opening
    # is a thing only the client can see.
    Stage("daily_sent", None, server_known=True),
    Stage("daily_opened", "daily_sent"),
)

BY_NAME: dict[str, Stage] = {stage.name: stage for stage in STAGES}
STAGE_NAMES: tuple[str, ...] = tuple(stage.name for stage in STAGES)

#: The only keys a caller may attach to an event, and every one of them
#: describes the product rather than the person: which system was on screen,
#: which chapter, which product key was being bought, which language the page
#: was in, which step of the quiz, which currency it was priced in, and — for
#: a decline — whether the overlay was dismissed or the offer was tapped past.
#: There is deliberately no `country`, because `currency` answers the market
#: question at a coarser grain, and deliberately no free-text key of any kind.
PROPERTIES: frozenset[str] = frozenset(
    {"system", "chapter", "product", "locale", "step", "variant", "currency", "how"}
)

#: A property value is a label, not a sentence. Sixty-four characters is more
#: than every product key, system slug and locale code we ship, and far less
#: than anything a person would type about themselves.
MAX_VALUE = 64

#: What a property value has to look like to be kept.
#:
#: The length was the only rule here, and length alone was never the rule this
#: module says it enforces. Every docstring in this file — and the one on
#: `Event` in `db/models.py`, and the paragraph the privacy page rests on —
#: claims the table cannot come to contain something a person typed, and
#: `ANON_ID` above says out loud that "an email address in `X-Alma-Anon` gets
#: the same answer as one in a property value". It did not: `{"how":
#: "sofia@example.com"}` and `{"variant": "Sofia Bianchi"}` are both short, both
#: on the allowlist, and both were written straight through. The claim was true
#: of the web only because `scrub` in `src/lib/track.ts` refused them before
#: they left the browser — which is to say the discipline was enforced on the
#: side of the wire that anybody can edit, and not on the side that owns the
#: column.
#:
#: So this is `LABEL` from `track.ts`, character for character, moved to where
#: it binds. A slug, a locale code, a currency, a step name: something we
#: minted, not something somebody was asked for. No whitespace and no `@`,
#: which between them are what make a name and an address structurally
#: impossible rather than merely absent so far.
#:
#: The rejected alternative was to loosen the client to match the server, on the
#: grounds that the two ends should agree and the server is the older of the
#: two. They should agree, and they now do — but agreement is not the only
#: property either end needs, and of the two rules on offer this is the one the
#: rest of the file already promised.
#:
#: Composed from `MAX_VALUE` rather than written with a 63 in it, so that the
#: ceiling stays one number with one name. The first character is spent on the
#: "starts with a letter or a digit" rule, which is what keeps `-` and `.` from
#: leading — a value beginning with a dash reads as a flag to half the tools
#: anybody would ever point at this table.
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0," + str(MAX_VALUE - 1) + r"}$")

#: How many events one account may write in a day. This bounds the table
#: rather than the burst: a per-second limiter would need state shared between
#: processes, which this service does not have, and the thing actually being
#: defended is a table that a script could otherwise grow without limit. A
#: full journey through every stage writes well under twenty rows, so the cap
#: is roughly ten sessions a day before anybody honest could notice it.
DAILY_LIMIT = 200

#: The metric the cap is counted under, in the same `UsageCounter` table that
#: already holds questions asked, money spent and the one downsell.
LIMIT_METRIC = "events"

#: What an anonymous id must look like to be stored.
#:
#: A UUID is what the clients send (`crypto.randomUUID` on the web), but the
#: pattern is deliberately a little wider than that: an app on a platform whose
#: idiomatic identifier is not a UUID should not have to fake one, and a rule
#: this file can state in one line is a rule that survives a second client.
#:
#: What it is really doing is refusing everything else. This header arrives from
#: a browser, it is written to a column, and the column is on a table whose
#: whole discipline is that nothing a person typed can reach it — so an id that
#: is not plausibly an id we issued is dropped rather than stored, and an email
#: address in `X-Alma-Anon` gets the same answer as one in a property value.
ANON_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")

#: How long any of this is kept.
#:
#: Stated here because the privacy page states it to the reader, and a number
#: that lives in one of those two places is a promise nobody can check. `purge`
#: is what makes it true and `backend/README.md` is where it is scheduled; a
#: retention that depends on somebody remembering to run a command is a
#: retention policy in the same sense that the renewal notice was a promise
#: before it had a cron line.
PURGE_AFTER_DAYS = 180

#: How long after a claim a row carrying only the browser id still belongs to
#: the account that claimed it.
#:
#: The claim is the moment a browser became an account, and from that moment on
#: everything that browser sends carries the token — so a row arriving *later*
#: with the id and no token is, by construction, not coming from the session
#: that holds the account. On a shared browser it is a second person, and
#: folding it onto the first person's account is a cross-person attribution
#: that nothing in the report looks wrong about. `audience` therefore stops
#: folding once this has passed, and counts the row as its own visitor.
#:
#: It is not zero because of the beacons already in flight when the account is
#: minted. The journey fires `quiz_complete` next to the birth save that mints,
#: `keepalive` lets a request outlive the page that started it, and the two
#: processes' clocks need not agree to the millisecond. A window measured in
#: minutes covers all of that and is still nowhere near "the rest of time",
#: which is what the old rule was.
CLAIM_GRACE = timedelta(minutes=5)


def clean_anon_id(anon_id: str | None) -> str | None:
    """The caller's anonymous id, or nothing at all.

    Dropped rather than refused, for the reason the whole of this module drops
    rather than refuses at the edges: the caller is a beacon that swallows its
    own errors. A client sending a malformed id would lose every event it ever
    sent and nothing anywhere would say so. Dropping it costs that client its
    attribution — which is loud, because the rung reads zero — and costs the
    rest of the funnel nothing.

    The route is the one place that turns "nothing at all" into an answer: with
    no account either, there is nothing to attribute the stage to, and it says
    so rather than writing an uncountable row.
    """
    if not anon_id:
        return None
    candidate = anon_id.strip()
    return candidate if ANON_ID.fullmatch(candidate) else None


# ── writing ───────────────────────────────────────────────────────────────


def clean_properties(properties: dict | None) -> dict:
    """Whatever of this is safe to keep. Everything else is dropped and logged.

    Dropping rather than refusing, and the asymmetry with a bad stage name is
    the point. An unknown *stage* has nowhere to be counted, so refusing it
    costs nothing. An unknown *label* on a good stage is different: the client
    is a beacon that swallows every failure it gets, so a 422 here would delete
    the whole event, and the day somebody adds one label to a screen the entire
    rung silently disappears from the funnel for a release. A missing dimension
    is a bad afternoon; a missing rung is a decision made on a wrong number.

    Which is also why it is logged. Nobody reads a 422 that a beacon threw
    away, but somebody does eventually read the logs, and the line names the
    key so the fix is to add it to `PROPERTIES` rather than to go looking.

    Values must be a boolean, a whole number, or a string shaped like `LABEL`.
    A nested object is where a whole birth record fits, and free text is where
    an email address fits — so neither is a value this function has a branch
    for.

    **The shape rule used to be a length rule, and the two are not the same
    promise.** `{"variant": "Sofia Bianchi"}` is fourteen characters and was
    stored verbatim; so was `{"how": "sofia@example.com"}`. The client refused
    both — `scrub` in `src/lib/track.ts` has always tested its values against a
    label pattern — which meant the discipline this module describes was being
    kept by the browser rather than by the code that owns the column, and a
    second client, a curl, or the day somebody passes a form value through in
    six months' time would each have written a person's name into an analytics
    table with nothing anywhere objecting.

    So the two ends now apply the same rule and `LABEL` says which way the
    disagreement was settled. Tightening the server rather than loosening the
    client costs nothing real: every value our three clients send is a
    catalogue slug, a system slug, a locale code, a currency or a fixed word,
    and a test posts each of them.
    """
    if not properties or not isinstance(properties, dict):
        return {}

    kept: dict = {}
    dropped: list[str] = []
    for key, value in properties.items():
        if key not in PROPERTIES:
            dropped.append(str(key))
            continue
        if isinstance(value, bool) or isinstance(value, int):
            kept[key] = value
            continue
        if not isinstance(value, str) or not LABEL.fullmatch(value):
            # Dropped whole rather than truncated or tidied. Half of somebody's
            # email address is still their email address, and a value that has
            # to be cleaned up before it fits is by definition not one of the
            # labels we mint — the honest thing to lose is the dimension.
            dropped.append(key)
            continue
        kept[key] = value

    if dropped:
        # The keys came from a client, so what is logged is bounded in both
        # directions — an unbounded list of caller-controlled strings is a way
        # to write whatever you like into somebody's log aggregator.
        names = ", ".join(name[:32] for name in sorted(dropped)[:5])
        log.warning("dropped %d label(s) not kept by this table: %s", len(dropped), names)
    return kept


async def spend_allowance(
    session: AsyncSession, user_id: str, *, limit: int | None = None
) -> int:
    """Count one event against today's cap, or raise `TooManyEvents`.

    What is capped is rows in the table, not requests at the door. The
    increment and the event are written in one transaction, so a refusal rolls
    both back and a client that keeps going after its 429 keeps being refused
    on the count it has already stored — which is the property that matters,
    because the thing being defended is the size of the table rather than the
    cost of answering. A limiter on requests would need state shared between
    processes, and this service has none.

    Both numeric fields are set explicitly because SQLAlchemy applies column
    defaults at INSERT, and a freshly constructed row reads back as `None`
    until then.

    The ceiling is read here rather than defaulted in the signature, where it
    would be bound once at import and no longer be the number this module
    documents.
    """
    from .db.models import UsageCounter

    ceiling = DAILY_LIMIT if limit is None else limit

    today = utcnow().date()
    key = f"{user_id}:{today.isoformat()}:{LIMIT_METRIC}"
    row = await session.get(UsageCounter, key)
    if row is None:
        row = UsageCounter(
            id=key, user_id=user_id, day=today, metric=LIMIT_METRIC, count=0, amount=0.0
        )
        session.add(row)
    row.count = (row.count or 0) + 1
    await session.flush()

    if row.count > ceiling:
        raise TooManyEvents(
            f"{ceiling} events is a day's worth for one account; "
            f"this one has sent {row.count}"
        )
    return row.count


async def spend_anonymous_allowance(
    session: AsyncSession, anon_id: str, *, limit: int | None = None
) -> int:
    """The same ceiling, for a caller who has no account to count against.

    Counted straight off this table rather than through `UsageCounter`, and the
    reason is not taste: that table's `user_id` is a foreign key into `user`
    with `ON DELETE CASCADE`, so counting an anonymous caller there would mean
    either inventing a user row — which is the entire thing this work exists to
    stop — or writing a dangling key into a constrained column.

    Counting rows is also what `spend_allowance` says it is defending in the
    first place: the size of this table. Here it does that literally, with one
    indexed `count(*)` over one identifier's rows since midnight. The ceiling is
    two hundred and a full journey writes four, so the query never counts a
    number worth optimising.

    It is approximate under concurrency, in a way the counter version is not:
    two beacons in flight together both read the same count. That is deliberate
    rather than overlooked — the exact number is not the point, and the
    alternative is a row-level lock on the hot path of a fire-and-forget beacon.
    """
    ceiling = DAILY_LIMIT if limit is None else limit
    midnight = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    written = (
        await session.execute(
            select(func.count())
            .select_from(Event)
            .where(Event.anon_id == anon_id, Event.created_at >= midnight)
        )
    ).scalar_one()

    if written >= ceiling:
        raise TooManyEvents(
            f"{ceiling} events is a day's worth for one visitor; "
            f"this one has sent {written}"
        )
    return written + 1


async def claim(session: AsyncSession, *, anon_id: str | None, user_id: str) -> bool:
    """Record that this browser became this account. Returns whether it did.

    Called from `deps.current_user` at the only moment the statement is true:
    the request that mints the account is the request that arrived from that
    browser. Everywhere else it would be a guess.

    **First claim wins, and a second one is not an error.** Two things can lead
    here with the same id — a race between two requests that both arrive with no
    token, and a browser whose person signs into a second account later — and in
    both cases the honest answer is that the id already belongs to somebody. The
    rejected alternative, re-pointing it, quietly moves one person's early
    stages onto another person's account; this way the second account is simply
    missing the stages it never had, which shows up as a gap between `reached`
    and `total` in the report rather than as a plausible wrong number.

    The insert is wrapped in a savepoint because the race is real and losing it
    must cost this request nothing: an `IntegrityError` that escapes to the
    session poisons the surrounding transaction, and the surrounding transaction
    is somebody saving their birth data.
    """
    cleaned = clean_anon_id(anon_id)
    if cleaned is None:
        return False

    if await session.get(AnonymousVisitor, cleaned) is not None:
        return False

    try:
        async with session.begin_nested():
            session.add(AnonymousVisitor(anon_id=cleaned, user_id=user_id))
    except IntegrityError:
        log.info("anonymous id claimed by another account first; leaving it there")
        return False
    return True


async def record(
    session: AsyncSession,
    *,
    user_id: str | None,
    stage: str,
    properties: dict | None = None,
    anon_id: str | None = None,
) -> Event:
    """Write one stage against one identity. No limit, no browser.

    This is the server-side entry point — the webhook, the checkout route —
    and it deliberately does not consult the daily cap: that exists to stop a
    client writing rows, and applying it to our own code would mean a busy
    day's purchases stopped being recorded. The HTTP route asks for the
    allowance itself before calling this.

    An account and an anonymous id are both written when both are known. That
    looks redundant — the account alone would count correctly — and it is the
    cheap half of the join: the claim table is the fact, and a row carrying both
    is the evidence an operator can check it against when a rate looks wrong.
    It costs nothing extra to delete, because `forget` removes rows by either.

    Neither is a refusal. A row with two nulls in it counts towards a
    `count(*)` and towards no funnel, which is the one way this table can be
    made to disagree with itself.
    """
    if stage not in BY_NAME:
        raise UnknownStage(f"{stage!r} is not a funnel stage — {', '.join(STAGE_NAMES)}")

    anonymous = clean_anon_id(anon_id)
    if user_id is None and anonymous is None:
        raise Unattributed(f"{stage!r} arrived with no account and no anonymous id")

    row = Event(
        user_id=user_id,
        anon_id=anonymous,
        name=stage,
        properties=clean_properties(properties),
    )
    session.add(row)
    await session.flush()
    return row


async def forget(session: AsyncSession, user_id: str) -> int:
    """Erase one account's events. Returns how many rows went.

    Deletion in this product is real — the privacy page says so in as many
    words — and an account's funnel rows are as much theirs as their readings.
    Kept here rather than as a `delete()` inlined into `accounts.erase` so that
    the table's own module owns the sentence, but `accounts.erase` is where it
    has to be called from.

    **The rows from before they had an account go too, and finding them is the
    only reason the claim survives this long.** Somebody who walked the whole
    journey and then signed in has their landing view and their quiz filed under
    a browser id, not under the account they are now asking us to erase. Erasing
    only the rows that carry the account id would leave those behind — still
    linked to each other, still linked to a string that is still in that
    person's browser — while the privacy page says the step labels went with
    everything else. The claim row is deleted last, so the ids it names are
    still readable when the events are.

    **And the claim may be filed under an account this person no longer uses.**
    Somebody who walked the journey as a guest on a phone and then signed into
    an account they already had has their browser id claimed by the *guest* row,
    because that is the row that existed when the browser handed it over;
    `accounts.merge` then folds the guest into the account and moves the events
    that carry a user id across, but the ones from before the account existed
    carry none and stay where they are. So the ids of every account that merged
    into this one are gathered first. Missing that is a deletion that looks
    complete and leaves the whole first half of somebody's journey behind.

    **This reaches wider than `audience` counts, on purpose.** A row written
    under this browser's id long after the claim is *not* counted as this
    account — see `CLAIM_GRACE` — and it is still deleted here. The two answer
    different questions and the safe direction is opposite for each. For a
    number, "we cannot tell whose this is" must never quietly become "it is
    theirs", because that inflates one person's conversion with a stranger's
    steps. For an erasure, a row keyed to an identifier this account owns, in a
    browser this account was created out of, goes: over-deleting a step label
    costs a line in a report, and under-deleting one leaves a record behind
    after somebody asked for it to be gone.
    """
    canonical = await _merged_into(session)
    theirs_too = {source for source, target in canonical.items() if target == user_id}
    every_id = {user_id, *theirs_too}

    owned = (
        await session.execute(
            select(AnonymousVisitor.anon_id).where(AnonymousVisitor.user_id.in_(every_id))
        )
    ).scalars().all()

    rows = Event.user_id.in_(every_id)
    if owned:
        rows = or_(rows, Event.anon_id.in_(owned))

    result = await session.execute(delete(Event).where(rows))
    await session.execute(
        delete(AnonymousVisitor).where(AnonymousVisitor.user_id.in_(every_id))
    )
    return result.rowcount or 0


async def purge(session: AsyncSession, *, days: int = PURGE_AFTER_DAYS) -> int:
    """Drop everything older than the retention this product promises.

    **Every row past the cutoff, not only the anonymous ones.** Deleting the
    unattributed top of an old funnel while leaving the purchases below it in
    place would not be a smaller dataset — it would be a wrong one, with every
    historical conversion rate divided by a denominator that had been quietly
    shrunk. A funnel window either exists whole or does not exist.

    A claim goes when the cutoff has passed *and* nothing references it any
    more. Both conditions, because the second alone would delete the join for a
    browser whose person came back yesterday, and the first alone would delete
    it while rows inside the window still need it to be counted as one person.
    """
    cutoff = utcnow() - timedelta(days=days)

    gone = await session.execute(delete(Event).where(Event.created_at < cutoff))

    still_referenced = select(Event.anon_id).where(Event.anon_id.is_not(None))
    await session.execute(
        delete(AnonymousVisitor).where(
            AnonymousVisitor.claimed_at < cutoff,
            AnonymousVisitor.anon_id.not_in(still_referenced),
        )
    )
    return gone.rowcount or 0


# ── reading ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Step:
    """One line of the answer.

    `reached` counts the people who got here *along the path* — everyone in
    this step is also in the step it is measured against. `total` counts
    everyone who reached the stage at all, by whatever route. The two are
    equal in a tidy funnel; a gap between them is people arriving in the
    middle, which is a real thing that happens when a link is shared, and it
    is reported rather than hidden because the nested count alone would read
    as traffic we never had.
    """

    stage: str
    of: str | None
    reached: int
    total: int
    rate: float | None


async def _merged_into(session: AsyncSession) -> dict[str, str]:
    """Every merged account id, mapped to the row that survived it.

    Chains are followed with a seen-set, the same way `accounts.resolve` does
    it: two merges in a row are ordinary, and a cycle would be a bug we should
    not hang on.
    """
    rows = (
        await session.execute(
            select(User.id, User.merged_into_id).where(User.merged_into_id.is_not(None))
        )
    ).all()
    pointer = {source: target for source, target in rows}

    resolved: dict[str, str] = {}
    for source in pointer:
        seen = {source}
        current = pointer[source]
        while current in pointer and current not in seen:
            seen.add(current)
            current = pointer[current]
        resolved[source] = current
    return resolved


async def _claimed_by(session: AsyncSession) -> dict[str, tuple[str, datetime | None]]:
    """Every anonymous id that has become an account, mapped to it and to when.

    The *when* is what stops the join being open-ended. An id resolves to its
    account for the rows recorded up to the claim; after that the browser has a
    token, so anything still arriving under the bare id is somebody the account
    cannot vouch for. See `CLAIM_GRACE`.
    """
    rows = (
        await session.execute(
            select(
                AnonymousVisitor.anon_id,
                AnonymousVisitor.user_id,
                AnonymousVisitor.claimed_at,
            )
        )
    ).all()
    return {anon_id: (user_id, claimed_at) for anon_id, user_id, claimed_at in rows}


async def audience(
    session: AsyncSession, *, since: datetime | None = None, until: datetime | None = None
) -> dict[str, set[str]]:
    """Who reached each stage in the window, as sets of surviving identities.

    **An identity is an account where there is one and a browser where there is
    not, and the join between them is what makes the report a funnel rather than
    two unrelated tallies.** Somebody who lands, does the quiz and then saves a
    birth is one person whose first three stages carry a browser id and whose
    later ones carry an account id; resolving the browser id through the claim
    is what stops the first conversion rate reading zero.

    The order matters and it is the reverse of what reads naturally. An
    anonymous id is resolved to the account that claimed it *before* the merge
    pointer is followed, because both indirections can apply to one row: a
    browser becomes a guest account, and that guest is later folded into an
    account the person already had. Following only one of the two leaves the
    same person counted as two, which is the failure this whole function exists
    to prevent.

    **The claim is a window, not a permanent redirection**, and that is the one
    rule here that was wrong rather than merely unstated. Resolving every bare
    id to whichever account once claimed it reads well and produces a
    cross-person attribution on the ordinary shared machine: a family computer
    or a library terminal where the first person's account minted out of the
    browser and the second person arrives with no token. Their landing view and
    their quiz were filed under the first person, whose conversion rate they
    silently improved, and whose deletion silently erased them. After the claim
    the browser that owns the account sends a token with every request, so a row
    that arrives without one is not that session — it is an identity we cannot
    name, and it is counted as one. See `CLAIM_GRACE` for why the boundary is
    not the claim instant exactly.

    An id nobody has claimed is a real identity of its own, prefixed so it can
    never collide with an account id. Dropping those instead would delete
    everybody who has not converted yet, which is to say the denominator.

    One browser can therefore contribute two identities to the same stage, and
    that is the honest answer rather than a rounding error: the rows inside the
    window are the person who converted, and the rows outside it are somebody
    about whom the only true statement is that they were here.

    The purchase stage is unioned in from the money trail rather than read from
    the event table. Union rather than replacement because a `purchase` row can
    only have been written by our own server-side code — the HTTP route refuses
    the name — so both sources are trustworthy and neither is complete on its
    own: a payment reconciled by hand has a `Purchase` row and no event.
    """
    canonical = await _merged_into(session)
    claimed = await _claimed_by(session)

    def fold(user_id: str) -> str:
        return canonical.get(user_id, user_id)

    def identities(
        user_id: str | None, anon_id: str | None, first: object, last: object
    ) -> set[str]:
        if user_id is not None:
            return {fold(user_id)}

        claim = claimed.get(anon_id or "")
        if claim is None:
            return {f"anon:{anon_id}"}

        owner, claimed_at = claim
        closes = as_utc(claimed_at)
        if closes is None:  # pragma: no cover - the column has a default
            return {fold(owner)}
        closes = closes + CLAIM_GRACE

        found: set[str] = set()
        if (as_utc(first) or closes) <= closes:
            found.add(fold(owner))
        if (as_utc(last) or closes) > closes:
            found.add(f"anon:{anon_id}")
        return found

    window = []
    if since is not None:
        window.append(Event.created_at >= since)
    if until is not None:
        window.append(Event.created_at < until)

    # Grouped rather than `DISTINCT`, and it returns the same number of rows the
    # `DISTINCT` did: one per (stage, identity). The two timestamps come out of
    # the aggregate instead of off each row, because this is the one table that
    # grows with traffic rather than with customers and the query walks every
    # row of a month — selecting `created_at` per row to compare it in Python
    # would have made `DISTINCT` a no-op and dragged the whole month back.
    rows = (
        await session.execute(
            select(
                Event.name,
                Event.user_id,
                Event.anon_id,
                func.min(Event.created_at),
                func.max(Event.created_at),
            )
            .where(
                or_(Event.user_id.is_not(None), Event.anon_id.is_not(None)),
                Event.name.in_(STAGE_NAMES),
                *window,
            )
            .group_by(Event.name, Event.user_id, Event.anon_id)
        )
    ).all()

    reached: dict[str, set[str]] = {name: set() for name in STAGE_NAMES}
    for name, user_id, anon_id, first, last in rows:
        reached[name] |= identities(user_id, anon_id, first, last)

    paid_window = []
    if since is not None:
        paid_window.append(Purchase.completed_at >= since)
    if until is not None:
        paid_window.append(Purchase.completed_at < until)

    paid = (
        await session.execute(
            select(Purchase.user_id)
            .where(
                Purchase.user_id.is_not(None),
                # `completed_at` is set by the webhook and only on a payment,
                # so this is money that actually moved rather than a checkout
                # that was opened or an adjustment that reduced one.
                Purchase.completed_at.is_not(None),
                *paid_window,
            )
            .distinct()
        )
    ).scalars().all()
    reached["purchase"] |= {fold(user_id) for user_id in paid}

    return reached


async def funnel(
    session: AsyncSession, *, since: datetime | None = None, until: datetime | None = None
) -> list[Step]:
    """Of the people who reached each stage, how many reached the next.

    Membership, not chronology: a step's population is the previous step's
    population intersected with everyone who reached this stage, and no
    ordering of timestamps is required. Requiring one sounds stricter and is
    wrong here — someone reads their portrait on Tuesday, thinks about it, and
    buys on Friday from the same account, and a browser that batches two
    beacons can deliver them a second apart in either order. An ordering rule
    would drop both, and it would drop them silently.
    """
    reached = await audience(session, since=since, until=until)

    along_the_path: dict[str, set[str]] = {}
    steps: list[Step] = []
    for stage in STAGES:
        everyone = reached[stage.name]
        base = along_the_path[stage.after] if stage.after else None
        here = everyone if base is None else everyone & base

        along_the_path[stage.name] = here
        steps.append(
            Step(
                stage=stage.name,
                of=stage.after,
                reached=len(here),
                total=len(everyone),
                # No rate against an empty base. A funnel that divides by zero
                # to report 0% tells whoever reads it that nobody converted,
                # when what happened is that nobody arrived.
                rate=(len(here) / len(base)) if base else None,
            )
        )
    return steps


def render(steps: list[Step]) -> str:
    """The funnel as a block of text, for a terminal or a log line."""
    lines = [f"{'stage':<18}{'reached':>9}{'total':>8}  of"]
    for step in steps:
        rate = "" if step.rate is None else f"  {step.rate * 100:5.1f}% of {step.of}"
        lines.append(f"{step.stage:<18}{step.reached:>9}{step.total:>8}{rate}")
    return "\n".join(lines)


async def _run(days: int) -> list[Step]:
    from .db.session import session_scope

    since = utcnow() - timedelta(days=days)
    async with session_scope() as session:
        return await funnel(session, since=since)


async def _purge(days: int) -> int:
    from .db.session import session_scope

    async with session_scope() as session:
        return await purge(session, days=days)


if __name__ == "__main__":  # pragma: no cover - the operator's entry point
    parser = argparse.ArgumentParser(description="The conversion funnel, from our own rows.")
    parser.add_argument(
        "--days", type=int, default=30,
        help="how far back to look; 30 is the window the pricing work asks for",
    )
    parser.add_argument(
        "--purge", action="store_true",
        help=(
            "delete every step label older than the retention on the privacy "
            f"page ({PURGE_AFTER_DAYS} days) and print how many went. This is "
            "the half of that promise a person cannot verify from the outside, "
            "so it belongs in cron — see backend/README.md."
        ),
    )
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if arguments.purge:
        print(f"{asyncio.run(_purge(PURGE_AFTER_DAYS))} step label(s) deleted")
    else:
        print(render(asyncio.run(_run(arguments.days))))
