# Alma — where it actually stands

**11 August 2026.** Everything below was run on this machine; where something was not
verified, it says so in those words, and there is a section for exactly that.

> ## The direction changed on 10 August
>
> The owner decided to **rewrite both apps in Flutter, porting from iOS**. The count the
> decision was made on is in `docs/PARITY.md`; the port's own diary — what is done, what
> was decided along the way and what is honestly missing — is `docs/FLUTTER-PORT.md`.
>
> **The two native apps are not deleted and still work.** Until the port catches up they
> are the only thing that can go to the stores, so everything below about them is still
> the truth about what ships. What changed is where new work goes.
>
> Native iOS is the reference the port is measured against, frame by frame, both apps
> installed on one simulator.

---

## 1 · Every gate, run today

```
$ cd backend && .venv/bin/python -m pytest -q
1629 passed

$ cd backend && .venv/bin/python tools/license_gate.py
clean: no GPL / AGPL / LGPL, direct or transitive

$ npx tsc --noEmit && node scripts/check-locales.mjs
tsc: clean · locales: 5 translated, no English left behind

$ cd mobile/ios && xcodebuild -scheme Alma \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
** BUILD SUCCEEDED **

$ cd mobile/android && ./gradlew :app:assembleDebug :app:testDebugUnitTest
BUILD SUCCESSFUL             (69 tests, 0 failures)

$ python3 mobile/store/check-listing.py
42 fields checked · OK
```

And one that is not a gate, because it costs money and reaches the network:

```
$ cd backend && .venv/bin/python tools/prose_report.py --locale ru
```

It measures how the writing actually reads over everything ever generated. See §3.

---

## 2 · What the five waves changed

**Wave 1 — the two bugs the owner photographed.**
`timeoutIntervalForRequest = 30` on iOS is the gap allowed *between bytes*, and a chapter
being written sends none for the better part of a minute — measured, 61.7 s. URLSession
cancelled successful generations and the app reported them as offline; the server finished
and stored the chapter anyway, which is why the second tap always worked. Generations now
carry their own 180-second timeout.

`_letters()` took only letters the Pythagorean table knows, and that table is Latin-only:
«Анатолий Михайлов» produced the empty string, so the fifth of five numerology chapters had
no factors and Alma refused to write it — for every Russian reader, on a paid chapter. Names
are romanised (BGN/PCGN, the passport spelling) before they are counted, and the spelling
travels with the numbers so a reader can redo the sum.

Back from a chapter went to the previous chapter. It goes to the system now.

**Wave 2 — what the owner asked to be removed.** Three pills and a dominant-element pill from
under the natal chapters, the free/open/locked tags from every chapter row, four explanatory
paragraphs from Settings, the «Письма» section, the inner stroke and the twenty-two dots from
the birth-card art (the card's name in words stands there now). The morning default moved
from 08:00 to 10:00.

Found on the way: five of the seven languages could not say "Saturn square your Sun" without
agreeing a possessive with a gender, and the string tables had solved that by making the
aspect word `— соединение` and the word for "your" a bare `—`. On the front page, in Russian:
«Юпитер — соединение — Асцендент». One template per language now; 55 aspect strings lost a
leading dash.

**Wave 4 — the writing.** The owner's verdict was that the chapters are ornate and
machine-made and that a person without astrology would not get through them. The measurement
agreed (§3). `voice.py` gained rules about dashes, banned vocabulary and explaining a term
with something checkable rather than with another term; `validator.plain_language` enforces
them the way `russian_gendered` already enforces its own rule. The engine now computes the
*working* behind every headline number and offers it as a citable factor, so a chapter opens
by saying where the number came from instead of announcing it.

Three real bugs surfaced under that work: the Cyrillic token ceiling was half what Russian
chapters actually use (mean 2050, max 4479, ceiling 2520), `cost.guard` was never passed the
script scale in `writer.py` while the month tally always got it, and the romanised name was
being refused as English leaking into Russian prose.

**Wave 3 and the Today screen.** Swipe-back restored (hiding the system back item takes it
away, and every screen here hides it), swipes between tabs, drag along the tab bar. The
"next chapter" button is gone: pulling past the last line opens the next one, and the end of
a system draws a tick. «Твой день», «Небо за словами» and «Точно сегодня» became one block
called «Гороскоп на сегодня», subscribers only, with the four life areas filled from real
transits and honest about the empty ones.

**Since:** the journey's art now shrinks out of the keyboard's way instead of being climbed
over, and Android's `PeopleScreen` — the last stub in the app — is a real screen.

---

## 3 · How the writing reads, measured

Over every Russian chapter this product has generated, before and after the plain-language
rules landed:

| | before | after |
|---|---|---|
| dashes per paragraph | 2.78 | 1.55 |
| paragraphs over budget | 70 of 124 | 8 of 31 |
| words per sentence | 16.2 | 11.9 |
| words that carry nothing | 14 | 0 |

Russian is allowed two dashes a paragraph where every other language gets one: it has no
present-tense copula, so «Сатурн — планета границ» has nowhere else to put the verb. A budget
of one was tried first and the model returned two, three and four on successive attempts,
which is what arguing with a grammar looks like from outside.

**One decision worth knowing.** The prose gate yields; the citation gate does not. Two Russian
generations of `natal/core` cost $0.148 against the free tier's $0.10 ceiling, so there is
budget for one retry. An invented placement is a lie about a person and is refused whatever
it cost to get there. Three dashes in a paragraph is worse writing than we want and better
than a 503 over a chapter that exists.

---

## 4 · What only the owner can do

Unchanged from `docs/HANDOVER.md`, which is the longer list. The three that block everything:

1. **The domain does not resolve.** `alma.pazl.ai` and `api.pazl.ai` are compiled into shipped
   builds and every legal URL in twelve store listings points at the first. Apple fetches the
   privacy policy during review and rejects on a dead link before a human opens the build.
2. **Google sign-in needs three strings** — an iOS OAuth client id into `Info.plist`'s
   `GIDClientID`, and a *web* client id into both `google_web_client_id` and `backend/.env`.
   The code is written on all three layers and the button hides itself while they are empty.
3. **`sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`.** Until this is run,
   nothing in this repository can tap the simulator — see §5.

---

## 5 · What has not been verified, and why

**Every gesture added in wave 3.** Swipe-back, swipes between tabs, the drag along the tab
bar, and the pull-past-the-end that opens the next chapter. `simctl` has no tap, no swipe and
no key subcommand, and the dedicated simulator integration refuses to attach until the
`xcode-select` above is run. The code compiles, the screens it draws were photographed, and
the gestures themselves were **not** exercised. That is the honest state and it is the first
thing to check by hand.

**Anything below the first screenful**, for the same reason — the natal chart's aspect block,
the settings sections after the first, the four horoscope areas. Their data was verified
through the API; their layout was not photographed.

**The journey's keyboard behaviour.** It needs a tap to focus a field, so it could not be
reached at all.

**Real store billing**, unchanged: no products exist in either console.

---

## 6 · What is not done

- The chat with Alma is unchanged and the owner has asked for it to be made better looking.
  Nothing was done blind, because a redesign of the main conversation surface that nobody
  could look at is worse than an honest gap.
- Russian on the web. The web is deliberately frozen at six languages while the apps are
  being worked on; this is a decision, recorded, not an oversight.
- `docs/DEPLOYMENT.md` is worth writing the day there is a server to deploy to.
- `mobile/store/APP-CHANGES-NEEDED.md` lists eighteen findings from 7 August. Several are
  closed and the document does not say which. It needs a pass.
