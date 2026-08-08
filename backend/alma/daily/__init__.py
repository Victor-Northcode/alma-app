"""The daily — what is actually happening in this person's chart today.

The monthly plan is sold as the living layer: transits, solar return,
compatibility, the three systems that move. Everything else is bought once and
kept. So the daily is not an extra — it is the only thing the subscription is
renting, and until it existed a subscriber had no reason to open the app
between one month and the next.

**What makes it Alma's daily rather than everybody else's.**
`alma/engine/transits.py` computes the exact instant an aspect perfects, by
root-finding rather than sampling, and its docstring draws the line this
feature lives on: *"Sun" is a horoscope; "Saturn squares your Sun exactly on
14 June, in orb from…" is a reading.* So the daily names the placement, the
aspect and the minute — *"Mars crosses your Ascendant at 14:20; it has been in
orb since Tuesday"* — and it goes through the same writer and the same citation
validator as a paid chapter, which means a sentence naming a placement this
chart does not contain is refused here exactly as it is there.

**And on days with nothing to say, it says nothing.** That is the load-bearing
decision. `docs/THE-DAILY.md` measured 20–36 day gaps between contacts worth
waking a phone for, and a daily that arrives every morning regardless is a
horoscope with extra steps. Silence is a supported state of every module here.

The five pieces, in the order they run:

| module | what it answers |
|---|---|
| `clock.py` | which clock the reader is actually looking at |
| `selection.py` | is anything worth saying today, and does it earn an interruption |
| `writing.py` | the one-event brief, through `ai/writer.py` and its validator |
| `storage.py` | written once per person per day, in the `reading` table |
| `notification.py` | the one true line for a lock screen, assembled not generated |
| `words.py` | every word of it in six languages |
| `service.py` | the four of them in order, with both cost ceilings |

Every measured constant traces to `docs/THE-DAILY.md`, and the scripts that
produced those numbers are kept in `backend/tools/daily/` so a figure can be
re-run rather than argued about. Nothing in this package re-decides them.
"""

from __future__ import annotations

from .notification import Notification, compose, line
from .selection import Decision, Occasion, decide, occasion_for
from .service import (
    Candidate,
    Daily,
    candidates,
    claim_push,
    hits_for,
    look,
    may_receive,
    piece_for,
)
from .words import DailyWords, words_for

__all__ = [
    "Candidate",
    "Daily",
    "DailyWords",
    "Decision",
    "Notification",
    "Occasion",
    "candidates",
    "claim_push",
    "compose",
    "decide",
    "hits_for",
    "line",
    "look",
    "may_receive",
    "occasion_for",
    "piece_for",
    "words_for",
]
