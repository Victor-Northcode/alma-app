"""Seven consecutive days for one real chart, against the real model.

Everything else about the daily is tested against `ScriptedProvider`, which is
right — a suite that reaches the network is a suite that fails when somebody
else's service does. But a scripted provider cannot tell you whether the
register works, whether the 80–130 word budget is met, whether the past-tense
instruction is obeyed, or whether the piece the notification points at is the
piece the notification describes. Only a real generation can, and until this
script ran nobody had ever seen one.

It writes seven days in a row for one chart, prints what each day produced —
**including the days that produced nothing, which are the majority and the
point** — composes the notification line in English and in German for the days
that produced something, and reads the total back out of the spend ledger
rather than adding up what the calls said they cost.

    .venv/bin/python tools/daily/a_real_week.py [--from 2026-08-07] [--days 7]

Costs real money: roughly two cents for a week.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _load_env() -> None:
    """The suite is sealed from `.env` on purpose. This script is not the suite."""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()
os.environ["ALMA_DATABASE_URL"] = (
    f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/week.db"
)
os.environ.setdefault("ALMA_JWT_SECRET", "a-real-week-not-the-default-secret")

from alma.ai import cost  # noqa: E402
from alma.ai.provider import default_provider  # noqa: E402
from alma.auth import accounts  # noqa: E402
from alma.calc.contract import BirthData  # noqa: E402
from alma.calc.service import chart_for  # noqa: E402
from alma.config import settings  # noqa: E402
from alma.daily import notification, service, storage  # noqa: E402
from alma.db import session as session_module  # noqa: E402
from alma.db.models import Entitlement, Profile, UsageCounter, utcnow  # noqa: E402
from sqlalchemy import select  # noqa: E402

#: Kraków, 1978 — the chart the judges' reproduction used, so the one live
#: failure anybody has actually seen can be looked for in the same sky.
BIRTH = BirthData(
    date=date(1978, 6, 14),
    time="04:20",
    latitude=50.0647,
    longitude=19.9450,
    timezone="Europe/Warsaw",
    place_label="Kraków, Poland",
    name="Anna",
)
ZONE = ZoneInfo("Europe/Warsaw")

RULE = "─" * 78


async def _person(session):
    user = await accounts.create_guest(session)
    session.add(
        Profile(
            user_id=user.id, is_self=True,
            birth_date=BIRTH.date, birth_time=BIRTH.time,
            latitude=BIRTH.latitude, longitude=BIRTH.longitude,
            timezone=BIRTH.timezone, place_label=BIRTH.place_label,
        )
    )
    session.add(
        Entitlement(
            user_id=user.id, system="*", kind="monthly", scope="live",
            expires_at=utcnow() + timedelta(days=30),
        )
    )
    await session.flush()
    profile = (
        await session.execute(select(Profile).where(Profile.user_id == user.id))
    ).scalar_one()
    return user, profile


async def run(start: date, days: int) -> None:
    await session_module.create_all()
    provider = default_provider()
    model = settings().model_mid
    chart = chart_for(BIRTH)

    print(RULE)
    print(f"A REAL WEEK — {BIRTH.place_label}, {BIRTH.date} {BIRTH.time}")
    print(f"{start} … {start + timedelta(days=days - 1)}  ·  model {model}")
    print(RULE)

    # One scan, a year ahead, exactly as §6.2 says to store it.
    hits = service.hits_for(
        BIRTH, start=datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    )
    print(f"scanned {len(hits)} contacts for the year ahead\n")

    written = 0
    async with session_module.session_scope() as session:
        user, profile = await _person(session)

        for offset in range(days):
            day = start + timedelta(days=offset)
            decision = await service.decide_for(
                session, user, hits=hits, on=day, zone=ZONE
            )

            print(f"{day}  {day.strftime('%A'):<10}", end="")
            if decision.occasion is None:
                print(f"—  nothing.  ({decision.reason})")
                continue

            occasion = decision.occasion
            if not decision.push:
                print(
                    f"·  {occasion.kernel} in the sky, no notification "
                    f"({decision.reason})"
                )
                # Still not written: nothing pulls it on a day with no push,
                # and writing one here would be spending money to prove a
                # point about a day nobody asked about.
                continue

            # Claim before writing, exactly as `notify/daily.py` does — and
            # not only for fidelity. `decide_for` reads the three-day gap and
            # both caps off these rows, so a script that never claimed would
            # print a week that ignores its own cadence rule.
            await service.claim_push(session, user, on=day)

            piece = await service.write_for(
                session, user,
                occasion=occasion, birth=BIRTH, profile_id=profile.id,
                provider=provider, model=model, tier="subscriber",
                locale="en", chart=chart,
            )
            await session.commit()
            written += 1

            body = piece.body
            paragraphs = body.get("body") or []
            words_used = sum(len(p.split()) for p in paragraphs)
            print(f"PUSH  {occasion.kernel}  ({decision.reason})")
            print(f"           weight {occasion.hit.weight:.2f} · "
                  f"{occasion.kind} at {occasion.at:%H:%M} · orb {occasion.orb:.2f}° · "
                  f"{len(paragraphs)} para · {words_used} words · "
                  f"attempt {body.get('attempts')}")
            print(f"           cited: {' | '.join(body.get('cited_factors') or [])}")
            print(f"           advice: {body.get('advice')!r}")
            print()
            print(f"           TEASER  {body.get('teaser')}")
            for para in paragraphs:
                print(f"           {para}")
            print()
            for locale in ("en", "de"):
                line = notification.line(occasion, locale=locale, read_at=piece.hour)
                print(f"           [{locale}] {line}")
            print()

    print(RULE)
    async with session_module.session_scope() as session:
        rows = (
            await session.execute(
                select(UsageCounter).where(UsageCounter.metric == cost.SPEND_METRIC)
            )
        ).scalars().all()
        spent = sum(r.amount or 0.0 for r in rows)
        stored_rows = (
            await session.execute(
                select(UsageCounter).where(UsageCounter.metric == storage.PUSH_METRIC)
            )
        ).scalars().all()

    print(f"{days} days · {written} pieces written · "
          f"{len(stored_rows)} push slots claimed")
    print(f"FROM THE LEDGER: {spent:.4f} cents total"
          + (f" · {spent / written:.4f} cents a piece" if written else ""))
    print(f"a year at this rate: ${spent / days * 365 / 100:.2f} against "
          f"$8.99 net US monthly revenue × 12")
    print(RULE)
    await session_module.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start", default=date.today().isoformat())
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    asyncio.run(run(date.fromisoformat(args.start), args.days))


if __name__ == "__main__":
    main()
