"""Пуш «отчёт пары готов» — кадр W7 холста (`docs/monetization/SCREENS-V3.md`).

Один пуш на один грант пары, сразу после того, как грант выписан: покупкой в
магазине (токен intent'а в подписанном пейлоаде), привязкой через
`POST /billing/pair/bind` или кредитом подписчика. Механизм — тот же, что у
дневной заметки (`notify/daily.py`): те же `DeviceToken`, тот же
`transport.Push`, те же сендеры APNs/FCM напрямую, та же таблица
`UsageCounter` для идемпотентности. Второго способа слать пуши здесь не
появляется — появляется второй повод.

**Чем этот пуш отличается от дневного, и почему это решения, а не пропуски.**

* **Нет каденции и нет тихих часов.** Дневная заметка — перебивка, и весь
  `rules.py` существует, чтобы она оставалась желанной. Этот пуш — ответ на
  действие самого человека секунды назад: он нажал «купить», привязал покупку
  или потратил кредит. Отвечать на собственное действие с задержкой «до утра»
  значило бы промолчать в единственный момент, когда ответа ждут. Ровно тот же
  довод, по которому пейволл в этом продукте — ответ, а не перебивка (принцип
  1 ТЗ). Правило W7 «≤1/день» — про контентный поток дневной заметки, а не про
  подтверждение покупки.
* **Отсутствие транспорта — тишина, а не отказ запуститься.** `daily.run`
  обязан упасть без креденшалов: пуш — вся его работа. Здесь пуш — побочный
  эффект платёжного пути, и уронить верификацию покупки из-за неподставленного
  APNs-ключа значило бы обменять деньги человека на нашу нотификацию. Поэтому
  всё, что для дневной заметки — громкий `PushUnavailable`, здесь — строка в
  логе не выше warning.
* **Отказы уважаются той же механикой, что и у дневной.** «Выключить
  уведомления» в этом продукте — удаление токенов, а не флаг
  (`routers/notify.py`: off is a deletion), так что человеку без строк в
  `DeviceToken` просто нечего слать — и это не ошибка.

**Идемпотентность.** Ключ дедупликации честный: одна пара (аккаунт, партнёр) —
максимум один *доставленный* пуш, что бы ни повторялось сверху. Повторы
приходят по трём путям сразу: `/iap/verify` и нотификация магазина — два
события об одной покупке, вторые $4.99 за того же партнёра — второй грант в ту
же строку. Все они упираются в одну строку `UsageCounter` (метрика
`pair_push`), написанную по образцу `daily.claim`: строка занимается до
отправки, подтверждается после и удаляется, если ни один вендор не принял —
чтобы неудачная минута APNs не съела уведомление навсегда. Коммитов здесь нет:
функция живёт внутри чужой (платёжной) транзакции и не имеет права рвать её на
свои; гонка двух процессов упрётся в первичный ключ на коммите запроса — тем же
способом и с той же ценой, что у `credits.ensure_period`.

**Текст.** Заголовок — настоящий фактор из расчёта совместимости, как рисует
W7: «Marcus's Sun sits in your seventh house». Фактор берётся из
`compute_cached("compatibility", …)` — того же вызова и того же процессного
кэша, что у `/systems/compatibility`, так что к моменту покупки расчёт почти
всегда уже лежит готовым. Выбирается оверлей — тело партнёра в доме владельца —
по дому (7 → 5 → 8 → 1: дом партнёрства, потом романа, потом общего, потом
присутствия; ровно те дома, которые `synastry._highlights` называет вслух),
внутри дома — по телу (светила и личные планеты вперёд). Если расчёт упал или
фактора нужной формы нет — честный запасной текст «{Имя} — ваш разбор готов»
без выдуманных факторов.

**Локали.** Язык выбирается правилом дневной заметки: локаль последнего
живого устройства, потом локаль аккаунта. Но ключей пары в бандле замороженного
клиента нет, поэтому предложение собирается на сервере целиком — это вторая
санкционированная щель в дизайне «ключ, не предложение», после тизера дневной
заметки (`transport.Push.body`), и по той же причине: строка с именем партнёра
не может жить в бандле. Таблицы ниже — все семь локалей `i18n/placements.py`,
имена тел подставляются из неё же.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from typing import Mapping

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Profile, UsageCounter, User, as_utc, utcnow
from ..i18n.placements import _base, placement
from . import tokens as token_store
from .transport import (
    CHANNEL_TRANSACTIONAL,
    Push,
    Receipt,
    Transport,
    Verdict,
    configured_platforms,
    transport_for,
)

log = logging.getLogger("alma.notify.pair")

#: Метрика в `UsageCounter` — своё слово, чтобы никогда не разделить строку ни
#: с дневной заметкой (`daily_push`), ни с продлениями.
METRIC = "pair_push"

#: Источники грантов, за которыми стоят настоящие деньги или включённый в
#: оплаченную подписку кредит. Всё остальное — `unknown` (грант, сделанный
#: руками, `entitlements.grant` без source), будущие `dev-*`/`manual` из
#: админских инструментов — пуша не получает: «ваш отчёт готов» о гранте,
#: который человек выписал себе сам для отладки, — это нотификация о ничём,
#: и первым её получит тот, кто тестирует. Список закрытый и совпадает с
#: именами адаптеров (`AppStoreProvider.name` и т.д.) плюс `credit` из
#: `billing/credits.spend`.
PAID_SOURCES = frozenset({"appstore", "googleplay", "paddle", "dodo", "credit"})

#: Дома, про которые пуш умеет говорить, в порядке предпочтения: седьмой — дом
#: партнёрства (его же W7 рисует на холсте), пятый — романа, восьмой — общего
#: и скрытого, первый — присутствия. Ровно те, которые `synastry._highlights`
#: считает достойными произнесения вслух; остальные восемь домов пуш не
#: называет — не потому, что они пусты, а потому, что строка на локскрине
#: должна попадать в тему отчёта, который откроется по тапу.
PRIORITY_HOUSES: tuple[int, ...] = (7, 5, 8, 1)

#: Тела в порядке предпочтения внутри дома: светила и личные планеты вперёд —
#: «его Солнце в твоём седьмом» сильнее «его Плутон в твоём седьмом», потому
#: что внешние планеты у ровесников почти общие. Порядок, а не веса: второй
#: системы скоринга здесь не появляется, как её нет и у дневной заметки.
PRIORITY_BODIES: tuple[str, ...] = (
    "sun", "moon", "venus", "mars", "mercury", "jupiter", "saturn",
    "true_node", "chiron", "lilith", "uranus", "neptune", "pluto",
)

# ── строки, все семь локалей placements ────────────────────────────────────
#
# Английский эталон — W7: `push.pair_title` «{name}'s Sun sits on your seventh
# cusp», `push.pair_body` «The attraction chapter for the two of you is ready
# to read». Ни в одной строке нет глагола «купи», «открой» или «попробуй» —
# заголовок обязан оставаться фактом из карты, а не приглашением (правило W7).
#
# Форма «{name}: …» в пяти языках — не небрежность, а тот же приём, которым
# переводчики дневных пушей в клиентских .arb обошли родительный падеж и род
# («{p1} и {p2}: соединение…»): притяжательное от произвольного имени сервер
# просклонять не может ни в русском, ни в немецком. Французский несёт узкий
# неразрывный U+202F перед двоеточием — правило всей локали разом
# (`tests/test_french_spacing.py`). Русский на «вы» — как запасной текст,
# заданный владельцем задачи, и как весь платёжный словарь `mail.py`.

#: Заголовок с фактором: {name} — имя партнёра как введено в профиле,
#: {body} — имя тела из `placements` в той же локали.
HOUSE_TITLES: dict[int, dict[str, str]] = {
    7: {
        "en": "{name}'s {body} sits in your seventh house",
        "es": "{name}: su {body} cae en tu séptima casa",
        "de": "{name}: {body} steht in deinem siebten Haus",
        "it": "{name}: {body} nella tua settima casa",
        "fr": "{name} : {body} dans ta septième maison",
        "pt-BR": "{name}: {body} na sua sétima casa",
        "ru": "{name}: {body} в вашем седьмом доме",
    },
    5: {
        "en": "{name}'s {body} sits in your fifth house",
        "es": "{name}: su {body} cae en tu quinta casa",
        "de": "{name}: {body} steht in deinem fünften Haus",
        "it": "{name}: {body} nella tua quinta casa",
        "fr": "{name} : {body} dans ta cinquième maison",
        "pt-BR": "{name}: {body} na sua quinta casa",
        "ru": "{name}: {body} в вашем пятом доме",
    },
    8: {
        "en": "{name}'s {body} sits in your eighth house",
        "es": "{name}: su {body} cae en tu octava casa",
        "de": "{name}: {body} steht in deinem achten Haus",
        "it": "{name}: {body} nella tua ottava casa",
        "fr": "{name} : {body} dans ta huitième maison",
        "pt-BR": "{name}: {body} na sua oitava casa",
        "ru": "{name}: {body} в вашем восьмом доме",
    },
    1: {
        "en": "{name}'s {body} sits in your first house",
        "es": "{name}: su {body} cae en tu primera casa",
        "de": "{name}: {body} steht in deinem ersten Haus",
        "it": "{name}: {body} nella tua prima casa",
        "fr": "{name} : {body} dans ta première maison",
        "pt-BR": "{name}: {body} na sua primeira casa",
        "ru": "{name}: {body} в вашем первом доме",
    },
}

#: Запасной заголовок, когда фактор недоступен: расчёт упал, у своего профиля
#: нет времени рождения (нет домов), нужной формы оверлея не нашлось. Честная
#: строка без выдуманных факторов — формулировка владельца задачи.
FALLBACK_TITLES: dict[str, str] = {
    "en": "{name} — your reading is ready",
    "es": "{name} — tu informe está listo",
    "de": "{name} — eure Analyse ist fertig",
    "it": "{name} — la vostra analisi è pronta",
    "fr": "{name} — votre analyse est prête",
    "pt-BR": "{name} — a análise de vocês está pronta",
    "ru": "{name} — ваш разбор готов",
}

#: Совсем без имени — грант, чей профиль уже удалён (отчёт остаётся, А7 §12),
#: или строка `pair:{id}`, указывающая на чужой профиль: чужое имя в пуше не
#: показывается никогда, по той же причине, по какой `pairs.my_pairs` читает
#: имена только из своих профилей.
NAMELESS_TITLES: dict[str, str] = {
    "en": "Your reading is ready",
    "es": "Tu informe está listo",
    "de": "Eure Analyse ist fertig",
    "it": "La vostra analisi è pronta",
    "fr": "Votre analyse est prête",
    "pt-BR": "A análise de vocês está pronta",
    "ru": "Ваш разбор готов",
}

#: Тело всегда одно — `push.pair_body` с холста: глава «Притяжение» и есть
#: первая глава отчёта пары, к которой ведёт тап.
BODIES: dict[str, str] = {
    "en": "The attraction chapter for the two of you is ready to read.",
    "es": "El capítulo de la atracción entre los dos ya está listo para leer.",
    "de": "Das Kapitel über die Anziehung zwischen euch ist bereit zum Lesen.",
    "it": "Il capitolo sull'attrazione tra voi due è pronto da leggere.",
    "fr": "Le chapitre de l'attirance entre vous est prêt à lire.",
    "pt-BR": "O capítulo da atração entre vocês está pronto para ler.",
    "ru": "Глава о притяжении для вас двоих готова к чтению.",
}

#: Ключ заголовка — деградация на случай пустого `title`, которого compose не
#: производит; в бандле клиента его нет, и это осознанно: см. модульный
#: докстринг про вторую щель в дизайне «ключ, не предложение».
TITLE_KEY = "push.pair.title"

#: Сколько вендор имеет право держать этот пуш, если телефон выключен.
#:
#: **Здесь стояло `expires_at=None` — и это значило не «не протухает», а прямо
#: обратное.** У APNs заголовок `apns-expiration` необязателен, но его
#: отсутствие равно нулю: «попытаться доставить один раз и не хранить». То есть
#: человек, купивший отчёт и убравший телефон в карман с севшей батареей, не
#: узнавал о покупке никогда — а строка `UsageCounter` при этом уже
#: подтверждена, потому что вендор ответил «принял». Дневная заметка живёт до
#: 22:00 своего дня, потому что она про день; купленный отчёт не про день, но
#: и не вечен: неделя — это горизонт, за которым уведомление «готово»
#: перестаёт быть новостью и становится напоминанием о том, что человек и так
#: уже открыл. Двенадцать часов FCM (`fcm.TTL_SECONDS`) остаются потолком на
#: Android — там `ttl` считается от отправки и его хватает.
DELIVERY_WINDOW = timedelta(days=7)


def counter_key(user_id: str, partner_id: str) -> str:
    """Ключ строки `UsageCounter`: одна пара — один пуш, навсегда.

    В отличие от дневного `daily.counter_key`, даты в ключе нет: пуш не «по
    одному в день», а «по одному на пару» — вторая покупка того же партнёра
    гранта не меняет (`pair:{profile_id}` уже есть) и «готов» второй раз не
    бывает. Партнёр входит хэшем, а не сырым id: колонка `id` — String(64), и
    два id по 32 знака плюс метрика в неё не помещаются; владелец остаётся в
    ключе открытым текстом, потому что по нему строку ищут глазами в инциденте.
    """
    digest = hashlib.sha256(partner_id.encode("utf-8")).hexdigest()[:20]
    return f"{METRIC}:{user_id[:32]}:{digest}"


def pick_factor(data: dict) -> tuple[str, int] | None:
    """Оверлей для заголовка: (тело партнёра, дом владельца) или ничего.

    `owner == "a"` — дома владельца аккаунта: `compatibility_result` строит
    расчёт от его рождения (`birth`), партнёр приходит как `other`, и оверлеи
    с этим владельцем — это тела партнёра в домах читателя. Ровно та
    ориентация, которую рисует W7: «*его* Солнце в *твоём* седьмом».
    """
    houses: dict[str, int] = {}
    for overlay in data.get("overlays") or []:
        if overlay.get("owner") == "a" and overlay.get("body") in PRIORITY_BODIES:
            houses[overlay["body"]] = overlay["house"]
    for house in PRIORITY_HOUSES:
        for body in PRIORITY_BODIES:
            if houses.get(body) == house:
                return body, house
    return None


def compose(
    *,
    partner_id: str,
    name: str | None,
    locale: str | None,
    factor: tuple[str, int] | None,
) -> Push:
    """Один пуш, готовый для любого из двух вендоров.

    Payload несёт `type: "pair_ready"` — клиент уже шлёт `push_opened{type}`
    по тапу (`mobile … main.dart`), — и `profile_id` партнёра, чтобы однажды
    открывать отчёт сразу, минуя список пар. `collapse_id` схлопывает повтор
    по той же паре, если гонка всё же дошла до вендора дважды.
    """
    tongue = _base(locale)
    if factor is not None and name:
        body_name, house = placement(factor[0], locale or "en"), factor[1]
        title = HOUSE_TITLES[house][tongue].format(name=name, body=body_name)
    elif name:
        title = FALLBACK_TITLES[tongue].format(name=name)
    else:
        title = NAMELESS_TITLES[tongue]

    return Push(
        title_key=TITLE_KEY,
        body_key="push.pair.ready",
        title=title,
        body=BODIES[tongue],
        thread="pair",
        # **Свой канал Android, а не канал дневной заметки.** Канал — единица,
        # которую человек выключает; «не хочу гороскоп каждое утро» — обычное
        # и законное желание, «не говорите мне, что готово купленное за $4.99»
        # — нет. Раньше `fcm.message` шил `alma.daily` всем подряд, и первое
        # желание молча влекло второе. См. `transport.CHANNEL_TRANSACTIONAL`.
        channel=CHANNEL_TRANSACTIONAL,
        collapse_id=f"pair-{partner_id}"[:64],
        # Не «до вечера», как у дневной заметки, но и не «никогда»: пустое поле
        # APNs читает как ноль — одна попытка и не хранить. См. DELIVERY_WINDOW.
        expires_at=utcnow() + DELIVERY_WINDOW,
        data={"type": "pair_ready", "profile_id": partner_id},
    )


def _transports() -> Mapping[str, Transport]:
    """Сендеры по настроенным креденшалам. Функция — шов для тестов."""
    return {name: transport_for(name) for name in configured_platforms()}


def _factor_for(session_profile_self, partner_profile) -> tuple[str, int] | None:
    """Фактор из расчёта совместимости — тем же вызовом, что и API.

    `compute_cached` с тем же процессным кэшем (`api.cache.result_cache`) и
    теми же опциями, что у `/systems/compatibility` по умолчанию, — значит,
    ключ кэша совпадает и к моменту покупки расчёт обычно уже готов: человек
    только что смотрел на пару. Импорты внутри вызова, чтобы модуль пуша не
    тянул расчётный слой при импорте (`daily.py` так же прячет своих).
    """
    from ..api.cache import result_cache
    from ..calc.cache import compute_cached
    from ..daily.service import birth_of

    result = compute_cached(
        "compatibility",
        birth_of(session_profile_self),
        cache=result_cache(),
        other=birth_of(partner_profile),
        house_system="placidus",
    )
    return pick_factor(result.data)


async def report_ready(
    session: AsyncSession,
    user: User,
    *,
    partner_id: str,
    source: str,
    transports: Mapping[str, Transport] | None = None,
) -> str:
    """Отправить владельцу гранта пуш «отчёт пары готов» — не больше одного.

    Возвращает слово для лога и тестов; никогда не поднимает исключение выше
    себя — этот вызов стоит внутри платёжных путей, и любое «не смогли
    уведомить» обязано стоить строки в логе, а не денег или гранта. Порядок
    отказов — дешёвые и про человека раньше дорогих и про небо, как в
    `rules.may_send`.
    """
    if source not in PAID_SOURCES:
        # Тестовый или ручной грант. Тишина — решение, записанное в PAID_SOURCES.
        log.debug("pair push skipped for %s: source %r is not a sale", user.id, source)
        return "skipped: source"

    # **Грант проверяется здесь, а не только у зовущего.** Все три вызова стоят
    # сразу за строкой, которая грант выписала, — но это соглашение, а не
    # правило: перестановка двух строк в чужом файле, ранний `return` на
    # ветке отказа, четвёртый путь оплаты, написанный по образцу третьего, — и
    # «ваш отчёт готов» уезжает человеку, у которого отчёта нет. Он открывает
    # пуш и упирается в пейволл за то, что ему только что пообещали. Проверка
    # стоит одного SELECT по строкам, которые тот же запрос уже трогал, и
    # делает «не может уйти тому, кто не покупал» свойством этого модуля, а не
    # свойством порядка строк в трёх других.
    from ..auth import entitlements

    if partner_id not in await entitlements.unlocked_pairs(session, user):
        log.warning(
            "pair push for %s refused: no live pair grant for %s (source %r)",
            user.id, partner_id, source,
        )
        return "skipped: no grant"

    if transports is None:
        transports = _transports()
    if not transports:
        # Не `PushUnavailable`, и это главное расхождение с daily.run — см.
        # модульный докстринг: пуш здесь побочный эффект платежа.
        log.info(
            "pair push for %s not sent: no push transport is configured", user.id
        )
        return "no transport"

    devices = await token_store.for_user(session, user.id)
    reachable = [d for d in devices if d.platform in transports]
    if not reachable:
        # Нет токенов — человек не включал уведомления или выключил их
        # (off — это удаление строк, `routers/notify.py`). Не ошибка вовсе.
        log.debug("pair push for %s: no reachable devices", user.id)
        return "unreachable"

    # Занять пару до отправки — как `daily.claim`, и с тем же смыслом: второй
    # путь (нотификация магазина вслед за /verify, вторая покупка того же
    # партнёра) увидит строку и промолчит. Savepoint, а не commit: транзакция
    # запроса не наша, рвать её на свои коммиты нельзя; проигранная гонка двух
    # процессов упрётся в первичный ключ на коммите — цена та же, что описана
    # в `credits.ensure_period`: один повтор доставки, ничего потерянного.
    row = UsageCounter(
        id=counter_key(user.id, partner_id),
        user_id=user.id,
        day=utcnow().date(),
        metric=METRIC,
        count=0,
        amount=0.0,
    )
    try:
        async with session.begin_nested():
            session.add(row)
    except IntegrityError:
        return "already"

    try:
        push = await _composed(session, user, partner_id, reachable)
        delivered = False
        for device in reachable:
            transport = transports[device.platform]
            try:
                receipt = await transport.send(device, push)
            except Exception as exc:
                # Оборванный сокет — ответ про одно устройство, а не про
                # человека: второй телефон обязан быть опрошен. Тот же довод,
                # что в `daily.deliver`, и та же трактовка — `retry`: про токен
                # ничего не узнали, строку не трогаем.
                log.warning(
                    "pair push device %s (%s) unreachable: %s",
                    device.id, device.platform, exc,
                )
                receipt = Receipt(Verdict.retry, exc.__class__.__name__, str(exc)[:200])
            outcome = await token_store.retire(session, device, receipt)
            if receipt.verdict is Verdict.sent:
                delivered = True
            elif receipt.verdict is Verdict.fatal:
                # У дневного джоба fatal останавливает весь прогон; здесь
                # прогона нет — есть один человек, и продолжать по его же
                # устройствам тем же креденшалом бессмысленно.
                log.warning(
                    "pair push: %s refused with %s (%s) — giving up on this "
                    "platform", device.platform, receipt.reason, receipt.detail,
                )
                break
            else:
                log.info(
                    "pair push device %s (%s): %s → %s",
                    device.id, device.platform, receipt.reason, outcome,
                )
    except Exception:
        # Ничего из платёжного пути не должно упасть из-за пуша. Строку
        # отдаём обратно, если сессия ещё жива, — чтобы повтор доставки события
        # мог попробовать снова; если сессия отравлена, откат сделает запрос.
        log.warning("pair push for %s failed", user.id, exc_info=True)
        try:
            await session.delete(row)
            await session.flush()
        except Exception:
            pass
        return "errored"

    if delivered:
        # Строка становится записью о доставленном. Без commit — его сделает
        # платёжная транзакция, внутри которой мы живём.
        row.count = 1
        await session.flush()
        return "sent"

    # Ни один вендор не принял. Вернуть пару: повтор события (магазин ретраит
    # нотификации, клиент ретраит verify) получит право попробовать ещё раз —
    # «максимум один пуш» считает доставленные, а не попытки.
    await session.delete(row)
    await session.flush()
    log.info("pair push for %s: no vendor accepted it", user.id)
    return "failed"


async def _composed(session: AsyncSession, user: User, partner_id: str, devices) -> Push:
    """Собрать текст: имя и фактор, а честный запасной — если их не из чего.

    Локаль — правилом дневной заметки (`daily.due`): язык последнего живого
    устройства, потом язык аккаунта. Фактор считается в try: упавший расчёт —
    это запасной текст, а не пропавший пуш.
    """
    newest = max(devices, key=lambda d: as_utc(d.last_seen_at) or utcnow())
    locale = newest.locale or user.locale

    partner = await session.get(Profile, partner_id)
    if partner is None or partner.user_id != user.id:
        # Профиль удалён (грант живёт дольше профиля — А7 §12) или строка
        # гранта указывает на чужой профиль: чужое имя в пуш не попадает.
        return compose(partner_id=partner_id, name=None, locale=locale, factor=None)

    factor: tuple[str, int] | None = None
    try:
        from ..daily.service import self_profile

        mine = await self_profile(session, user)
        if mine is not None and mine.id != partner.id:
            factor = _factor_for(mine, partner)
    except Exception as exc:
        # Расчёт недоступен или упал (нет эфемерид, двусмысленное время,
        # кривые координаты) — фактор не выдумывается, текст остаётся честным.
        log.info("pair push factor unavailable for %s: %s", user.id, exc)

    return compose(
        partner_id=partner_id, name=partner.name, locale=locale, factor=factor
    )
