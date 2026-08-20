"""Sign-in. No passwords anywhere.

Three ways in — Google, Apple, and a link in an email — and all three land in
the same place: `accounts.sign_in`, which either attaches the identity to the
guest row the person is already using or folds that guest into an account
they already had.

The magic-link flow deliberately gives the same answer whether or not an
address is known to us. "We sent you a link" for an unknown address is a
white lie that costs nothing; "no account with that email" is an oracle that
tells anyone who asks which addresses have accounts here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ...auth import accounts, tokens
from ...auth.providers import InvalidIdentityToken, verify_apple, verify_google
from ...config import settings
from ...db.models import AuthProvider, MagicLink, User, as_utc, utcnow
from ...mail import send_magic_link
from ..deps import CurrentUser, SessionDep, local_sandbox, request_source, window
from ..schemas import (
    AppleSignIn,
    GoogleSignIn,
    MagicLinkConsume,
    MagicLinkRequest,
    SessionOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_out(user: User) -> SessionOut:
    return SessionOut(
        token=tokens.issue(user.id),
        user_id=user.id,
        is_guest=user.is_guest,
        email=user.email,
        display_name=user.display_name,
        locale=user.locale,
    )


@router.get("/providers")
async def providers() -> dict:
    """Which ways in this deployment can actually verify.

    **A sign-in button over an unverifiable provider is worse than no button.**
    Both `/auth/google` and `/auth/apple` answer 401 without their client id —
    the token cannot be checked, so it must not be trusted — and the app that
    drew the button anyway would answer every tap with an error. A person
    reading that error does not conclude «this deployment is misconfigured»;
    they conclude their account is broken.

    So the client asks instead of guessing. Until now it guessed at build time:
    a `--dart-define` flag that had to be flipped by hand in the same hour the
    credentials were pasted into the server's environment, in two places that
    know nothing about each other. Here the button appears the moment
    `GOOGLE_CLIENT_ID` or `APPLE_CLIENT_ID` is set, and disappears if it is
    unset again.

    No token required: this says nothing about anybody. It is the shape of the
    door, not who is behind it.
    """
    config = settings()
    return {
        "google": bool(config.google_client_id),
        "apple": bool(config.apple_client_id),
        # Почта — не провайдер, но для экрана это третья дверь, и она тоже
        # может быть закрыта: без ключа почтовика ссылка никуда не уйдёт.
        # Локальная разработка — исключение: сервер возвращает токен в ответе,
        # и войти можно без единой настройки.
        "email": bool(config.resend_api_key) or config.debug,
    }


@router.get("/session", response_model=SessionOut)
async def whoami(user: CurrentUser) -> SessionOut:
    """Who this token belongs to — and a guest account if it belonged to nobody."""
    return _session_out(user)


@router.post("/google", response_model=SessionOut)
async def google(payload: GoogleSignIn, user: CurrentUser, session: SessionDep) -> SessionOut:
    try:
        identity = await verify_google(payload.credential)
    except InvalidIdentityToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    signed_in = await accounts.sign_in(
        session,
        email=identity.email,
        provider=identity.provider,
        subject=identity.subject,
        display_name=identity.display_name,
        guest=user,
    )
    return _session_out(signed_in)


@router.post("/apple", response_model=SessionOut)
async def apple(payload: AppleSignIn, user: CurrentUser, session: SessionDep) -> SessionOut:
    try:
        identity = await verify_apple(payload.identity_token, full_name=payload.full_name)
    except InvalidIdentityToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    signed_in = await accounts.sign_in(
        session,
        email=identity.email,
        provider=identity.provider,
        subject=identity.subject,
        display_name=identity.display_name,
        guest=user,
    )
    return _session_out(signed_in)


#: Сколько писем со ссылкой входа уходит на **один адрес** за час.
#:
#: Потолок здесь не про перебор, а про человека на том конце. Адрес в теле
#: запроса — чужой ровно так же легко, как свой, ответ по замыслу одинаков для
#: знакомого и незнакомого, и до этой правки одна строка в цикле означала
#: почтовый ящик, заваленный письмами **с нашего домена и нашей подписью**: мы
#: становимся орудием травли, платим за каждое письмо и попадаем в спам-листы
#: собственной репутацией. Три штуки в час покрывают «письмо не пришло, пришлите
#: ещё раз» и не покрывают ничего сверх.
MAGIC_LINKS_PER_EMAIL_PER_HOUR = 3

#: И сколько их за час уходит от **одного источника**, какие бы адреса он ни
#: называл. Первый потолок сам по себе не мешает пройтись списком из тысячи
#: чужих адресов по разу — это те же тысяча писем, только веером. Второй потолок
#: и есть ответ на перебор; он выше первого, потому что за одним адресом сети
#: сидит не один человек (см. `deps.GUEST_MINTS_PER_HOUR`), а вход по ссылке —
#: единственная дверь для того, кто не пользуется Google и Apple.
MAGIC_LINKS_PER_SOURCE_PER_HOUR = 10

MAGIC_LINK_WINDOW_SECONDS = 3600.0

#: **Оба счёта общие для всех воркеров и переживают выкладку.** До 19.08.2026
#: они жили в памяти процесса, то есть «три письма в час на адрес» на
#: восьмиядерной машине означали двадцать четыре, а `docker compose up` обнулял
#: и это. Теперь счёт лежит в `rate_window` (`deps.SharedWindow`), и адрес туда
#: уходит отпечатком, а не текстом: таблица потолков с живыми почтовыми
#: ящиками была бы вторым, необъявленным местом, где мы их храним.


def _too_many_links() -> HTTPException:
    """Один и тот же отказ для обоих потолков.

    Разные ответы («этот адрес просил недавно» / «вы просили недавно») сказали
    бы спрашивающему, писали ли на чужой ящик, — то самое различие, которое
    остальная часть этого маршрута старательно не выдаёт.
    """
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "magic_link_rate_limit",
            "message": "too many sign-in links requested — try again a bit later",
        },
        headers={"Retry-After": str(int(MAGIC_LINK_WINDOW_SECONDS))},
    )


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(
    request: Request, payload: MagicLinkRequest, user: CurrentUser, session: SessionDep
) -> dict:
    """Send a sign-in link.

    Always answers the same way. Whether the address has an account here is
    not information this endpoint is willing to hand out.

    **Два потолка, и оба до записи строки в `MagicLink`.** По адресу получателя
    — потому что письмо уходит человеку, который нас об этом не просил; по
    источнику запроса — потому что первый потолок обходится списком адресов.
    Отказ раньше `new_magic_token`: иначе в таблице копились бы живые ссылки,
    которых никто не заказывал, и каждая из них — вход в аккаунт.
    """
    # Адрес приводится к нижнему регистру только для ключа счётчика: в базу и в
    # письмо идёт то, что прислали. `Sofia@` и `sofia@` — один почтовый ящик и
    # обязаны делить потолок, иначе он снимается сменой регистра.
    if not await window(
        request,
        "magic_link_email",
        limit=MAGIC_LINKS_PER_EMAIL_PER_HOUR,
        seconds=MAGIC_LINK_WINDOW_SECONDS,
    ).hit(session, payload.email.strip().lower()):
        raise _too_many_links()

    if not await window(
        request,
        "magic_link_source",
        limit=MAGIC_LINKS_PER_SOURCE_PER_HOUR,
        seconds=MAGIC_LINK_WINDOW_SECONDS,
    ).hit(session, request_source(request)):
        raise _too_many_links()

    token, token_hash = tokens.new_magic_token()
    session.add(
        MagicLink(
            token_hash=token_hash,
            email=payload.email,
            guest_user_id=user.id if user.is_guest else None,
            expires_at=tokens.magic_link_expiry(),
        )
    )
    await session.flush()

    delivered = await send_magic_link(
        to=payload.email, token=token, locale=payload.locale
    )
    response: dict = {
        "sent": True,
        "expires_in_minutes": settings().magic_link_minutes,
    }
    if not delivered and _may_show_debug_token():
        # Локальной разработке нужен работающий вход без почтового провайдера.
        # Условие — **разрешение, а не отрицание одного слова**: раньше здесь
        # стояло `not is_production`, то есть всё, что не названо ровно
        # "production"/"prod", отдавало рабочий токен входа прямо в JSON. Стенд
        # с ALMA_ENV=staging и без ключа почты раздавал бы вход в любой аккаунт
        # тому, кто знает адрес.
        response["debug_token"] = token
    return response


def _may_show_debug_token() -> bool:
    """Можно ли вернуть токен входа в теле ответа.

    Правило переехало в `deps.local_sandbox`: тот же замок сторожит подробности
    `/ready`, а два экземпляра одного правила расходятся ровно в тот день, когда
    его ужесточают в одном месте. Имя оставлено здесь, потому что здесь оно
    читается по делу — «показывать ли отладочный токен».
    """
    return local_sandbox()


@router.post("/magic-link/consume", response_model=SessionOut)
async def consume_magic_link(
    payload: MagicLinkConsume, user: CurrentUser, session: SessionDep
) -> SessionOut:
    result = await session.execute(
        select(MagicLink).where(MagicLink.token_hash == tokens.hash_magic_token(payload.token))
    )
    link = result.scalar_one_or_none()
    # Каждый из трёх отказов несёт **типизированный код**, а не только фразу.
    # Клиент (`sign-in/page.tsx`) прежде различал их по английской подстроке
    # message (`includes("already"/"expired")`), и это ломалось дважды: сетевой
    # сбой «no connection» проваливался в «ссылка недействительна», а любая
    # локализация этих строк обнулила бы разбор целиком. Человеческий текст
    # остаётся в `message` (его читают тесты и он уходит на экран как запасной),
    # а ветвление теперь идёт по `error`. Найдено 20.08.2026.
    if link is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"error": "link_invalid", "message": "this link is not valid"},
        )

    expires = as_utc(link.expires_at)
    if link.used_at is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"error": "link_used", "message": "this link has already been used"},
        )
    if expires <= datetime.now(timezone.utc):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"error": "link_expired", "message": "this link has expired"},
        )

    # Single use, marked before the account work so a double submit cannot
    # produce two sign-ins from one email.
    link.used_at = utcnow()
    await session.flush()

    # **Гость берётся только тот, кто предъявил токен вот этим запросом.**
    #
    # Здесь стояла подмена: если ссылку запросили «в другой вкладке», код
    # доставал сохранённого в строке гостя и предпочитал его кликнувшему.
    # Намерение было доброе — не потерять карту, посчитанную до входа, — а
    # следствие открывало захват чужого аккаунта целиком.
    #
    # Разбор атаки. Никто не мешает попросить ссылку на **чужой** адрес: в
    # строку `MagicLink` при этом пишется гость просящего. Жертве уходит
    # настоящее письмо с нашего домена, она открывает свою почту и жмёт свою
    # кнопку — а подмена подставляет в `sign_in` гостя атакующего. Дальше
    # `accounts.sign_in` либо вешает почту жертвы прямо на строку атакующего,
    # либо сливает её аккаунт с этой строкой; в обоих случаях старый гостевой
    # токен атакующего (90 дней) с этой секунды аутентифицирует его как
    # жертву — со всей картой рождения, беседами, покупками и правом удалить
    # аккаунт. Ни одного «взлома» не требуется: только знание чужого адреса.
    #
    # Поэтому сохранённый идентификатор используется ровно как **сверка**, а
    # не как источник личности: совпал с кликнувшим — хорошо, разошёлся —
    # игнорируется молча. Цена честная и мелкая: тот, кто попросил ссылку на
    # телефоне и открыл письмо на компьютере, войдёт на компьютере в пустой
    # аккаунт, а карта останется в госте телефона и присоединится к аккаунту
    # при первом же входе с самого телефона. Данные не теряются — сдвигается
    # момент склейки.
    guest = user if user.is_guest else None

    signed_in = await accounts.sign_in(
        session,
        email=link.email,
        provider=AuthProvider.email.value,
        subject=None,
        guest=guest,
    )
    return _session_out(signed_in)


@router.post("/refresh", response_model=SessionOut)
async def refresh(user: CurrentUser) -> SessionOut:
    """A fresh token for the same person. No state changes."""
    return _session_out(user)
