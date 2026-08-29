"""Settings, read from the environment and nowhere else.

No secret is ever written to a file in this repository. Keys live in the
process environment — `.env.local` in development, the platform's secret
store in production — and the application reads them at startup. If a
required secret is missing the service says so loudly rather than starting up
in a degraded state that only fails on the first paying customer.

`ALMA_` prefixes everything we own; the exceptions are `ANTHROPIC_API_KEY` and
the four processors' variables, which keep the names their own documentation
uses so that copying a value from a dashboard into a shell just works. That is
also why the Dodo names are the long `DODO_PAYMENTS_*` ones rather than a tidy
`DODO_*`: the tidier name is not the one printed next to the value.

Two of the store variables are worth reading twice, because they are the only
places in this file where a name does not mean what its neighbours mean.
`APPLE_BUNDLE_ID` is a **credential that is not a secret** — it is public, it is
in every copy of the app, and it is nonetheless the whole of what stops another
app's Apple-signed purchase unlocking a reading here.
`GOOGLE_PLAY_PUBSUB_AUDIENCE` is the reverse: an ordinary-looking string that is
in practice a shared secret, because it is the only claim distinguishing Google
Play's notifications from any other Google customer's.
"""

from __future__ import annotations

import os

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:  # only for the annotation — importing it here would cycle
    from .billing.provider import BillingProvider

BASE_DIR = Path(__file__).resolve().parents[1]

#: The processors this build can talk to. Four, and they are not four bets on
#: the same table.
#:
#: The first two are card processors and both are wagers: our category is
#: *prohibited* by Paddle's acceptable-use policy — "clairvoyance, horoscopes,
#: fortune-telling" — and merely reviewable by Dodo's, and neither has approved
#: us. The second two are the stores, where the category question does not
#: arise: Apple and Google both permit astrology apps outright, and both are the
#: merchant of record, which is also what removes the EU OSS registration, the
#: Brazilian CNPJ and the US state registrations.
#:
#: Named here so the error for a mistyped `ALMA_BILLING_PROVIDER` can list them,
#: and kept as one knob rather than two because a build serves one of these at a
#: time: the iOS binary is configured `appstore`, the Android binary
#: `googleplay`, and the web landing keeps a card processor for as long as it
#: sells anything at all.
BILLING_PROVIDERS: tuple[str, ...] = ("paddle", "dodo", "appstore", "googleplay")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Skipped under the test suite: a suite that reads the developer's
        # `.env` tests their machine rather than the code, and the failure
        # mode is silent — an assertion about a *missing* key passes only
        # while the key happens to be missing.
        env_file=() if os.getenv("ALMA_SKIP_DOTENV") else (".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── service ────────────────────────────────────────────────────────────
    environment: str = Field(default="development", alias="ALMA_ENV")
    debug: bool = Field(default=False, alias="ALMA_DEBUG")
    base_url: str = Field(default="http://localhost:8000", alias="ALMA_BASE_URL")
    web_url: str = Field(default="http://localhost:3000", alias="ALMA_WEB_URL")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000", alias="ALMA_CORS_ORIGINS"
    )

    #: Стоит ли перед нами край (CDN/балансировщик), которому можно верить
    #: заголовки о клиенте и его стране.
    #:
    #: **По умолчанию `False`, и это решение безопасности, а не удобства.**
    #: `request_source` (потолки по источнику) и `region.from_headers` (валюта и
    #: цена по стране) читали `CF-Connecting-IP`, `True-Client-IP`, `X-Real-IP`,
    #: `CF-IPCountry` и т.п. Эти заголовки достоверны, только если край их
    #: **перезаписывает** поверх присланного клиентом. На инстансе, доступном
    #: напрямую (или за CDN, который их не чистит), их присылает атакующий: смена
    #: одного заголовка на запрос обнуляет любой потолок по источнику
    #: (брутфорс `/admin`, безлимитная ротация гостей = месячные бюджеты, перебор
    #: кодов из письма), а подделка `CF-IPCountry` выбирает валюту и локальную
    #: цену. Найдено аудитом 29.08.2026 (BUG-003, BUG-004).
    #:
    #: Пока флаг выключен, `deps.request_source` берёт только адрес сокета, а
    #: `region` — только `?country=` из тела/строки (для витрины), не заголовок.
    #: На проде за Cloudflare владелец ставит `ALMA_TRUSTED_EDGE=true`, и тогда
    #: край снова становится источником правды. Что именно читать при доверенном
    #: крае — списки `deps.CLIENT_IP_HEADERS` и `region.EDGE_COUNTRY_HEADERS`;
    #: на проде их стоит сузить до одного заголовка, который край гарантированно
    #: перезаписывает (`cf-connecting-ip`, `cf-ipcountry`).
    trusted_edge: bool = Field(default=False, alias="ALMA_TRUSTED_EDGE")

    # ── storage ────────────────────────────────────────────────────────────
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'alma.db'}",
        alias="ALMA_DATABASE_URL",
    )

    # ── auth ───────────────────────────────────────────────────────────────
    # A generated default keeps development frictionless. Production refuses
    # to start without a real one — see `check_production_ready`.
    jwt_secret: str = Field(default="dev-only-not-a-secret", alias="ALMA_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="ALMA_JWT_ALGORITHM")
    access_token_days: int = Field(default=90, alias="ALMA_ACCESS_TOKEN_DAYS")
    magic_link_minutes: int = Field(default=20, alias="ALMA_MAGIC_LINK_MINUTES")

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def _empty_secret_is_unset(cls, value):
        # `.env.example` и `.env.local` держат `ALMA_JWT_SECRET=` пустым — это
        # «ещё не задано», а не «задано пустым». Пустая строка перезаписывала
        # непустой дефолт, приложение стартовало здоровым и падало 500
        # (`HMAC key must not be empty`) на первом же запросе, минтящем токен, —
        # перед клиентом, а не на старте. Найдено аудитом 20.08.2026.
        #
        # Свести пустое к дефолту: в разработке беструдно, а прод и так отвергает
        # дефолт (`_production_failures`, `missing_for_production`) — теперь той
        # же дорогой отвергается и пустое, громко и на старте.
        if value is not None and not str(value).strip():
            return "dev-only-not-a-secret"
        return value

    #: Солёный scrypt-хэш пароля админки (`/admin`), формат
    #: `scrypt$n$r$p$salt$hash` — сгенерировать `python -m tools.admin_password`.
    #: Пароль в .env не живёт — хэш пускает внутрь ровно так же, а его утечка
    #: паролем не является (медленный KDF, BUG-005). Пусто — админки нет: вход
    #: отвечает 503, никакого дефолта. Старый голый SHA-256 больше не принимается.
    admin_password_hash: str = Field(default="", alias="ALMA_ADMIN_PASSWORD_HASH")

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    apple_client_id: str = Field(default="", alias="APPLE_CLIENT_ID")

    # ── mail ───────────────────────────────────────────────────────────────
    mail_from: str = Field(default="alma@example.com", alias="ALMA_MAIL_FROM")
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")

    # ── AI ─────────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    model_strong: str = Field(default="claude-opus-5", alias="ALMA_MODEL_STRONG")
    model_mid: str = Field(default="claude-sonnet-5", alias="ALMA_MODEL_MID")
    model_cheap: str = Field(default="claude-haiku-4-5", alias="ALMA_MODEL_CHEAP")

    #: Hard ceilings, in US dollars. Crossing one is an incident, not a cost.
    #: These two bound a single generation.
    free_user_budget: float = Field(default=0.05, alias="ALMA_FREE_USER_BUDGET")
    full_report_budget: float = Field(default=0.50, alias="ALMA_FULL_REPORT_BUDGET")

    #: ...and these three bound an *account*, across a calendar month. A
    #: per-call ceiling cannot see a thousand individually-cheap calls, so on
    #: its own it stops nothing that matters; the cumulative number is the one
    #: that decides how much a tier is allowed to lose before it stops being a
    #: customer worth having. The tiers must not cross — see the validator.
    #:
    #: **A ceiling is a refusal threshold, not a forecast.** Each of these has
    #: to sit *above* everything its tier is openly promised, or the promise is
    #: a lie the person discovers halfway through a month: they are told they
    #: have questions left and answered 429 `month_budget`. The three numbers
    #: were 0.45 / 0.70 / 1.00 and none of them cleared its own tier — an owner
    #: was advertised fifty questions a day, thirteen times what the ceiling
    #: could fund, and ran out on about the fourth. The arithmetic is pinned by
    #: `test_readings_budget.py::test_no_tier_is_promised_more_than_its_ceiling_can_fund`,
    #: which prices each tier's advertised allowance through the router's own
    #: projection helpers, so the pair cannot drift apart again.
    #:
    #: They are large relative to what a tier actually costs, and that is the
    #: point: the expected free account uses a fraction of three questions a
    #: day and reads two sample chapters, while the ceiling has to clear a free
    #: account that uses every question every day *and* reads all eight
    #: samples in the same month.
    #:
    #: It was 1.00 and the promise grew past it. Alma's conversation rules —
    #: what she does with a greeting, a language she does not write, a person
    #: saying they feel awful — are a system prompt sent on every chat turn,
    #: and writing the twenty branches of `docs/CONVERSATION.md §7` costs about
    #: 3,400 characters where the four rules they replaced cost 830. Priced by
    #: the same projection the test uses: **$0.0082 → $0.0090 a turn on the
    #: cheap model**, and across a maximal free month, $0.956 → $1.029. The
    #: choice was to withdraw rules or to move this number, and this file's own
    #: instruction is that the ceiling clears the promise rather than the other
    #: way round: a ceiling is a refusal threshold, and refusing to teach her
    #: how to answer "hello" to save three cents of a worst case almost nobody
    #: reaches is not a saving, it is the bug the rules were written for.
    #:
    #: The structural fix, taken: the system block is byte-identical on every
    #: turn of every conversation, so it is sent with `cache_control` and read
    #: from cache at a tenth of the input price (`ai/provider.py`), and the
    #: cost arithmetic prices cache reads and writes at their own rates
    #: (`ai/cost.py`). The ceilings stay where they are — they are refusal
    #: thresholds sized to the uncached worst case, and a cold cache is
    #: exactly that case.
    #:
    #: **19.08.2026: число то же, но считает оно теперь другое.** Расход витрины
    #: (открывающие абзацы закрытых глав) переехал в свою статью леджера —
    #: `cost.SHOWCASE_METRIC`, — потому что по замеру он один съедал этот потолок
    #: целиком: 36 достижимых абзацев × 3.556¢ = $1.28 против $1.10, то есть
    #: человек, посмотревший витрину, получал 429 на первом же бесплатном
    #: вопросе. Что осталось под этим потолком: три приветственных вопроса и
    #: одна бесплатная глава — $0.29 по замеренным ставкам, запас почти
    #: четырёхкратный, и он не лишний, потому что сюда же ходят превью сфер и
    #: ежедневная заметка, которых в худшем месяце теста нет.
    #:
    #: Витрина при этом не бесплатна и не безнадзорна: её потолок — шестьдесят
    #: абзацев в месяц (`readings.OPENING_ALLOWANCE`), в деньгах $2.50
    #: (`readings.SHOWCASE_MONTH_CEILING`). Худший месяц свободного аккаунта
    #: складывается из двух слагаемых, и это надо читать как «$1.10 чтения плюс
    #: до $2.50 показа», а не как «$1.10 всего».
    free_month_budget: float = Field(default=1.10, alias="ALMA_FREE_MONTH_BUDGET")
    #: The owner ceiling recurs and the payment that earned it does not.
    #: `tier_of` answers "owner" for any in-force one-time purchase, and a
    #: one-time grant never expires, so an $8.99 door buys this allowance every
    #: month for as long as the account lives. Chapters are written once and
    #: re-served from the `Reading` row, so what actually recurs is chat:
    #: `paid_questions_per_day` at the cheap model, about $0.68 a month at the
    #: measured rate, which pays back an $8.99 door in a little over a year.
    #: That is a real decision and it has not been made — the honest options
    #: are to let the owner allowance decay after N months, or to fund it from
    #: the subscription instead. It is written here rather than in a ticket
    #: because the number reads, silently, as though the purchase repeats.
    #:
    #: 3.00 → 3.25 for the same reason as the free ceiling above, and by the
    #: same arithmetic: an owner is promised five questions a day, so the extra
    #: 2,600 characters of conversation rules cost this tier 150 × $0.0008 =
    #: $0.12 a month at the worst case, and 3.00 no longer cleared the promise
    #: (2.977 → 3.098). Nothing about the *expected* owner changed; this is the
    #: threshold at which we stop serving somebody who uses every question of
    #: every day and buys the whole archive in the same month.
    #:
    #: **3.25 → 3.60, 17.08.2026, и это прямая цена двух решений владельца.**
    #: Худший месяц владельца — это теперь обход всех сорока закрытых глав
    #: *до* покупки ($0.693 открывающих абзацев), а потом весь архив после неё;
    #: и сам архив подорожал, потому что семь первых глав перестали быть
    #: бесплатными и пишутся сильной моделью в 480 слов вместо средней в 320
    #: ($2.253 → $2.459 в проекции потолка). Итого $3.415 против прежних
    #: $3.098 — то есть 3.25 перестало покрывать обещание в тот же коммит, и
    #: поймано это было `test_no_tier_is_promised_more_than_its_ceiling_can_fund`,
    #: а не счётом от провайдера.
    #:
    #: Что важно не спутать: это **порог отказа по худшему случаю**, а не
    #: ожидаемый расход. Обычный покупатель не обходит сорок закрытых глав
    #: перед покупкой и не дочитывает архив за месяц; но тот, кто сделал и то и
    #: другое, заплатил нам $19.99 за бандл, и упереться ему в 429 посреди
    #: купленного разбора было бы худшей из возможных ошибок этого числа.
    #:
    #: **3.60 → 5.50, 19.08.2026, и это не рост расходов, а конец их занижения.**
    #: Всё, что стоит выше, посчитано по проекции `cost.estimate`, а она вдвое
    #: ниже счёта: по `data/alma.db` глава на opus стоит 11.19¢ против 6.07¢
    #: проекции, ход беседы — 7.68¢ против 3.20¢ (`cost.MEASURED_OVER_PROJECTED`,
    #: там же и оговорка о выборке). Пересчитанный худший месяц владельца:
    #: весь архив $4.53 + пять вопросов на сильной модели $0.64 = **$5.18**
    #: против прежнего потолка $3.60, то есть владелец бандла упирался в 429
    #: примерно на семидесятом проценте купленного. Открывающих абзацев в этой
    #: строке больше нет — они ушли в статью витрины, — и это единственное, что
    #: её удешевило.
    #:
    #: Запас до 5.50 — шесть процентов, и меньше делать нельзя: сами проекции
    #: считаются по сегодняшнему небу и гуляют примерно на процент от часа к
    #: часу (список транзитных факторов то длиннее, то короче), так что потолок,
    #: подогнанный впритык, падал бы в CI по расписанию Луны. Больше — тоже нет:
    #: это порог отказа по худшему случаю, а не прогноз. Обычный владелец не
    #: дочитывает архив за месяц, а перечитывание написанной главы бесплатно.
    owner_month_budget: float = Field(default=5.50, alias="ALMA_OWNER_MONTH_BUDGET")
    #: Поднят с 3.50 вместе с длиной платных глав: сорок одна глава по
    #: 480 слов плюс вопросы месяца дают $3.52 в худшем случае, и прежний
    #: потолок обещал больше, чем мог оплатить. Поймано
    #: `test_no_tier_is_promised_more_than_its_ceiling_can_fund`.
    #:
    #: Число вопросов с тех пор снижено владельцем до 30 (25 на кириллице), и
    #: запас стал только больше — но потолок не опущен обратно намеренно:
    #: он считается по худшему случаю, а худший случай теперь дешевле обещания,
    #: и это правильная сторона ошибки.
    #:
    #: **4.50 → 7.30, 19.08.2026, по той же причине, что и потолок владельца:
    #: обещание считалось в предсказанных деньгах, а платим мы в настоящих.**
    #: Подписчику обещаны весь архив и 30 вопросов в месяц; по замеру это
    #: 41 × 11.19¢ + 30 × 7.68¢ = **$6.86** (проекция говорила $3.36, и потому
    #: $4.50 выглядели запасом вдвое). Подписчик, взявший обещанное, упирался в
    #: 429 примерно на 59 % пути — то есть в середине первого же месяца, за
    #: который он заплатил.
    #:
    #: Резать обещание, чтобы оно влезло, здесь нельзя, и это записанное решение:
    #: `docs/monetization/alma-monetization-v3-tech-appendix.md` §А12 — «если не
    #: проходит, поднимаем потолок, а не режем обещание». Запас до 7.30 —
    #: шесть процентов, по тому же доводу, что и у владельца выше.
    #:
    #: **Что этот порог означает для маржи — вопрос владельца, а не кода.**
    #: $7.30 — это потолок первого месяца подписчика, который дочитал весь архив;
    #: со второго месяца архив уже написан и отдаётся из `Reading`, так что
    #: повторяющаяся часть — только вопросы, $2.32 в худшем случае. При $9.99
    #: и магазинной комиссии это значит: первый месяц может уйти почти в ноль,
    #: дальше маржа возвращается. Число поднято именно потому, что отказ в
    #: середине оплаченного месяца стоит дороже любой из этих цифр.
    subscriber_month_budget: float = Field(default=7.30, alias="ALMA_SUBSCRIBER_MONTH_BUDGET")

    # ── billing ────────────────────────────────────────────────────────────
    #: Which processor takes the money. One knob, because being refused by a
    #: processor is a thing that happens to businesses like ours rather than a
    #: hypothetical: Paddle's acceptable-use policy names our category —
    #: clairvoyance, horoscopes, fortune-telling — as *prohibited*, and
    #: FastSpring and 2Checkout carry the same clause almost word for word.
    #: Dodo puts us on a requires-review list instead. Nobody has approved us
    #: yet, so the processor is a decision that will be made *for* us, possibly
    #: twice, and this line is what makes the second time an afternoon.
    #:
    #: The value is a name, not a URL or a class path: an operator changing
    #: processors under pressure should be typing a word they have read in our
    #: documentation, and anything else here refuses to start — see
    #: `_billing_is_configured_or_plainly_off`.
    billing_provider: str = Field(default="paddle", alias="ALMA_BILLING_PROVIDER")

    paddle_api_key: str = Field(default="", alias="PADDLE_API_KEY")
    paddle_client_token: str = Field(default="", alias="PADDLE_CLIENT_TOKEN")
    paddle_webhook_secret: str = Field(default="", alias="PADDLE_WEBHOOK_SECRET")
    paddle_environment: str = Field(default="sandbox", alias="PADDLE_ENVIRONMENT")

    #: Dodo's two secrets and its environment word. There is no third
    #: credential to match `PADDLE_CLIENT_TOKEN`, and that is a property of the
    #: design rather than an omission: Dodo's server creates the checkout
    #: session and hands back a URL or a per-session client secret, so there is
    #: nothing publishable for the browser to hold.
    dodo_api_key: str = Field(default="", alias="DODO_PAYMENTS_API_KEY")
    dodo_webhook_secret: str = Field(default="", alias="DODO_PAYMENTS_WEBHOOK_KEY")
    #: Their own two words, "test_mode" and "live_mode", rather than Paddle's
    #: "sandbox" and "production". Translating them here would mean an operator
    #: reading our documentation and their dashboard sees two different words
    #: for the same switch.
    dodo_environment: str = Field(default="test_mode", alias="DODO_PAYMENTS_ENVIRONMENT")

    #: **Apple's only credential, and it is not a secret.** There is no shared
    #: key with the App Store: a StoreKit transaction is a JWS signed by a
    #: certificate chain rooting in Apple Root CA - G3, which is pinned in
    #: `billing/appstore.py`, so verification needs nothing from us. What the
    #: bundle id does is answer the *other* question — a valid Apple signature
    #: proves Apple signed it, not that it is ours, and Apple signs a
    #: transaction for every app on the store. Somebody's flashlight purchase
    #: presented to `/billing/iap/verify` is a genuine Apple signature over a
    #: genuine transaction, and this line is the whole of what refuses it.
    apple_bundle_id: str = Field(default="", alias="APPLE_BUNDLE_ID")

    #: Whether a Sandbox-signed transaction may grant.
    #:
    #: **True, and turning it off breaks App Review.** Apple's reviewers run the
    #: production build against sandbox StoreKit accounts, so a build that
    #: refuses `environment: "Sandbox"` is a build that gets rejected for
    #: in-app purchases that do not work. The cost of leaving it on is real and
    #: is stated rather than hidden: anyone who can create a sandbox tester
    #: against our bundle can mint purchases that verify. Both halves of the
    #: trade are bad and there is no third option; what makes it survivable is
    #: that the environment is recorded on every event and every grant, so the
    #: two populations can be told apart afterwards.
    apple_accept_sandbox: bool = Field(default=True, alias="ALMA_APPLE_ACCEPT_SANDBOX")

    #: Google's three. Unlike Apple, a Play purchase token proves nothing on its
    #: own — it is a key into Google's database — so verifying one means calling
    #: the Play Developer API *as us*, which is what the service account is for.
    #: The JSON may be the credentials themselves or a path to a file holding
    #: them, because a platform secret store hands over a string and a mounted
    #: volume hands over a path, and a second variable saying which would be one
    #: more thing to get wrong.
    google_play_package: str = Field(default="", alias="GOOGLE_PLAY_PACKAGE_NAME")
    google_play_service_account: str = Field(
        default="", alias="GOOGLE_PLAY_SERVICE_ACCOUNT_JSON"
    )
    #: The audience on our Pub/Sub push subscription, and the nearest thing this
    #: adapter has to a webhook secret. A Real-time Developer Notification is an
    #: unsigned body; what is signed is the OIDC token Pub/Sub puts in the
    #: `Authorization` header, and Google will mint a valid one for any of its
    #: customers — so the signature alone proves only that *somebody* with a
    #: Google account sent it. The audience is configured on our subscription
    #: and nowhere else, which is what makes it ours. Required, therefore, in
    #: the same breath as the other two: without it the notification endpoint
    #: grants renewals to whoever finds the URL.
    google_play_pubsub_audience: str = Field(
        default="", alias="GOOGLE_PLAY_PUBSUB_AUDIENCE"
    )
    #: ...and, optionally, *which* identity may push. Optional because a
    #: deployment can be correct without it and required-in-spirit because with
    #: it an audience string leaking from a proxy log is no longer enough on its
    #: own. The adapter logs a warning when it is unset rather than failing, so
    #: the gap is visible in the place operators actually look.
    google_play_pubsub_service_account: str = Field(
        default="", alias="GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT"
    )

    #: What our products are called in App Store Connect and the Play Console.
    #:
    #: A rule rather than a table, and the difference is the difference between
    #: a store and a card processor. A Paddle price id is *issued* — it appears
    #: in a dashboard and no code can predict it, which is why
    #: `Product.processor_ids` is empty and filled in by hand. A store product
    #: id is *chosen*: we type it into the console. So the catalogue key is the
    #: id, with this prefix in front of it and hyphens turned into underscores,
    #: because neither console accepts a hyphen. See
    #: `billing/provider.py::store_product_id`, which is the one place the rule
    #: lives, and which still lets a pinned `processor_ids` entry win.
    #: **Решено владельцем 17 августа 2026: как в приложении.** Выбор стоял
    #: между `alma.` — тем, что просили все прежние сборки, — и `ai.pazl.alma.`,
    #: совпадающим с идентификатором самого приложения. Владелец: «как в
    #: приложении».
    #:
    #: Решение необратимо: ни один магазин не даёт переименовать или
    #: переиспользовать идентификатор товара после публикации, и цена ошибки —
    #: второй набор товаров плюс перенос всех, кто уже купил. Менять это
    #: значение после первой публикации нельзя.
    store_product_prefix: str = Field(
        default="ai.pazl.alma.", alias="ALMA_STORE_PRODUCT_PREFIX"
    )

    # ── push ───────────────────────────────────────────────────────────────
    #: Apple's four, and they are one credential rather than four settings.
    #:
    #: The `.p8` is the private half of a token-signing key and is the only
    #: secret here; the other three are public identifiers that decide what the
    #: signature *means*. A key with the wrong team id signs a token Apple
    #: rejects, and a wrong topic is `400 DeviceTokenNotForTopic` — so all four
    #: are required together or none of them is, which is what
    #: `missing_push_credentials` enforces.
    #:
    #: The value may be the PEM itself or a path to a file holding it, for the
    #: same reason the Play service account may be: a platform secret store
    #: hands over a string and a mounted volume hands over a path, and a second
    #: variable saying which would be one more thing to get wrong.
    apns_key_p8: str = Field(default="", alias="ALMA_APNS_KEY_P8")
    apns_key_id: str = Field(default="", alias="ALMA_APNS_KEY_ID")
    apns_team_id: str = Field(default="", alias="ALMA_APNS_TEAM_ID")
    #: The bundle identifier, which is also `apns-topic`. Blocked on the
    #: product-id prefix decision in `STATUS.md §4②` — you cannot enable Push
    #: Notifications on an App ID that does not exist yet.
    apns_topic: str = Field(default="", alias="ALMA_APNS_TOPIC")
    #: Which host a token with **no recorded environment** is sent to. Not the
    #: switch it looks like: `DeviceToken.environment` decides per token, and
    #: this is only the answer for a row written before that column existed.
    #: A deployment-wide environment switch is exactly the design that sends
    #: every TestFlight tester's notification into the void — see PUSH.md §1.8.
    apns_environment: str = Field(default="production", alias="ALMA_APNS_ENVIRONMENT")

    #: Google's two. Same string-or-path rule as the Play billing service
    #: account, and deliberately not the same credential: this one needs the
    #: `firebase.messaging` scope and the billing one does not, and a single
    #: over-scoped key is a key whose leak costs more than it had to.
    fcm_service_account: str = Field(default="", alias="ALMA_FCM_SERVICE_ACCOUNT_JSON")
    fcm_project_id: str = Field(default="", alias="ALMA_FCM_PROJECT_ID")

    # ── limits ─────────────────────────────────────────────────────────────
    #: The chat allowances, in one place so they can be read against each
    #: other and against the monthly ceilings above.
    #:
    #: **Zero, and the cheap tier is gone.** Free used to be three a day for
    #: ever on the cheapest model, and the owner's verdict on that model was
    #: final — it made Alma sound stupid, and a shop window that makes the
    #: product look worse than it is sells against it. The free taste is the
    #: welcome question below, on the model that sells; after it the
    #: conversation belongs to the plan. Everything else the product is —
    #: eight systems, calculated in full — stays free for ever.
    free_questions_per_day: int = Field(default=0, alias="ALMA_FREE_QUESTIONS")
    paid_questions_per_day: int = Field(default=5, alias="ALMA_PAID_QUESTIONS")
    #: Questions included with a one-time purchase, for the life of the
    #: account rather than per day — five, on the **strong** model, the same
    #: voice the paid readings are written in. The tasting rather than the
    #: meal: about fifty cents of generation against eight dollars of net
    #: revenue, and when it runs out the subscription is the way to have more.
    owner_question_bundle: int = Field(default=5, alias="ALMA_OWNER_BUNDLE")
    #: The first questions anybody ever asks, on the better model, once per
    #: account and never again.
    #:
    #: **The shop window used to run on the cheapest model.** Free meant
    #: `claude-haiku-4-5`, and the owner's verdict on his own product was that
    #: Alma is stupid. Measured on one chart, one question — *what are my
    #: talents* — the cheap model returned four flat sentences and the mid model
    #: returned the specific, usable one: *"you see the error in the invoice
    #: before anyone else does."* The second is the product. The first is what
    #: everybody who has not paid was being shown.
    #:
    #: Three a month, and they are the whole free conversation. «Один и
    #: навсегда» здесь уже стояло — и это было решение владельца до v3; ТЗ
    #: монетизации v3 (§2, §3 P6) перерешило: бесплатный слой — **3 вопроса в
    #: месяц**, и экран квоты встречает четвёртый, а не второй. Порядок цены
    #: тот же — центы за активного бесплатного читателя в месяц, на модели,
    #: которая продаёт; после третьего беседу несёт план.
    free_welcome_bundle: int = Field(default=3, alias="ALMA_WELCOME_BUNDLE")
    #: `ALMA_PREVIEW_CHAPTERS` жил здесь и снят вместе с самим превью.
    #:
    #: Он задавал, сколько закрытых глав аккаунту напишут по-настоящему до
    #: оплаты: глава сочинялась целиком, первый абзац показывался, остальное
    #: размывалось. Владелец отменил это правило — каждое превью стоило записи
    #: сильной моделью ($0.02–0.10) за того, кто не заплатил ничего. Ручку
    #: убрали, а не оставили с нулём: настройка, которая ничего не включает,
    #: обещает включаемость. Правило и причина записаны там, где стоит стена, —
    #: `api/routers/readings.py`, в `read()`.
    #: Counted per month rather than per day: what runs out for a subscriber is
    #: money, not patience, so a daily allowance large enough to feel like a
    #: subscription would be a promise that stops working on the eighth.
    #: Forty, not seventy. The figure the pricing model was built on assumed a
    #: chat turn costs $0.0135; a live turn on a real chart costs **$0.0472**,
    #: because these models reason before they answer and the reasoning is most
    #: of the tokens. Seventy turns is $3.30 of a $8.99 net subscription — a
    #: 62% margin on a product priced for 87%. Forty holds the margin at 78%
    #: and is still more conversation than anyone has in a month.
    subscriber_questions_per_month: int = Field(
        default=30, alias="ALMA_SUBSCRIBER_QUESTIONS"
    )

    #: То же для кириллицы, где тот же ответ стоит примерно вдвое.
    #:
    #: Русский текст токенизируется вдвое дороже латинского — это измерено и
    #: записано в `writer.py`. Одна и та же цифра для всех языков означала бы,
    #: что русский подписчик обходится дороже английского при той же цене.
    #: Владелец выбрал равную маржу, а не равный счёт вопросов.
    subscriber_questions_per_month_cyrillic: int = Field(
        default=25, alias="ALMA_SUBSCRIBER_QUESTIONS_CYRILLIC"
    )

    #: Недельная подписка — вход, а не месяц со скидкой.
    #:
    #: Она давала ту же месячную порцию за €4.99 против €9.99, и на комиссии
    #: 30% уходила в минус примерно на доллар с каждой. Десять вопросов на
    #: неделю — та же плотность разговора, что у месячной, но по своему сроку.
    weekly_questions_per_week: int = Field(
        default=10, alias="ALMA_WEEKLY_QUESTIONS"
    )

    # ── регулярные прогоны ─────────────────────────────────────────────────
    #: Сколько получателей утренняя рассылка обрабатывает одновременно.
    #:
    #: **Восемь, и это число выведено из арифметики, а не выбрано на глаз.**
    #: Одна утренняя запись — вызов `claude-sonnet-5` на ~1400 входных и ~420
    #: выходных токенов (`docs/THE-DAILY.md §2.2`), то есть порядка 8–12 секунд
    #: ожидания сети, из которых наш процесс занят долями секунды. Строго
    #: последовательный прогон на десяти тысячах подписчиков даёт в пиковый час
    #: часы вместо минут — полный расчёт в `docs/DEPLOY.md §6`, и он же
    #: показывает, что при восьми одновременных пиковый час укладывается в ~7
    #: минут.
    #:
    #: **Почему не «все разом».** Каждый получатель держит свою сессию к базе и
    #: свой запрос к модели. Тысяча одновременных корутин — это тысяча запросов
    #: к Anthropic в одну секунду (429 на всех сразу, и каждый 429 стоит
    #: попытки) и тысяча ожидающих соединений к Postgres, то есть отказ базы
    #: обслуживать сам API. Предел здесь — не оптимизация, а то, что отделяет
    #: параллельность от отказа: восемь одновременных генераций держат меньше
    #: одного запроса в секунду к модели и восемь соединений к базе.
    #:
    #: Ручка, а не константа, потому что верхняя граница задаётся не нашим
    #: кодом: её задают лимит аккаунта у Anthropic и размер пула базы, и оба
    #: меняются без единой строки правок здесь.
    daily_concurrency: int = Field(default=8, alias="ALMA_DAILY_CONCURRENCY")

    #: Каталог для файла-замка регулярных прогонов — `notify/daily.single_run`.
    #: Каталог, а не путь к файлу: замок нужен каждому регулярному процессу
    #: отдельно, и один каталог переживёт появление второго.
    run_lock_dir: str = Field(default=str(BASE_DIR / "data"), alias="ALMA_RUN_LOCK_DIR")

    @model_validator(mode="after")
    def _budgets_hold_together(self) -> Settings:
        """Refuse a set of ceilings that contradict each other.

        `ALMA_DAILY_SPEND_ALERT` used to sit alongside these and nothing in
        the codebase ever read it. A threshold no code checks is worse than no
        threshold at all — it reads, to whoever finds it next, as a promise
        that spending is being watched — so it was deleted rather than left
        there as reassurance. What replaces it is a check that actually runs:
        the numbers that *are* read have to make sense together.

        A budget of zero or less is almost always a mistyped environment
        variable, and it fails as a service that silently refuses to write
        anything. The tier order matters for a different reason: if a tier's
        monthly allowance is below the tier under it, paying us money buys
        somebody less than they had, and they find that out mid-sentence.
        """
        budgets = {
            "ALMA_FREE_USER_BUDGET": self.free_user_budget,
            "ALMA_FULL_REPORT_BUDGET": self.full_report_budget,
            "ALMA_FREE_MONTH_BUDGET": self.free_month_budget,
            "ALMA_OWNER_MONTH_BUDGET": self.owner_month_budget,
            "ALMA_SUBSCRIBER_MONTH_BUDGET": self.subscriber_month_budget,
        }
        for name, value in budgets.items():
            if value <= 0:
                raise ValueError(f"{name} is {value}; a ceiling of zero refuses everything")

        if not self.free_month_budget <= self.owner_month_budget <= self.subscriber_month_budget:
            raise ValueError(
                "the monthly ceilings must not cross: free "
                f"({self.free_month_budget}) ≤ owner ({self.owner_month_budget}) ≤ "
                f"subscriber ({self.subscriber_month_budget}), or an upgrade "
                "buys somebody less than they already had"
            )
        return self

    @model_validator(mode="after")
    def _billing_is_configured_or_plainly_off(self) -> Settings:
        """Refuse a processor we cannot talk to, and one configured by halves.

        Two failures, both of which used to be discovered by a customer.

        A name we do not ship is fatal in every environment. The alternative —
        falling back to the default — means a typo in `ALMA_BILLING_PROVIDER`
        silently routes real money through Paddle, which is the one processor
        whose policy names our category as prohibited.

        Half the credentials is fatal too, and the asymmetry with *no*
        credentials is the whole point. Nothing set is a legitimate state: this
        service runs all eight calculations without a processor, and the
        checkout answers 503 saying exactly which variables are absent. One of
        two set is somebody who believed they had finished — an API key with no
        webhook secret opens checkouts that can never be verified into a grant,
        so the money arrives and the reading does not, and the first person to
        find out is the one who paid.
        """
        try:
            credentials = self.billing_credentials
        except KeyError as exc:
            raise ValueError(
                f"ALMA_BILLING_PROVIDER is {self.billing_provider!r}, which is not a "
                f"processor this build can talk to — it ships {', '.join(BILLING_PROVIDERS)}"
            ) from exc

        present = [name for name, value in credentials.items() if value]
        if present and len(present) != len(credentials):
            missing = [name for name, value in credentials.items() if not value]
            raise ValueError(
                f"{self.billing_provider} billing is half configured: "
                f"{', '.join(present)} set, {', '.join(missing)} missing. "
                "A checkout that cannot be verified into a grant takes the money "
                "and gives nothing back."
            )
        return self

    @property
    def billing_credentials(self) -> dict[str, str]:
        """What the *selected* processor cannot run without, by variable name."""
        return self.credentials_for(self.billing_provider)

    def credentials_for(self, provider: str) -> dict[str, str]:
        """What **any** named processor cannot run without, by variable name.

        Keyed by the name an operator would export, because every caller of this
        either reports what is missing or refuses to start, and both are useless
        unless they say which line of the deploy configuration to fix.

        Named rather than always the selected one, because one deployment serves
        more than one store. `ALMA_BILLING_PROVIDER` decides who takes the money
        on the *web*, and the notification endpoint with it; but a single backend
        answers an iOS app and an Android app at the same time, and
        `/billing/iap/verify` resolves its adapter from the platform in the
        request. So "is this processor usable" is a question about a name, not
        about the configuration's favourite.

        Raises `KeyError` for a processor we do not ship; the validator turns
        that into a refusal at construction, so nothing at request time has to
        consider the possibility.
        """
        return {
            "paddle": {
                "PADDLE_API_KEY": self.paddle_api_key,
                "PADDLE_WEBHOOK_SECRET": self.paddle_webhook_secret,
            },
            "dodo": {
                "DODO_PAYMENTS_API_KEY": self.dodo_api_key,
                "DODO_PAYMENTS_WEBHOOK_KEY": self.dodo_webhook_secret,
            },
            # One variable, and it is not a secret — see the field. It is listed
            # here anyway, because what this mapping is for is "can the selected
            # processor do its job", and without a bundle id Apple's adapter
            # cannot tell our transactions from another app's. A single-entry
            # mapping also cannot be half configured, which is why the
            # half-configured check below is written against the length rather
            # than against a count of two.
            "appstore": {"APPLE_BUNDLE_ID": self.apple_bundle_id},
            "googleplay": {
                "GOOGLE_PLAY_PACKAGE_NAME": self.google_play_package,
                "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON": self.google_play_service_account,
                # In the required set rather than the optional one: a
                # notification endpoint with no audience to check is an endpoint
                # that extends subscriptions for anyone who finds the URL, and
                # discovering that from a `verify` refusal in production is
                # discovering it after the renewals have stopped landing.
                "GOOGLE_PLAY_PUBSUB_AUDIENCE": self.google_play_pubsub_audience,
            },
        }[provider.lower()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def is_postgres(self) -> bool:
        """Хранилище, которое переживёт больше одного пишущего процесса.

        Спрошено по схеме URL, а не по наличию слова «postgres» где угодно в
        строке: `postgresql+asyncpg://` и `postgresql://` — единственные две
        формы, которые SQLAlchemy здесь примет, и обе начинаются одинаково.
        """
        return self.database_url.strip().lower().startswith("postgresql")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def billing_enabled(self) -> bool:
        """Whether the *configured* processor can actually take money.

        Asked of whichever processor is selected, never of Paddle by name. It
        read `paddle_api_key and paddle_webhook_secret` outright, so a deploy
        that had switched to Dodo and still carried its old Paddle keys — which
        is exactly what a switchover looks like for a week — reported billing as
        working, opened checkouts, and could not verify a single webhook.
        """
        return not self.missing_billing_credentials()

    def missing_billing_credentials(self) -> list[str]:
        """The selected processor's variables that are still empty."""
        return [name for name, value in self.billing_credentials.items() if not value]

    def push_credentials(self, platform: str) -> dict[str, str]:
        """What one platform's push transport cannot run without, by variable.

        Keyed by the name an operator would export, exactly as
        `credentials_for` is and for the same reason: every caller of this
        either refuses to start or reports what is missing, and both are
        useless unless they name the line of the deploy configuration to fix.

        Per platform rather than one set, because the two halves ship
        independently — the iOS app can be sending for a month before the
        Android build is in review — and a single "push is configured" boolean
        would make the first release wait for the second.
        """
        return {
            "ios": {
                "ALMA_APNS_KEY_P8": self.apns_key_p8,
                "ALMA_APNS_KEY_ID": self.apns_key_id,
                "ALMA_APNS_TEAM_ID": self.apns_team_id,
                "ALMA_APNS_TOPIC": self.apns_topic,
            },
            "android": {
                "ALMA_FCM_SERVICE_ACCOUNT_JSON": self.fcm_service_account,
                "ALMA_FCM_PROJECT_ID": self.fcm_project_id,
            },
        }[platform.lower()]

    def missing_push_credentials(self, platform: str) -> list[str]:
        return [name for name, value in self.push_credentials(platform).items() if not value]

    def missing_for_production(self) -> list[str]:
        """What still has to be set before real money can change hands.

        Returned rather than raised so `/health` can report it and a deploy
        can be checked before it takes traffic. The one thing that *is* fatal
        is a production JWT secret left at its development default — every
        session token in the system would be forgeable.
        """
        missing: list[str] = []
        if self.jwt_secret == "dev-only-not-a-secret":
            missing.append("ALMA_JWT_SECRET")
        if not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        # SQLite в проде — не «медленнее», а «один пишущий на весь сервис».
        # Файл держит одну запись за раз (`db/session.py` включает WAL и
        # пятисекундное ожидание именно поэтому), а прод — это несколько
        # воркеров gunicorn плюс три регулярных процесса, то есть пять-шесть
        # претендентов на одну блокировку. Отказ выглядит как «database is
        # locked» посреди оплаченной генерации.
        if not self.is_postgres:
            missing.append("ALMA_DATABASE_URL")
        # Whichever processor is selected, named the way its own dashboard
        # names it. Listing Paddle's variables while `ALMA_BILLING_PROVIDER` is
        # "dodo" would send somebody to fill in credentials nothing reads.
        missing.extend(self.missing_billing_credentials())
        if not (self.google_client_id or self.apple_client_id or self.resend_api_key):
            missing.append("a sign-in method (GOOGLE_CLIENT_ID / APPLE_CLIENT_ID / RESEND_API_KEY)")
        # Push is reported only once somebody has started configuring it, and
        # that asymmetry is deliberate. Listing four APNs variables on a deploy
        # that has never sent a notification would train whoever reads this list
        # to skip it, and a readiness check people skip is worse than no check.
        # *Half* configured is the state that actually hurts — a signing key
        # with no topic mints valid tokens for notifications Apple refuses — so
        # that is the state that gets named. `notify.transport_for` refuses the
        # same shape at the job's own boot, which is where it is fatal.
        for platform in ("ios", "android"):
            configured = self.push_credentials(platform)
            if any(configured.values()):
                missing.extend(name for name, value in configured.items() if not value)
        return missing

    #: Что прод обязан иметь, чтобы вообще запуститься, и почему именно это.
    #:
    #: Три, не больше. Каждая строка — переменная, её проверка и объяснение,
    #: которое читает не программист: сообщение об отказе печатается целиком, а
    #: «неверная конфигурация» без имени переменной — это сообщение, по
    #: которому нельзя ничего сделать.
    #:
    #: **Почему это отказ, а не предупреждение.** До сих пор прод поднимался на
    #: SQLite и с пустым ключом модели, и оба отказа обнаруживал первый
    #: заплативший: файл-база отвечала «database is locked» под вторым воркером,
    #: пустой ключ — пятьсот третьей ошибкой посреди главы, за которую человек
    #: уже отдал деньги. Упавший деплой стоит десяти минут; тихо поднявшийся
    #: неполный прод стоит доверия, и узнаём мы о нём последними.
    #:
    #: Биллинга здесь намеренно нет. Сервис считает все восемь систем без
    #: процессора, а касса отвечает 503 с именами недостающих переменных — это
    #: рабочее состояние, а не поломка. `/ready` его всё равно покажет.
    def _production_failures(self) -> list[str]:
        failures: list[str] = []
        if self.jwt_secret == "dev-only-not-a-secret":
            failures.append(
                "ALMA_JWT_SECRET — всё ещё значение по умолчанию для разработки. "
                "Любой сеансовый токен подделывается кем угодно, кто читал этот "
                "репозиторий. Сгенерировать: "
                'python -c "import secrets;print(secrets.token_urlsafe(48))"'
            )
        if not self.is_postgres:
            failures.append(
                f"ALMA_DATABASE_URL — сейчас {self.database_url.split('://')[0]!r}, "
                "а в проде нужен postgresql+asyncpg://пользователь:пароль@хост/база. "
                "SQLite держит одного пишущего на всю базу, а прод — это несколько "
                "воркеров плюс три регулярных процесса: пятый претендент получает "
                "«database is locked» посреди чужой оплаченной генерации."
            )
        if not self.anthropic_api_key:
            failures.append(
                "ANTHROPIC_API_KEY — пусто. Расчёты работают и без него, но всё, "
                "что продаётся — главы, разговор, утренняя запись, — это вызов "
                "модели, и без ключа он отвечает отказом уже после оплаты."
            )
        return failures

    def check_production_ready(self) -> None:
        """Отказ стартовать в проде, называющий всё недостающее разом.

        Разом — это половина ценности проверки. Отказ по первой же найденной
        причине превращает настройку в очередь из трёх деплоев: поправил
        секрет — узнал про базу, поправил базу — узнал про ключ. Список
        собирается целиком и печатается целиком.
        """
        if not self.is_production:
            return
        failures = self._production_failures()
        if failures:
            raise RuntimeError(
                "ALMA_ENV=production, но запускаться не с чем. Не хватает:\n  — "
                + "\n  — ".join(failures)
                + "\nЛибо допишите это в окружение, либо снимите ALMA_ENV=production. "
                "Прод, поднявшийся наполовину, ломается не при старте, а у первого "
                "заплатившего."
            )


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()


def billing_adapter(name: str | None = None) -> BillingProvider:
    """The adapter for the configured processor.

    The whole of "which processor are we on" is this function plus one
    environment variable. Callers ask for an adapter and get one that speaks
    the vocabulary in `billing/provider.py`; nothing above the seam is allowed
    to know whose API is on the other side of it, which is why this returns the
    adapter rather than the name.

    Not cached. Settings are, and the tests clear that cache between cases;
    caching a second time here would hand a test the processor the previous
    test selected, which is the kind of bug that only appears when the suite is
    run in a different order.

    Imported inside the call because every adapter reads settings on the way
    up — importing them here would be a cycle, and it would also make loading
    the configuration drag an HTTP client in behind it.
    """
    from .billing.provider import provider_for

    return provider_for(name or settings().billing_provider)
