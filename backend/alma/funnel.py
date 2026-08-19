"""The stages a person passes through, and how many fell out between them.

There has been an `event` table since the first migration and nothing has ever
written a row to it. Every conversion number the pricing work rests on is
therefore an assumption someone typed, which is why that analysis says plainly
that no advertising money should be spent until this table has thirty days of
real data in it. This module is the smallest thing that produces that data
honestly, plus the query that makes it worth having — a table nobody can ask a
question of is a table nobody will look at.

Six decisions, and the reasons they went this way rather than the obvious way.

**The stage names are a closed set.** An analytics endpoint that accepts any
string is an analytics table that fills with `offer_view`, `offerView`,
`offer-view` and `offer_veiw`, and the funnel query that reads it answers a
confident, wrong number for months. The rejected alternative — take anything,
tidy it up later — cannot work: by the time the typo is noticed the rows it
should have been are gone. A refusal costs one 422 in development and nothing
in production, because the client hard-codes its eight — `STAGES` below is
spelt to match `src/lib/track.ts` for exactly that reason, and the ninth name
is the one only this server may write.

**Somebody who has told us nothing counts, and does not become a row in the
`user` table for it.** That sentence used to read "a guest counts", and it was
paid for in a way nobody had costed: `POST /v1/events` minted an account for
any caller without a token, the landing fired `landing_view` on mount, and so a
browser that loaded the page and touched nothing left an account behind. The
dev database showed 143 users against 46 profiles — two thirds of the rows were
page views wearing an account's clothes, and every per-account number computed
over them (how many accounts exist, how many convert, what an account costs)
was measuring the wrong population.

So the top of the funnel is recorded against an **anonymous id**: a random
string the client keeps, sent in `X-Alma-Anon`, which is not an account and
grants nothing. The account is minted at the first act that gives us something
to keep — a birth saved, or a sign-in — and `deps.current_user` claims the
anonymous id for it at that moment.

**Which is the whole reason `AnonymousVisitor` exists, and it is not
bookkeeping.** Without the claim, the stages before the account and the stages
after it are two identities belonging to one person, and "of the people who saw
the landing, how many finished the journey" — the number the pricing model
rests on — reads as zero on data that looks perfectly healthy. That is the same
failure the old code had, arriving from the other direction. The join is
therefore written at the one moment it is a *fact* rather than an inference,
which is the moment the account is created out of that browser's request.

The rejected alternative was to infer the join at read time from rows that
carry both ids. It needs no extra table and it is wrong in a way that cannot be
seen: a shared browser where a second person signs in would silently move the
first person's landing view onto the second person's account.

Attribution is one of those two ids and nothing else: no IP address, no user
agent, no device fingerprint, no address.

**A purchase is not the browser's word for it.** The browser knows an overlay
closed; the processor's signed webhook knows money moved, and it already writes
a `Purchase` row with `completed_at` on it. So the purchase stage is read from
the money trail rather than from this table, and `POST /v1/events` refuses the
name outright. Anything else means the number that decides how much is spent on
advertising is a number anybody with a terminal can inflate.

**What follows a checkout are three siblings, not three steps.** Opening one
has exactly three known endings, and each is measured against
`checkout_opened` rather than against the one printed above it:
`purchase_completed` is the overlay reporting that it ran to the end,
`purchase` is money that actually arrived, and `offer_declined` is the overlay
being closed. Chained instead, `offer_declined` would count the people who
declined *among the people who bought* — nobody, a zero indistinguishable from
a broken beacon — and `purchase` would count only buyers whose browser also
sent a beacon, so every customer with Do Not Track set would vanish out of the
revenue line. The gap between the middle two is worth watching on its own: an
overlay that finished with no payment behind it is a webhook that did not
arrive, and that is a person who paid and got nothing.

**Событие лестницы монетизации без `surface` — отказ, а не строка.** Двенадцать
имён из §7 ТЗ v3 живут в том же закрытом наборе, что и всё остальное здесь, и
единственное, чем они отличаются: у каждого обязана быть поверхность из §3 —
`p1` (конец бесплатной главы), `p5` (живой слой), `p6` (квота) и так далее.
Причина в том, зачем эти события вообще заводятся. `paywall_shown`, сложенный по
всем экранам сразу, — это счётчик пейволлов вообще: он не отвечает ни на один
вопрос, ради которого §7 писался («какая поверхность продаёт, какую убрать»), и
цена ошибки здесь не «нет одного измерения», а «решение, где стоит следующий
пейволл, принято по числу, которое ничего не значит». То есть поверхность для
этих двенадцати — вторая половина имени события, а не его размерность, и правило
ей достаётся то же, что имени: незнакомая — 422 со списком, отсутствующая — 422
с указанием на §3, обе — со строкой в лог, потому что маяк своё 422 глотает
молча и никто его не увидит.

**Значения по умолчанию у неё нет, и это решение, а не пропуск.** Подставить
`unknown` было бы дешевле для клиента и хуже для всего остального: гейт §А12
(«все события §7 приходят с `surface`») выполнялся бы формально, в таблице
появилось бы ведро, означающее «клиент забыл», и ни один отчёт не смог бы
отличить его от настоящей поверхности. Отказ стоит одного потерянного маяка в
разработке, где его видно и по логу, и по тестам; значение по умолчанию стоит
неверного ответа в проде, который выглядит здоровым. Клиент при этом знает, на
каком он экране, — это ровно то единственное, в чём он не может ошибиться.

**Merges are folded when the funnel is read**, and it is worth being exact
about which rows need it, because the obvious answer is wrong. `accounts.merge`
*does* know about this table — `Event` is in the list of tables it re-points,
and it says why — so a guest's rows that carry a user id follow the guest into
the account they merged into, and those need no folding at all. What it cannot
move is the rows written **before** the account existed, because those carry
only an anonymous id and there is no user id on them to re-point. Those are
resolved through the claim instead, and the claim names the guest — the row that
existed when the browser handed its id over — so the merge pointer has to be
followed *after* the claim rather than instead of it. Read-time folding also
fixes rows already written, which a backfill would not.

**What must never be stored.** The privacy page names every field Alma holds
and promises that nothing is collected to build a profile for anyone else. A
birth date, a birth time, a place, a name, an email address, an IP address, a
user agent, a referrer or a full URL in this table would each make that page
false — and a free-form `properties` bag is exactly how one arrives, one
well-meaning `{"birthDate": …}` at a time. Hence `PROPERTIES`: a short
allowlist of words that describe the *product*, never the person, with short
values, and silence for anything else — see `clean_properties` for why an
unwanted label is dropped where an unwanted stage name is refused.

**An anonymous id is still an identifier, and it gets an identifier's rules.**
It is not a user row, but it is a string in somebody's browser that ties their
visits together, so: it is random and carries nothing derived from the person
or the device; it is refused unless it looks like one we would have issued, so
this table cannot be used to store somebody's address in a header; every row
carrying it dies with the account that claimed it, in `forget`; and none of them
outlives `PURGE_AFTER_DAYS`, which `purge` enforces and the privacy page
states. The retention deletes *every* row past the cutoff rather than only the
anonymous ones, and that is the deliberate choice: deleting the unattributed
top of an old funnel while leaving the conversions below it intact would make
every historical rate wrong in the direction that flatters us.

There is no HTTP route for the read side, on purpose. The funnel is the
business's own numbers, an unauthenticated endpoint publishes them to
competitors, and an authenticated one needs an operator credential that this
service does not have. So it is a module and a `__main__`, run as
`python -m alma.funnel --days 30`, the same shape as the renewal notices.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .db.models import AnonymousVisitor, Event, Purchase, User, as_utc, utcnow

log = logging.getLogger("alma.funnel")


class UnknownStage(ValueError):
    """A stage name outside the closed set. See `STAGES` for why that is fatal."""


class Unattributed(ValueError):
    """An event with neither an account nor an anonymous id behind it.

    Refused rather than written as a row with two nulls in it. Such a row can
    never be counted — the funnel counts distinct identities — but it *would*
    be counted in a `SELECT count(*)`, so it is exactly the kind of row that
    makes a table disagree with itself depending on who queries it.
    """


class TooManyEvents(RuntimeError):
    """This caller has written as many events today as it is allowed to."""


class SurfaceMissing(ValueError):
    """Событие лестницы монетизации пришло без `surface`.

    Отказ, а не строка с пустым местом. Эти двенадцать имён (§7 ТЗ) заводились
    ради сравнения поверхностей между собой; `paywall_shown` без поверхности не
    ступень, а счётчик пейволлов вообще, и он молча портит ровно тот отчёт,
    ради которого всё это писалось. Гейт §А12 — «все события §7 приходят с
    `surface`» — держится здесь, а не в договорённости с клиентом.
    """


class UnknownSurface(ValueError):
    """Поверхность вне закрытого набора §3.

    Та же болезнь, что у опечатки в имени ступени, и то же лечение: `p1` и
    `paywall_p1` — две когорты, одна из которых конвертируется в ноль, и в
    отчёте это выглядит здоровым. `SURFACES` перечислен в теле отказа, чтобы
    тот, кто ошибся, увидел слова, которые надо было прислать.
    """


@dataclass(frozen=True)
class Stage:
    """One rung of the funnel.

    `after` is the stage this one's rate is measured against, which is usually
    but not always the one printed above it — see the note about the three
    endings of a checkout.
    `server_known` marks a stage the browser is not permitted to report,
    because something on our side knows it for certain.

    `monetization` помечает одно из событий §7 ТЗ v3, и это один флаг с двумя
    следствиями, потому что следствие у него по сути одно. Такому событию
    разрешены дополнительные ярлыки `MONETIZATION_PROPERTIES` — и оно **обязано**
    нести `surface` из `SURFACES`, иначе не пишется вовсе. Обе половины про одно:
    эти события существуют, чтобы поверхности сравнивать друг с другом, так что
    поверхность им — вторая половина имени, а не размерность.
    """

    name: str
    after: str | None
    server_known: bool = False
    monetization: bool = False


#: The whole funnel, in order. Adding a stage here is the only way to add one:
#: the endpoint validates against this tuple and the query walks it.
#:
#: The names are the ones `src/lib/track.ts` sends, down to the spelling. The
#: brief for this work called the last two "purchase" and "declined"; the
#: shipped client says `purchase_completed` and `offer_declined`, and since a
#: beacon swallows its own failures, a server that insisted on the other
#: spelling would refuse every event in production without anybody finding out
#: for a month.
STAGES: tuple[Stage, ...] = (
    Stage("landing_view", None),
    Stage("quiz_start", "landing_view"),
    Stage("quiz_complete", "quiz_start"),
    Stage("portrait_view", "quiz_complete"),
    Stage("offer_view", "portrait_view"),
    Stage("checkout_opened", "offer_view"),
    # The browser's own view of the overlay closing successfully. Kept
    # deliberately separate from the money below rather than treated as the
    # same fact: the client's own comment concedes that where the two
    # disagree, the webhook is right.
    Stage("purchase_completed", "checkout_opened"),
    # Read from the `Purchase` row the webhook writes, never from a client.
    # Measured against the checkout rather than against the beacon above it,
    # so that a buyer whose browser sent nothing is still a sale.
    Stage("purchase", "checkout_opened", server_known=True),
    # The third ending, not a step beyond buying.
    Stage("offer_declined", "checkout_opened"),

    # ── the daily ──────────────────────────────────────────────────────────
    #
    # Not part of the acquisition funnel above and deliberately at the end of
    # it: these two measure what happens *after* somebody is already paying,
    # which is retention rather than conversion. They are here because this
    # tuple is the only way to add a stage — the endpoint validates against it
    # and the query walks it — and because until they existed the daily was
    # unmeasured. `alma/notify/daily.py::FUNNEL_STAGES` names both and
    # `_measure` already calls `record`; it was logging a warning and dropping
    # the event.
    #
    # `THE-DAILY.md §6.3` makes the ratio of Off to Occasionally after thirty
    # days the only metric that measures what the owner actually asked for —
    # "not annoying" — and `daily_opened / daily_sent` is the other half of
    # it: a notification people open is one they wanted.
    #
    # `daily_sent` is `server_known` for the same reason `purchase` is. The
    # job knows it accepted a vendor's receipt; a browser cannot report it and
    # must not be allowed to. `daily_opened` is the client's, because opening
    # is a thing only the client can see.
    Stage("daily_sent", None, server_known=True),
    Stage("daily_opened", "daily_sent"),

    # ── лестница монетизации v3 (§7 ТЗ) ────────────────────────────────────
    #
    # В §7 двенадцать имён, здесь одиннадцать. Двенадцатое — `purchase`, оно
    # уже стоит выше и остаётся `server_known`: ТЗ просит `purchase{sku,
    # surface, price}`, но деньги по-прежнему знает подписанный вебхук, а не
    # телефон, и открыть это имя клиенту значило бы сделать число, по которому
    # решают рекламный бюджет, полем формы. Поверхность продажи читается из
    # `checkout_started` того же человека — оно ниже, и без `surface` его не
    # принимают.
    #
    # Все одиннадцать помечены `monetization=True`, и это гейт §А12. Цена
    # ошибки, если поверхность станет необязательной: `paywall_shown` сложится
    # в одно число по всем экранам, «какая поверхность продаёт» перестанет быть
    # вопросом, на который есть ответ, и §7 останется списком имён без отчёта.
    #
    # `after` расставлен по целевым цифрам §7, а не по тому, что читается
    # сверху вниз: у каждой строки отчёта должен быть знаменатель, про который
    # владелец уже сказал, каким он должен быть.
    Stage("paywall_shown", None, monetization=True),
    # Два конца пейволла — братья, а не шаги, ровно как три конца чекаута выше.
    # Сцепив их в цепочку, `paywall_dismissed` считал бы закрывших среди
    # заплативших, то есть ноль, неотличимый от сломанного маяка.
    Stage("paywall_dismissed", "paywall_shown", monetization=True),
    # Не переименованный `checkout_opened`. Тот пишет этот сервер, когда сам
    # открывает сессию Paddle для браузера; этот — телефон, у которого поднялся
    # системный лист покупки. Слить их в одно имя значило бы сделать одну
    # ступень из двух фактов, наблюдаемых с разных сторон: приложения первый не
    # пишут никогда, веб второй не пишет никогда, и общее число читалось бы как
    # провал платформы, которая на самом деле просто отвечает другим именем.
    Stage("checkout_started", "paywall_shown", monetization=True),
    # §7: «главу I дочитывают ≥55%». Знаменатель — дошедшие до конца квиза:
    # глава I натала открывается сразу за ним (P1), а бесплатные главы прочих
    # систем приходят сюда же с другой поверхностью и видны как разрыв между
    # `reached` и `total`, который `Step` печатает отдельно.
    Stage("free_chapter_completed", "quiz_complete", monetization=True),
    # §7: «≥25% купивших натал добавляют партнёра». Знаменатель — покупка, то
    # есть денежный след, а не маяк: иначе доля считалась бы среди тех, чей
    # браузер о покупке рассказал.
    Stage("partner_added", "purchase", monetization=True),
    Stage("pair_teaser_completed", "partner_added", monetization=True),
    # Дальше — три корня. Квоту вопросов, вход в отмену и открытие пуша не к
    # чему прицепить честно: подписка, которую сейчас отменяют, могла быть
    # куплена за месяц до окна отчёта, и цепочка к `purchase` считала бы долю
    # отмен среди купивших *в этом окне* — число, которое тем меньше, чем
    # длиннее окно.
    Stage("question_quota_hit", None, monetization=True),
    Stage("cancel_flow_entered", None, monetization=True),
    # §7: «save-оффер спасает ≥10% отмен» — это ровно эти две ступени под
    # входом в отмену.
    Stage("save_offer_shown", "cancel_flow_entered", monetization=True),
    Stage("save_offer_accepted", "save_offer_shown", monetization=True),
    # Пересекается с `daily_opened` выше, и это не дубль по недосмотру. Тот
    # меряется против `daily_sent` и отвечает на единственный вопрос, который
    # владелец задал про уведомления, — «не назойливо ли»; этот отвечает на
    # вопрос лестницы: с какого пуша человек пришёл на поверхность. Клиент,
    # приславший на утреннюю заметку оба, ничего не ломает: ступени считаются
    # по разным именам и каждая по различным личностям.
    Stage("push_opened", None, monetization=True),
)

BY_NAME: dict[str, Stage] = {stage.name: stage for stage in STAGES}
STAGE_NAMES: tuple[str, ...] = tuple(stage.name for stage in STAGES)

#: The only keys a caller may attach to an event, and every one of them
#: describes the product rather than the person: which system was on screen,
#: which chapter, which product key was being bought, which language the page
#: was in, which step of the quiz, which currency it was priced in, and — for
#: a decline — whether the overlay was dismissed or the offer was tapped past.
#: There is deliberately no `country`, because `currency` answers the market
#: question at a coarser grain, and deliberately no free-text key of any kind.
PROPERTIES: frozenset[str] = frozenset(
    {"system", "chapter", "product", "locale", "step", "variant", "currency", "how"}
)

#: Ярлыки, которые разрешены дополнительно и только событиям лестницы (§7 ТЗ).
#: Имена — те самые, что в §7, буква в букву: клиент пишется по ТЗ, а
#: переименовать `sku` в существующий `product` на сервере значило бы тихо
#: ронять ярлык — маяк своё предупреждение из лога не увидит, и размерность
#: пропала бы у всех событий сразу.
#:
#: **Почему отдельным набором, а не строкой в `PROPERTIES`.** `PROPERTIES` —
#: это ровно `KEYS` из `src/lib/track.ts`, и равенство двух списков проверяет
#: тест: веб заморожен на четырёх ступенях v2 и ни одной из этих поверхностей
#: не имеет. Ключ, который веб не пришлёт никогда, не должен расширять мешок,
#: об который чистится каждый маяк лендинга: чем шире общий список, тем меньше
#: он значит.
#:
#: `price` здесь для A/B из Ф3 («$19.99 против $24.99») — это цена, которая
#: **была на экране**, а не выручка. Выручку по-прежнему считают по `Purchase`;
#: число, которое клиент может назвать сам, деньгами не является.
#: `system` (§7 `free_chapter_completed{system}`) и `variant` уже есть в
#: `PROPERTIES` и не дублируются.
MONETIZATION_PROPERTIES: frozenset[str] = frozenset(
    {"surface", "sku", "trigger", "nbo_reason", "method", "price", "type"}
)

#: Поверхности из §3 ТЗ — карта пути целиком, десять штук, и закрытый набор по
#: той же причине, по которой закрыт список ступеней: `p1`, `P1` и `paywall_p1`
#: в одной колонке — три когорты, две из которых конвертируются в ноль.
#:
#: Имена — коды ТЗ, а не описания. Так их пишут и в §3, и в задачах, и в
#: разговоре, и совпадение здесь важнее читаемости отчёта: клиента пишет другой
#: человек по тому же документу, а разошедшиеся словари на этом проводе не
#: видно ни с одной стороны — маяк глотает 422 молча.
#:
#: `p0` в наборе есть, хотя §3 запрещает на нём цены вовсе. Отказ прятал бы
#: нарушение инварианта вместо того, чтобы его посчитать: строка «пейволлы,
#: показанные на p0» в отчёте — это то, как о сломанном P1 узнают.
SURFACES: tuple[str, ...] = (
    "p0",  # онбординг и квиз — цен нет вообще
    "p1",  # результат квиза, оффер в конце бесплатной главы
    "p2",  # тап по закрытой главе — дверь системы
    "p3",  # конец купленного разбора — карточка «Что дальше»
    "p4",  # флоу совместимости: ввод, тизер, пейволл, отчёт
    "p5",  # живой слой день 2+ — пейволл подписки
    "p6",  # квота вопросов
    "p7",  # экран «Все планы»
    "p8",  # отмена подписки — save-оффер
    "p9",  # пуш
)

#: A property value is a label, not a sentence. Sixty-four characters is more
#: than every product key, system slug and locale code we ship, and far less
#: than anything a person would type about themselves.
MAX_VALUE = 64

#: What a property value has to look like to be kept.
#:
#: The length was the only rule here, and length alone was never the rule this
#: module says it enforces. Every docstring in this file — and the one on
#: `Event` in `db/models.py`, and the paragraph the privacy page rests on —
#: claims the table cannot come to contain something a person typed, and
#: `ANON_ID` above says out loud that "an email address in `X-Alma-Anon` gets
#: the same answer as one in a property value". It did not: `{"how":
#: "sofia@example.com"}` and `{"variant": "Sofia Bianchi"}` are both short, both
#: on the allowlist, and both were written straight through. The claim was true
#: of the web only because `scrub` in `src/lib/track.ts` refused them before
#: they left the browser — which is to say the discipline was enforced on the
#: side of the wire that anybody can edit, and not on the side that owns the
#: column.
#:
#: So this is `LABEL` from `track.ts`, character for character, moved to where
#: it binds. A slug, a locale code, a currency, a step name: something we
#: minted, not something somebody was asked for. No whitespace and no `@`,
#: which between them are what make a name and an address structurally
#: impossible rather than merely absent so far.
#:
#: The rejected alternative was to loosen the client to match the server, on the
#: grounds that the two ends should agree and the server is the older of the
#: two. They should agree, and they now do — but agreement is not the only
#: property either end needs, and of the two rules on offer this is the one the
#: rest of the file already promised.
#:
#: Composed from `MAX_VALUE` rather than written with a 63 in it, so that the
#: ceiling stays one number with one name. The first character is spent on the
#: "starts with a letter or a digit" rule, which is what keeps `-` and `.` from
#: leading — a value beginning with a dash reads as a flag to half the tools
#: anybody would ever point at this table.
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0," + str(MAX_VALUE - 1) + r"}$")

#: How many events one account may write in a day. This bounds the table
#: rather than the burst: a per-second limiter would need state shared between
#: processes, which this service does not have, and the thing actually being
#: defended is a table that a script could otherwise grow without limit. A
#: full journey through every stage writes well under twenty rows, so the cap
#: is roughly ten sessions a day before anybody honest could notice it.
DAILY_LIMIT = 200

#: The metric the cap is counted under, in the same `UsageCounter` table that
#: already holds questions asked, money spent and the one downsell.
LIMIT_METRIC = "events"

#: What an anonymous id must look like to be stored.
#:
#: A UUID is what the clients send (`crypto.randomUUID` on the web), but the
#: pattern is deliberately a little wider than that: an app on a platform whose
#: idiomatic identifier is not a UUID should not have to fake one, and a rule
#: this file can state in one line is a rule that survives a second client.
#:
#: What it is really doing is refusing everything else. This header arrives from
#: a browser, it is written to a column, and the column is on a table whose
#: whole discipline is that nothing a person typed can reach it — so an id that
#: is not plausibly an id we issued is dropped rather than stored, and an email
#: address in `X-Alma-Anon` gets the same answer as one in a property value.
ANON_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")

#: How long any of this is kept.
#:
#: Stated here because the privacy page states it to the reader, and a number
#: that lives in one of those two places is a promise nobody can check. `purge`
#: is what makes it true and `backend/README.md` is where it is scheduled; a
#: retention that depends on somebody remembering to run a command is a
#: retention policy in the same sense that the renewal notice was a promise
#: before it had a cron line.
PURGE_AFTER_DAYS = 180

#: How long after a claim a row carrying only the browser id still belongs to
#: the account that claimed it.
#:
#: The claim is the moment a browser became an account, and from that moment on
#: everything that browser sends carries the token — so a row arriving *later*
#: with the id and no token is, by construction, not coming from the session
#: that holds the account. On a shared browser it is a second person, and
#: folding it onto the first person's account is a cross-person attribution
#: that nothing in the report looks wrong about. `audience` therefore stops
#: folding once this has passed, and counts the row as its own visitor.
#:
#: It is not zero because of the beacons already in flight when the account is
#: minted. The journey fires `quiz_complete` next to the birth save that mints,
#: `keepalive` lets a request outlive the page that started it, and the two
#: processes' clocks need not agree to the millisecond. A window measured in
#: minutes covers all of that and is still nowhere near "the rest of time",
#: which is what the old rule was.
CLAIM_GRACE = timedelta(minutes=5)


def clean_anon_id(anon_id: str | None) -> str | None:
    """The caller's anonymous id, or nothing at all.

    Dropped rather than refused, for the reason the whole of this module drops
    rather than refuses at the edges: the caller is a beacon that swallows its
    own errors. A client sending a malformed id would lose every event it ever
    sent and nothing anywhere would say so. Dropping it costs that client its
    attribution — which is loud, because the rung reads zero — and costs the
    rest of the funnel nothing.

    The route is the one place that turns "nothing at all" into an answer: with
    no account either, there is nothing to attribute the stage to, and it says
    so rather than writing an uncountable row.
    """
    if not anon_id:
        return None
    candidate = anon_id.strip()
    return candidate if ANON_ID.fullmatch(candidate) else None


# ── writing ───────────────────────────────────────────────────────────────


def check_surface(stage: str, properties: dict | None) -> str | None:
    """Поверхность этого события в каноническом написании, или `None`.

    `None` — если ступень поверхности не требует; для всех прочих либо строка
    из `SURFACES`, либо отказ. Единственная точка, где живёт гейт §А12, и
    вызывают её обе стороны: маршрут — чтобы ответить 422 до того, как событие
    съест дневную квоту, и `record` — чтобы серверный вызов, написанный через
    полгода, не мог обойти правило мимо HTTP.

    **Отсутствующая и незнакомая поверхности разведены нарочно.** Это два
    разных исправления в клиенте: в первом случае поле забыли, во втором
    прислали своё слово вместо кода §3, и один общий отказ отправил бы автора
    искать не там. Проверяется сырой мешок, до `clean_properties`: значение,
    непохожее на ярлык, тот выбросит, и «прислали мусор» стало бы неотличимо
    от «не прислали ничего».

    **Регистр приводится, остальное — нет.** ТЗ пишет `P1`, код пишет `p1`, и
    отчёт, разъехавшийся на две когорты из-за заглавной буквы, — ровно та
    болезнь, от которой закрытый набор и заводят. Разбор члена перечисления —
    не то же самое, что подчистка значения (её этот модуль не делает нигде:
    половина чьего-то адреса — всё ещё его адрес), поэтому ничего, кроме
    регистра и обрамляющих пробелов, здесь не прощается.

    Отказ ещё и логируется. 422 достаётся маяку, который его глотает молча, —
    без строки в логе рухнувшая ступень выглядела бы как «эту поверхность
    просто никто не видел».
    """
    known = BY_NAME.get(stage)
    if known is None or not known.monetization:
        return None

    raw = (properties or {}).get("surface")
    if raw is None:
        log.warning("%s refused: §7 events carry a surface and this one had none", stage)
        raise SurfaceMissing(
            f"{stage!r} is a monetization event and must say where it happened: "
            f"send one of {', '.join(SURFACES)} as `surface`"
        )

    candidate = raw.strip().lower() if isinstance(raw, str) else raw
    if candidate not in SURFACES:
        log.warning("%s refused: %r is not a surface this product has", stage, str(raw)[:32])
        raise UnknownSurface(
            f"{str(raw)[:32]!r} is not a surface — {', '.join(SURFACES)}"
        )
    return candidate


def clean_properties(properties: dict | None, *, stage: str | None = None) -> dict:
    """Whatever of this is safe to keep. Everything else is dropped and logged.

    Dropping rather than refusing, and the asymmetry with a bad stage name is
    the point. An unknown *stage* has nowhere to be counted, so refusing it
    costs nothing. An unknown *label* on a good stage is different: the client
    is a beacon that swallows every failure it gets, so a 422 here would delete
    the whole event, and the day somebody adds one label to a screen the entire
    rung silently disappears from the funnel for a release. A missing dimension
    is a bad afternoon; a missing rung is a decision made on a wrong number.

    Which is also why it is logged. Nobody reads a 422 that a beacon threw
    away, but somebody does eventually read the logs, and the line names the
    key so the fix is to add it to `PROPERTIES` rather than to go looking.

    Values must be a boolean, a whole number, or a string shaped like `LABEL`.
    A nested object is where a whole birth record fits, and free text is where
    an email address fits — so neither is a value this function has a branch
    for.

    **The shape rule used to be a length rule, and the two are not the same
    promise.** `{"variant": "Sofia Bianchi"}` is fourteen characters and was
    stored verbatim; so was `{"how": "sofia@example.com"}`. The client refused
    both — `scrub` in `src/lib/track.ts` has always tested its values against a
    label pattern — which meant the discipline this module describes was being
    kept by the browser rather than by the code that owns the column, and a
    second client, a curl, or the day somebody passes a form value through in
    six months' time would each have written a person's name into an analytics
    table with nothing anywhere objecting.

    So the two ends now apply the same rule and `LABEL` says which way the
    disagreement was settled. Tightening the server rather than loosening the
    client costs nothing real: every value our three clients send is a
    catalogue slug, a system slug, a locale code, a currency or a fixed word,
    and a test posts each of them.

    **Разрешённый список зависит от ступени, и только в одну сторону.** Событию
    лестницы (§7) дополнительно разрешены `MONETIZATION_PROPERTIES`; всем
    остальным — нет, и `{"sku": …}` на `landing_view` выбрасывается со строкой
    в логе, как любой незнакомый ярлык. Причина в том, что `PROPERTIES` — общий
    словарь с вебом, слово в слово, а `sku` и `nbo_reason` веб не пришлёт
    никогда: список, в который дописывают всё подряд, перестаёт быть обещанием
    того, что в этой таблице лежит.
    """
    if not properties or not isinstance(properties, dict):
        return {}

    known = BY_NAME.get(stage or "")
    allowed = (
        PROPERTIES | MONETIZATION_PROPERTIES
        if known is not None and known.monetization
        else PROPERTIES
    )

    kept: dict = {}
    dropped: list[str] = []
    for key, value in properties.items():
        if key not in allowed:
            dropped.append(str(key))
            continue
        if isinstance(value, bool) or isinstance(value, int):
            kept[key] = value
            continue
        if not isinstance(value, str) or not LABEL.fullmatch(value):
            # Dropped whole rather than truncated or tidied. Half of somebody's
            # email address is still their email address, and a value that has
            # to be cleaned up before it fits is by definition not one of the
            # labels we mint — the honest thing to lose is the dimension.
            dropped.append(key)
            continue
        kept[key] = value

    if dropped:
        # The keys came from a client, so what is logged is bounded in both
        # directions — an unbounded list of caller-controlled strings is a way
        # to write whatever you like into somebody's log aggregator.
        names = ", ".join(name[:32] for name in sorted(dropped)[:5])
        log.warning("dropped %d label(s) not kept by this table: %s", len(dropped), names)
    return kept


async def spend_allowance(
    session: AsyncSession, user_id: str, *, limit: int | None = None
) -> int:
    """Count one event against today's cap, or raise `TooManyEvents`.

    What is capped is rows in the table, not requests at the door. The
    increment and the event are written in one transaction, so a refusal rolls
    both back and a client that keeps going after its 429 keeps being refused
    on the count it has already stored — which is the property that matters,
    because the thing being defended is the size of the table rather than the
    cost of answering.

    **Списание атомарное, и прежняя оговорка на этом месте снята.** Здесь
    стояло «a limiter on requests would need state shared between processes,
    and this service has none» — общее состояние у сервиса теперь есть
    (`db/counters.py`, `deps.SharedWindow`), и сам счётчик больше не читается
    перед записью: `spend_and_check` прибавляет и узнаёт результат одним
    запросом. Два маяка, пришедшие вместе, раньше читали один и тот же ноль.

    The ceiling is read here rather than defaulted in the signature, where it
    would be bound once at import and no longer be the number this module
    documents.
    """
    from .db import counters

    ceiling = DAILY_LIMIT if limit is None else limit

    try:
        return await counters.spend_and_check(
            session,
            user_id=user_id,
            day=utcnow().date(),
            metric=LIMIT_METRIC,
            limit=ceiling,
        )
    except counters.QuotaExceeded as exc:
        raise TooManyEvents(
            f"{ceiling} events is a day's worth for one account; "
            f"this one has sent {int(exc.spent)}"
        ) from exc


async def spend_anonymous_allowance(
    session: AsyncSession, anon_id: str, *, limit: int | None = None
) -> int:
    """The same ceiling, for a caller who has no account to count against.

    Counted straight off this table rather than through `UsageCounter`, and the
    reason is not taste: that table's `user_id` is a foreign key into `user`
    with `ON DELETE CASCADE`, so counting an anonymous caller there would mean
    either inventing a user row — which is the entire thing this work exists to
    stop — or writing a dangling key into a constrained column.

    Counting rows is also what `spend_allowance` says it is defending in the
    first place: the size of this table. Here it does that literally, with one
    indexed `count(*)` over one identifier's rows since midnight. The ceiling is
    two hundred and a full journey writes four, so the query never counts a
    number worth optimising.

    It is approximate under concurrency, in a way the counter version is not:
    two beacons in flight together both read the same count. That is deliberate
    rather than overlooked — the exact number is not the point, and the
    alternative is a row-level lock on the hot path of a fire-and-forget beacon.
    """
    ceiling = DAILY_LIMIT if limit is None else limit
    midnight = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    written = (
        await session.execute(
            select(func.count())
            .select_from(Event)
            .where(Event.anon_id == anon_id, Event.created_at >= midnight)
        )
    ).scalar_one()

    if written >= ceiling:
        raise TooManyEvents(
            f"{ceiling} events is a day's worth for one visitor; "
            f"this one has sent {written}"
        )
    return written + 1


async def claim(session: AsyncSession, *, anon_id: str | None, user_id: str) -> bool:
    """Record that this browser became this account. Returns whether it did.

    Called from `deps.current_user` at the only moment the statement is true:
    the request that mints the account is the request that arrived from that
    browser. Everywhere else it would be a guess.

    **First claim wins, and a second one is not an error.** Two things can lead
    here with the same id — a race between two requests that both arrive with no
    token, and a browser whose person signs into a second account later — and in
    both cases the honest answer is that the id already belongs to somebody. The
    rejected alternative, re-pointing it, quietly moves one person's early
    stages onto another person's account; this way the second account is simply
    missing the stages it never had, which shows up as a gap between `reached`
    and `total` in the report rather than as a plausible wrong number.

    The insert is wrapped in a savepoint because the race is real and losing it
    must cost this request nothing: an `IntegrityError` that escapes to the
    session poisons the surrounding transaction, and the surrounding transaction
    is somebody saving their birth data.
    """
    cleaned = clean_anon_id(anon_id)
    if cleaned is None:
        return False

    if await session.get(AnonymousVisitor, cleaned) is not None:
        return False

    try:
        async with session.begin_nested():
            session.add(AnonymousVisitor(anon_id=cleaned, user_id=user_id))
    except IntegrityError:
        log.info("anonymous id claimed by another account first; leaving it there")
        return False
    return True


async def record(
    session: AsyncSession,
    *,
    user_id: str | None,
    stage: str,
    properties: dict | None = None,
    anon_id: str | None = None,
) -> Event:
    """Write one stage against one identity. No limit, no browser.

    This is the server-side entry point — the webhook, the checkout route —
    and it deliberately does not consult the daily cap: that exists to stop a
    client writing rows, and applying it to our own code would mean a busy
    day's purchases stopped being recorded. The HTTP route asks for the
    allowance itself before calling this.

    An account and an anonymous id are both written when both are known. That
    looks redundant — the account alone would count correctly — and it is the
    cheap half of the join: the claim table is the fact, and a row carrying both
    is the evidence an operator can check it against when a rate looks wrong.
    It costs nothing extra to delete, because `forget` removes rows by either.

    Neither is a refusal. A row with two nulls in it counts towards a
    `count(*)` and towards no funnel, which is the one way this table can be
    made to disagree with itself.

    **Гейт поверхности стоит и здесь, не только на маршруте.** Правило §А12
    держится не договорённостью с клиентом, а функцией, которую нельзя обойти:
    серверный вызов — вебхук, задача рассылки, код, написанный через полгода, —
    приходит сюда, а не через HTTP, и событие лестницы без поверхности он
    записал бы молча.
    """
    if stage not in BY_NAME:
        raise UnknownStage(f"{stage!r} is not a funnel stage — {', '.join(STAGE_NAMES)}")

    anonymous = clean_anon_id(anon_id)
    if user_id is None and anonymous is None:
        raise Unattributed(f"{stage!r} arrived with no account and no anonymous id")

    surface = check_surface(stage, properties)
    kept = clean_properties(properties, stage=stage)
    if surface is not None:
        # Каноническое написание, в каком бы регистре оно ни пришло: `p1` и
        # `P1` в одной колонке — две ступени в отчёте вместо одной.
        kept["surface"] = surface

    row = Event(
        user_id=user_id,
        anon_id=anonymous,
        name=stage,
        properties=kept,
    )
    session.add(row)
    await session.flush()
    return row


async def forget(session: AsyncSession, user_id: str) -> int:
    """Erase one account's events. Returns how many rows went.

    Deletion in this product is real — the privacy page says so in as many
    words — and an account's funnel rows are as much theirs as their readings.
    Kept here rather than as a `delete()` inlined into `accounts.erase` so that
    the table's own module owns the sentence, but `accounts.erase` is where it
    has to be called from.

    **The rows from before they had an account go too, and finding them is the
    only reason the claim survives this long.** Somebody who walked the whole
    journey and then signed in has their landing view and their quiz filed under
    a browser id, not under the account they are now asking us to erase. Erasing
    only the rows that carry the account id would leave those behind — still
    linked to each other, still linked to a string that is still in that
    person's browser — while the privacy page says the step labels went with
    everything else. The claim row is deleted last, so the ids it names are
    still readable when the events are.

    **And the claim may be filed under an account this person no longer uses.**
    Somebody who walked the journey as a guest on a phone and then signed into
    an account they already had has their browser id claimed by the *guest* row,
    because that is the row that existed when the browser handed it over;
    `accounts.merge` then folds the guest into the account and moves the events
    that carry a user id across, but the ones from before the account existed
    carry none and stay where they are. So the ids of every account that merged
    into this one are gathered first. Missing that is a deletion that looks
    complete and leaves the whole first half of somebody's journey behind.

    **This reaches wider than `audience` counts, on purpose.** A row written
    under this browser's id long after the claim is *not* counted as this
    account — see `CLAIM_GRACE` — and it is still deleted here. The two answer
    different questions and the safe direction is opposite for each. For a
    number, "we cannot tell whose this is" must never quietly become "it is
    theirs", because that inflates one person's conversion with a stranger's
    steps. For an erasure, a row keyed to an identifier this account owns, in a
    browser this account was created out of, goes: over-deleting a step label
    costs a line in a report, and under-deleting one leaves a record behind
    after somebody asked for it to be gone.
    """
    canonical = await _merged_into(session)
    theirs_too = {source for source, target in canonical.items() if target == user_id}
    every_id = {user_id, *theirs_too}

    owned = (
        await session.execute(
            select(AnonymousVisitor.anon_id).where(AnonymousVisitor.user_id.in_(every_id))
        )
    ).scalars().all()

    rows = Event.user_id.in_(every_id)
    if owned:
        rows = or_(rows, Event.anon_id.in_(owned))

    result = await session.execute(delete(Event).where(rows))
    await session.execute(
        delete(AnonymousVisitor).where(AnonymousVisitor.user_id.in_(every_id))
    )
    return result.rowcount or 0


async def purge(session: AsyncSession, *, days: int = PURGE_AFTER_DAYS) -> int:
    """Drop everything older than the retention this product promises.

    **Every row past the cutoff, not only the anonymous ones.** Deleting the
    unattributed top of an old funnel while leaving the purchases below it in
    place would not be a smaller dataset — it would be a wrong one, with every
    historical conversion rate divided by a denominator that had been quietly
    shrunk. A funnel window either exists whole or does not exist.

    A claim goes when the cutoff has passed *and* nothing references it any
    more. Both conditions, because the second alone would delete the join for a
    browser whose person came back yesterday, and the first alone would delete
    it while rows inside the window still need it to be counted as one person.
    """
    cutoff = utcnow() - timedelta(days=days)

    gone = await session.execute(delete(Event).where(Event.created_at < cutoff))

    still_referenced = select(Event.anon_id).where(Event.anon_id.is_not(None))
    await session.execute(
        delete(AnonymousVisitor).where(
            AnonymousVisitor.claimed_at < cutoff,
            AnonymousVisitor.anon_id.not_in(still_referenced),
        )
    )
    return gone.rowcount or 0


# ── reading ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Step:
    """One line of the answer.

    `reached` counts the people who got here *along the path* — everyone in
    this step is also in the step it is measured against. `total` counts
    everyone who reached the stage at all, by whatever route. The two are
    equal in a tidy funnel; a gap between them is people arriving in the
    middle, which is a real thing that happens when a link is shared, and it
    is reported rather than hidden because the nested count alone would read
    as traffic we never had.
    """

    stage: str
    of: str | None
    reached: int
    total: int
    rate: float | None


async def _merged_into(session: AsyncSession) -> dict[str, str]:
    """Every merged account id, mapped to the row that survived it.

    Chains are followed with a seen-set, the same way `accounts.resolve` does
    it: two merges in a row are ordinary, and a cycle would be a bug we should
    not hang on.
    """
    rows = (
        await session.execute(
            select(User.id, User.merged_into_id).where(User.merged_into_id.is_not(None))
        )
    ).all()
    pointer = {source: target for source, target in rows}

    resolved: dict[str, str] = {}
    for source in pointer:
        seen = {source}
        current = pointer[source]
        while current in pointer and current not in seen:
            seen.add(current)
            current = pointer[current]
        resolved[source] = current
    return resolved


async def _claimed_by(session: AsyncSession) -> dict[str, tuple[str, datetime | None]]:
    """Every anonymous id that has become an account, mapped to it and to when.

    The *when* is what stops the join being open-ended. An id resolves to its
    account for the rows recorded up to the claim; after that the browser has a
    token, so anything still arriving under the bare id is somebody the account
    cannot vouch for. See `CLAIM_GRACE`.
    """
    rows = (
        await session.execute(
            select(
                AnonymousVisitor.anon_id,
                AnonymousVisitor.user_id,
                AnonymousVisitor.claimed_at,
            )
        )
    ).all()
    return {anon_id: (user_id, claimed_at) for anon_id, user_id, claimed_at in rows}


async def audience(
    session: AsyncSession, *, since: datetime | None = None, until: datetime | None = None
) -> dict[str, set[str]]:
    """Who reached each stage in the window, as sets of surviving identities.

    **An identity is an account where there is one and a browser where there is
    not, and the join between them is what makes the report a funnel rather than
    two unrelated tallies.** Somebody who lands, does the quiz and then saves a
    birth is one person whose first three stages carry a browser id and whose
    later ones carry an account id; resolving the browser id through the claim
    is what stops the first conversion rate reading zero.

    The order matters and it is the reverse of what reads naturally. An
    anonymous id is resolved to the account that claimed it *before* the merge
    pointer is followed, because both indirections can apply to one row: a
    browser becomes a guest account, and that guest is later folded into an
    account the person already had. Following only one of the two leaves the
    same person counted as two, which is the failure this whole function exists
    to prevent.

    **The claim is a window, not a permanent redirection**, and that is the one
    rule here that was wrong rather than merely unstated. Resolving every bare
    id to whichever account once claimed it reads well and produces a
    cross-person attribution on the ordinary shared machine: a family computer
    or a library terminal where the first person's account minted out of the
    browser and the second person arrives with no token. Their landing view and
    their quiz were filed under the first person, whose conversion rate they
    silently improved, and whose deletion silently erased them. After the claim
    the browser that owns the account sends a token with every request, so a row
    that arrives without one is not that session — it is an identity we cannot
    name, and it is counted as one. See `CLAIM_GRACE` for why the boundary is
    not the claim instant exactly.

    An id nobody has claimed is a real identity of its own, prefixed so it can
    never collide with an account id. Dropping those instead would delete
    everybody who has not converted yet, which is to say the denominator.

    One browser can therefore contribute two identities to the same stage, and
    that is the honest answer rather than a rounding error: the rows inside the
    window are the person who converted, and the rows outside it are somebody
    about whom the only true statement is that they were here.

    The purchase stage is unioned in from the money trail rather than read from
    the event table. Union rather than replacement because a `purchase` row can
    only have been written by our own server-side code — the HTTP route refuses
    the name — so both sources are trustworthy and neither is complete on its
    own: a payment reconciled by hand has a `Purchase` row and no event.
    """
    canonical = await _merged_into(session)
    claimed = await _claimed_by(session)

    def fold(user_id: str) -> str:
        return canonical.get(user_id, user_id)

    def identities(
        user_id: str | None, anon_id: str | None, first: object, last: object
    ) -> set[str]:
        if user_id is not None:
            return {fold(user_id)}

        claim = claimed.get(anon_id or "")
        if claim is None:
            return {f"anon:{anon_id}"}

        owner, claimed_at = claim
        closes = as_utc(claimed_at)
        if closes is None:  # pragma: no cover - the column has a default
            return {fold(owner)}
        closes = closes + CLAIM_GRACE

        found: set[str] = set()
        if (as_utc(first) or closes) <= closes:
            found.add(fold(owner))
        if (as_utc(last) or closes) > closes:
            found.add(f"anon:{anon_id}")
        return found

    window = []
    if since is not None:
        window.append(Event.created_at >= since)
    if until is not None:
        window.append(Event.created_at < until)

    # Grouped rather than `DISTINCT`, and it returns the same number of rows the
    # `DISTINCT` did: one per (stage, identity). The two timestamps come out of
    # the aggregate instead of off each row, because this is the one table that
    # grows with traffic rather than with customers and the query walks every
    # row of a month — selecting `created_at` per row to compare it in Python
    # would have made `DISTINCT` a no-op and dragged the whole month back.
    rows = (
        await session.execute(
            select(
                Event.name,
                Event.user_id,
                Event.anon_id,
                func.min(Event.created_at),
                func.max(Event.created_at),
            )
            .where(
                or_(Event.user_id.is_not(None), Event.anon_id.is_not(None)),
                Event.name.in_(STAGE_NAMES),
                *window,
            )
            .group_by(Event.name, Event.user_id, Event.anon_id)
        )
    ).all()

    reached: dict[str, set[str]] = {name: set() for name in STAGE_NAMES}
    for name, user_id, anon_id, first, last in rows:
        reached[name] |= identities(user_id, anon_id, first, last)

    paid_window = []
    if since is not None:
        paid_window.append(Purchase.completed_at >= since)
    if until is not None:
        paid_window.append(Purchase.completed_at < until)

    paid = (
        await session.execute(
            select(Purchase.user_id)
            .where(
                Purchase.user_id.is_not(None),
                # `completed_at` is set by the webhook and only on a payment,
                # so this is money that actually moved rather than a checkout
                # that was opened or an adjustment that reduced one.
                Purchase.completed_at.is_not(None),
                *paid_window,
            )
            .distinct()
        )
    ).scalars().all()
    reached["purchase"] |= {fold(user_id) for user_id in paid}

    return reached


async def funnel(
    session: AsyncSession, *, since: datetime | None = None, until: datetime | None = None
) -> list[Step]:
    """Of the people who reached each stage, how many reached the next.

    Membership, not chronology: a step's population is the previous step's
    population intersected with everyone who reached this stage, and no
    ordering of timestamps is required. Requiring one sounds stricter and is
    wrong here — someone reads their portrait on Tuesday, thinks about it, and
    buys on Friday from the same account, and a browser that batches two
    beacons can deliver them a second apart in either order. An ordering rule
    would drop both, and it would drop them silently.
    """
    reached = await audience(session, since=since, until=until)

    along_the_path: dict[str, set[str]] = {}
    steps: list[Step] = []
    for stage in STAGES:
        everyone = reached[stage.name]
        base = along_the_path[stage.after] if stage.after else None
        here = everyone if base is None else everyone & base

        along_the_path[stage.name] = here
        steps.append(
            Step(
                stage=stage.name,
                of=stage.after,
                reached=len(here),
                total=len(everyone),
                # No rate against an empty base. A funnel that divides by zero
                # to report 0% tells whoever reads it that nobody converted,
                # when what happened is that nobody arrived.
                rate=(len(here) / len(base)) if base else None,
            )
        )
    return steps


def render(steps: list[Step]) -> str:
    """The funnel as a block of text, for a terminal or a log line.

    Колонка имени — 24, а не 18: `free_chapter_completed` длиннее восемнадцати,
    и на узкой колонке числа съезжали бы ровно у ступеней лестницы, то есть у
    тех строк, ради которых отчёт теперь и открывают.
    """
    lines = [f"{'stage':<24}{'reached':>9}{'total':>8}  of"]
    for step in steps:
        rate = "" if step.rate is None else f"  {step.rate * 100:5.1f}% of {step.of}"
        lines.append(f"{step.stage:<24}{step.reached:>9}{step.total:>8}{rate}")
    return "\n".join(lines)


async def _run(days: int) -> list[Step]:
    from .db.session import session_scope

    since = utcnow() - timedelta(days=days)
    async with session_scope() as session:
        return await funnel(session, since=since)


async def _purge(days: int) -> int:
    from .db.session import session_scope

    async with session_scope() as session:
        return await purge(session, days=days)


if __name__ == "__main__":  # pragma: no cover - the operator's entry point
    parser = argparse.ArgumentParser(description="The conversion funnel, from our own rows.")
    parser.add_argument(
        "--days", type=int, default=30,
        help="how far back to look; 30 is the window the pricing work asks for",
    )
    parser.add_argument(
        "--purge", action="store_true",
        help=(
            "delete every step label older than the retention on the privacy "
            f"page ({PURGE_AFTER_DAYS} days) and print how many went. This is "
            "the half of that promise a person cannot verify from the outside, "
            "so it belongs in cron — see backend/README.md."
        ),
    )
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if arguments.purge:
        print(f"{asyncio.run(_purge(PURGE_AFTER_DAYS))} step label(s) deleted")
    else:
        print(render(asyncio.run(_run(arguments.days))))
