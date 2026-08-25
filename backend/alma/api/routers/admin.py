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
        "active_subscriptions": active_subs,
        "owner_grants": grants,
        "revenue": [
            {"currency": currency, "cents": int(cents or 0)}
            for currency, cents in paid_rows
        ],
        "devices": devices,
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
<style>
  :root { --night:#0A0D1C; --night2:#101636; --gold:#C9AE6B; --goldhi:#E4D3A2;
          --body:#EDE7DA; --muted:#8b8578; --line:#2a2b3d; --bad:#c96b6b; }
  * { box-sizing:border-box; margin:0; }
  body { background:var(--night); color:var(--body);
         font-family:Georgia, 'Times New Roman', serif; min-height:100vh; }
  .wrap { max-width:760px; margin:0 auto; padding:40px 20px 80px; }
  h1 { font-size:26px; letter-spacing:.16em; color:var(--gold); font-weight:normal; }
  h2 { font-size:13px; letter-spacing:.14em; text-transform:uppercase;
       color:var(--muted); margin:34px 0 12px; font-weight:normal; }
  input, button { font:inherit; }
  input { width:100%; background:rgba(16,22,54,.55); border:1px solid var(--line);
          border-radius:14px; color:var(--body); padding:13px 16px; outline:none; }
  input:focus { border-color:var(--gold); }
  button { background:none; border:1px solid var(--gold); color:var(--goldhi);
           border-radius:22px; padding:11px 22px; cursor:pointer; letter-spacing:.04em; }
  button:hover { background:rgba(201,174,107,.12); }
  button:disabled { opacity:.4; cursor:default; }
  button.ghost { border-color:var(--line); color:var(--muted); }
  button.bad { border-color:var(--bad); color:var(--bad); }
  .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
  .cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:10px; }
  .card { border:1px solid var(--line); border-radius:14px; padding:14px 16px; }
  .card b { display:block; font-size:24px; color:var(--goldhi); font-weight:normal; }
  .card span { font-size:12px; color:var(--muted); letter-spacing:.06em; }
  table { width:100%; border-collapse:collapse; margin-top:8px; font-size:14.5px; }
  td { padding:9px 6px; border-top:1px solid var(--line); vertical-align:top; }
  .muted { color:var(--muted); } .ok { color:var(--goldhi); } .off { color:var(--muted); }
  .note { margin-top:14px; min-height:22px; font-size:14.5px; }
  .note.bad { color:var(--bad); }
  #app { display:none; }
</style>
</head>
<body>
<div class="wrap">
  <h1>ALMA · АДМИНКА</h1>

  <div id="login">
    <h2>Вход</h2>
    <div class="row">
      <input id="pw" type="password" placeholder="Пароль" style="max-width:320px"
             onkeydown="if(event.key==='Enter')signIn()">
      <button onclick="signIn()">Войти</button>
    </div>
    <div class="note" id="loginNote"></div>
  </div>

  <div id="app">
    <h2>Сегодня</h2>
    <div class="cards" id="stats"></div>

    <h2>Человек</h2>
    <div class="row">
      <input id="email" type="email" placeholder="почта@пример.com" style="max-width:340px"
             onkeydown="if(event.key==='Enter')lookup()">
      <button onclick="lookup()">Найти</button>
    </div>
    <div id="person"></div>
    <div class="note" id="note"></div>
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
  if (!r.ok) throw new Error(body.detail || ('HTTP ' + r.status));
  return body;
});

const show = inside => {
  document.getElementById('login').style.display = inside ? 'none' : 'block';
  document.getElementById('app').style.display = inside ? 'block' : 'none';
  if (inside) refreshStats();
};

async function signIn() {
  const note = document.getElementById('loginNote');
  note.className = 'note'; note.textContent = '…';
  try {
    const out = await api('login', { method: 'POST',
      body: JSON.stringify({ password: document.getElementById('pw').value }) });
    sessionStorage.almaAdmin = out.token;
    document.getElementById('pw').value = '';
    note.textContent = '';
    show(true);
  } catch (e) { note.className = 'note bad'; note.textContent = e.message; }
}

async function refreshStats() {
  try {
    const s = await api('overview');
    const money = s.revenue.length
      ? s.revenue.map(r => (r.cents / 100).toFixed(2) + ' ' + r.currency).join(' · ')
      : '0';
    document.getElementById('stats').innerHTML = [
      card(s.users_total, 'аккаунтов всего'),
      card(s.users_today, 'новых за сутки'),
      card(s.with_email, 'с почтой'),
      card(s.active_subscriptions, 'платных подписок'),
      card(s.owner_grants, 'подарков активно'),
      card(s.devices, 'устройств с пушами'),
      card(money, 'выручка, всего'),
    ].join('');
  } catch (e) {}
}
const card = (v, label) => `<div class="card"><b>${v}</b><span>${label}</span></div>`;

let current = null;

async function lookup() {
  const email = document.getElementById('email').value.trim();
  if (!email) return;
  say('…');
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
      <p style="margin-top:14px">Аккаунта с почтой <b class="ok">${u.email}</b> ещё нет.
      Подарок создаст его — подписка будет ждать первого входа этой почтой.</p>
      ${grantButtons()}`;
    return;
  }
  const rows = u.entitlements.map(e => `
    <tr>
      <td>${e.system === '*' ? 'вся Alma' : e.system}<br>
          <span class="muted">${e.kind} · ${e.source}</span></td>
      <td>${e.amount_cents ? (e.amount_cents / 100).toFixed(2) + ' ' + e.currency : 'подарок'}</td>
      <td>${e.revoked_at ? '<span class="off">отозвано</span>'
            : e.active ? '<span class="ok">до ' + (e.expires_at || '∞').slice(0, 10) + '</span>'
            : '<span class="off">истекло ' + (e.expires_at || '').slice(0, 10) + '</span>'}</td>
      <td>${e.revocable ? `<button class="bad" onclick="revoke('${e.id}')">Отозвать</button>` : ''}</td>
    </tr>`).join('');
  box.innerHTML = `
    <table>
      <tr><td class="muted">Почта</td><td colspan="3">${u.email ?? '—'}</td></tr>
      <tr><td class="muted">Аккаунт</td><td colspan="3">${u.user_id} · ${u.provider}
          · язык ${u.locale}${u.display_name ? ' · ' + u.display_name : ''}</td></tr>
      <tr><td class="muted">Появился</td><td colspan="3">${u.created_at.slice(0, 10)}
          · был ${u.last_seen_at.slice(0, 10)} · устройств: ${u.devices}</td></tr>
    </table>
    <h2>Права</h2>
    ${u.entitlements.length ? '<table>' + rows + '</table>'
      : '<p class="muted">Пока ничего не открыто.</p>'}
    ${grantButtons()}`;
}

const grantButtons = () => `
  <h2>Подарить подписку</h2>
  <div class="row">
    <button onclick="grant(1)">Месяц</button>
    <button onclick="grant(3)">3 месяца</button>
    <button onclick="grant(12)">Год</button>
    <button onclick="grant(null)">Навсегда</button>
  </div>`;

async function grant(months) {
  const email = (current && current.email) || document.getElementById('email').value.trim();
  say('…');
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

async function revoke(id) {
  say('…');
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
  note.textContent = text;
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
