"""What a reading costs, refused before it is spent rather than found later.

The economics of this product are simple and unforgiving: a free user must
cost almost nothing, and a paid report must cost a fraction of its price. Both
ceilings are configuration, both are enforced before the call rather than
regretted after it, and both are reported per generation so that "the model
got more expensive" is a number rather than a feeling.

**Two guards, because there are two ways to lose money here.** `guard` bounds
one call: a prompt that grew, a `max_tokens` somebody raised, a model swapped
for a dearer one. `guard_month` bounds one account across a calendar month: a
thousand calls that each passed `guard` because each one was genuinely cheap.
Neither substitutes for the other, and for a long time only the first existed
— which meant an account could spend without limit as long as it did so a
fraction of a cent at a time.

Prices are per million tokens, in US dollars, and are a *table* rather than a
lookup against the provider — a pricing change should be a visible commit, not
a silent increase in the bill.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.models import UsageCounter, User

#: model id → (input $/Mtok, output $/Mtok). Keep in step with the price list.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5": (10.00, 50.00),
}

#: Used for a model we have no price for. Deliberately the most expensive
#: entry: an unknown model should overestimate and trip a budget early rather
#: than underestimate and quietly run up a bill.
FALLBACK_PRICE = (10.00, 50.00)


class BudgetExceeded(Exception):
    """This generation would cost more than its ceiling allows."""


@dataclass(frozen=True, slots=True)
class Spend:
    model: str
    input_tokens: int
    output_tokens: int
    dollars: float

    @property
    def cents(self) -> float:
        return self.dollars * 100.0

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "dollars": round(self.dollars, 6),
        }


def price_of(model: str) -> tuple[float, float]:
    return PRICES.get(model, FALLBACK_PRICE)


def cost(model: str, input_tokens: int, output_tokens: int) -> Spend:
    per_input, per_output = price_of(model)
    dollars = (input_tokens * per_input + output_tokens * per_output) / 1_000_000
    return Spend(model, input_tokens, output_tokens, dollars)


def estimate(model: str, *, prompt_chars: int, max_output_tokens: int) -> float:
    """A worst-case cost before the call is made.

    Four characters to the token is a rough English average and an
    underestimate for the factor lists we send, which is fine: this is used to
    refuse an obviously-too-expensive call, not to bill anyone.
    """
    approximate_input = prompt_chars // 4
    return cost(model, approximate_input, max_output_tokens).dollars


def ceiling(*, paid: bool) -> float:
    """What a *single* generation may cost. See `month_ceiling` for the other."""
    config = settings()
    return config.full_report_budget if paid else config.free_user_budget


def guard(model: str, *, prompt_chars: int, max_output_tokens: int, paid: bool, scale: float = 1.0) -> float:
    """Refuse a call too expensive to make at all. Returns the estimate.

    This is the per-call ceiling, and it only ever catches one shape of
    mistake: a single generation that is too big. It says nothing about how
    many of them an account has already made — that is `guard_month`.
    """
    # `scale` is the script multiplier: Cyrillic tokenises at roughly twice
    # the Latin rate, so the same honest words genuinely cost more — the
    # ceiling scales with the writing system, never with appetite.
    limit = ceiling(paid=paid) * scale
    projected = estimate(model, prompt_chars=prompt_chars, max_output_tokens=max_output_tokens)
    if projected > limit:
        raise BudgetExceeded(
            f"this generation would cost about ${projected:.4f} against a "
            f"${limit:.2f} ceiling — shorten the prompt, lower max_tokens, "
            f"or use a cheaper model than {model}"
        )
    return projected


@dataclass
class Ledger:
    """Running total for one request or one background job.

    In memory and gone when the request ends. It exists to stop a retry loop
    from spending the cap three times over inside a single generation; it is
    not, and must not be mistaken for, a record of what an account has cost —
    that is `month_spend`, which reads what the request path persisted.
    """

    spends: list[Spend]

    def __init__(self) -> None:
        self.spends = []

    def record(self, spend: Spend) -> Spend:
        self.spends.append(spend)
        return spend

    @property
    def dollars(self) -> float:
        return sum(s.dollars for s in self.spends)

    @property
    def input_tokens(self) -> int:
        return sum(s.input_tokens for s in self.spends)

    @property
    def output_tokens(self) -> int:
        return sum(s.output_tokens for s in self.spends)

    def check(self, *, paid: bool, scale: float = 1.0) -> None:
        limit = ceiling(paid=paid) * scale
        if self.dollars > limit:
            raise BudgetExceeded(
                f"spent ${self.dollars:.4f} against a ${limit:.2f} ceiling "
                f"across {len(self.spends)} call(s)"
            )

    def as_dict(self) -> dict:
        return {
            "calls": len(self.spends),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "dollars": round(self.dollars, 6),
        }


# ── the cumulative ledger ──────────────────────────────────────────────────
#
# Everything above this line forgets what it saw the moment the request ends.
# Everything below reads the `UsageCounter` rows the request path already
# writes, which is why there is no new table: a second store of the same
# number is a second number, and they diverge on the day it matters.

#: The metric under which per-day spend is accumulated in `UsageCounter`.
#: Named here because this module is what reads it back; the writer in the
#: readings router should import this rather than repeat the string.
SPEND_METRIC = "spend_cents"

#: Tier → the setting that holds its monthly allowance. Kept as a mapping so
#: that the tiers a caller may name and the ceilings that exist are the same
#: list, read from one place.
_MONTH_CEILINGS: dict[str, str] = {
    "free": "free_month_budget",
    "owner": "owner_month_budget",
    "subscriber": "subscriber_month_budget",
}


def month_ceiling(tier: str) -> float:
    """What one account of this tier may cost us in one calendar month.

    A refusal threshold, not a forecast — it has to sit above everything the
    tier is openly promised, or the promise is a lie discovered mid-month. The
    arithmetic and the reasoning are next to the settings themselves in
    `config.py`, including the one decision that is still open: the owner
    ceiling recurs and the single payment that earned it does not.

    An unrecognised tier is charged the free allowance. That is the only
    answer that cannot cost money: treating a subscriber as free produces a
    complaint from somebody we can identify, apologise to and refund within
    the hour, while treating a free account as a subscriber produces a bill
    nobody sees until it arrives. Raising instead would turn a data problem
    into a 500 on a path that already knows how to say "not right now".
    """
    config = settings()
    return getattr(config, _MONTH_CEILINGS.get(tier, "free_month_budget"))


def month_bounds(at: datetime | None = None) -> tuple[date, date]:
    """The half-open day range `[first, next-first)` of a calendar month.

    Half-open, and the upper bound found by stepping into the next month
    rather than by arithmetic on month length: December has to roll into
    January without special-casing, and a closed upper bound quietly drops
    everything spent on the last day of the month.
    """
    moment = at or datetime.now(timezone.utc)
    first = moment.date().replace(day=1)
    following = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first, following


async def month_spend(
    session: AsyncSession, user: User, *, at: datetime | None = None
) -> float:
    """Everything this account has cost us this calendar month, in dollars.

    `UsageCounter` stores the figure in **cents**, and every ceiling in this
    module is in dollars. The conversion happens here and only here, so that
    no caller can compare a cents total against a dollar ceiling and be wrong
    by a factor of a hundred in the direction that costs money.

    A calendar month rather than a rolling window because it is the unit the
    person is billed in, and therefore the only one a support conversation
    can be had about.
    """
    first, following = month_bounds(at)
    total = await session.scalar(
        select(func.sum(UsageCounter.amount)).where(
            UsageCounter.user_id == user.id,
            UsageCounter.metric == SPEND_METRIC,
            UsageCounter.day >= first,
            UsageCounter.day < following,
        )
    )
    return (total or 0.0) / 100.0


async def guard_month(
    session: AsyncSession, user: User, *, tier: str, projected: float
) -> None:
    """Refuse a call this account can no longer afford this month.

    The failure this exists for is invisible to `guard`: every call it
    approved may have been genuinely, individually cheap. Without a cumulative
    check, one account can spend without limit as long as it does so in small
    enough pieces — which is the shape of the abuse case and of the honest
    enthusiast alike, and the invoice cannot tell them apart.

    Checked before the call and against the projection rather than after and
    against the actual: a ceiling enforced once the tokens are already spent
    is a report, not a ceiling. `projected` is what `guard` returned, so the
    two guards agree about what the call is expected to cost.
    """
    limit = month_ceiling(tier)
    spent = await month_spend(session, user)
    if spent + projected > limit:
        raise BudgetExceeded(
            f"this account has cost ${spent:.4f} so far this month and this "
            f"call would add about ${projected:.4f}, against a ${limit:.2f} "
            f"ceiling for the {tier} tier"
        )
