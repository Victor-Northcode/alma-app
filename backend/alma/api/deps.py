"""Shared request plumbing: who is asking, and what they may see.

Guest-first was a deliberate design and most of it is right: a person can use
the whole product before they have decided to tell us anything, the guest **is**
an account rather than a session that gets migrated later, and signing in
attaches an identity to the row that already exists. None of that changes here.

What changed is **when the row appears**, and it was wrong in a way that made
every per-account number in the business a different number from the one it was
named after. `current_user` minted an account for any request that arrived
without a token, and `POST /v1/events` — the funnel beacon, fired by the landing
page on mount — went through it like everything else. So a browser that loaded
the site and touched nothing left an account behind. The dev database showed 143
users against 46 profiles: two thirds of the accounts had never saved a birth,
because they were page views.

The rule now:

* **`visitor` never creates anything.** It answers with the account behind the
  token, or with nothing. Measurement uses it, and so should anything else whose
  answer is the same whether or not a row exists. Two routes take it today:
  `POST /v1/events`, the beacon the landing fires on mount, and
  `GET /v1/billing/catalogue`, which the landing's pricing section fetches on
  mount as well. The second was found after the first was fixed and is the
  reason this list exists rather than a sentence naming one route: the rule is
  about *every* call a page view makes, and blaming the loudest one left a
  quieter one minting the same rows through a different door.
* **`current_user` still mints, and that is now a statement about the route
  rather than about the request.** A route that depends on it is a route where
  something is being kept — a birth saved, a sign-in landed, a purchase
  verified — and minting there is the account being created *by an act*.
* **The anonymous id is claimed at exactly that moment.** The request that mints
  the account is the request that came from that browser, which is the only
  moment the join between the two is a fact rather than a guess. See
  `funnel.claim`; without it, the stages recorded before the account and the
  stages recorded after it are two people, and the conversion rate the pricing
  model rests on reads as zero.
* **Сколько строк может появиться, тоже имеет предел.** «Когда» без «сколько» —
  половина правила: каждый месячный бюджет отмерян на `user.id`, а `user.id`
  выдавался по одному HTTP-вызову, так что ротация гостей брала столько
  бюджетов, сколько раз позвонила. Потолок стоит по источнику запроса — см.
  `GUEST_MINTS_PER_HOUR` и `request_source`.
* **И этот потолок общий для всех рабочих процессов.** Он был не общим: счёт
  жил в памяти воркера, восемь воркеров давали восьмикратную норму, а выкладка
  обнуляла её целиком. Счёт переехал в базу — `SharedWindow` и таблица
  `rate_window`; в памяти осталось только то, что умеет отказывать быстро.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import time
from datetime import date as date_type
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import funnel, region
from ..auth import accounts, tokens
from ..auth.accounts import AccountDeleted
from ..calc import BirthData
from ..db import User, get_session
from ..db import counters
from ..db.models import Profile
from ..geo import is_known_timezone
from .schemas import BirthInput

log = logging.getLogger("alma.api.deps")

#: The header a client reads to pick up a freshly minted guest token.
ISSUED_TOKEN_HEADER = "X-Alma-Token"


# ── откуда пришёл запрос, и сколько раз оттуда уже приходили ───────────────
#
# Три потолка в этом сервисе (гости здесь, письма входа в `routers/auth.py`,
# события анонима в `routers/events.py`) считаются по «источнику запроса», и
# все три — про одно: то, что клиент назначает себе сам, потолком быть не
# может. Токен гостя выдаётся любому, `X-Alma-Anon` клиент генерирует
# сам, адрес в теле письма пишет тоже он. Единственное, что остаётся, —
# сетевой адрес, с которого пришло соединение.

#: Заголовки, которыми край (CDN, балансировщик) сообщает адрес клиента.
#:
#: Все четыре **перезаписываются** краем поверх присланного клиентом — это то
#: же основание, на котором `region.py` верит `CF-IPCountry`. `X-Forwarded-For`
#: намеренно не в списке, хотя он первый, о котором думают: прокси его
#: **дописывают**, а не перезаписывают, поэтому первый элемент цепочки — текст,
#: сочинённый вызывающим, и потолок по нему снимается одной строкой заголовка.
CLIENT_IP_HEADERS: tuple[str, ...] = (
    "cf-connecting-ip",    # Cloudflare
    "true-client-ip",      # Cloudflare Enterprise, Akamai
    "fastly-client-ip",    # Fastly
    "x-real-ip",           # nginx, Traefik
)

#: Сказано ли уже в лог, что источник запросов неразличим. Один раз на процесс:
#: это свойство деплоя, а не запроса, и строка на каждый запрос утонет.
_warned_about_source = False


def request_source(request: Request) -> str:
    """Кто стучится, с точки зрения потолков. Никогда не пусто.

    Край, если он есть, иначе адрес сокета. **Заголовок здесь — не дыра, а
    заявленное допущение деплоя**: край перезаписывает его поверх присланного
    клиентом, ровно как `CF-IPCountry`, на котором уже стоит вся ценовая логика.
    Сервис, выставленный в интернет напрямую, этих заголовков не получает — и
    тогда любой может их прислать; поэтому если края нет, его не должно быть и в
    списке выше. Это решение владельца деплоя, а не свойство кода.

    Обратный случай — адрес сокета, оказавшийся петлёй или приватной сетью при
    молчащем крае: значит, перед нами прокси, который не представился, и **все
    клиенты мира сложились в один ключ**. Потолок тогда бьёт по живым людям, а
    не по скрипту, и это надо увидеть в логе, а не по жалобам. Тот же приём, что
    `region.observe`: два состояния, неразличимые на проводе, разведены строкой.
    """
    global _warned_about_source

    for name in CLIENT_IP_HEADERS:
        value = (request.headers.get(name) or "").split(",")[0].strip()
        if value:
            return value

    peer = request.client.host if request.client else ""
    if not peer:
        return "unknown"

    if not _warned_about_source:
        try:
            address = ipaddress.ip_address(peer)
        except ValueError:  # TestClient шлёт «testclient», это не адрес
            address = None
        if address is not None and (address.is_loopback or address.is_private):
            _warned_about_source = True
            log.warning(
                "requests arrive from %s and no edge header names the client: "
                "per-source ceilings are counting everybody as one caller — "
                "set one of %s at the proxy",
                peer,
                ", ".join(CLIENT_IP_HEADERS),
            )
    return peer


class SharedWindow:
    """Сколько раз этот ключ приходил за окно. Счёт — в базе, один на всех.

    **Раньше он жил в памяти процесса, и потолка фактически не было.** Прод —
    это `gunicorn` по числу ядер: на восьмиядерной машине восемь процессов, у
    каждого свой словарь, и «тридцать гостей в час с адреса» превращалось в
    двести сорок. Выкладка обнуляла и это: `docker compose up -d --build`
    поднимает новые процессы с чистыми счётчиками, то есть потолок снимался
    каждым деплоем. Оба свойства были записаны в прежнем докстринге как
    осознанный компромисс — компромисс перестал быть честным ровно тогда, когда
    воркеров стало больше одного.

    **Общее хранилище — наша же база, и никакого Redis.** Строка на
    (ограничитель, окно, отпечаток ключа), увеличение — один
    `INSERT … ON CONFLICT DO UPDATE … RETURNING` (`db/counters.hit_window`), то
    есть без окна между чтением и записью. Отдельная таблица `rate_window`, а
    не `usage_counter`: у того `user_id` — внешний ключ в `user`, а всё, что
    здесь ограничивают, случается до аккаунта или вместо него (довод целиком —
    в докстринге модели).

    **Дёшево оно за счёт памяти, но памяти, которая умеет только отказывать.**
    Процесс помнит последнее, что база сказала про ключ в текущем окне; если
    там уже потолок — отказ выдаётся без единого запроса, и скрипт, который
    крутит тысячу запросов в секунду, стоит нам одной записи в словарь. Память
    **никогда не пропускает** — пропустить может только база, — иначе мы бы
    вернули ровно те же попроцессные потолки, от которых уходим.

    Окно фиксированное, а не скользящее, и его номер — это `время // длина`, то
    есть одно и то же число во всех процессах и после перезапуска. На стыке
    окон пропускается до двойного лимита; цена та же, что была, и она куплена
    за одну строку на ключ вместо списка отметок.

    `max_keys` — про память процесса: словарь, растущий по числу адресов, сам
    стал бы способом уронить сервис.
    """

    __slots__ = ("name", "limit", "seconds", "max_keys", "_seen")

    def __init__(
        self, *, name: str, limit: int, seconds: float, max_keys: int = 20_000
    ) -> None:
        self.name = name
        self.limit = limit
        self.seconds = seconds
        self.max_keys = max_keys
        #: **отпечаток** → (номер окна, что база ответила в последний раз).
        #: Только для отказа; см. докстринг. Отпечаток, а не сам источник:
        #: словарь на двадцать тысяч живых адресов в памяти каждого воркера — то
        #: же хранение IP, только без таблицы.
        self._seen: dict[str, tuple[int, int]] = {}

    def _window_index(self, now: float) -> int:
        return int(now // self.seconds)

    def digest(self, key: str) -> str:
        """Отпечаток источника — **под секретом**, иначе это не отпечаток.

        Сюда приходит сетевой адрес или почтовый ящик, а таблица потолков с
        живыми адресами посетителей — это то самое хранение IP, которого
        privacy-страница обещает не делать.

        **`key=` обязателен, и его отсутствие здесь стоило проверки.** Первая
        версия звала `blake2b` без секрета. Хеш без секрета не скрывает
        значение из маленького множества: IPv4 — это 2³², и на этой машине
        замерено 2,5 млн blake2b в секунду одним ядром, то есть всё
        пространство адресов перебирается за полчаса; проверявший восстановил
        `203.0.113.77` из сохранённого отпечатка. Номер окна в хеш не входит —
        он только в префиксе строки, — поэтому одна посчитанная таблица
        обращала бы **все** строки во всех окнах и навсегда. Дамп таблицы был
        бы журналом адресов посетителей с одним лишним шагом.
        Секрет — тот же, которым подписаны токены; так же поступает
        `billing/provider.py`.

        `person=` разводит одинаковые ключи разных ограничителей: один и тот же
        адрес в `guest_mint` и в `anon_events` обязан считаться отдельно, а
        сравнивать отпечатки разных ограничителей мы не должны уметь вовсе.
        """
        from ..config import settings

        return hashlib.blake2b(
            key.encode("utf-8", "replace"),
            key=settings().jwt_secret.encode("utf-8")[:64],
            digest_size=16,
            person=self.name.encode("utf-8")[:16],
        ).hexdigest()

    def row_id(self, digest: str, index: int) -> str:
        """Первичный ключ строки окна. Принимает **отпечаток**, а не источник.

        Подпись именно такая, чтобы сырой адрес нельзя было передать сюда по
        рассеянности: единственное место, где он превращается в отпечаток, —
        `digest` выше, и `hit` зовёт его один раз в самом начале.
        """
        return f"{self.name}:{index}:{digest}"

    def expiry(self, index: int) -> datetime:
        """Конец окна — то, что уходит клиенту в `Retry-After`."""
        return datetime.fromtimestamp((index + 1) * self.seconds, tz=timezone.utc)

    async def hit(self, session: AsyncSession, key: str) -> bool:
        """Засчитать обращение. `False` — потолок уже выбран.

        **Отказ не откатывает чужую работу и не нуждается в откате своей.** У
        HTTP-маршрута отказ — это `HTTPException`, а `session_scope` на любом
        исключении откатывает транзакцию целиком, унося и это увеличение. Счёт
        от этого не разъезжается: в базе остаётся ровно столько, сколько
        обращений было **пропущено**, а отказанные пересчитываются заново и
        снова упираются. Это и есть нужное свойство — потолок держится, а
        отказанные попытки не накручивают его дальше вверх.
        """
        now = time.time()
        index = self._window_index(now)

        # Отпечаток снимается первым делом, и дальше по функции живёт только он.
        # Память процесса тоже держала сырой ключ — до двадцати тысяч живых
        # адресов и почтовых ящиков в RSS каждого воркера, вычищаемых лишь при
        # переполнении и никогда по истечении окна. «Мы не храним адрес» — это
        # обещание про сервис, а не про одну таблицу.
        digest = self.digest(key)

        seen = self._seen.get(digest)
        if seen is not None and seen[0] == index and seen[1] >= self.limit:
            # Потолок этого окна уже известен выбранным. В базу не идём: это
            # тот самый путь, по которому ходит скрипт, и он обязан быть
            # бесплатным.
            return False

        count = await counters.hit_window(
            session,
            row_id=self.row_id(digest, index),
            expires_at=self.expiry(index),
        )
        self._remember(digest, index, count)
        return count <= self.limit

    def _remember(self, key: str, index: int, count: int) -> None:
        if len(self._seen) >= self.max_keys and key not in self._seen:
            self._forget_stale(index)
        self._seen[key] = (index, count)

    def _forget_stale(self, index: int) -> None:
        for key, (window_index, _count) in list(self._seen.items()):
            if window_index != index:
                del self._seen[key]
        if len(self._seen) >= self.max_keys:
            # Ни одно окно не истекло — значит, идёт наплыв с многих адресов.
            # Забываем всё: следующее обращение каждого из них сходит в базу,
            # где счёт цел, — то есть теряется скорость, а не потолок.
            self._seen.clear()


def window(request: Request, name: str, *, limit: int, seconds: float) -> SharedWindow:
    """Именованный ограничитель, живущий столько же, сколько приложение.

    На `app.state`, а не в модуле, и это не вкусовщина: модульный словарь
    переживает `create_app()`, а значит и тест, и один прогон набора выбрал бы
    потолок за всех остальных. Здесь у каждого приложения свои — и в проде их
    ровно одни на процесс, как и задумано.

    Потолок читается **на каждом вызове**, а не запоминается при создании:
    тесты подменяют числа через `monkeypatch.setattr`, а объект переживает
    запрос, и запомненное значение сделало бы подмену невидимой начиная со
    второго теста в файле.
    """
    counters_by_name: dict[str, SharedWindow] = getattr(
        request.app.state, "rate_windows", None
    )
    if counters_by_name is None:
        counters_by_name = {}
        request.app.state.rate_windows = counters_by_name
    found = counters_by_name.get(name)
    if found is None:
        found = counters_by_name[name] = SharedWindow(
            name=name, limit=limit, seconds=seconds
        )
    found.limit = limit
    found.seconds = seconds
    return found


#: Сколько гостевых аккаунтов один источник может завести за час.
#:
#: **Считаем по источнику, потому что деньги висят на `user.id`.** Месячные
#: потолки генераций (`free_month_budget` и соседи) — это столько-то долларов на
#: аккаунт, а аккаунт до этой правки стоил один запрос без токена: скрипт брал
#: столько бюджетов, сколько раз позвонил. Ограничивать по чему-то, что клиент
#: присылает сам (`X-Alma-Anon`, `User-Agent`, тело запроса), — значит просить
#: скрипт ограничить себя. Остаётся сеть.
#:
#: Число — компромисс, и он смещён в сторону живого человека. За одним адресом
#: сидит не один человек: CGNAT мобильного оператора, офис, университет,
#: институтский Wi-Fi — а продукт мобильный, и первая же минута нового человека
#: обязана быть без стены. Тридцать в час — это тридцать *новых* людей с одного
#: адреса в час; заметить это может разве что рекламный залп на общий NAT, а
#: скрипт упирается на тридцать первом. Точное значение — вопрос владельца:
#: ниже — риск отказать настоящему новичку, выше — дороже утечка.
GUEST_MINTS_PER_HOUR = 30
GUEST_MINT_WINDOW_SECONDS = 3600.0


# ── фоновые ходы беседы ────────────────────────────────────────────────────


#: Сколько недописанных ходов беседы воркер держит одновременно.
#:
#: Ход попадает сюда, когда клиент ушёл со `/chat/stream`, а генерация ещё идёт
#: (довод, почему её не отменяют, — в `readings.py`, в `finally` того маршрута).
#: Потолка не было вовсе, и это второй способ уронить воркер после потолка на
#: гостей: каждый брошенный ход держит корутину, соединение к модели и до
#: 40 секунд памяти под prompt, а бросить их можно ровно столько, сколько раз
#: удастся начать беседу и закрыть вкладку.
#:
#: Число считано от воркера, а не от вкуса. Пул базы у воркера — 20 постоянных
#: соединений (`db/session.POOL_SIZE`), ход берёт короткую транзакцию в трёх
#: местах, и на остановке мы обязаны дождаться их всех за
#: `app.STREAM_TURN_GRACE_SECONDS` = 100 с. Тридцать две брошенные генерации по
#: 10–40 с укладываются в это окно; сто — уже нет, и выкладка снова начала бы
#: терять оплаченные ответы, только теперь по своей вине.
MAX_BACKGROUND_TURNS = 32


class TurnRegistry:
    """Фоновые ходы беседы: сколько их, и как их дождаться при остановке.

    **Замена голому `set` в `readings.py`, и разница ровно в двух вещах.**
    Первая — счёт: сверх `MAX_BACKGROUND_TURNS` реестр кричит в лог, потому что
    столько брошенных генераций сразу означает, что окно остановки их больше не
    покрывает. Задачу он при этом всё равно берёт — почему именно так, написано
    у `admit`. Вторая — `drain`: множество, которое некому дождаться, при выкладке просто
    исчезает вместе с процессом, а вместе с ним исчезает и ответ, за который
    уже заплачено (`session_scope` внутри задачи получает `CancelledError` и
    откатывает расход, списанный вопрос и сам текст).

    Живёт здесь, а не в `readings.py`: `api/app.py` обязан уметь дождаться этих
    задач в `lifespan`, а импортировать роутер ради приватного имени — значит
    подписаться под тем, что имя не переименуют. Сегодня `readings.py` держит
    свой собственный `set` и владелец того файла может переехать сюда двумя
    строками — см. отчёт; `app._pending_turns` до тех пор ждёт оба.

    Слабых ссылок здесь нет намеренно: `asyncio` держит на задачи только их,
    и брошенная задача пропадает в сборщике мусора посреди генерации — то есть
    ровно тем способом, от которого всё это и уходит.
    """

    __slots__ = ("limit", "_tasks")

    def __init__(self, *, limit: int = MAX_BACKGROUND_TURNS) -> None:
        self.limit = limit
        self._tasks: set = set()

    def admit(self, task) -> bool:
        """Взять задачу под присмотр. `False` — мест больше нет, но она взята.

        **Ссылка берётся всегда, и потолок её не отменяет.** Сначала здесь было
        наоборот: сверх потолка задача не добавлялась вовсе. Это отменяло не
        нагрузку, а единственную гарантию, ради которой реестр и существует:
        `asyncio` держит на задачи только слабые ссылки, и задача, на которую
        никто не смотрит, пропадает в сборщике мусора посреди генерации. То есть
        отказ «беречь» ровно тридцать третий оплаченный ответ был бы способом
        потерять его гарантированно и непредсказуемо — вместо «потерять при
        остановке процесса, если она случится».

        Отказаться от задачи в этой точке нельзя ничем: модель уже позвана и
        оплачена, отмена — это деньги без ответа. Значит и потолок здесь может
        быть только громким, а не запретительным: `False` говорит «нас залило,
        посмотри в лог», и вызывающий волен на это посмотреть.

        Настоящее место для отказа — до генерации, на входе в беседу: там ещё
        ничего не стоило. Такого подпора сейчас нет, и это записано честно, а не
        сымитировано потолком, который срабатывает слишком поздно, чтобы
        что-нибудь сберечь.
        """
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        if len(self._tasks) > self.limit:
            log.error(
                "%d background conversation turns are running at once; the "
                "shutdown window is %s and may no longer cover them",
                len(self._tasks),
                MAX_BACKGROUND_TURNS,
            )
            return False
        return True

    def pending(self) -> set:
        """Копия множества — по ней безопасно ждать, пока оно меняется."""
        return set(self._tasks)

    def __len__(self) -> int:
        return len(self._tasks)


#: Реестр этого процесса. Модульный, а не на `app.state`, потому что ждать его
#: обязан `lifespan`, а тот получает `app` уже после того, как задачи начались.
STREAM_TURNS = TurnRegistry()


def local_sandbox() -> bool:
    """Можно ли показывать этому вызывающему внутренности сервиса.

    Один замок на два места — токен входа в теле ответа (`routers/auth.py`) и
    подробности готовности (`routers/health.py`). Две копии одного правила
    разъезжаются ровно тогда, когда правило ужесточают: чинят то место, о
    котором вспомнили.

    Оба условия разом: окружение из **белого списка** локальных и локальный же
    адрес сервиса. Белый список, а не чёрный: неизвестное имя окружения — повод
    молчать, а не считать его песочницей. Адрес — вторая половина: стенд,
    которому забыли сменить `ALMA_ENV`, обычно уже смотрит наружу, и по адресу
    это видно.
    """
    from ..config import settings

    config = settings()
    return config.environment.lower() in {
        "development",
        "dev",
        "local",
        "test",
    } and ("localhost" in config.base_url or "127.0.0.1" in config.base_url)

#: The header a client *sends* to say which browser or installation this is,
#: when it has no account yet.
#:
#: It is never minted here, and that is not an oversight. A server that issued
#: it would issue one per request that arrived without one — and the very first
#: thing the landing does is fire a beacon while three other calls are in
#: flight, so a single visitor would collect four ids and appear four times at
#: the top of the funnel. A client that generates its own has exactly one before
#: it makes its first request. `funnel.clean_anon_id` is what stops that being a
#: free-text field.
ANON_ID_HEADER = "X-Alma-Anon"


def get_provider():
    """The model provider, as a dependency so tests can substitute one.

    Everything above the AI layer takes its provider through here, which is
    what lets the whole generation path — prompts, validation, regeneration,
    refusal — run in CI against a scripted provider with no key and no
    network.

    Constructed lazily rather than eagerly. FastAPI resolves every dependency
    before the route body runs, so building the provider here would make an
    unconfigured API key outrank the paywall: asking for a chapter you have
    not bought would answer "the AI is unavailable" instead of "this is
    locked". Returning a factory puts the entitlement check first, where it
    belongs.
    """
    from ..ai.provider import ModelUnavailable, default_provider

    def build():
        try:
            return default_provider()
        except ModelUnavailable as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "ai_unavailable", "message": str(exc)},
            ) from exc

    return build


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def anonymous_id(
    x_alma_anon: Annotated[str | None, Header()] = None,
) -> str | None:
    """The caller's own id for this browser or installation, if it sent one.

    Validated in `alma/funnel.py` rather than here, because that module is
    where the rule about what may be written to that table lives and a second
    copy of it is a second thing to get wrong. Anything unrecognisable comes
    back as `None`, which callers treat as "did not send one".
    """
    return funnel.clean_anon_id(x_alma_anon)


AnonymousId = Annotated[str | None, Depends(anonymous_id)]


async def edge_country(request: Request, response: Response) -> str | None:
    """Which country the network says this request came from, or `None`.

    A dependency rather than a line in each route, because the country is a
    property of the request and every route that prices anything needs the same
    answer to it. The rule about *which* header and whose word wins lives in
    `alma/region.py`; this is only the wire into FastAPI.

    Nothing here fails. An edge that did not set a header, a value that is not a
    country code, and Cloudflare's own `XX` for an address it could not place
    all come back as `None`, which every caller already handles: `currency_for`
    answers USD, and USD is a stated fallback rather than a guess.

    **The `Vary` is not decoration.** `GET /v1/billing/catalogue` is a plain
    cacheable GET whose body now depends on a request header, which is the exact
    shape of the bug where a CDN serves one country's prices to the next
    country's visitor — a wrong price, shown confidently, to somebody about to
    decide to spend money. Nothing caches this today, and that is precisely why
    it has to be declared here rather than remembered on the day somebody puts a
    cache in front of the API. `append` rather than assignment because the CORS
    middleware writes its own `Vary: Origin` on credentialed responses, and an
    overwrite would trade one cache poisoning for another.
    """
    for name in region.EDGE_COUNTRY_HEADERS:
        response.headers.append("Vary", name)
    country = region.from_headers(request.headers)
    # Counted, and warned about once, so that a deployment with no edge in front
    # of it can be told apart from one where everybody genuinely is in the
    # United States. See `region.observe` — the two answers look identical on
    # the wire and only one of them is a working configuration.
    region.observe(country)
    return country


#: The country the network reports. Routes that also accept a client-supplied
#: one pass both through `region.resolve`, which prefers this — see the security
#: note there.
EdgeCountry = Annotated[str | None, Depends(edge_country)]


#: The header a client *sends* to say which zone the **device** is in, as
#: opposed to the zone somebody was born in. All three clients already attach it
#: to every call — `AlmaClient.swift`, `alma_client.dart` and `AlmaHttp.kt` each
#: hold the same name against `TimeZone.current` and its two equivalents — so
#: this arrives on requests that have nothing to do with notifications, which is
#: the point of taking it here rather than in one route.
DEVICE_TIMEZONE_HEADER = "X-Alma-Timezone"


async def device_timezone(
    x_alma_timezone: Annotated[str | None, Header()] = None,
) -> str | None:
    """Which clock this installation is on, or `None`.

    A dependency rather than a line in one route, because `docs/PUSH.md §3` and
    `THE-DAILY.md §6.8` both asked for it here and the reason is not tidiness:
    the zone is a property of the request, every call carries it, and a person
    who flies is caught by whichever call they make first rather than by the one
    route that happened to read the header itself.

    **`Profile.timezone` is the birth zone and is not this.** Somebody born in
    Auckland who now lives in Berlin has `Profile.timezone == "Pacific/Auckland"`
    and nothing else in the system knows they moved; using it as the delivery
    clock sends a good-morning piece at 20:00 (`THE-DAILY.md §3.1`). This header
    is the only thing that knows better.

    Nothing here fails. Absent, blank, or a zone this machine's `tzdata` has
    never heard of all come back as `None`, exactly as the country header does:
    a client on an old Android should lose the optimisation, not the request.

    **Reading it is half the contract; the other half is persisting it.** The
    job that sends at 08:00 local runs at 03:00 on a server with no request to
    read a header from, so `POST /v1/notifications/devices` writes this onto the
    device row — see `notify/tokens.register`. That is also why there is no
    `Vary` here, unlike `edge_country`: no cacheable GET's body depends on it.
    """
    candidate = (x_alma_timezone or "").strip()
    if candidate and is_known_timezone(candidate):
        return candidate
    return None


#: The device's own zone, validated, or `None`. The ladder that decides which
#: clock actually wins — this, then a zone chosen in settings, then birth —
#: lives in `notify/rules.zone_for`, not here.
DeviceTimezone = Annotated[str | None, Depends(device_timezone)]


async def visitor(
    request: Request,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """The account behind this request, or nothing. Creates no rows.

    A missing, expired or forged token is not an error — it is somebody who has
    not given us anything yet. Refusing it would put a sign-in wall in front of
    a product whose entire first impression depends on there not being one; and
    inventing an account for it is what this dependency exists to not do.

    A *deleted* account is the one hard answer: 410, so the client drops the
    token instead of silently becoming somebody new.
    """
    raw = tokens.bearer(authorization) or request.cookies.get("alma_token")
    if not raw:
        return None

    try:
        user = await accounts.resolve(session, tokens.subject(raw))
    except tokens.InvalidToken:
        return None
    except AccountDeleted as exc:
        raise HTTPException(status.HTTP_410_GONE, detail=str(exc)) from exc

    if user is not None:
        await accounts.touch(session, user)
    return user


Visitor = Annotated[User | None, Depends(visitor)]


def _minted_locale(accept_language: str | None) -> str:
    """The language a brand-new guest starts life in.

    `create_guest` used to default every row to English, and the default was
    load-bearing in the worst way: `user.locale` feeds the partner-limit
    refusal, the purchase receipt and the daily's fallback, and none of those
    are preceded by the settings screen where a person would have said
    otherwise. The clients do push the device language — fire-and-forget, on
    some later launch — so the stored value was English exactly during the
    first session, which is when a guest meets most of those sentences.

    The first tag of `Accept-Language` is the phone saying the same thing on
    the very request that mints the row. Resolved through `i18n.resolve` so
    the column holds one of the locales we ship rather than `de-AT,de;q=0.9`.
    """
    from .. import i18n

    if not accept_language:
        return i18n.DEFAULT_LOCALE
    first = accept_language.split(",", 1)[0].split(";", 1)[0].strip()
    return i18n.resolve(first)


async def current_user(
    request: Request,
    response: Response,
    session: SessionDep,
    known: Visitor,
    anon: AnonymousId,
    accept_language: Annotated[str | None, Header()] = None,
) -> User:
    """The user behind this request, creating a guest if there is none.

    **Depending on this is a claim about the route: something here is worth
    keeping.** Saving a birth, landing a sign-in link, verifying a purchase — an
    act, in the owner's words, rather than a visit. The routes that only look at
    something should take `Visitor` and answer for nobody. Two were getting this
    wrong and both fired on page load: `POST /v1/events`, the funnel beacon, and
    `GET /v1/billing/catalogue`, which the pricing section fetches on mount and
    which the browser actually issues *first* — so after the beacon was fixed a
    page view still minted a row, and minted it on the one request that had no
    anonymous id to claim yet.

    When a row is minted, the anonymous id that came with the request is claimed
    for it, so that everything the person did before this moment can still be
    counted as the same person afterwards. The claim is deliberately not made
    anywhere else: this is the only point in the system where "that browser
    became this account" is something we watched happen.
    """
    if known is not None:
        return known

    # **Гость бесплатен для человека и не бесконечен для скрипта.**
    #
    # Всё, что стоит денег, отмеряется на `user.id`: месячный бюджет генераций,
    # дневная норма вопросов, счётчики `UsageCounter`. Строка `user` при этом
    # заводилась любому запросу без токена — то есть цена нового месячного
    # бюджета равнялась одному HTTP-вызову, и «потолок на аккаунт» на самом деле
    # не был потолком ни на что. Ротация гостей обходила его целиком.
    #
    # Отказ стоит **до** `create_guest`, а не после: смысл в том, чтобы строка
    # не появилась. Кто уже предъявил токен, сюда не доходит — это возврат
    # выше, — так что потолок не касается ни одного существующего аккаунта, ни
    # гостевого, ни настоящего. `Retry-After` в часах, потому что окно часовое:
    # клиенту честнее увидеть срок, чем гадать.
    if not await window(
        request,
        "guest_mint",
        limit=GUEST_MINTS_PER_HOUR,
        seconds=GUEST_MINT_WINDOW_SECONDS,
    ).hit(session, request_source(request)):
        log.warning("guest minting refused: one source asked for more than %d in an hour",
                    GUEST_MINTS_PER_HOUR)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "guest_rate_limit",
                "message": (
                    "too many new sessions from here — wait a little, or sign in "
                    "with an account you already have"
                ),
            },
            headers={"Retry-After": str(int(GUEST_MINT_WINDOW_SECONDS))},
        )

    user = await accounts.create_guest(session, locale=_minted_locale(accept_language))
    await funnel.claim(session, anon_id=anon, user_id=user.id)
    response.headers[ISSUED_TOKEN_HEADER] = tokens.issue(user.id)
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def require_account(user: CurrentUser) -> User:
    """For routes that genuinely need a signed-in person — billing, export."""
    if user.is_guest:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="sign in first — this needs an account we can attach to you",
        )
    return user


Account = Annotated[User, Depends(require_account)]


def birth_from_input(payload: BirthInput) -> BirthData:
    return BirthData(
        date=payload.birth_date,
        time=payload.birth_time,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone=payload.timezone,
        place_label=payload.place_label,
        name=payload.name,
        on_ambiguous=payload.on_ambiguous,
    )


def birth_from_profile(profile: Profile) -> BirthData:
    birth_date = profile.birth_date
    if not isinstance(birth_date, date_type):  # pragma: no cover - driver variance
        birth_date = date_type.fromisoformat(str(birth_date))
    return BirthData(
        date=birth_date,
        time=profile.birth_time,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
        place_label=profile.place_label,
        name=profile.name,
        # Ответ, если он был дан. NULL — «не спрашивали»: расчёт снова упрётся
        # в развилку и снова спросит, что и требуется.
        on_ambiguous=profile.on_ambiguous or "raise",
    )


async def load_profile(session: AsyncSession, user: User, profile_id: str) -> Profile:
    profile = await session.get(Profile, profile_id)
    # Same answer for "does not exist" and "belongs to someone else": a
    # different one would turn this endpoint into a way to enumerate ids.
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no such profile")
    return profile


async def partner_profile_id(
    session: AsyncSession, user: User, stated: str | None = None
) -> str | None:
    """О ком идёт речь, когда речь о совместимости, — или `None`.

    Совместимость в v3 покупается поштучно: грант называет один профиль
    (`pair:{profile_id}`), поэтому вопрос «открыта ли совместимость» без
    названного партнёра — вопрос без ответа. Эта функция и есть то место, где
    он получает ответ до того, как его зададут `entitlements.check`.

    **Мягкая, а не строгая: она не поднимает исключений.** Строгий разбор
    («партнёров ноль» / «партнёров несколько, назови») уже стоит в
    `readings._partner` и должен срабатывать *после* проверки прав, иначе
    неоплативший человек с двумя партнёрами получит 422 вместо пейволла и не
    узнает, что глава вообще продаётся.

    Один сохранённый партнёр — подавляющее большинство аккаунтов, и тогда он
    единственный возможный ответ. Несколько без названного id — `None`: угадать
    значит открыть отчёт про не того человека.
    """
    if stated:
        return stated

    from sqlalchemy import select

    others = (
        await session.execute(
            select(Profile.id)
            .where(Profile.user_id == user.id, Profile.is_self.is_(False))
            .limit(2)
        )
    ).scalars().all()
    return others[0] if len(others) == 1 else None


async def resolve_birth(
    session: AsyncSession,
    user: User,
    *,
    profile_id: str | None,
    birth: BirthInput | None,
) -> BirthData:
    """Take a birth from either a saved profile or the request body."""
    if profile_id:
        return birth_from_profile(await load_profile(session, user, profile_id))
    if birth is not None:
        return birth_from_input(birth)

    from sqlalchemy import select

    result = await session.execute(
        select(Profile).where(Profile.user_id == user.id, Profile.is_self.is_(True)).limit(1)
    )
    own = result.scalar_one_or_none()
    if own is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="no birth data — send `birth`, or save a profile first",
        )
    return birth_from_profile(own)
