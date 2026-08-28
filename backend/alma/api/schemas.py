"""Request and response shapes.

Validation lives here so that a bad request is a 422 with a readable message
rather than a stack trace from three layers down. Two rules are enforced at
this boundary rather than deeper:

* A birth time is either "HH:MM" or absent. There is no empty string, no
  "unknown", no zero — one representation of not-knowing, so that no code
  downstream has to guess which flavour of missing it received.
* A timezone must be one the system actually knows. An unrecognised zone
  would otherwise surface as a chart in UTC, which looks like an answer.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..i18n import MAX_TAG as MAX_LOCALE_TAG

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class BirthInput(BaseModel):
    """One birth, as the client sends it."""

    model_config = ConfigDict(extra="forbid")

    birth_date: date
    birth_time: str | None = Field(default=None, description='"HH:MM" local, or null')
    # `allow_inf_nan=False`: `NaN`/`Infinity` — валидный вход json-парсера, но не
    # координата. Без этого отказ приходил как «должно быть ≤ 90» вместо честного
    # «должно быть конечным числом», а сам ответ 422 не сериализовался (см.
    # `app._fold_nonfinite`). Найдено аудитом 20.08.2026.
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    timezone: str = Field(min_length=1, max_length=64)
    place_label: str | None = Field(default=None, max_length=200)
    place_id: int | None = None
    name: str | None = Field(default=None, max_length=120)
    on_ambiguous: str = Field(default="raise", pattern="^(raise|earlier|later)$")

    @field_validator("birth_time", mode="before")
    @classmethod
    def _normalise_time(cls, value):
        # An empty string is what a cleared form field sends. It means "not
        # known", and turning it into None here keeps that one meaning of
        # missing from becoming three.
        if value in (None, "", "unknown"):
            return None
        if isinstance(value, str) and TIME_PATTERN.match(value.strip()):
            return value.strip()
        raise ValueError('birth_time must be "HH:MM" in 24-hour form, or null')

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        from ..geo import is_known_timezone

        if not is_known_timezone(value):
            raise ValueError(
                f"unknown timezone {value!r} — an unrecognised zone would produce "
                "a chart in UTC, which looks exactly like a correct one"
            )
        return value

    @field_validator("birth_date")
    @classmethod
    def _in_range(cls, value: date) -> date:
        if not (1900 <= value.year <= 2100):
            raise ValueError(
                "birth dates outside 1900–2100 are outside the ephemeris we ship"
            )
        return value


class ProfileInput(BirthInput):
    relation: str | None = Field(default=None, max_length=40)
    #: The language of the *refusal*, not of the profile. Every other route
    #: answers errors in the request's language; without this field the
    #: partner-limit 402 fell back to `user.locale`, which on a fresh guest is
    #: still the minting default until the client's fire-and-forget locale
    #: PATCH happens to land — so the first refusal arrived in English.
    locale: str | None = Field(default=None, max_length=8)
    #: The reader's grammatical gender, volunteered at the journey's "about
    #: you" step. Only two values are meaningful to the writer; absence is a
    #: first-class state, not a default.
    gender: str | None = Field(default=None, pattern="^(female|male)$")
    #: Ответ квиза V0 «что сейчас важнее всего» — сигнал NBO, не астрология.
    #: Закрытый список тот же, что в ТЗ §4; absence — первоклассное состояние:
    #: человек мог пройти анкету до появления вопроса или молча его пропустить.
    interest: str | None = Field(default=None, pattern="^(love|money|self|future)$")
    #: Whose birth this is. `None` means "not said", which resolves to the
    #: first birth an account saves and to nobody after that — see
    #: `profiles.create_profile`. It used to default to `True`, and saving a
    #: second self *deletes* the first, so a client that omitted the field
    #: while adding a partner destroyed the account owner's own chart and
    #: every reading keyed to it. A default that can delete data has to be the
    #: safe one.
    is_self: bool | None = None
    #: Где человек живёт сейчас — для главы астрокартографии «Где ты сейчас»
    #: (29.08.2026; довод у колонок в `db/models.py`). `None` — «не менять»:
    #: PATCH профиля шлёт форму целиком, и клиент, правящий имя, не обязан
    #: помнить про город — иначе каждая правка имени стирала бы его.
    current_latitude: float | None = Field(default=None, ge=-90, le=90)
    current_longitude: float | None = Field(default=None, ge=-180, le=180)
    current_place_label: str | None = Field(default=None, max_length=200)


class ProfileOut(BaseModel):
    id: str
    name: str | None
    relation: str | None
    is_self: bool
    gender: str | None = None
    interest: str | None = None
    birth_date: date
    birth_time: str | None
    latitude: float
    longitude: float
    timezone: str
    place_label: str | None
    current_latitude: float | None = None
    current_longitude: float | None = None
    current_place_label: str | None = None
    on_ambiguous: str | None = None
    #: Солнечный знак по дате рождения — для глифа в строке списка людей.
    #: `None` в двух случаях, и оба честные: день перехода Солнца из знака в
    #: знак (без часа рождения ответа нет) и отказ эфемериды. Клиент рисует
    #: тогда инициал, а не выдуманный знак. См. `engine/sunsign.py`.
    sun_sign: str | None = None


class PlaceOut(BaseModel):
    id: int
    name: str
    region: str | None
    country: str
    country_code: str
    label: str
    latitude: float
    longitude: float
    timezone: str


class SessionOut(BaseModel):
    token: str
    user_id: str
    is_guest: bool
    email: str | None = None
    display_name: str | None = None
    locale: str = "en"


class GoogleSignIn(BaseModel):
    credential: str = Field(min_length=16, description="the Google ID token")


class AppleSignIn(BaseModel):
    identity_token: str = Field(min_length=16)
    full_name: str | None = Field(default=None, max_length=120)


class MagicLinkRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    locale: str = Field(default="en", max_length=8)

    @field_validator("email")
    @classmethod
    def _looks_like_an_address(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
            raise ValueError("that does not look like an email address")
        return cleaned


class MagicLinkConsume(BaseModel):
    token: str = Field(min_length=16)


class EmailCodeConsume(BaseModel):
    """Вход по коду из письма — то же письмо, что несёт ссылку.

    Адрес обязателен: код хэширован вместе с ним (`tokens.hash_email_code`),
    и шесть цифр без адреса не находят ничего — это и есть защита от перебора
    кодов против всех ожидающих строк сразу.
    """

    email: str = Field(min_length=3, max_length=320)
    code: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def _fold(cls, value: str) -> str:
        return value.strip().lower()


class CalcRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str | None = None
    birth: BirthInput | None = None
    house_system: str = Field(default="placidus", pattern="^(placidus|whole_sign|porphyry)$")
    #: The reader's language, as the client's own setting reports it. Widened
    #: past the six tags we ship because `i18n.resolve` is what decides which
    #: of them a reader gets, and it answers *every* tag — a request refused at
    #: this boundary never reaches it. See `i18n.MAX_TAG`.
    locale: str = Field(default="en", max_length=MAX_LOCALE_TAG)


#: Самое длинное окно транзитов, которое продукт действительно просит.
#:
#: Не догадка — перечень всех вызывающих: клиент шлёт `POST /systems/transits`
#: с пустым телом (`today_model._loadSky`, `system_screen`), то есть берёт
#: умолчание; `readings._options_for` шлёт ровно `days: 365`;
#: `daily.service.SCAN_DAYS` — те же 365. Больше года не просит никто, и
#: незачем: экран «Сегодня» смотрит на 30 дней вперёд, оглавление главы — на
#: год.
#:
#: Потолок был 1095. Замерено на этой машине, сколько стоил его край:
#:
#:     days=1095, include_moon=True  — 11.9 с
#:     days=1095, include_moon=False —  4.2 с
#:     days= 365, include_moon=True  —  3.7 с
#:     days= 365, include_moon=False —  1.26 с   ← что продукт просит на самом деле
#:
#: Двенадцать секунд — это одно тело запроса на четыре поля, и до правки они
#: были двенадцатью секундами **застывшего событийного цикла**: воркер не
#: отвечал никому, включая проверку живости. Теперь расчёт в потоке, так что
#: это «всего лишь» занятый поток из `app.thread_pool_size()` — но пул конечен,
#: и двадцать таких запросов выносят его целиком. Потолок и поток лечат разные
#: половины одной беды, и нужны обе.
MAX_TRANSIT_DAYS = 365

#: И отдельный, куда более узкий, когда просят Луну.
#:
#: Луна проходит зодиак за 27.3 суток, то есть за месяц она успевает сделать
#: каждый аспект к каждой натальной точке. Годовой список её контактов — это
#: тринадцать копий одного и того же, и стоит эта копия дорого: Луна одна
#: утраивает скан (1.26 с → 3.73 с на 365 днях), потому что двигается на два
#: порядка быстрее остальных тел и ищется мелким шагом. `daily/service.py`
#: держит `include_moon=False` жёстко и объясняет это теми же словами: "The
#: Moon is excluded and stays so."
#:
#: 31 день — месяц, то есть полный оборот с запасом: всё, что Луна умеет,
#: внутри окна уже есть. Замер на краю: 0.42 с.
MAX_TRANSIT_DAYS_WITH_MOON = 31


class TransitsRequest(CalcRequest):
    days: int = Field(default=MAX_TRANSIT_DAYS, ge=1)
    include_moon: bool = False
    start: date | None = None

    @field_validator("days")
    @classmethod
    def _within_a_year(cls, value: int) -> int:
        # Своё сообщение вместо `le=` у Field: умолчание pydantic — "Input
        # should be less than or equal to 365", а на том конце сидит человек,
        # который пишет клиента, и ему важно не число, а что мы не жадничаем.
        if value > MAX_TRANSIT_DAYS:
            raise ValueError(
                f"a transit scan looks at most {MAX_TRANSIT_DAYS} days ahead — "
                "a year is the longest window anything in the product asks for, "
                "and a longer one costs seconds of server time per request"
            )
        return value

    @model_validator(mode="after")
    def _the_moon_only_within_a_month(self) -> "TransitsRequest":
        if self.include_moon and self.days > MAX_TRANSIT_DAYS_WITH_MOON:
            raise ValueError(
                "the Moon can only be scanned "
                f"{MAX_TRANSIT_DAYS_WITH_MOON} days at a time — it goes round the "
                "whole chart every 27 days, so a longer window is the same "
                "aspects listed over and over, at three times the cost"
            )
        return self


class SolarReturnRequest(CalcRequest):
    year: int | None = Field(default=None, ge=1900, le=2100)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)


class CompatibilityRequest(CalcRequest):
    other_profile_id: str | None = None
    other: BirthInput | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = None
    profile_id: str | None = None
    #: As on `CalcRequest`, and for the same reason.
    locale: str = Field(default="en", max_length=MAX_LOCALE_TAG)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    body: str
    cited_factors: list[str] = []
    created_at: str


class ChatOut(BaseModel):
    thread_id: str
    message: ChatMessageOut
    questions_left: int | None = None


class ReadingRequest(BaseModel):
    profile_id: str | None = None
    birth: BirthInput | None = None
    system: str
    chapter: str | None = None
    #: As on `CalcRequest`. What is *stored* on the reading is the resolved
    #: tag, not this one — the route narrows it to one of the six before it
    #: goes anywhere near the database, which is what keeps this ceiling and
    #: the `String(8)` column compatible.
    locale: str = Field(default="en", max_length=MAX_LOCALE_TAG)
    house_system: str = Field(default="placidus", pattern="^(placidus|whole_sign|porphyry)$")
    #: The second person, for a compatibility reading. Required there and
    #: ignored everywhere else. Without this field the route had nothing to
    #: resolve `other` from, so every compatibility reading — including the
    #: free sample that exists to sell the system — was a 500.
    partner_profile_id: str | None = None


class ErrorOut(BaseModel):
    error: str
    detail: str | None = None
    field: str | None = None
