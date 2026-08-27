"""Админка владельца: выдать подписку по почте, посмотреть человека, отозвать.

Появилась 25.08.2026 по слову владельца: «веб-админка, чтоб можно было
выдавать по почте подписки». До неё каждый грант делался руками в базе по
ssh — так был выдан и его собственный (`source='owner_grant'`), и это ровно
тот процесс, который ломается в день, когда владелец захочет подарить месяц
другу с телефона.

**Пароль в конфиге не живёт — только его SHA-256.** `.env` читают глаза,
которым пароль не нужен: деплой, бэкап, тикет. Хэш пускает внутрь ровно так
же, а его утечка паролем не является. Сравнение — `hmac.compare_digest`:
обычное `==` отвечает быстрее на почти верный пароль, и это измеримо.

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

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ...auth import tokens
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

    typed = hashlib.sha256(payload.password.encode()).hexdigest()
    if not hmac.compare_digest(typed, digest):
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
    """Последние аккаунты и последние права — как они лежат в базе.

    Лента, а не отчёт: владелец открывает админку посмотреть «что происходит»,
    и до этой ручки ответ состоял из семи чисел. Числа складываются из строк —
    вот строки. Гости показываются наравне с почтами: это тоже настоящие
    визиты, и прятать их значило бы рисовать продукт популярнее, чем он есть.
    """
    _configured()
    people = (
        await session.execute(
            select(User).order_by(User.created_at.desc()).limit(RECENT)
        )
    ).scalars().all()
    rows = (
        await session.execute(
            select(Entitlement, User.email)
            .join(User, User.id == Entitlement.user_id)
            .order_by(Entitlement.granted_at.desc())
            .limit(RECENT)
        )
    ).all()
    return {
        "users": [
            {
                "email": u.email,
                "provider": u.provider,
                "display_name": u.display_name,
                "locale": u.locale,
                "created_at": as_utc(u.created_at).isoformat(),
                "last_seen_at": as_utc(u.last_seen_at).isoformat(),
            }
            for u in people
        ],
        "entitlements": [
            {**_entitlement_row(e), "email": email} for e, email in rows
        ],
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
  .wrap { max-width:820px; margin:0 auto; padding:34px 20px 90px; }

  .mark { display:flex; align-items:center; gap:12px; justify-content:space-between; }
  .mark .word { font:26px 'Playfair Display', Georgia, serif; letter-spacing:.34em;
                color:var(--goldhi); }
  .mark .word i { font-style:normal; color:var(--gold); margin-right:10px; }
  .sub { font-size:11px; letter-spacing:.28em; color:var(--muted); text-transform:uppercase;
         margin-top:4px; }

  h2 { font-size:11.5px; letter-spacing:.22em; text-transform:uppercase;
       color:var(--golddeep); margin:34px 0 0; font-weight:600; }
  .rule { height:1px; margin:8px 0 0;
          background:linear-gradient(90deg, transparent, rgba(201,174,107,.34), transparent); }

  input, button { font:inherit; }
  input { width:100%; background:rgba(13,16,28,.85); border:1px solid var(--line);
          border-radius:24px; color:var(--ink); padding:13px 20px; outline:none;
          transition:border-color .18s, background .18s; }
  input::placeholder { color:rgba(237,231,218,.4); }
  input:focus { border-color:rgba(201,174,107,.8); background:rgba(13,16,28,.4); }

  button { background:none; border:1px solid rgba(201,174,107,.55); color:var(--goldhi);
           border-radius:24px; padding:12px 24px; cursor:pointer; letter-spacing:.05em;
           transition:background .18s, border-color .18s, opacity .18s; }
  button:hover { background:rgba(201,174,107,.13); border-color:var(--gold); }
  button:disabled { opacity:.4; cursor:default; }
  button.primary { background:linear-gradient(180deg, #1A1626, #0C0A14);
                   border-color:var(--golddeep);
                   box-shadow:0 0 20px rgba(201,174,107,.16); }
  button.ghost { border-color:var(--line); color:var(--muted); }
  button.bad { border-color:rgba(224,145,127,.55); color:var(--bad); }
  button.bad:hover { background:rgba(224,145,127,.1); border-color:var(--bad); }
  button.small { padding:8px 16px; font-size:13.5px; }

  .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }

  .panel { border:1px solid var(--linegold); border-radius:18px; padding:22px 24px;
           background:linear-gradient(180deg, rgba(10,13,28,.88), rgba(7,10,22,.97));
           box-shadow:0 18px 50px rgba(4,6,14,.5); }

  /* Вход — церемония по центру экрана. */
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
         padding:13px 17px; margin-top:10px; background:var(--card); }
  .ent .what b { font-weight:600; color:var(--ink); }
  .ent .what span { display:block; font-size:12.5px; color:var(--muted); }
  .pill { border-radius:12px; padding:3px 12px; font-size:12.5px; white-space:nowrap; }
  .pill.on  { color:var(--ok);   border:1px solid rgba(143,191,154,.4); }
  .pill.off { color:var(--muted); border:1px solid var(--line); }
  .pill.rev { color:var(--bad);  border:1px solid rgba(224,145,127,.4); }

  .note { margin-top:14px; min-height:22px; font-size:14.5px; }
  .note.bad { color:var(--bad); }
  .breath { display:inline-block; animation:breath 1.1s ease-in-out infinite; color:var(--gold); }
  @keyframes breath { 50% { opacity:.25; } }
  #app { display:none; animation:rise .35s ease; }
  @keyframes rise { from { opacity:0; transform:translateY(6px); } }
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

    <h2>Сегодня</h2><div class="rule"></div>
    <div class="cards" id="stats"></div>

    <h2>Человек</h2><div class="rule"></div>
    <div class="row" style="margin-top:12px">
      <input id="email" type="email" placeholder="почта@пример.com" style="max-width:340px"
             onkeydown="if(event.key==='Enter')lookup()">
      <button class="primary" onclick="lookup()">Найти</button>
    </div>
    <div id="person"></div>
    <div class="note" id="note"></div>

    <h2>Последние права</h2><div class="rule"></div>
    <div id="recentEnts"></div>

    <h2>Последние аккаунты</h2><div class="rule"></div>
    <div id="recentUsers"></div>
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

const show = inside => {
  document.getElementById('login').style.display = inside ? 'none' : 'flex';
  document.getElementById('app').style.display = inside ? 'block' : 'none';
  if (inside) refreshStats(); else setTimeout(() => document.getElementById('pw').focus(), 50);
};

function signOut() {
  sessionStorage.removeItem('almaAdmin');
  document.getElementById('person').innerHTML = '';
  document.getElementById('email').value = '';
  show(false);
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
    const money = s.revenue.length
      ? s.revenue.map(r => (r.cents / 100).toFixed(2) + ' ' + r.currency).join(' · ')
      : '0';
    document.getElementById('stats').innerHTML = [
      card(s.with_email, 'людей с почтой'),
      card(s.guests, 'гостей без входа'),
      card(s.users_today, 'новых за сутки'),
      card(s.active_subscriptions, 'платных подписок'),
      card(s.owner_grants, 'подарков активно'),
      card(s.devices, 'устройств с пушами'),
      card(money, 'выручка, всего'),
    ].join('');
  } catch (e) {
    // Не молчать навсегда: сразу после рестарта контейнера первый запрос
    // может не дойти, и владелец видел пустые карточки до перелогина.
    if (++statsTries <= 3) setTimeout(refreshStats, 1200 * statsTries);
    return;
  }
  refreshRecent();
}

// Живые ленты: последние аккаунты и последние права, как они лежат в базе.
async function refreshRecent() {
  try {
    const r = await api('recent');
    const when = iso => iso.slice(0, 10) + ' ' + iso.slice(11, 16);
    document.getElementById('recentUsers').innerHTML = r.users.map(u => `
      <div class="ent">
        <div class="what">
          ${u.email
            ? `<b><a href="#" style="color:var(--goldhi);text-decoration:none"
                 onclick="pick('${u.email}');return false">${u.email}</a></b>`
            : '<b style="color:var(--muted);font-weight:400">гость</b>'}
          <span>${u.provider} · ${u.locale}${u.display_name ? ' · ' + u.display_name : ''}</span>
        </div>
        <span class="pill off">${when(u.created_at)}</span>
      </div>`).join('') || '<p style="color:var(--muted);margin-top:12px">Пока пусто.</p>';
    document.getElementById('recentEnts').innerHTML = r.entitlements.map(e => `
      <div class="ent">
        <div class="what">
          <b>${e.system === '*' ? 'Вся Alma' : e.system}</b>
          <span>${e.email
              ? `<a href="#" style="color:inherit" onclick="pick('${e.email}');return false">${e.email}</a> · `
              : ''}${e.source} · ${e.amount_cents
              ? (e.amount_cents / 100).toFixed(2) + ' ' + e.currency : 'подарок'}</span>
        </div>
        <div class="row" style="gap:8px">
          ${e.revoked_at ? '<span class="pill rev">отозвано</span>'
            : e.active ? '<span class="pill on">до ' + (e.expires_at || '∞').slice(0, 10) + '</span>'
            : '<span class="pill off">истекло</span>'}
          <span class="pill off">${when(e.granted_at)}</span>
        </div>
      </div>`).join('') || '<p style="color:var(--muted);margin-top:12px">Пока не выдано ни одного права.</p>';
  } catch (e) {}
}

function pick(email) {
  document.getElementById('email').value = email;
  lookup();
  document.getElementById('email').scrollIntoView({ behavior: 'smooth' });
}
const card = (v, label) => `<div class="card"><b>${v}</b><span>${label}</span></div>`;

let current = null;

async function lookup() {
  const email = document.getElementById('email').value.trim();
  if (!email) return;
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
      <p style="margin-top:16px">Аккаунта с почтой <b style="color:var(--goldhi)">${u.email}</b>
      ещё нет. Подарок создаст его — подписка будет ждать первого входа этой почтой.</p>
      ${grantButtons()}`;
    return;
  }
  const ents = u.entitlements.map(e => `
    <div class="ent">
      <div class="what">
        <b>${e.system === '*' ? 'Вся Alma' : e.system}</b>
        <span>${e.kind} · ${e.source} · ${e.amount_cents
          ? (e.amount_cents / 100).toFixed(2) + ' ' + e.currency : 'подарок'}</span>
      </div>
      <div class="row" style="gap:8px">
        ${e.revoked_at ? '<span class="pill rev">отозвано</span>'
          : e.active ? '<span class="pill on">до ' + (e.expires_at || '∞').slice(0, 10) + '</span>'
          : '<span class="pill off">истекло ' + (e.expires_at || '').slice(0, 10) + '</span>'}
        ${e.revocable ? `<button class="bad small" onclick="revoke('${e.id}', this)">Отозвать</button>` : ''}
      </div>
    </div>`).join('');
  box.innerHTML = `
    <div class="panel" style="margin-top:16px">
      <div class="facts">
        <span class="k">Почта</span><span>${u.email ?? '—'}</span>
        <span class="k">Аккаунт</span><span>${u.user_id}</span>
        <span class="k">Появился</span><span>${u.created_at.slice(0, 10)}
          · был ${u.last_seen_at.slice(0, 10)}</span>
      </div>
      <div style="margin-top:12px">
        <span class="chip">${u.provider}</span><span class="chip">язык · ${u.locale}</span
        ><span class="chip">устройств · ${u.devices}</span>${u.display_name
          ? '<span class="chip">' + u.display_name + '</span>' : ''}
      </div>
    </div>
    <h2>Права</h2><div class="rule"></div>
    ${u.entitlements.length ? ents
      : '<p style="color:var(--muted);margin-top:12px">Пока ничего не открыто.</p>'}
    ${grantButtons()}`;
}

const grantButtons = () => `
  <h2>Подарить подписку</h2><div class="rule"></div>
  <div class="row" style="margin-top:12px">
    <button onclick="grant(1)">Месяц</button>
    <button onclick="grant(3)">3 месяца</button>
    <button onclick="grant(12)">Год</button>
    <button class="primary" onclick="grant(null)">Навсегда</button>
  </div>`;

async function grant(months) {
  const email = (current && current.email) || document.getElementById('email').value.trim();
  say(wait);
  try {
    const u = await api('grant', { method: 'POST',
      body: JSON.stringify({ email, months }) });
    render({ found: true, ...u });
    say(u.created_account
      ? 'Подписка подарена. Аккаунт создан — подарок ждёт первого входа.'
      : 'Подписка подарена — уже открыта.');
    refreshStats();
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

show(Boolean(sessionStorage.almaAdmin));
</script>
</body>
</html>"""


@router.get("", response_class=HTMLResponse)
async def page() -> str:
    # Страница отдаётся и ненастроенной админкой: в ней нет ни одной цифры,
    # а вход всё равно упрётся в 503/401. Прятать HTML — не защита.
    return PAGE
