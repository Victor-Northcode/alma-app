"""The seam where a push service plugs in, and the words both sides speak.

Two vendors, one interface, for the same reason `billing/provider.py` puts
four payment processors behind one: the thing above the seam — who gets a
notification this morning, and whether they have had too many lately — is a
product decision that must not acquire an `if platform == "ios"` in it. There
is no third push service coming, so this is not future-proofing. It is that
the two vendors disagree about almost every noun, and a rule that has to be
written twice is a rule that will eventually be two different rules.

**What is inherent to sending a push**, and therefore lives here:

* A notification is **a key and some words**, never a sentence. Both platforms
  can carry a localisation key plus arguments and resolve it against the app
  bundle in the *device's* language (`docs/PUSH.md §1.6`). That keeps the
  sentence off the wire, keeps the six translations where every other string
  in this product lives, and means the server never has to guess what language
  a phone is in.
* A send is **accepted, not delivered.** Both vendors answer for their own
  queue and neither promises a lock screen. `Verdict.sent` says exactly that
  much and nothing more.
* A token **dies**, and the moment it dies is a fact the vendor holds and we
  do not. This is the leak every push system grows: a dead token retried
  forever is a row that costs a request a day until somebody notices the
  table. `Verdict.dead` is the whole of the fix, and `tokens.retire` is what
  acts on it.
* A token can be **alive and unusable** — right device, wrong environment,
  wrong topic, wrong project. Deleting those is worse than keeping them,
  because the client re-registers the identical token on the next launch and
  the loop starts over. `Verdict.disable` is that state, and it names itself.
* The credential can be **wrong for everybody at once**, which is not a fact
  about any token. `Verdict.fatal` stops the run rather than repeating the
  same 403 a thousand times.

**What is an accident of one vendor** — none of this may leak past a sender:

* Apple's ES256 provider token, its twenty-minute refresh floor, its
  `apns-*` header family, `410` meaning gone and the millisecond timestamp in
  the body. Google's OAuth2 access token, its `messages:send` envelope, and
  its `UNREGISTERED` spelling of the same idea.
* `loc-key` versus `body_loc_key`; `apns-collapse-id` versus `collapse_key`;
  `apns-expiration` as an absolute epoch second versus `ttl` as a duration
  string; `apns-priority: 5` versus `android.priority: "normal"`.
* Android notification channels, which exist on one platform only and matter
  enormously there — the daily must never share a channel with the renewal
  notice, or a person silencing a horoscope silences a legal commitment.
* Which environment a token belongs to, a question Google does not have.

**Refusing loudly is part of the interface.** `transport_for` raises rather
than returning something that quietly does nothing, because a push system that
appears to work and sends nothing is the worst failure this feature has: every
number downstream looks healthy, the job logs "sent 0" beside "due 0", and the
first person to find out is a subscriber wondering why they are paying.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from ..db.models import DeviceToken

#: The two platforms, spelled the way `DeviceToken.platform` spells them.
PLATFORMS: tuple[str, ...] = ("ios", "android")


class PushUnavailable(RuntimeError):
    """No credential, no client library, or a vendor we do not ship.

    Raised rather than returned as a `None`, and the distinction matters at
    exactly one moment: the job's start. A `None` there would be indexed into
    a loop that sends nothing and reports success.
    """


class Verdict(str, enum.Enum):
    """What one send means for the token it was sent to.

    Five, and the two in the middle are the ones a naive implementation
    collapses into each other — which is how a push system ends up either
    deleting live tokens or retrying dead ones forever.
    """

    sent = "sent"
    #: The vendor is unwell or is throttling us. Try on a later run, not in
    #: this one: Apple asks for fifteen minutes after a 500 and Google for a
    #: minute after a 429, and neither is a wait to take inside a job that is
    #: holding a database session open.
    retry = "retry"
    #: The registration is gone and will never be valid again. Delete the row.
    dead = "dead"
    #: The device is real; this configuration cannot reach it. Keep the row,
    #: stop trying, and say which of the three it was.
    disable = "disable"
    #: Our credential is wrong for every token, not for this one. Stop.
    fatal = "fatal"


@dataclass(frozen=True, slots=True)
class Receipt:
    """What the vendor said, in this seam's vocabulary."""

    verdict: Verdict
    #: The vendor's own word — `Unregistered`, `SENDER_ID_MISMATCH` — kept
    #: verbatim, because it is what a support conversation and a vendor's
    #: documentation both use, and translating it here would mean the log line
    #: and the documentation disagree.
    reason: str = ""
    #: Anything else worth having at two in the morning: a status code, an
    #: `apns-id`, the body of a refusal.
    detail: str = ""
    #: For `dead` only, and only Apple provides it: the instant the vendor
    #: confirmed the token stopped being valid. `tokens.retire` compares it
    #: against `last_seen_at`, because a person who deleted the app on Monday
    #: and reinstalled on Tuesday must not lose their notifications to a 410
    #: we are processing on Wednesday.
    dead_since: datetime | None = None


@dataclass(frozen=True, slots=True)
class Push:
    """One notification, before either vendor has seen it.

    Deliberately not a payload. There is no `aps` key here and no `message`
    envelope; those are each sender's business, and a field named after one of
    them would be that vendor leaking upward through the seam.

    `body_key` and `args` are the design decision from `docs/PUSH.md §1.6`
    stated as a type: what crosses the wire is a key and a handful of words,
    never a composed sentence about somebody's chart. The arguments are
    substituted **verbatim** by both operating systems — there is no nested
    lookup — so they must already be in the reader's language when they get
    here. `alma/i18n/placements.py` is where they come from.
    """

    title_key: str
    body_key: str
    args: tuple[str, ...] = ()

    #: Готовый заголовок в языке читателя — вторая и последняя санкция на
    #: собранное сервером предложение в этом типе, после `body` ниже.
    #:
    #: Нужна ровно одному пушу — «отчёт пары готов» (`notify/pair.py`): его
    #: заголовок несёт имя партнёра и фактор из расчёта совместимости, а
    #: подставлять имя в ключ бандла не умеет ни одна из двух ОС — `loc-args`
    #: подставляются дословно, но клиент заморожен и ключей пары в его бандле
    #: нет. Правило то же, что у `body`: либо ключ, либо предложение, никогда
    #: оба — оба сендера трактуют это одинаково.
    title: str = ""

    #: The written piece's own first sentence, already in the reader's
    #: language. When it is set, both senders use it as the notification body
    #: and leave `body_key`/`args` out of the payload.
    #:
    #: **This is the one place a composed sentence is allowed across the wire,
    #: and it earns it.** `body_key` is the design in `docs/PUSH.md §1.6` and
    #: it is right for a line the *server* assembles: the key resolves in the
    #: device's language, so a phone set to Italian gets Italian whatever the
    #: account chose. But the daily is not only a line — it is a piece, and the
    #: notification is that piece's opening. `Written.teaser` went through
    #: `validator.check` with the rest of the paragraph it belongs to, which is
    #: a stronger guarantee than any string in a bundle has, and it is the only
    #: body that can be true to a reading rather than merely true.
    #:
    #: The title stays a key. So a phone whose language we guessed wrong still
    #: gets a correct headline, and only the sentence underneath is in the
    #: language the piece was written in — which is the language the reader
    #: will find when they tap it.
    body: str = ""
    #: Groups consecutive dailies so somebody who did not read Tuesday's does
    #: not find three separate rows on Thursday.
    thread: str = "daily"
    #: Two sends for the same day replace each other rather than stacking.
    #: Cheap insurance against a retry that raced a success.
    collapse_id: str = ""
    #: When this stops being worth delivering — the end of the recipient's
    #: local day. Both vendors will hold a notification for a phone that is
    #: off, and a daily that lands at 23:40 to describe a day already had is
    #: worse than one that never lands. Expire rather than queue.
    expires_at: datetime | None = None
    #: What the app reads to open the right screen. Small, and never prose:
    #: it travels through a vendor's servers exactly as the alert does.
    data: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class Transport(Protocol):
    """One vendor, reduced to the one thing the job needs from it."""

    platform: str

    async def send(self, token: DeviceToken, push: Push) -> Receipt:
        ...


def transport_for(platform: str) -> Transport:
    """The sender for one platform, or a refusal naming what is missing.

    Imported inside the call for the reason `config.billing_adapter` does it:
    the senders reach for an HTTP client and a crypto library on the way up,
    and neither belongs in the import graph of a module that only wanted to
    know what a `Verdict` is.

    Not cached. Settings are, and the tests clear that cache between cases;
    a second cache here would hand one test the credential the previous test
    configured.
    """
    key = platform.lower()
    if key == "ios":
        from .apns import APNs

        return APNs()
    if key == "android":
        from .fcm import FCM

        return FCM()
    raise PushUnavailable(
        f"{platform!r} is not a platform this build can send to — it ships "
        f"{', '.join(PLATFORMS)}"
    )


def configured_platforms() -> tuple[str, ...]:
    """The platforms whose credentials are all present.

    Used by the job to decide whether it may run at all. A build with neither
    platform configured is not a quiet build, it is a broken one, and
    `daily.run` says so before it looks at a single user.
    """
    from ..config import settings

    config = settings()
    return tuple(p for p in PLATFORMS if not config.missing_push_credentials(p))
