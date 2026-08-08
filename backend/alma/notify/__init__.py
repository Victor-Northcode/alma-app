"""Getting the daily onto a phone, and — mostly — not.

This package is the delivery half of the daily: device tokens, the schedule,
the two vendors, and the rules that decide almost every morning that nobody
should be interrupted. The other half — what is actually happening in a
person's chart today, and the prose about it — belongs to `alma/daily/`, and
the seam between them is one function described in `daily._selector`.

Five modules, and the order they read in is the order a notification happens:

| module | what it owns |
|---|---|
| `tokens` | registering a device, and retiring one before it becomes a leak |
| `rules` | who may be interrupted, when, and how often — all of it measured |
| `message` | one chosen transit turned into a key and two or three nouns |
| `transport` | the seam; `apns` and `fcm` are the two things behind it |
| `daily` | the hourly job that puts the four together, idempotently |

**What this package is really for is not sending.** Sending is free on both
platforms and technically dull. The measured design in `docs/THE-DAILY.md`
lands the median subscriber at 0.88 notifications a week and the noisiest
chart in a 24-chart cohort at 1.13, and the outside evidence says that above
six a week people are 3.4× more likely to uninstall inside a month. An
uninstall costs the whole remaining subscription and there is no channel back
to an app that is no longer installed, so the expected value of a marginal
notification is negative unless it is clearly worth reading. Every constant in
`rules.py` is that arithmetic, and the floor is zero: **a month with nothing in
it is a correct month.**

**Two refusals are deliberate and loud.** `transport_for` refuses to hand back
a sender without a credential, and `daily.run` refuses to start without a
transport or without something to ask what today contains. Both could have
been a shrug and a zero, and a push system that appears to work and sends
nothing is the worst failure available here — every number downstream looks
healthy and the first person to find out is a subscriber wondering why they
are paying.
"""

from __future__ import annotations

from .rules import Decision, Preference, may_send
from .tokens import BadToken, forget, register, remove, retire, sweep
from .transport import (
    PLATFORMS,
    Push,
    PushUnavailable,
    Receipt,
    Transport,
    Verdict,
    configured_platforms,
    transport_for,
)

__all__ = [
    "BadToken",
    "Decision",
    "PLATFORMS",
    "Preference",
    "Push",
    "PushUnavailable",
    "Receipt",
    "Transport",
    "Verdict",
    "configured_platforms",
    "forget",
    "may_send",
    "register",
    "remove",
    "retire",
    "sweep",
    "transport_for",
]
