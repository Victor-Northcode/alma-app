"""The IANA zone database must be present regardless of the OS image.

Every timezone check in the product — the `timezone` field of a birth
(`schemas._known_timezone`), the `X-Alma-Timezone` header
(`deps.device_timezone`) — goes through `zoneinfo.available_timezones()`, which
reads the system `/usr/share/zoneinfo`. The runtime image is
`python:3.12-slim`, which has no such directory, so unless the `tzdata` PyPI
package is installed the set is *empty* and every zone, even "UTC", is
rejected 422 — no birth can be saved and the whole product is down.

Found 2026-08-20 in a clean venv (and on this Windows host, which also lacks a
system zone database): `available_timezones()` returned 0 until `tzdata` was
added to `pyproject.toml`. This test fails exactly the way production did —
the common zones simply are not known.
"""

from __future__ import annotations

from zoneinfo import available_timezones

from alma.geo import is_known_timezone


def test_the_zone_database_is_shipped_not_borrowed_from_the_host():
    zones = available_timezones()
    assert zones, (
        "available_timezones() is empty — no system zoneinfo and no tzdata "
        "package. On python:3.12-slim this means every birth timezone is "
        "rejected 422 and nobody can save a birth."
    )


def test_the_zones_the_product_actually_uses_are_known():
    for zone in ("UTC", "Europe/London", "America/New_York", "Europe/Berlin",
                 "Asia/Tokyo", "America/Sao_Paulo"):
        assert is_known_timezone(zone), f"{zone!r} is not known — see BUG-001"
