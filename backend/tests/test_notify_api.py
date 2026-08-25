"""Registering a phone over HTTP, and the one tap that turns the daily off.

Two of these tests are about a promise rather than a feature. Apple's
guideline 4.5.4 requires an in-app way to stop receiving notifications, and
`docs/THE-DAILY.md §5` makes the stronger claim that it must be one tap from
inside the notification itself — so Off has to work first time, from a route
that does not need a sign-in, and it has to delete the row rather than set a
flag. And a switch that accepts a preference nothing will ever honour is the
one behaviour that file names as indefensible: the free user is told what the
answer is, not left to wonder for a month.
"""

from __future__ import annotations

from datetime import timedelta

from conftest import read_async

APPLE = "a" * 64


def _register(api, headers, **overrides) -> dict:
    body = {"platform": "ios", "token": APPLE, "environment": "sandbox"}
    body.update(overrides)
    return api.post("/v1/notifications/devices", json=body, headers=headers)


async def _subscribe(user_id: str) -> None:
    from alma.auth import entitlements
    from alma.db import session_scope
    from alma.db.models import User

    async with session_scope() as session:
        user = await session.get(User, user_id)
        await entitlements.grant(
            session,
            user,
            system="*",
            kind="monthly",
            scope="live",
            duration=timedelta(days=30),
        )


def _me(api, headers) -> str:
    return api.get("/v1/account", headers=headers).json()["id"]


def test_a_device_registers_and_re_registering_is_the_same_device(api, auth_headers):
    assert _register(api, auth_headers).status_code == 201
    assert _register(api, auth_headers, timezone="America/Toronto").status_code == 201
    assert len(api.get("/v1/notifications", headers=auth_headers).json()["devices"]) == 1


def test_a_guest_may_register_because_a_guest_may_also_be_paying(api, auth_headers):
    """`docs/PUSH.md §3` asked for `require_account` and it is wrong for this product.

    A guest is a real account here with a row and an id, guests buy, and
    demanding a sign-in before somebody may receive the thing they are paying
    for would lock out most of the paying population to solve nothing.
    Entitlement is checked when the notification is sent.
    """
    assert api.get("/v1/account", headers=auth_headers).json()["is_guest"]
    assert _register(api, auth_headers).status_code == 201


def test_the_device_timezone_may_arrive_in_a_header(api, auth_headers):
    """Until `deps.py` grows the dependency, the registration call carries it.

    That covers the case that matters, because the client re-registers on every
    launch — so a person who lands somewhere else is right within a day.
    """
    headers = {**auth_headers, "X-Alma-Timezone": "Asia/Tokyo"}
    assert _register(api, headers).status_code == 201
    assert api.get("/v1/notifications", headers=auth_headers).json()["timezone"] == "Asia/Tokyo"


def test_an_unrecognised_timezone_is_ignored_rather_than_refused(api, auth_headers):
    """Same rule as the country header: a stale tzdata costs the optimisation, not the install."""
    headers = {**auth_headers, "X-Alma-Timezone": "Mars/Olympus"}
    assert _register(api, headers).status_code == 201
    body = api.get("/v1/notifications", headers=auth_headers).json()
    assert body["timezone"] is None
    assert body["timezone_source"] == "birth"


def test_a_token_that_is_not_a_token_is_refused(api, auth_headers):
    assert _register(api, auth_headers, token="short").status_code == 422


def test_the_settings_say_where_the_clock_came_from(api, auth_headers):
    """The field that makes the override discoverable to the person who needs it."""
    _register(api, auth_headers, timezone="Europe/Warsaw")
    assert api.get("/v1/notifications", headers=auth_headers).json()["timezone_source"] == "device"

    api.patch("/v1/notifications", json={"timezone": "Europe/Lisbon"}, headers=auth_headers)
    body = api.get("/v1/notifications", headers=auth_headers).json()
    assert (body["timezone"], body["timezone_source"]) == ("Europe/Lisbon", "chosen")


def test_a_free_user_is_off_by_default_and_told_why_when_they_try(api, auth_headers):
    body = api.get("/v1/notifications", headers=auth_headers).json()
    assert body["daily"] == "off"
    assert body["entitled"] is False
    assert body["chosen"] is False

    refused = api.patch(
        "/v1/notifications", json={"daily": "occasionally"}, headers=auth_headers
    )
    assert refused.status_code == 402
    assert refused.json()["detail"]["error"] == "locked"


def test_a_subscriber_is_occasionally_by_default(api, auth_headers):
    read_async(lambda: _subscribe(_me(api, auth_headers)))
    body = api.get("/v1/notifications", headers=auth_headers).json()
    assert body["daily"] == "occasionally"
    assert body["entitled"] is True


def test_off_deletes_the_tokens_rather_than_setting_a_flag(api, auth_headers):
    """The simplest possible proof that off means off: there is nothing to send to."""
    read_async(lambda: _subscribe(_me(api, auth_headers)))
    _register(api, auth_headers)
    assert api.get("/v1/notifications", headers=auth_headers).json()["devices"]

    turned_off = api.patch("/v1/notifications", json={"daily": "off"}, headers=auth_headers)
    assert turned_off.status_code == 200
    assert turned_off.json()["daily"] == "off"
    assert turned_off.json()["devices"] == []


def test_turning_it_off_survives_a_later_subscription(api, auth_headers):
    """A stored choice always wins, including the one a column default gets wrong."""
    api.patch("/v1/notifications", json={"daily": "off"}, headers=auth_headers)
    read_async(lambda: _subscribe(_me(api, auth_headers)))
    assert api.get("/v1/notifications", headers=auth_headers).json()["daily"] == "off"


def test_the_chosen_hour_is_honoured_exactly_any_of_the_24(api, auth_headers):
    """Выбранный час отдаётся как есть — владелец, 25.08.2026: «любое время».

    До этого дня 3 и 6 тихо превращались в 8, и человек читал это как
    «настройка не работает». Теперь зажат только диапазон типа (0–23).
    """
    for hour in (3, 6, 9, 0, 23):
        api.patch("/v1/notifications", json={"hour": hour}, headers=auth_headers)
        assert api.get("/v1/notifications", headers=auth_headers).json()["hour"] == hour
    assert api.patch(
        "/v1/notifications", json={"hour": 24}, headers=auth_headers
    ).status_code == 422


def test_quiet_hours_are_gone_from_the_payload(api, auth_headers):
    """Поле, которое ничего не ограничивает, читалось бы как ограничение."""
    body = api.get("/v1/notifications", headers=auth_headers).json()
    assert "quiet_hours" not in body
    assert api.patch(
        "/v1/notifications", json={"quiet_hours": [1, 2]}, headers=auth_headers
    ).status_code == 422


def test_a_device_can_be_forgotten_on_its_own(api, auth_headers):
    _register(api, auth_headers)
    gone = api.post(
        "/v1/notifications/devices/delete",
        json={"platform": "ios", "token": APPLE},
        headers=auth_headers,
    )
    assert gone.json() == {"removed": True}
    assert api.get("/v1/notifications", headers=auth_headers).json()["devices"] == []


def test_somebody_elses_token_cannot_be_silenced(api, auth_headers):
    """A device token turns up in crash logs; it must not be a way to switch somebody off."""
    _register(api, auth_headers)
    other = api.get("/v1/auth/session").json()["token"]
    stolen = api.post(
        "/v1/notifications/devices/delete",
        json={"platform": "ios", "token": APPLE},
        headers={"Authorization": f"Bearer {other}"},
    )
    assert stolen.json() == {"removed": False}
    assert api.get("/v1/notifications", headers=auth_headers).json()["devices"]
