# Talking to Alma

The harness behind `docs/CONVERSATION.md`. It sends real messages to a running backend with a
live key and records, verbatim, what comes back — because the question "is she comfortable to
talk to" cannot be answered by reading a prompt.

```
cd backend
python3 tools/conversation/talk.py tools/conversation/cases.json out.jsonl
```

It mints a **fresh guest account and self-profile per case**, which is what keeps a 43-turn
battery inside the free tier's three-questions-a-day: the limit is per account, not per
machine. Turns inside one case share a thread unless the turn carries `"fresh": true`, so a
follow-up like `"why?"` is genuinely a follow-up and a one-off question is genuinely a cold
start.

It spends money — 23.68¢ for the run in `transcript-2026-08-07.jsonl`, on
`claude-haiku-4-5` — so it is deliberately **not** collected by `testpaths` and must never be
called from a test. Re-run it after changing `CHAT_RULES`, `voice.VOICE`, or anything about
locale handling, and diff the new transcript against the recorded one. The regressions worth
watching are listed in `docs/CONVERSATION.md` §8.
