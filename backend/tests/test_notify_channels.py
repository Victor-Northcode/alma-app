"""Канал Android и маршрут тапа — два поля, каждое из которых уже ломалось.

**Канал.** На Android канал — это единица, которую человек выключает, и до
этой правки `fcm.message` шил `channel_id="alma.daily"` **всем** уведомлениям:
пуш «отчёт пары готов» ехал по каналу дневной заметки, то есть выключивший
утренний гороскоп молча переставал узнавать о собственных покупках. Хуже того,
на API 26+ уведомление в канал, которого приложение не заводило, система
выбрасывает без следа на устройстве — поэтому идентификатор здесь сверяется
строкой, а не «каким-нибудь непустым».

**Тип.** Клиент читает `payload['type']` — и `AppDelegate.swift`, который
поднимает наверх строковые поля `userInfo`, и `main.dart`, который пишет
`push_opened{type}`. Дневная заметка клала `kind` (имя из `docs/PUSH.md §1.6`,
которого на телефоне никогда не искали), пуш пары — `type`. То есть половина
тапов считалась с пустым типом, и открыть по такому пушу было нечего.

Ни один вендор не поднимается: `FCM.message` и `APNs.payload` — чистые функции
над `Push`, ровно затем, чтобы каждую строку конверта можно было проверить без
сокета и без креденшала.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from alma.i18n.placements import LOCALES
from alma.notify import message, pair
from alma.notify.apns import APNs
from alma.notify.fcm import FCM
from alma.notify.rules import Chosen
from alma.notify.transport import CHANNEL_DAILY, CHANNEL_TRANSACTIONAL, Push

from test_notify_daily import Contact


class Row:
    """Строка `DeviceToken` в объёме, который читает конверт."""

    token = "z" * 140
    environment = "production"
    platform = "android"


def envelope(push: Push) -> dict:
    """Конверт FCM без конструктора: `FCM()` требует креденшалов, а `message` —
    чистая функция над `Push`, и проверять её без ключей владельца — весь смысл
    того, что она отдельный метод."""
    return FCM.message(FCM.__new__(FCM), Row(), push)


def headers_for(push: Push) -> dict:
    """То же самое со стороны Apple: заголовки без сокета и без ключа."""
    return APNs.headers(APNs.__new__(APNs), Row(), push, bearer="test")


def a_daily() -> Push:
    return message.compose(
        Chosen(Contact(), "exact"),
        zone=ZoneInfo("Europe/Warsaw"),
        local=datetime(2026, 8, 7, 10, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        locale="en",
        teaser="Saturn squares your Sun at 14:20.",
    )


def a_pair() -> Push:
    return pair.compose(
        partner_id="abc123", name="Marcus", locale="en", factor=("sun", 7)
    )


# ── канал ──────────────────────────────────────────────────────────────────


def test_the_daily_and_the_pair_push_do_not_share_a_channel():
    """Разные обещания читателю — разные выключатели.

    «Не хочу гороскоп каждое утро» — обычное и законное желание. «Не говорите
    мне, когда готово то, за что я заплатил» — нет, и одно не имеет права
    означать другое.
    """
    daily = envelope(a_daily())
    report = envelope(a_pair())
    assert daily["message"]["android"]["notification"]["channel_id"] == CHANNEL_DAILY
    assert (
        report["message"]["android"]["notification"]["channel_id"]
        == CHANNEL_TRANSACTIONAL
    )
    assert CHANNEL_DAILY != CHANNEL_TRANSACTIONAL


def test_the_channel_travels_on_the_push_rather_than_being_stamped_by_the_sender():
    """Категория — решение того, кто составляет уведомление, а не отправителя.

    Сендер, выбирающий канал, — это сендер, решающий, что человеку разрешено
    выключить. Здесь это проверяется третьим, выдуманным каналом: если он
    доезжает до конверта нетронутым, значит поле действительно ведущее, а не
    декоративное рядом с константой в `fcm.py`.
    """
    invented = Push(title_key="t", body_key="b", channel="alma.something.else")
    built = envelope(invented)
    assert (
        built["message"]["android"]["notification"]["channel_id"]
        == "alma.something.else"
    )


def test_a_push_built_without_a_channel_is_a_daily_rather_than_nowhere():
    """Пустое поле на Android хуже неверного: уведомление исчезает молча.

    Поэтому у `Push.channel` есть значение по умолчанию, а у сендера — пол под
    ним. Пуш, собранный кодом, который про каналы не знал, попадает в канал
    дневной заметки — единственный, который приложение точно завело.
    """
    built = envelope(Push(title_key="t", body_key="b"))
    assert built["message"]["android"]["notification"]["channel_id"] == CHANNEL_DAILY


def test_the_channel_never_leaks_into_the_apple_payload():
    """Каналов у iOS нет, и придуманный ключ внутри `aps` — это 400 от Apple."""
    payload = APNs.payload(a_pair())
    assert "channel" not in payload
    assert "channel_id" not in payload
    assert "channel_id" not in payload["aps"]


# ── маршрут тапа ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "push,expected",
    [(a_daily(), "daily"), (a_pair(), "pair_ready")],
)
def test_every_push_names_its_type_under_the_key_the_client_reads(push, expected):
    """`type`, потому что `type` — это то, что читает телефон.

    Дневная заметка клала `kind`, и `push_opened` считался с пустым типом: тап
    доезжал, а лестница §7 не могла сказать, с какого пуша человек пришёл.
    """
    assert push.data["type"] == expected
    assert "kind" not in push.data


@pytest.mark.parametrize("push", [a_daily(), a_pair()])
def test_the_type_survives_both_envelopes_as_a_top_level_string(push):
    """У Apple — рядом с `aps`, у Google — в `data`, и обязательно строкой.

    `AppDelegate.swift` поднимает наверх только строковые поля верхнего уровня
    `userInfo`, а FCM отказывает нестроковому значению в `data` целиком
    (`INVALID_ARGUMENT`) — то есть нестрока здесь стоила бы либо потерянного
    маршрута, либо всей отправки на Android.
    """
    apple = APNs.payload(push)
    assert apple["type"] == push.data["type"]
    assert "type" not in apple["aps"], "чужой ключ внутри `aps` — это 400"

    google = envelope(push)
    assert google["message"]["data"]["type"] == push.data["type"]
    assert all(isinstance(value, str) for value in google["message"]["data"].values())


def test_the_pair_push_carries_the_profile_the_tap_has_to_open():
    """Тип говорит «куда», `profile_id` — «что именно»: без него открывается
    список пар, а человек только что купил конкретный отчёт."""
    push = a_pair()
    assert push.data["profile_id"] == "abc123"
    assert push.collapse_id == "pair-abc123"


def test_the_daily_carries_the_local_day_it_is_about():
    """Дата — местная, а не UTC: по ней открывается «Сегодня», и в Окленде эти
    две расходятся треть каждых суток."""
    assert a_daily().data["date"] == "2026-08-07"


# ── срок жизни ─────────────────────────────────────────────────────────────


def test_the_pair_push_asks_apns_to_hold_it_rather_than_to_drop_it():
    """Пустой `apns-expiration` — это не «не протухает», а ноль.

    У APNs отсутствие заголовка равно «одна попытка и не хранить»: человек,
    купивший отчёт и убравший телефон с севшей батареей, не узнавал о покупке
    никогда — а строка `UsageCounter` при этом уже подтверждена, потому что
    вендор ответил «принял».
    """
    push = a_pair()
    assert push.expires_at is not None
    headers = headers_for(push)
    assert int(headers["apns-expiration"]) > 0

    # Двенадцать часов FCM остаются потолком — `ttl` там считается от отправки.
    assert envelope(push)["message"]["android"]["ttl"] == "43200s"


def test_the_daily_expires_with_the_day_it_describes():
    """Заметка про сегодня, доставленная в 23:40, — про день, который уже был."""
    push = a_daily()
    assert push.expires_at is not None and push.expires_at.hour == 22
    assert push.expires_at.date().isoformat() == push.data["date"]


# ── семь языков пуша пары ──────────────────────────────────────────────────
#
# У дневной заметки строки живут в бандле клиента и сверяются
# `test_notify_strings.py`. У пуша пары их там нет намеренно (имя партнёра в
# ключ бандла не подставить), предложение собирает сервер — значит все семь
# локалей обязаны быть здесь, и проверить их может только этот файл.


@pytest.mark.parametrize("locale", LOCALES)
def test_every_locale_has_every_line_the_pair_push_can_need(locale):
    for house, row in pair.HOUSE_TITLES.items():
        assert locale in row and row[locale].strip(), f"дом {house}"
    for table, what in (
        (pair.FALLBACK_TITLES, "запасной заголовок"),
        (pair.NAMELESS_TITLES, "заголовок без имени"),
        (pair.BODIES, "тело"),
    ):
        assert locale in table and table[locale].strip(), what


@pytest.mark.parametrize("locale", LOCALES)
def test_no_placeholder_survives_into_the_composed_line(locale):
    """Подстановка — не «есть строка», а «в строке не осталось скобок».

    Незакрытый `{name}` на локскрине выглядит как сломанное приложение, и
    поймать его может только сборка настоящего пуша в каждой из семи локалей.
    """
    with_factor = pair.compose(
        partner_id="p", name="Marcus", locale=locale, factor=("sun", 7)
    )
    fallback = pair.compose(partner_id="p", name="Marcus", locale=locale, factor=None)
    nameless = pair.compose(partner_id="p", name=None, locale=locale, factor=None)

    for push in (with_factor, fallback, nameless):
        assert "{" not in push.title and "}" not in push.title
        assert "{" not in push.body and "}" not in push.body
        assert push.title.strip() and push.body.strip()

    assert "Marcus" in with_factor.title and "Marcus" in fallback.title
    assert "Marcus" not in nameless.title, "чужого имени в пуше не бывает"


@pytest.mark.parametrize("reported", ["it-IT", "pt_BR", "ru-RU", "de-AT", "klingon", "", None])
def test_a_device_language_shaped_however_the_platform_likes_it_still_composes(reported):
    """Клиенты отдают тег в своей форме; неизвестный — это английский, а не 500.

    Одно слово не на том языке — куда меньшая беда, чем `KeyError` внутри
    платёжного пути, который в этот момент выписывает грант.
    """
    push = pair.compose(partner_id="p", name="Marcus", locale=reported, factor=("moon", 5))
    assert push.title.strip() and push.body.strip()
    assert "{" not in push.title


@pytest.mark.parametrize(
    "locale,expected",
    [
        ("en", "Exact today"),
        ("it-IT", "Esatto oggi"),
        ("ru", "Точный аспект сегодня"),
        ("pt_BR", "Aspecto exato hoje"),
        ("klingon", "Exact today"),
    ],
)
def test_the_daily_headline_arrives_written_rather_than_as_a_key(locale, expected):
    """Ключ разрешается в нативном бандле, которого у порта нет.

    `.arb` компилируются в Dart, iOS смотрит в `Localizable.strings`, и такого
    файла в дереве нет вовсе (`knownRegions = (en, Base)`). Неразрешённый
    `title-loc-key` iOS показывает **сырой строкой**: каждая заметка приезжала
    бы с заголовком `push.daily.title`.
    """
    push = message.compose(
        Chosen(Contact(), "exact"),
        zone=ZoneInfo("Europe/Warsaw"),
        local=datetime(2026, 8, 7, 10, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        locale=locale,
        teaser="…",
    )
    assert push.title == expected
    assert APNs.payload(push)["aps"]["alert"]["title"] == expected
    assert envelope(push)["message"]["android"]["notification"]["title"] == expected
    # Ключ никуда не делся: вернуть дизайн «ключ, а не предложение» — это одна
    # строка в `compose`, как только в бандле появится каталог.
    assert push.title_key == message.TITLE_KEY


def test_the_body_of_the_pair_push_is_a_sentence_and_not_a_key():
    """Ключей пары в замороженном бандле нет: рядом с предложением не должно
    остаться ни `loc-key`, ни `body_loc_key`, иначе на локскрине покажется сырая
    строка ключа."""
    push = a_pair()
    alert = APNs.payload(push)["aps"]["alert"]
    assert alert["title"] == push.title and "title-loc-key" not in alert
    assert alert["body"] == push.body and "loc-key" not in alert

    android = envelope(push)
    notification = android["message"]["android"]["notification"]
    assert notification["title"] == push.title and "title_loc_key" not in notification
    assert notification["body"] == push.body and "body_loc_key" not in notification
