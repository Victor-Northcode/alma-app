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

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..i18n import MAX_TAG as MAX_LOCALE_TAG

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class BirthInput(BaseModel):
    """One birth, as the client sends it."""

    model_config = ConfigDict(extra="forbid")

    birth_date: date
    birth_time: str | None = Field(default=None, description='"HH:MM" local, or null')
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
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
    #: Whose birth this is. `None` means "not said", which resolves to the
    #: first birth an account saves and to nobody after that — see
    #: `profiles.create_profile`. It used to default to `True`, and saving a
    #: second self *deletes* the first, so a client that omitted the field
    #: while adding a partner destroyed the account owner's own chart and
    #: every reading keyed to it. A default that can delete data has to be the
    #: safe one.
    is_self: bool | None = None


class ProfileOut(BaseModel):
    id: str
    name: str | None
    relation: str | None
    is_self: bool
    birth_date: date
    birth_time: str | None
    latitude: float
    longitude: float
    timezone: str
    place_label: str | None


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


class TransitsRequest(CalcRequest):
    days: int = Field(default=365, ge=1, le=1095)
    include_moon: bool = False
    start: date | None = None


class SolarReturnRequest(CalcRequest):
    year: int | None = Field(default=None, ge=1900, le=2100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


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
