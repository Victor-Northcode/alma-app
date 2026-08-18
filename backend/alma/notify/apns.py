"""Apple Push Notification service.

Token-based, with a `.p8` signing key, rather than certificates. A certificate
expires on a date nobody has written down, needs one per topic, and is renewed
by hand in a browser at the worst possible moment; a signing key does not
expire, one key covers every topic on the team, and a leaked provider token is
worth an hour rather than a year. The private half never leaves this process.

Three things in here are not obvious and each one has cost somebody a day:

**The provider token is cached, and it has to be.** Apple accepts a JWT for at
most an hour and refuses one *refreshed* more often than every twenty minutes
with `429 TooManyProviderTokenUpdates`. A naive `sign_jwt()` called per
notification therefore works for exactly one send and then stops — which looks
like a rate limit on notifications and is not. The token is minted at most
once every `_REFRESH_FLOOR` and reused for `_LIFETIME`.

**`410` does not mean "delete the row".** It means the token stopped being
valid for this topic at the millisecond timestamp in the body. If the app has
registered since that moment, the person deleted the app and reinstalled it,
and deleting on sight would silently end the notifications of somebody who is
still paying. The comparison lives in `tokens.retire`; this module's job is to
carry the timestamp up honestly.

**A bad device token and a dead device token are different failures.** Apple
answers `410 Unregistered` for the app being gone and `400 BadDeviceToken` for
a sandbox token presented to the production host. The first is the token's
fault and the row goes; the second is *our* configuration's fault, the device
is fine, and deleting the row would mean the client re-registers the identical
token on the next launch and we do it all again. See `docs/PUSH.md §1.8`.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings
from ..db.models import DeviceToken
from .transport import Push, PushUnavailable, Receipt, Verdict

log = logging.getLogger("alma.notify.apns")

HOSTS = {
    "production": "https://api.push.apple.com",
    "sandbox": "https://api.sandbox.push.apple.com",
}

#: How long a minted provider token is used for. Apple's ceiling is one hour;
#: fifty minutes leaves room for a job that started just before the boundary.
_LIFETIME = 50 * 60
#: And Apple's floor on refreshing one. Minting more often than this is what
#: earns `429 TooManyProviderTokenUpdates`, so a forced refresh below the floor
#: is refused here rather than by Apple.
_REFRESH_FLOOR = 20 * 60

#: Reasons that mean the registration is gone. Both arrive with 410.
_DEAD = {"Unregistered", "ExpiredToken"}

#: Reasons that mean the device is fine and our configuration is not. The row
#: is kept and disabled; deleting it would loop with the client's next launch.
_MISCONFIGURED = {"BadDeviceToken", "DeviceTokenNotForTopic", "TopicDisallowed"}

#: Reasons that are true of every token at once. One of these means stopping,
#: not moving on to the next person: a thousand identical 403s is a thousand
#: requests spent proving the same thing.
_CREDENTIAL = {
    "InvalidProviderToken",
    "MissingProviderToken",
    "BadEnvironmentKeyInToken",
    "BadEnvironmentKeyIdInToken",
    "InvalidProviderTokenPayload",
}

#: Minted once per process and reused. Module state rather than instance state
#: on purpose: two `APNs()` objects in one job must not mint two tokens twenty
#: minutes apart from each other.
_token: tuple[str, float] | None = None


def _key_material() -> str:
    """The PEM, whether the environment holds it or holds a path to it.

    Same rule as the Play service account, and the same reason: a platform
    secret store hands over a string and a mounted volume hands over a path,
    and a second variable saying which is one more thing to get wrong.
    """
    raw = settings().apns_key_p8.strip()
    if "BEGIN" in raw:
        return raw
    path = Path(raw)
    if not path.is_file():
        raise PushUnavailable(
            "ALMA_APNS_KEY_P8 is neither a PEM nor a readable file — it holds "
            f"{raw[:40]!r}. Give it the contents of the .p8, or a path to it."
        )
    return path.read_text()


def provider_token(*, force: bool = False, now: float | None = None) -> str:
    """The `authorization: bearer` value, minted at most as often as allowed.

    `force` is for the one case that justifies an early refresh — Apple
    answering `ExpiredProviderToken` — and it is still refused below the
    twenty-minute floor. A token we minted eight minutes ago that Apple calls
    expired is a clock that disagrees with Apple's, and re-minting into that
    would trade a stuck job for a rate limit and leave the real cause in place.
    """
    global _token
    import jwt

    moment = time.time() if now is None else now
    if _token is not None:
        value, minted = _token
        if not force and moment - minted < _LIFETIME:
            return value
        if force and moment - minted < _REFRESH_FLOOR:
            raise PushUnavailable(
                "APNs called our provider token expired "
                f"{int(moment - minted)}s after it was minted, which is inside "
                "Apple's own twenty-minute refresh floor. Re-minting would earn "
                "429 TooManyProviderTokenUpdates and hide the cause: check this "
                "host's clock."
            )

    config = settings()
    value = jwt.encode(
        {"iss": config.apns_team_id, "iat": int(moment)},
        _key_material(),
        algorithm="ES256",
        headers={"kid": config.apns_key_id},
    )
    _token = (value, moment)
    return value


def _forget_token() -> None:
    """Drop the cached provider token. For tests and for a credential rotation."""
    global _token
    _token = None


class APNs:
    """Apple's half of `transport.Transport`.

    Constructing one validates the credentials, which is what makes a
    misconfigured deployment fail at the job's start rather than at the first
    subscriber. Building the HTTP client is deferred, because a client is a
    connection pool and the boot check is a string comparison.
    """

    platform = "ios"

    def __init__(self) -> None:
        missing = settings().missing_push_credentials("ios")
        if missing:
            raise PushUnavailable(
                "APNs is not configured: " + ", ".join(missing) + " missing. "
                "A push transport that starts without a credential sends "
                "nothing and reports success, which is the failure nobody sees."
            )
        self._clients: dict[str, object] = {}

    def _client(self, environment: str):
        """One HTTP/2 client per environment, reused across sends.

        HTTP/2 is not a preference — APNs speaks nothing else, and one
        connection multiplexes the whole run. A client per notification would
        pay a TLS handshake per person.
        """
        import httpx

        host = HOSTS.get(environment) or HOSTS[settings().apns_environment]
        if host not in self._clients:
            try:
                self._clients[host] = httpx.AsyncClient(
                    base_url=host, http2=True, timeout=10.0
                )
            except ImportError as exc:  # pragma: no cover - depends on the install
                raise PushUnavailable(
                    "APNs speaks HTTP/2 only and the `h2` package is not "
                    "installed. Install the backend with `httpx[http2]`."
                ) from exc
        return self._clients[host]

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()  # type: ignore[attr-defined]
        self._clients.clear()

    def headers(self, token: DeviceToken, push: Push, *, bearer: str) -> dict[str, str]:
        """Every header Apple reads, with the value Alma chose and the reason.

        Separated from `send` so it can be asserted against without a network:
        the difference between `apns-priority: 5` and `10` is invisible in a
        test that mocks the whole request, and it is one of the few decisions
        here that the operating system grades us on.
        """
        headers = {
            "authorization": f"bearer {bearer}",
            "apns-topic": settings().apns_topic,
            # Required on watchOS and recommended everywhere; a wrong value is
            # `400 InvalidPushType`, so it is sent always rather than sometimes.
            "apns-push-type": "alert",
            # 5, not 10. `10` claims immediate delivery, which is a small lie
            # told to an operating system that keeps score — and 5 lets APNs
            # coalesce delivery, which is what a person actually wants from a
            # notification that arrives every morning.
            "apns-priority": "5",
            "apns-id": str(uuid.uuid4()),
        }
        if push.collapse_id:
            headers["apns-collapse-id"] = push.collapse_id[:64]
        if push.expires_at is not None:
            headers["apns-expiration"] = str(int(push.expires_at.timestamp()))
        return headers

    @staticmethod
    def payload(push: Push) -> dict:
        """The body, which carries a key and some words and never a sentence.

        `interruption-level: passive` is the honest level for a daily: it does
        not light the screen and does not break through a Focus.
        `relevance-score` ranks it *inside* the notification summary, which is
        where a daily belongs — above the summary is where the reviews start
        using the word "bullying". Custom keys sit beside `aps`, never inside
        it; anything inside `aps` that Apple does not recognise is a 400.
        """
        # The title is always a key; the body is the written piece's own
        # sentence when there is one, and a key when there is not. Apple
        # resolves `loc-key` against the bundle and takes `body` literally, and
        # sending both would make the payload ambiguous about which wins — so
        # it is one or the other, never a fallback pair.
        # Готовый заголовок вытесняет ключ по тому же правилу «одно из двух»,
        # что и body ниже: ключа пары в замороженном бандле клиента нет, и
        # `title-loc-key` рядом с ним показал бы сырую строку ключа на локскрине.
        alert: dict = (
            {"title": push.title} if push.title else {"title-loc-key": push.title_key}
        )
        if push.body:
            alert["body"] = push.body
        else:
            alert["loc-key"] = push.body_key
            alert["loc-args"] = list(push.args)

        return {
            "aps": {
                "alert": alert,
                "thread-id": push.thread,
                "interruption-level": "passive",
                "relevance-score": 0.6,
                "sound": "default",
            },
            **push.data,
        }

    async def send(self, token: DeviceToken, push: Push) -> Receipt:
        client = self._client(token.environment or settings().apns_environment)
        body = json.dumps(self.payload(push)).encode()

        response = await client.post(  # type: ignore[attr-defined]
            f"/3/device/{token.token}",
            content=body,
            headers=self.headers(token, push, bearer=provider_token()),
        )
        receipt = self.read(response.status_code, response.text)
        if receipt.verdict is Verdict.fatal and receipt.reason == "ExpiredProviderToken":
            # The one refusal worth a second attempt, and exactly one: a token
            # that expired between minting and sending is ordinary, and a loop
            # over the same 403 is not.
            response = await client.post(  # type: ignore[attr-defined]
                f"/3/device/{token.token}",
                content=body,
                headers=self.headers(token, push, bearer=provider_token(force=True)),
            )
            receipt = self.read(response.status_code, response.text)
        return receipt

    @staticmethod
    def read(status: int, body: str) -> Receipt:
        """Apple's answer, in this seam's vocabulary.

        A static method over the two things a response actually is, so that
        every row of `docs/PUSH.md §1.7` can be asserted without a socket. The
        table is the part that has to be right; the HTTP call around it is
        the part that is boring.
        """
        reason = ""
        timestamp: float | None = None
        if body:
            try:
                parsed = json.loads(body)
                reason = str(parsed.get("reason", ""))
                raw = parsed.get("timestamp")
                # Milliseconds, and it is the sort of thing read as seconds
                # once and then debugged for an afternoon: a 2026 timestamp
                # read as seconds lands in 57000 AD, and every 410 would look
                # newer than every registration.
                timestamp = float(raw) / 1000.0 if raw is not None else None
            except (ValueError, TypeError):
                reason = body[:200]

        if status == 200:
            return Receipt(Verdict.sent)
        if status == 410 or reason in _DEAD:
            return Receipt(
                Verdict.dead,
                reason or "Unregistered",
                dead_since=(
                    datetime.fromtimestamp(timestamp, timezone.utc) if timestamp else None
                ),
            )
        if reason in _MISCONFIGURED:
            return Receipt(Verdict.disable, reason, f"HTTP {status}")
        if reason in _CREDENTIAL:
            return Receipt(Verdict.fatal, reason, f"HTTP {status}")
        if reason == "ExpiredProviderToken":
            return Receipt(Verdict.fatal, reason, f"HTTP {status}")
        if status == 429:
            # Both spellings back off. `TooManyProviderTokenUpdates` is our own
            # bug rather than Apple's load, but the response to it is the same
            # and the cache above is what stops it recurring.
            return Receipt(Verdict.retry, reason or "TooManyRequests", f"HTTP {status}")
        if status >= 500:
            return Receipt(Verdict.retry, reason or "ServiceUnavailable", f"HTTP {status}")
        # Everything left is a 400/404/405/413 with a reason we do not
        # recognise, which means the request was built wrong — and it was built
        # wrong for every token, not for this one.
        return Receipt(Verdict.fatal, reason or "BadRequest", f"HTTP {status}")
