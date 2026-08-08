"""Firebase Cloud Messaging, which is the only way to reach an Android phone.

There is no alternative and it is worth being clear about what that costs.
Google Play Services is the notification transport on Android; a plain HTTP
call to Google will not wake an app that is dozing, and no third party can
substitute for it. So `firebase-messaging` becomes a declared dependency of
the Android build, Firebase Installations arrives with it, and two sentences
in `mobile/store/DATA-INVENTORY.md` that currently read as clean stop being
true. That is a disclosure to update, not a reason to look for a workaround.

**iOS deliberately does not go through here.** FCM will happily relay to APNs,
and routing both platforms through one vendor would be the tidier code. It
would also put the Firebase SDK into an iOS binary that today links no
third-party framework at all, hand Google a copy of every notification we
send to an Apple device, and make an Apple outage indistinguishable from a
Google one. `apns.py` talks to Apple directly; that is worth defending.

The access token is an OAuth2 assertion flow — a service-account JWT signed
RS256, exchanged at Google's token endpoint for a bearer good for an hour.
The same caching argument as `apns.provider_token` applies, for a plainer
reason: the exchange is a network round trip, and paying one per notification
would double the cost of the job.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from ..config import settings
from ..db.models import DeviceToken
from .transport import Push, PushUnavailable, Receipt, Verdict

log = logging.getLogger("alma.notify.fcm")

ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"
TOKEN_URL = "https://oauth2.googleapis.com/token"

#: The narrowest scope that can send a message. Deliberately not the broader
#: `cloud-platform`: a credential that can also read the project is a
#: credential whose leak is a larger incident than it had to be.
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

#: Google issues these for an hour. Fifty minutes, for the reason `apns.py`
#: gives — a job that starts just before the boundary should not discover it.
_LIFETIME = 50 * 60

#: The channel the daily posts on, and it must never be the one the renewal
#: notice uses. An Android channel is the unit a person silences, and a shared
#: one would let somebody switch off "you are about to be charged $9.99" by
#: switching off the horoscope. Channel ids are permanent for an install, so
#: this is a decision that is very cheap now and very expensive later.
CHANNEL = "alma.daily"

#: Twelve hours. The counterpart of `apns-expiration`: better absent than late.
TTL_SECONDS = 12 * 60 * 60

_token: tuple[str, float] | None = None


def _service_account() -> dict:
    """The credentials, whether the environment holds JSON or a path to it."""
    raw = settings().fcm_service_account.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    path = Path(raw)
    if not path.is_file():
        raise PushUnavailable(
            "ALMA_FCM_SERVICE_ACCOUNT_JSON is neither JSON nor a readable file. "
            "Give it the contents of the service-account key, or a path to it."
        )
    return json.loads(path.read_text())


async def access_token(*, now: float | None = None) -> str:
    """A bearer good for an hour, cached for fifty minutes."""
    global _token
    import httpx
    import jwt

    moment = time.time() if now is None else now
    if _token is not None and moment - _token[1] < _LIFETIME:
        return _token[0]

    account = _service_account()
    assertion = jwt.encode(
        {
            "iss": account["client_email"],
            "scope": SCOPE,
            "aud": TOKEN_URL,
            "iat": int(moment),
            "exp": int(moment) + 3600,
        },
        account["private_key"],
        algorithm="RS256",
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
    if response.status_code != 200:
        raise PushUnavailable(
            "Google refused the FCM service account "
            f"({response.status_code}): {response.text[:200]}"
        )
    value = response.json()["access_token"]
    _token = (value, moment)
    return value


def _forget_token() -> None:
    global _token
    _token = None


class FCM:
    """Google's half of `transport.Transport`."""

    platform = "android"

    def __init__(self) -> None:
        missing = settings().missing_push_credentials("android")
        if missing:
            raise PushUnavailable(
                "FCM is not configured: " + ", ".join(missing) + " missing. "
                "A push transport that starts without a credential sends "
                "nothing and reports success, which is the failure nobody sees."
            )

    def message(self, token: DeviceToken, push: Push) -> dict:
        """The v1 envelope, with the four fields that are decisions.

        `priority: normal` rather than `high`, because `high` wakes a dozing
        device immediately and that is for a message somebody is waiting for.
        Android's own heuristics penalise an app that claims high priority for
        everything, and a daily is the definition of something that can wait
        for the next maintenance window.

        The `notification` block is not optional here even though a data-only
        message would be more private: the system draws a `notification` block
        when the app is backgrounded, and that is what makes it arrive at all.
        A data-only message is handed to the app's own service and is deferred
        by Doze — a daily that maybe arrives is not a daily.
        """
        ttl = TTL_SECONDS
        if push.expires_at is not None:
            remaining = int(push.expires_at.timestamp() - time.time())
            ttl = max(60, min(TTL_SECONDS, remaining))

        # Same division as APNs: the title resolves in the device's language,
        # the body is the written piece's own sentence when there is one.
        # `body` and `body_loc_key` are mutually exclusive here too — Android
        # prefers the literal and would silently ignore the key, which is a
        # payload that means two things depending on who reads it.
        alert: dict = {
            "channel_id": CHANNEL,
            "title_loc_key": push.title_key,
            "notification_priority": "PRIORITY_DEFAULT",
        }
        if push.body:
            alert["body"] = push.body
        else:
            alert["body_loc_key"] = push.body_key
            alert["body_loc_args"] = list(push.args)

        return {
            "message": {
                "token": token.token,
                "android": {
                    "priority": "normal",
                    "ttl": f"{ttl}s",
                    "collapse_key": push.collapse_id or push.thread,
                    "notification": alert,
                },
                "data": dict(push.data),
            }
        }

    async def send(self, token: DeviceToken, push: Push) -> Receipt:
        import httpx

        bearer = await access_token()
        url = ENDPOINT.format(project=settings().fcm_project_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=self.message(token, push),
                headers={"Authorization": f"Bearer {bearer}"},
            )
        return self.read(response.status_code, response.text)

    @staticmethod
    def read(status: int, body: str) -> Receipt:
        """Google's answer, in this seam's vocabulary.

        FCM puts its own vocabulary in `error.details[].errorCode` and a
        looser one in `error.status`; both are read, because the first is the
        documented one and the second is what actually arrives when the
        request never reached the messaging layer.
        """
        code = ""
        if body:
            try:
                error = json.loads(body).get("error", {})
                code = str(error.get("status", ""))
                for detail in error.get("details", []) or []:
                    if detail.get("errorCode"):
                        code = str(detail["errorCode"])
                        break
            except (ValueError, TypeError, AttributeError):
                code = body[:200]

        if status == 200:
            return Receipt(Verdict.sent)
        if code == "UNREGISTERED" or status == 404:
            # Gone, and unlike Apple's 410 there is no timestamp to reason
            # about — Google does not say when. The row goes.
            return Receipt(Verdict.dead, code or "UNREGISTERED", f"HTTP {status}")
        if code == "SENDER_ID_MISMATCH":
            # A real device registered against a different Firebase project.
            # Ours to fix, and deleting the row would not fix it.
            return Receipt(Verdict.disable, code, f"HTTP {status}")
        if code == "INVALID_ARGUMENT":
            # Ambiguous by design: it is either our payload or their token, and
            # Google will not say which. Treated as a configuration fault
            # rather than a dead token, because the payload here is generated
            # from a template and is the same for everybody — so if it were the
            # payload, this would be failing for every single person, which is
            # visible in a way that one disabled row is not.
            return Receipt(Verdict.disable, code, f"HTTP {status}")
        if code == "THIRD_PARTY_AUTH_ERROR":
            # The APNs credential *inside* Firebase. Cannot happen while iOS
            # goes to Apple directly, and if it ever does, somebody has quietly
            # started routing iOS through here.
            return Receipt(Verdict.fatal, code, f"HTTP {status}")
        if status in (401, 403):
            return Receipt(Verdict.fatal, code or "UNAUTHENTICATED", f"HTTP {status}")
        if status == 429 or code == "QUOTA_EXCEEDED":
            return Receipt(Verdict.retry, code or "QUOTA_EXCEEDED", f"HTTP {status}")
        if status >= 500:
            return Receipt(Verdict.retry, code or "UNAVAILABLE", f"HTTP {status}")
        return Receipt(Verdict.fatal, code or "UNSPECIFIED_ERROR", f"HTTP {status}")
