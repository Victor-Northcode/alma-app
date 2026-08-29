"""Админка владельца: выдать подписку по почте, посмотреть человека, отозвать.

Появилась 25.08.2026 по слову владельца: «веб-админка, чтоб можно было
выдавать по почте подписки». До неё каждый грант делался руками в базе по
ssh — так был выдан и его собственный (`source='owner_grant'`), и это ровно
тот процесс, который ломается в день, когда владелец захочет подарить месяц
другу с телефона.

**Пароль в конфиге не живёт — только его солёный scrypt-хэш** (`auth/admin_password`).
`.env` читают глаза, которым пароль не нужен: деплой, бэкап, тикет. Хэш пускает
внутрь ровно так же, а его утечка паролем не является — но лишь пока хэш дорого
обратить: голый SHA-256 (как было до 29.08.2026) перебирается по словарю за
минуты, поэтому теперь это солёный медленный KDF. Сравнение — `hmac.compare_digest`
внутри `verify`: обычное `==` отвечает быстрее на почти верный хэш, и это измеримо.

**Сессия — тот же JWT, что у приложения, с меткой `adm`.** Своя криптография
для одной страницы — это вторая копия того, что уже проверено; метка же
обязательна: токен обычного пользователя не должен открывать админку, каким
бы свежим он ни был. Сутки жизни: владелец заходит с телефона между делами,
и логин на каждый чих — это админка, которой перестают пользоваться.

**Отзывается только выданное рукой.** Магазинные права живут по магазину:
отозвать здесь оплаченную подписку значило бы разойтись с деньгами, которые
Apple продолжит списывать. Кнопка отзыва у таких строк не рисуется, а ручка
отвечает отказом даже прямому запросу.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ...auth import admin_password, tokens
from ...config import settings
from ...db.models import DeviceToken, Entitlement, User, as_utc, utcnow
from ..deps import SessionDep, request_source, window

log = logging.getLogger("alma.admin")

router = APIRouter(prefix="/admin", include_in_schema=False)

#: Пять попыток входа в час с одного источника. Против перебора пароля этого
#: достаточно с запасом: хэш не в сети, а окно делает подбор арифметикой лет.
LOGIN_TRIES_PER_HOUR = 5

#: Сколько живёт админ-сессия. Сутки — см. докстринг модуля.
SESSION_DAYS = 1

#: «Навсегда» гранта — та же дата, что у гранта владельца: далеко за горизонт
#: продукта и при этом честная строка в колонке, а не NULL с особым смыслом.
FOREVER = datetime(2099, 1, 1, tzinfo=timezone.utc)


def _configured() -> str:
    digest = settings().admin_password_hash.strip().lower()
    if not digest:
        # Без хэша админки не существует: страница отвечает, но вход закрыт
        # наглухо — это честнее тихой дыры с дефолтным паролем.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin is not configured on this deployment",
        )
    return digest


async def _admin(authorization: str | None = Header(default=None)) -> None:
    bearer = tokens.bearer(authorization)
    if bearer is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="sign in first")
    try:
        payload = tokens.read(bearer)
    except tokens.InvalidToken:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="the session has expired"
        ) from None
    # Метка — а не просто валидный токен: токен приложения сюда не пускает.
    if payload.get("adm") is not True:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not an admin session")


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


@router.post("/api/login")
async def login(payload: LoginIn, request: Request, session: SessionDep) -> dict:
    digest = _configured()
    if not await window(
        request, "admin_login", limit=LOGIN_TRIES_PER_HOUR, seconds=3600
    ).hit(session, request_source(request)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many attempts — try again in an hour",
        )
    # Цена попытки необратима тем же приёмом, что у кода из письма: отказ
    # ниже откатил бы транзакцию вместе со счётчиком, и перебор был бы
    # бесплатным (см. email-code/consume, где это поймал тест).
    await session.commit()

    # Солёный медленный scrypt, а не голый SHA-256 (BUG-005). Старый формат
    # (64 hex-символа без `scrypt$`) — не крэш, а «этот деплой надо
    # перенастроить»: `verify` вернёт `False`, а мы один раз скажем, чем именно.
    if not admin_password.looks_like_scrypt(digest):
        log.error(
            "ALMA_ADMIN_PASSWORD_HASH is in the legacy unsalted-SHA-256 format; "
            "admin login is disabled until it is regenerated with "
            "`python -m tools.admin_password`"
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="wrong password")
    if not admin_password.verify(payload.password, digest):
        log.warning("admin login refused from %s", request_source(request))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="wrong password")

    log.info("admin signed in from %s", request_source(request))
    return {
        "token": tokens.issue("admin", days=SESSION_DAYS, extra={"adm": True}),
        "expires_in_hours": SESSION_DAYS * 24,
    }


def _entitlement_row(e: Entitlement) -> dict:
    now = datetime.now(timezone.utc)
    expires = as_utc(e.expires_at) if e.expires_at else None
    return {
        "id": e.id,
        "system": e.system,
        "kind": e.kind,
        "source": e.source,
        "granted_at": as_utc(e.granted_at).isoformat(),
        "expires_at": expires.isoformat() if expires else None,
        "revoked_at": as_utc(e.revoked_at).isoformat() if e.revoked_at else None,
        "active": e.revoked_at is None and (expires is None or expires > now),
        "amount_cents": e.amount_cents,
        "currency": e.currency,
        # Отзывной только грант руки — см. докстринг модуля.
        "revocable": e.source == "owner_grant" and e.revoked_at is None,
    }


async def _user_card(session, user: User) -> dict:
    rows = (
        await session.execute(
            select(Entitlement)
            .where(Entitlement.user_id == user.id)
            .order_by(Entitlement.granted_at.desc())
        )
    ).scalars().all()
    devices = (
        await session.execute(
            select(func.count()).select_from(DeviceToken).where(
                DeviceToken.user_id == user.id
            )
        )
    ).scalar_one()
    return {
        "user_id": user.id,
        "email": user.email,
        "provider": user.provider,
        "display_name": user.display_name,
        "locale": user.locale,
        "created_at": as_utc(user.created_at).isoformat(),
        "last_seen_at": as_utc(user.last_seen_at).isoformat(),
        "devices": devices,
        "entitlements": [_entitlement_row(e) for e in rows],
    }


@router.get("/api/user")
async def find_user(
    email: str, session: SessionDep, _: None = Depends(_admin)
) -> dict:
    _configured()
    normalised = email.strip().lower()
    user = (
        await session.execute(select(User).where(func.lower(User.email) == normalised))
    ).scalar_one_or_none()
    if user is None:
        return {"found": False, "email": normalised}
    return {"found": True, **await _user_card(session, user)}


class GrantIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    #: Месяцы; null — навсегда.
    months: int | None = Field(default=1, ge=1, le=120)


@router.post("/api/grant")
async def grant(
    payload: GrantIn, session: SessionDep, _: None = Depends(_admin)
) -> dict:
    _configured()
    normalised = payload.email.strip().lower()
    if "@" not in normalised or "." not in normalised.split("@")[-1]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="that is not an email")

    user = (
        await session.execute(select(User).where(func.lower(User.email) == normalised))
    ).scalar_one_or_none()
    created = False
    if user is None:
        # Аккаунта ещё нет — он создаётся прямо здесь, привязанный к почте.
        # Человек, вошедший этой почтой любой из трёх дверей, попадёт ровно в
        # эту строку (`accounts.by_email`) и найдёт подарок ждущим.
        user = User(email=normalised, provider="email")
        session.add(user)
        await session.flush()
        created = True

    now = datetime.now(timezone.utc)
    expires = (
        FOREVER if payload.months is None else now + timedelta(days=31 * payload.months)
    )
    session.add(
        Entitlement(
            user_id=user.id,
            system="*",
            kind="monthly",
            granted_at=now,
            expires_at=expires,
            source="owner_grant",
            amount_cents=0,
            currency="USD",
            status="active",
        )
    )
    await session.flush()
    log.info(
        "admin grant: %s until %s (account %s)",
        normalised,
        "forever" if payload.months is None else expires.date().isoformat(),
        "created" if created else "existing",
    )
    return {"created_account": created, **await _user_card(session, user)}


class RevokeIn(BaseModel):
    entitlement_id: str = Field(min_length=1, max_length=64)


@router.post("/api/revoke")
async def revoke(
    payload: RevokeIn, session: SessionDep, _: None = Depends(_admin)
) -> dict:
    _configured()
    row = (
        await session.execute(
            select(Entitlement).where(Entitlement.id == payload.entitlement_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no such grant")
    if row.source != "owner_grant":
        # Магазинную подписку здесь не трогают — деньги живут у магазина.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="only owner grants can be revoked here — store money lives at the store",
        )
    if row.revoked_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="already revoked")
    row.revoked_at = utcnow()
    await session.flush()
    user = (
        await session.execute(select(User).where(User.id == row.user_id))
    ).scalar_one()
    log.info("admin revoke: grant %s of %s", row.id, user.email)
    return await _user_card(session, user)


@router.get("/api/overview")
async def overview(session: SessionDep, _: None = Depends(_admin)) -> dict:
    _configured()
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)

    async def one(query) -> int:
        return (await session.execute(query)).scalar_one()

    users_total = await one(select(func.count()).select_from(User))
    users_today = await one(
        select(func.count()).select_from(User).where(User.created_at >= day_ago)
    )
    with_email = await one(
        select(func.count()).select_from(User).where(User.email.is_not(None))
    )
    active_subs = await one(
        select(func.count()).select_from(Entitlement).where(
            Entitlement.kind == "monthly",
            Entitlement.revoked_at.is_(None),
            Entitlement.expires_at > now,
            Entitlement.source != "owner_grant",
        )
    )
    grants = await one(
        select(func.count()).select_from(Entitlement).where(
            Entitlement.source == "owner_grant",
            Entitlement.revoked_at.is_(None),
            Entitlement.expires_at > now,
        )
    )
    paid_rows = (
        await session.execute(
            select(Entitlement.currency, func.sum(Entitlement.amount_cents))
            .where(Entitlement.amount_cents > 0)
            .group_by(Entitlement.currency)
        )
    ).all()
    devices = await one(select(func.count()).select_from(DeviceToken))
    return {
        "users_total": users_total,
        "users_today": users_today,
        "with_email": with_email,
        # Гость — отдельным числом, а не вычитанием в голове. Сервер заводит
        # аккаунт на каждый первый визит, включая краулеров сайта, и «156
        # аккаунтов» без этой строки читалось выдумкой рядом с четырьмя
        # настоящими почтами (владелец, 27.08.2026: «чтоб были настоящие
        # данные»). Настоящие — это когда видно, из чего число состоит.
        "guests": users_total - with_email,
        "active_subscriptions": active_subs,
        "owner_grants": grants,
        "revenue": [
            {"currency": currency, "cents": int(cents or 0)}
            for currency, cents in paid_rows
        ],
        "devices": devices,
    }


#: Сколько строк несут живые ленты. Двадцать — экран телефона с запасом;
#: история глубже — вопрос к базе напрямую, а не к странице.
RECENT = 20


@router.get("/api/recent")
async def recent(session: SessionDep, _: None = Depends(_admin)) -> dict:
    """Последние права — как они лежат в базе.

    Лента, а не отчёт: владелец открывает админку посмотреть «что происходит»,
    и до этой ручки ответ состоял из семи чисел. Ленты аккаунтов здесь больше
    нет: она была из одних гостей («нахера мне гостей смотреть» — владелец,
    27.08.2026), люди живут во вкладке с пагинацией (`/api/users`).
    """
    _configured()
    rows = (
        await session.execute(
            select(Entitlement, User.email)
            .join(User, User.id == Entitlement.user_id)
            .order_by(Entitlement.granted_at.desc())
            .limit(RECENT)
        )
    ).all()
    return {
        "entitlements": [
            {**_entitlement_row(e), "email": email} for e, email in rows
        ],
    }


@router.get("/api/users")
async def users(
    session: SessionDep,
    _: None = Depends(_admin),
    page: int = 1,
    q: str = "",
    guests: bool = False,
) -> dict:
    """Люди — страницами, живые первыми, гости выключены по умолчанию.

    Гость — это визит, а не человек: почты нет, покупок нет, смотреть не на
    что, а в ленте их было двадцать на одного живого. Кто хочет полную
    картину — `guests=true`. Порядок по последнему визиту: владелец смотрит
    «кто пользуется», а не архив регистраций. `q` ищет по почте и имени.
    """
    _configured()
    page = max(1, page)
    where = []
    if not guests:
        where.append(User.email.is_not(None))
    needle = q.strip().lower()
    if needle:
        like = f"%{needle}%"
        where.append(
            func.lower(func.coalesce(User.email, "")).like(like)
            | func.lower(func.coalesce(User.display_name, "")).like(like)
        )
    total = (
        await session.execute(select(func.count()).select_from(User).where(*where))
    ).scalar_one()
    pages = max(1, -(-total // RECENT))
    page = min(page, pages)
    devices = (
        select(func.count())
        .select_from(DeviceToken)
        .where(DeviceToken.user_id == User.id)
        .scalar_subquery()
    )
    now = datetime.now(timezone.utc)
    rights = (
        select(func.count())
        .select_from(Entitlement)
        .where(
            Entitlement.user_id == User.id,
            Entitlement.revoked_at.is_(None),
            Entitlement.expires_at > now,
        )
        .scalar_subquery()
    )
    # Счёт покупок, а не сумма: суммы в разных валютах не складываются в одно
    # честное число, а «покупок: 2» честно всегда.
    paid = (
        select(func.count())
        .select_from(Entitlement)
        .where(Entitlement.user_id == User.id, Entitlement.amount_cents > 0)
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(User, devices, rights, paid)
            .where(*where)
            .order_by(User.last_seen_at.desc())
            .offset((page - 1) * RECENT)
            .limit(RECENT)
        )
    ).all()
    return {
        "page": page,
        "pages": pages,
        "total": total,
        "rows": [
            {
                "email": u.email,
                "provider": u.provider,
                "display_name": u.display_name,
                "locale": u.locale,
                "created_at": as_utc(u.created_at).isoformat(),
                "last_seen_at": as_utc(u.last_seen_at).isoformat(),
                "devices": int(d),
                "active_rights": int(r),
                "paid_count": int(p),
            }
            for u, d, r, p in rows
        ],
    }


@router.get("/api/revenue")
async def revenue(
    session: SessionDep, _: None = Depends(_admin), page: int = 1
) -> dict:
    """Прибыль: итоги по валютам, последние двенадцать месяцев, покупки страницами.

    Помесячная свёртка считается в Python по строкам года, а не SQL-функцией
    даты: `date_trunc` есть у Postgres и нет у SQLite, на котором идут тесты,
    а покупок за год меньше, чем строк на одной странице этой же ленты.
    """
    _configured()
    page = max(1, page)
    paid = Entitlement.amount_cents > 0
    totals = (
        await session.execute(
            select(
                Entitlement.currency,
                func.sum(Entitlement.amount_cents),
                func.count(),
            )
            .where(paid)
            .group_by(Entitlement.currency)
        )
    ).all()

    year_ago = datetime.now(timezone.utc) - timedelta(days=366)
    year_rows = (
        await session.execute(
            select(Entitlement.granted_at, Entitlement.currency, Entitlement.amount_cents)
            .where(paid, Entitlement.granted_at >= year_ago)
        )
    ).all()
    months: dict[tuple[str, str], dict] = {}
    for granted_at, currency, cents in year_rows:
        key = (as_utc(granted_at).strftime("%Y-%m"), currency)
        bucket = months.setdefault(
            key, {"month": key[0], "currency": currency, "cents": 0, "count": 0}
        )
        bucket["cents"] += cents
        bucket["count"] += 1

    total = (
        await session.execute(select(func.count()).select_from(Entitlement).where(paid))
    ).scalar_one()
    pages = max(1, -(-total // RECENT))
    page = min(page, pages)
    purchases = (
        await session.execute(
            select(Entitlement, User.email)
            .join(User, User.id == Entitlement.user_id)
            .where(paid)
            .order_by(Entitlement.granted_at.desc())
            .offset((page - 1) * RECENT)
            .limit(RECENT)
        )
    ).all()
    return {
        "totals": [
            {"currency": currency, "cents": int(cents or 0), "count": int(count)}
            for currency, cents, count in totals
        ],
        "months": sorted(
            months.values(), key=lambda m: (m["month"], m["currency"]), reverse=True
        ),
        "purchases": {
            "page": page,
            "pages": pages,
            "total": total,
            "rows": [
                {**_entitlement_row(e), "email": email} for e, email in purchases
            ],
        },
    }


#: Страница. Одним файлом и без сборки: админка — инструмент, а не продукт,
#: и её единственный клиент — браузер владельца. Ночь и золото — те же, что в
#: приложении: инструмент семьи узнаётся семьёй.
PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Alma · Админка</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;1,400&family=Golos+Text:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root { --night:#0A0D1C; --night2:#101636; --gold:#C9AE6B; --golddeep:#A8873C;
          --goldhi:#E4D3A2; --star:#F6E7BC; --body:#EDE7DA; --ink:#F6F1E4;
          --muted:rgba(237,231,218,.62); --line:rgba(237,231,218,.10);
          --linegold:rgba(201,174,107,.30); --bad:#E0917F; --ok:#8FBF9A;
          --card:rgba(10,13,28,.55); }
  * { box-sizing:border-box; margin:0; }
  html { color-scheme:dark; }
  body { min-height:100vh; color:var(--body);
         font:15px/1.55 'Golos Text', system-ui, sans-serif;
         background:
           radial-gradient(1.4px 1.4px at 22% 12%, rgba(246,231,188,.7), transparent 50%),
           radial-gradient(1.1px 1.1px at 74% 20%, rgba(246,231,188,.5), transparent 50%),
           radial-gradient(1px 1px at 44% 40%, rgba(246,231,188,.32), transparent 50%),
           radial-gradient(1.2px 1.2px at 84% 66%, rgba(246,231,188,.3), transparent 50%),
           radial-gradient(1px 1px at 12% 78%, rgba(246,231,188,.28), transparent 50%),
           radial-gradient(120% 60% at 50% -8%, rgba(58,52,132,.55), rgba(30,58,150,.12) 45%, transparent 65%),
           linear-gradient(180deg, #0A0D1C 0%, #090C1A 55%, #0d1430 130%);
         background-attachment:fixed; }
  .wrap { max-width:860px; margin:0 auto; padding:34px 20px 90px; }

  .mark { display:flex; align-items:center; gap:12px; justify-content:space-between; }
  .mark .word { font:26px 'Playfair Display', Georgia, serif; letter-spacing:.34em;
                color:var(--goldhi); }
  .mark .word i { font-style:normal; color:var(--gold); margin-right:10px; }
  .sub { font-size:11px; letter-spacing:.28em; color:var(--muted); text-transform:uppercase;
         margin-top:4px; }

  h2 { font-size:11.5px; letter-spacing:.22em; text-transform:uppercase;
       color:var(--golddeep); margin:30px 0 0; font-weight:600; }
  .rule { height:1px; margin:8px 0 0;
          background:linear-gradient(90deg, transparent, rgba(201,174,107,.34), transparent); }

  input, button, select { font:inherit; }
  input { width:100%; background:rgba(13,16,28,.85); border:1px solid var(--line);
          border-radius:24px; color:var(--ink); padding:12px 20px; outline:none;
          transition:border-color .18s, background .18s; }
  input::placeholder { color:rgba(237,231,218,.4); }
  input:focus { border-color:rgba(201,174,107,.8); background:rgba(13,16,28,.4); }

  button { background:none; border:1px solid rgba(201,174,107,.55); color:var(--goldhi);
           border-radius:24px; padding:11px 22px; cursor:pointer; letter-spacing:.05em;
           transition:background .18s, border-color .18s, opacity .18s; }
  button:hover { background:rgba(201,174,107,.13); border-color:var(--gold); }
  button:disabled { opacity:.35; cursor:default; background:none; }
  button.primary { background:linear-gradient(180deg, #1A1626, #0C0A14);
                   border-color:var(--golddeep);
                   box-shadow:0 0 20px rgba(201,174,107,.16); }
  button.ghost { border-color:var(--line); color:var(--muted); }
  button.bad { border-color:rgba(224,145,127,.55); color:var(--bad); }
  button.bad:hover { background:rgba(224,145,127,.1); border-color:var(--bad); }
  button.small { padding:8px 16px; font-size:13.5px; }

  .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }

  .tabs { display:flex; gap:8px; margin-top:26px; }
  .tabs button { border-color:var(--line); color:var(--muted); padding:9px 20px; }
  .tabs button.on { border-color:var(--golddeep); color:var(--goldhi);
                    background:rgba(201,174,107,.1); }

  .panel { border:1px solid var(--linegold); border-radius:18px; padding:22px 24px;
           background:linear-gradient(180deg, rgba(10,13,28,.88), rgba(7,10,22,.97));
           box-shadow:0 18px 50px rgba(4,6,14,.5); }

  #login { min-height:86vh; display:flex; align-items:center; justify-content:center; }
  #login .panel { width:min(400px, 92vw); text-align:center; padding:40px 32px 30px; }
  #login .star { font-size:30px; color:var(--gold);
                 text-shadow:0 0 22px rgba(246,231,188,.55); }
  #login .word { font:24px 'Playfair Display', Georgia, serif; letter-spacing:.4em;
                 color:var(--goldhi); margin:12px 0 2px; text-indent:.4em; }
  #login input { text-align:center; margin:22px 0 12px; }
  #login button { width:100%; }

  .cards { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr));
           gap:10px; margin-top:12px; }
  .card { border:1px solid var(--line); border-radius:16px; padding:15px 17px 13px;
          background:var(--card); }
  .card b { display:block; font:24px 'Playfair Display', Georgia, serif;
            color:var(--goldhi); font-weight:400; }
  .card span { font-size:11.5px; color:var(--muted); letter-spacing:.05em; }

  .facts { display:grid; grid-template-columns:auto 1fr; gap:7px 18px;
           font-size:14.5px; margin-top:4px; }
  .facts .k { color:var(--muted); }
  .chip { display:inline-block; border:1px solid var(--linegold); border-radius:12px;
          padding:2px 11px; font-size:12.5px; color:var(--goldhi); margin:0 6px 4px 0; }

  .ent { display:flex; gap:14px; align-items:center; justify-content:space-between;
         flex-wrap:wrap; border:1px solid var(--line); border-radius:16px;
         padding:12px 17px; margin-top:10px; background:var(--card); }
  .ent.click { cursor:pointer; transition:border-color .15s; }
  .ent.click:hover { border-color:var(--linegold); }
  .ent .what b { font-weight:600; color:var(--ink); }
  .ent .what span { display:block; font-size:12.5px; color:var(--muted); }
  .pill { border-radius:12px; padding:3px 12px; font-size:12.5px; white-space:nowrap; }
  .pill.on  { color:var(--ok);   border:1px solid rgba(143,191,154,.4); }
  .pill.off { color:var(--muted); border:1px solid var(--line); }
  .pill.rev { color:var(--bad);  border:1px solid rgba(224,145,127,.4); }
  .pill.gold { color:var(--goldhi); border:1px solid var(--linegold); }

  table { width:100%; border-collapse:collapse; margin-top:12px; font-size:14px; }
  th { text-align:left; font-size:11px; letter-spacing:.14em; text-transform:uppercase;
       color:var(--muted); font-weight:500; padding:6px; }
  td { padding:9px 6px; border-top:1px solid var(--line); }

  .pager { display:flex; gap:10px; align-items:center; justify-content:center;
           margin-top:16px; color:var(--muted); font-size:13.5px; }

  label.toggle { display:inline-flex; gap:8px; align-items:center; color:var(--muted);
                 font-size:13.5px; cursor:pointer; user-select:none; }
  label.toggle input { width:auto; accent-color:var(--golddeep); }

  .note { margin-top:14px; min-height:22px; font-size:14.5px; }
  .note.bad { color:var(--bad); }
  .breath { display:inline-block; animation:breath 1.1s ease-in-out infinite; color:var(--gold); }
  @keyframes breath { 50% { opacity:.25; } }
  #app { display:none; animation:rise .35s ease; }
  @keyframes rise { from { opacity:0; transform:translateY(6px); } }
  .tab { display:none; } .tab.on { display:block; }
</style>
</head>
<body>
<div class="wrap">

  <div id="login">
    <div class="panel">
      <div class="star">✦</div>
      <div class="word">ALMA</div>
      <div class="sub">АДМИНКА ВЛАДЕЛЬЦА</div>
      <input id="pw" type="password" placeholder="Пароль" autocomplete="current-password"
             onkeydown="if(event.key==='Enter')signIn()" autofocus>
      <button class="primary" onclick="signIn()">Войти</button>
      <div class="note" id="loginNote"></div>
    </div>
  </div>

  <div id="app">
    <div class="mark">
      <div>
        <div class="word"><i>✦</i>ALMA</div>
        <div class="sub">АДМИНКА ВЛАДЕЛЬЦА</div>
      </div>
      <button class="ghost small" onclick="signOut()">Выйти</button>
    </div>

    <div class="tabs">
      <button id="tab-over" class="on" onclick="showTab('over')">Обзор</button>
      <button id="tab-people" onclick="showTab('people')">Люди</button>
      <button id="tab-money" onclick="showTab('money')">Прибыль</button>
    </div>

    <!-- ── Обзор ─────────────────────────────────────────────────────── -->
    <div id="view-over" class="tab on">
      <h2>Сегодня</h2><div class="rule"></div>
      <div class="cards" id="stats"></div>
      <h2>Последние права</h2><div class="rule"></div>
      <div id="recentEnts"></div>
    </div>

    <!-- ── Люди ──────────────────────────────────────────────────────── -->
    <div id="view-people" class="tab">
      <h2>Люди</h2><div class="rule"></div>
      <div class="row" style="margin-top:12px">
        <input id="q" placeholder="почта или имя" style="max-width:300px"
               onkeydown="if(event.key==='Enter'){usersPage=1;loadUsers()}">
        <button class="primary" onclick="usersPage=1;loadUsers()">Найти</button>
        <label class="toggle"><input type="checkbox" id="withGuests"
               onchange="usersPage=1;loadUsers()"> показывать гостей</label>
      </div>
      <div id="person"></div>
      <div class="note" id="note"></div>
      <div id="usersList"></div>
      <div class="pager" id="usersPager"></div>
    </div>

    <!-- ── Прибыль ───────────────────────────────────────────────────── -->
    <div id="view-money" class="tab">
      <h2>Итого</h2><div class="rule"></div>
      <div class="cards" id="revTotals"></div>
      <h2>По месяцам</h2><div class="rule"></div>
      <div id="revMonths"></div>
      <h2>Покупки</h2><div class="rule"></div>
      <div id="revRows"></div>
      <div class="pager" id="revPager"></div>
    </div>
  </div>
</div>

<script>
const api = (path, options = {}) => fetch('/admin/api/' + path, {
  ...options,
  headers: {
    'Content-Type': 'application/json',
    ...(sessionStorage.almaAdmin ? { Authorization: 'Bearer ' + sessionStorage.almaAdmin } : {}),
  },
}).then(async r => {
  if (r.status === 401) { sessionStorage.removeItem('almaAdmin'); show(false); }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : ('HTTP ' + r.status));
  return body;
});

const wait = '<span class="breath">✦</span>';
const money = c => (c / 100).toFixed(2);
const when = iso => iso.slice(0, 10) + ' ' + iso.slice(11, 16);

const show = inside => {
  document.getElementById('login').style.display = inside ? 'none' : 'flex';
  document.getElementById('app').style.display = inside ? 'block' : 'none';
  if (inside) refreshStats(); else setTimeout(() => document.getElementById('pw').focus(), 50);
};

function signOut() {
  sessionStorage.removeItem('almaAdmin');
  document.getElementById('person').innerHTML = '';
  show(false);
}

function showTab(name) {
  for (const t of ['over', 'people', 'money']) {
    document.getElementById('tab-' + t).classList.toggle('on', t === name);
    document.getElementById('view-' + t).classList.toggle('on', t === name);
  }
  if (name === 'people' && !document.getElementById('usersList').innerHTML) loadUsers();
  if (name === 'money') loadRevenue();
}

async function signIn() {
  const note = document.getElementById('loginNote');
  note.className = 'note'; note.innerHTML = wait;
  try {
    const out = await api('login', { method: 'POST',
      body: JSON.stringify({ password: document.getElementById('pw').value }) });
    sessionStorage.almaAdmin = out.token;
    document.getElementById('pw').value = '';
    note.textContent = '';
    show(true);
  } catch (e) { note.className = 'note bad'; note.textContent = e.message; }
}

let statsTries = 0;
async function refreshStats() {
  try {
    const s = await api('overview');
    statsTries = 0;
    const cash = s.revenue.length
      ? s.revenue.map(r => money(r.cents) + ' ' + r.currency).join(' · ')
      : '0';
    document.getElementById('stats').innerHTML = [
      card(s.with_email, 'людей с почтой'),
      card(s.guests, 'гостей без входа'),
      card(s.users_today, 'новых за сутки'),
      card(s.active_subscriptions, 'платных подписок'),
      card(s.owner_grants, 'подарков активно'),
      card(s.devices, 'устройств с пушами'),
      card(cash, 'выручка, всего'),
    ].join('');
  } catch (e) {
    // Не молчать навсегда: сразу после рестарта контейнера первый запрос
    // может не дойти, и владелец видел пустые карточки до перелогина.
    if (++statsTries <= 3) setTimeout(refreshStats, 1200 * statsTries);
    return;
  }
  refreshRecent();
}
const card = (v, label) => `<div class="card"><b>${v}</b><span>${label}</span></div>`;

const entRow = (e, extra) => `
  <div class="ent">
    <div class="what">
      <b>${e.system === '*' ? 'Вся Alma' : e.system}</b>
      <span>${e.email
          ? `<a href="#" style="color:inherit" onclick="openPerson('${e.email}');return false">${e.email}</a> · `
          : ''}${e.source} · ${e.amount_cents
          ? money(e.amount_cents) + ' ' + e.currency : 'подарок'}</span>
    </div>
    <div class="row" style="gap:8px">
      ${e.revoked_at ? '<span class="pill rev">отозвано</span>'
        : e.active ? '<span class="pill on">до ' + (e.expires_at || '∞').slice(0, 10) + '</span>'
        : '<span class="pill off">истекло</span>'}
      <span class="pill off">${when(e.granted_at)}</span>
      ${extra || ''}
    </div>
  </div>`;

async function refreshRecent() {
  try {
    const r = await api('recent');
    document.getElementById('recentEnts').innerHTML =
      r.entitlements.map(e => entRow(e)).join('')
      || '<p style="color:var(--muted);margin-top:12px">Пока не выдано ни одного права.</p>';
  } catch (e) {}
}

// ── Люди ────────────────────────────────────────────────────────────────
let usersPage = 1;

function pager(el, page, pages, go) {
  el.innerHTML = pages > 1 ? `
    <button class="ghost small" ${page <= 1 ? 'disabled' : ''}
            onclick="${go}(${page - 1})">‹</button>
    <span>стр. ${page} из ${pages}</span>
    <button class="ghost small" ${page >= pages ? 'disabled' : ''}
            onclick="${go}(${page + 1})">›</button>` : '';
}

function goUsers(p) { usersPage = p; loadUsers(); }
function goRev(p) { revPage = p; loadRevenue(); }

async function loadUsers() {
  const box = document.getElementById('usersList');
  box.innerHTML = '<p style="margin-top:14px">' + wait + '</p>';
  const q = document.getElementById('q').value.trim();
  const guests = document.getElementById('withGuests').checked;
  try {
    const r = await api('users?page=' + usersPage + '&q=' + encodeURIComponent(q)
      + (guests ? '&guests=true' : ''));
    if (!r.rows.length) {
      box.innerHTML = q.includes('@')
        ? '' : '<p style="color:var(--muted);margin-top:14px">Никого не нашлось.</p>';
      // Почты нет в базе — но подарить ей всё равно можно: карточкой ниже.
      if (q.includes('@')) lookup(q);
    } else {
      box.innerHTML = r.rows.map(u => `
        <div class="ent click" onclick="openPerson('${u.email || ''}')">
          <div class="what">
            ${u.email ? `<b>${u.email}</b>`
                      : '<b style="color:var(--muted);font-weight:400">гость</b>'}
            <span>${u.provider} · ${u.locale}${u.display_name ? ' · ' + u.display_name : ''}
              · пришёл ${u.created_at.slice(0, 10)}</span>
          </div>
          <div class="row" style="gap:8px">
            ${u.paid_count ? `<span class="pill gold">покупок · ${u.paid_count}</span>` : ''}
            ${u.active_rights ? `<span class="pill on">прав · ${u.active_rights}</span>` : ''}
            ${u.devices ? `<span class="pill off">📱 ${u.devices}</span>` : ''}
            <span class="pill off">был ${when(u.last_seen_at)}</span>
          </div>
        </div>`).join('');
    }
    pager(document.getElementById('usersPager'), r.page, r.pages, 'goUsers');
  } catch (e) { box.innerHTML = ''; say(e.message, true); }
}

function openPerson(email) {
  if (!email) return;
  showTab('people');
  lookup(email);
  document.getElementById('person').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

let current = null;

async function lookup(email) {
  say(wait);
  try {
    const u = await api('user?email=' + encodeURIComponent(email));
    render(u); say('');
  } catch (e) { say(e.message, true); }
}

function render(u) {
  current = u;
  const box = document.getElementById('person');
  if (!u.found) {
    box.innerHTML = `
      <div class="panel" style="margin-top:16px">
      <p>Аккаунта с почтой <b style="color:var(--goldhi)">${u.email}</b>
      ещё нет. Подарок создаст его — подписка будет ждать первого входа этой почтой.
      ${grantButtons()}</p></div>`;
    return;
  }
  const ents = u.entitlements.map(e => entRow({ ...e, email: null },
    e.revocable ? `<button class="bad small" onclick="revoke('${e.id}', this)">Отозвать</button>` : ''))
    .join('');
  box.innerHTML = `
    <div class="panel" style="margin-top:16px">
      <div class="row" style="justify-content:space-between">
        <div class="facts">
          <span class="k">Почта</span><span>${u.email ?? '—'}</span>
          <span class="k">Аккаунт</span><span>${u.user_id}</span>
          <span class="k">Появился</span><span>${u.created_at.slice(0, 10)}
            · был ${when(u.last_seen_at)}</span>
        </div>
        <button class="ghost small" onclick="closePerson()">✕</button>
      </div>
      <div style="margin-top:12px">
        <span class="chip">${u.provider}</span><span class="chip">язык · ${u.locale}</span
        ><span class="chip">устройств · ${u.devices}</span>${u.display_name
          ? '<span class="chip">' + u.display_name + '</span>' : ''}
      </div>
      <h2 style="margin-top:20px">Права</h2><div class="rule"></div>
      ${u.entitlements.length ? ents
        : '<p style="color:var(--muted);margin-top:12px">Пока ничего не открыто.</p>'}
      ${grantButtons()}
    </div>`;
}

function closePerson() { document.getElementById('person').innerHTML = ''; say(''); }

const grantButtons = () => `
  <h2 style="margin-top:20px">Подарить подписку</h2><div class="rule"></div>
  <div class="row" style="margin-top:12px">
    <button onclick="grant(1)">Месяц</button>
    <button onclick="grant(3)">3 месяца</button>
    <button onclick="grant(12)">Год</button>
    <button class="primary" onclick="grant(null)">Навсегда</button>
  </div>`;

async function grant(months) {
  const email = current && current.email;
  if (!email) return;
  say(wait);
  try {
    const u = await api('grant', { method: 'POST',
      body: JSON.stringify({ email, months }) });
    render({ found: true, ...u });
    say(u.created_account
      ? 'Подписка подарена. Аккаунт создан — подарок ждёт первого входа.'
      : 'Подписка подарена — уже открыта.');
    refreshStats(); loadUsers();
  } catch (e) { say(e.message, true); }
}

// Отзыв — в два нажатия: первое переспрашивает, второе действует. Подарок,
// отозванный промахом пальца, — это звонок владельцу от обиженного друга.
async function revoke(id, btn) {
  if (btn && btn.dataset.armed !== '1') {
    btn.dataset.armed = '1'; btn.textContent = 'Точно отозвать?';
    setTimeout(() => { btn.dataset.armed = ''; btn.textContent = 'Отозвать'; }, 3500);
    return;
  }
  say(wait);
  try {
    const u = await api('revoke', { method: 'POST',
      body: JSON.stringify({ entitlement_id: id }) });
    render({ found: true, ...u });
    say('Отозвано.');
    refreshStats();
  } catch (e) { say(e.message, true); }
}

const say = (text, bad) => {
  const note = document.getElementById('note');
  note.className = bad ? 'note bad' : 'note';
  note.innerHTML = text;
};

// ── Прибыль ─────────────────────────────────────────────────────────────
let revPage = 1;

async function loadRevenue() {
  const totals = document.getElementById('revTotals');
  if (!totals.innerHTML) totals.innerHTML = '<div class="card"><b>' + wait + '</b></div>';
  try {
    const r = await api('revenue?page=' + revPage);
    totals.innerHTML = (r.totals.length
      ? r.totals.map(t => card(money(t.cents) + ' ' + t.currency,
          'выручка · покупок ' + t.count)).join('')
      : card('0', 'выручки пока нет'));
    document.getElementById('revMonths').innerHTML = r.months.length ? `
      <table>
        <tr><th>Месяц</th><th>Сумма</th><th>Покупок</th></tr>
        ${r.months.map(m => `<tr><td>${m.month}</td>
          <td style="color:var(--goldhi)">${money(m.cents)} ${m.currency}</td>
          <td>${m.count}</td></tr>`).join('')}
      </table>` : '<p style="color:var(--muted);margin-top:12px">За последний год покупок не было.</p>';
    document.getElementById('revRows').innerHTML =
      r.purchases.rows.map(e => entRow(e)).join('')
      || '<p style="color:var(--muted);margin-top:12px">Покупок пока нет — как появятся, лягут сюда.</p>';
    pager(document.getElementById('revPager'), r.purchases.page, r.purchases.pages, 'goRev');
  } catch (e) { totals.innerHTML = ''; }
}

show(Boolean(sessionStorage.almaAdmin));
</script>
</body>
</html>"""


@router.get("", response_class=HTMLResponse)
async def page() -> str:
    # Страница отдаётся и ненастроенной админкой: в ней нет ни одной цифры,
    # а вход всё равно упрётся в 503/401. Прятать HTML — не защита.
    return PAGE
