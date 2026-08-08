# Alma — screenshots

Six shots that tell one story, in six languages, at two different aspect ratios. This file is
the shot list task #38 renders against: what each frame contains, what state the app has to be
in for it to be true, and the caption in each language.

Every caption in section 3 that could come from a string already shipping in
`/Users/anatoliymikhaylow/alma_project1/src/lib/i18n/` does. That is not laziness — those
sentences were written natively in each language, reviewed, and are on screen in the product
today. A caption invented for the store in six languages is six new chances to sound
translated.

---

## 0. Pixel dimensions, as the stores state them today

### Apple — App Store Connect

| Asset | Portrait | Notes |
|---|---|---|
| **iPhone 6.9"** (17 Pro Max, 16 Pro Max, 15 Pro Max) | **1320 × 2868** | **Required.** This is the set to produce. |
| iPhone 6.5" (14 Plus, 13 Pro Max, 12 Pro Max) | 1284 × 2778 | Only needed if 6.9" is *not* supplied. We supply 6.9", so skip. |
| **iPad 13"** (iPad Pro M5/M4/6th–1st gen, iPad Air M4/M3/M2) | **2064 × 2752** | Required **only if the app ships for iPad**. Undecided — see open questions. |
| iPad 11" | 1488 × 2266 | Not required when 13" is supplied. |

- **1 to 10 per localisation.** We use 6.
- `.png`, `.jpeg` or `.jpg`. **No alpha channel, no transparency** — flatten on export.
- Source: <https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/>

### Google — Play Console

| Asset | Size | Notes |
|---|---|---|
| **Phone screenshots** | **1080 × 1920** | Min 2, max 8 per device type. JPEG or 24-bit PNG. Min side 320 px, max side 3840 px, **16:9 or 9:16 aspect**. 1080 × 1920 is exactly 9:16 and comfortably inside the bounds. |
| Tablet screenshots | 1440 × 2560 | Minimum 4 suggested; 1,080–7,680 px; 9:16. Only if we ship a tablet build. |
| **Feature graphic** | **1024 × 500** | **Required.** JPEG or 24-bit PNG, **no alpha**. |
| App icon | 512 × 512 | 32-bit PNG **with alpha**, max 1024 KB. Note this is the opposite alpha rule from Apple's icon, which comes from the build. Two different files; do not export one from the other. |

- Source: <https://support.google.com/googleplay/android-developer/answer/9866151>

### The one thing that will cost time if it is missed

**Apple's 1320 × 2868 is 0.4606:1. Play requires 9:16, which is 0.5625:1.** They are not the
same shape and a Play upload cannot be a crop of an Apple one without either cutting the
caption off or letterboxing. **Render each shot twice, from the same composition, at both
sizes.** Compose the caption inside a safe band that survives both.

Neither is a raw device capture, either. The 6.9" simulator gives 1320 × 2868 directly, but no
Android phone has a 9:16 display any more — a Pixel 8 Pro is 1080 × 2400. Capture on Android at
whatever the device gives, then place the capture inside a 1080 × 1920 composition.

### Production count

6 shots × 6 locales × 2 aspect ratios = **72 images**. Add 36 more if iPad ships. The feature
graphic should be typographic-but-wordless so one file serves all six Play locales; if it
carries a sentence it becomes six files.

**Naming:** `alma-<locale>-<store>-<nn>-<slug>.png`, e.g. `alma-de-apple-04-disagreement.png`.
Locale codes exactly as the stores use them: `en-US`, `es-ES`, `de-DE`, `it`, `fr-FR`, `pt-BR`
on Apple; `en-US`, `es-ES`, `de-DE`, `it-IT`, `fr-FR`, `pt-BR` on Play.

---

## 1. Rules that apply to all 72 images

**One person, one chart, all six shots, all six locales.** The facts have to agree between
frames — a Sun sign that changes between shot 2 and shot 6 is the kind of thing a reviewer
notices and a customer screenshots back at you. Use a fictional profile with a known birth
time so the house-dependent screens render rather than showing "unavailable":

```
Name   Sofia            (journey.namePlaceholder)
Born   14 March 1994, 07:42
Place  Milan            (journey.placePlaceholder)
```

A second fictional person is only needed if a compatibility shot is added later; none of the
six requires one.

**Everything on screen must be real output.** No mocked prose, no retouched citations. The
factor chips under a paragraph come from the engine and are checked character-for-character by
`backend/alma/ai/validator.py`; a screenshot with a hand-edited citation would be the one
untrue thing in a product whose entire argument is that it does not do that.

**The app locale must match the store locale.** Set the simulator/device language, not just an
in-app toggle, so system-formatted dates and numbers localise too.

**Purchases must be visible.** Apple 2.3.2: *"If your app includes in-app purchases, make sure
your app description, screenshots, and previews clearly indicate whether any featured items,
levels, subscriptions, etc. require additional purchases."* Shots **3, 4 and 6** carry it — 3
and 4 through the sub-caption, 6 through the lock state visible in the hub. Do not remove it to
make a frame look cleaner.

**No prices in any frame.** Apple 2.3.7 — metadata must not include prices. That includes the
paywall, which is therefore not one of the six shots.

**4+ appropriate.** Apple 2.3.8: screenshots must suit a 4+ rating whatever the app is rated.
Nothing in these six is near the line, but the compatibility chapters are — which is another
reason no compatibility frame is in the set.

**Status bar:** 9:41, full signal, full battery, no notification badges, no carrier name that
identifies a country.

**No other platform.** Apple 2.3.10 — no Android device frame, no Play badge, anywhere in the
iOS set. Keep the two sets in separate folders so nobody cross-uploads by accident.

---

## 2. The six shots, in order

Slot 1 is what most people see in search results and is the only one many will look at. Slots
1–3 are visible without swiping on most phones. The order below is deliberate: the free thing
first, the proof second and third, the thing nobody else has fourth.

---

### Slot 1 — The sky and the date

**Screen:** `Today` (`mobile/ios/Alma/Screens/Today/TodayScreen.swift`; Android
`ui/screens/TodayScreen.kt`).

**State:** signed in as Sofia, no purchases, first launch of the day so the daily sky is
populated.

**Must be visible:** today's date in the device locale; the moon glyph and phase; the *Daily
sky* / *Read from* block with the lunar day, Moon and Ascendant rows; at least two rows of
*active now* aspects with their glyph notation.

**Must not be visible:** the paywall, any price, an empty-state placeholder.

Why first: it is the app's free surface at its most alive, it dates itself to the day the
person is looking at it, and it contains no prose to translate badly.

---

### Slot 2 — The portrait, with a real chart

**Screen:** `Systems` hub, top card (`Screens/Systems/SystemsScreen.swift`) — or the journey's
portrait step if the hub's top card reads thin at this size.

**Must be visible:** the computed chart facts — Sun, Moon, Ascendant with degrees; the life
path number; the birth card; the `n/8 calculated` counter.

**Must not be visible:** any "sample data" state (`states.sample`). If the backend is not
reachable the app says so, and that string must never reach a screenshot.

Why second: it answers "what do I actually get" with numbers rather than adjectives, and the
degrees are what separate this frame from every other astrology listing on the store.

---

### Slot 3 — A chapter, citing its factors

**Screen:** `ChapterScreen` (`Screens/Systems/ChapterScreen.swift`), natal chapter I *Core* —
the free chapter, so this frame is capturable without a purchase and shows the reading a
visitor genuinely gets.

**Must be visible:** two or three paragraphs of real chapter prose; **the `Read from` section
below it with its factor chips** (`ChapterScreen.swift:112`); the chapter numeral and title;
enough of the chapter rail or the following row to show that other chapters exist and are
locked (`ChapterScreen.swift:151, 210–220`).

**Must not be visible:** a price.

This is the shot the whole 4.3(b) argument rests on. Frame it so the citation chips are
legible at thumbnail size — if only one thing in this image survives being shrunk, it should be
the chips, not the prose.

---

### Slot 4 — Cross-synthesis: where they disagree

**Screen:** `SystemScreen` → `SynthesisPanel` (`Screens/Systems/SystemScreen.swift:274–302`).

**State:** no purchase needed. The synthesis preview keeps `summary`, `agreements`,
`disagreements`, `single_voice` and `axes` for a locked account
(`backend/alma/api/routers/systems.py:77`), so the counts *and* the axes render for a free user.
The written reading behind them does not, which is exactly the honest frame.

**Must be visible:** the agree / disagree / seen-by-one chips with their counts; at least three
axis rows, and **at least one of them a disagreement**, rendered in the disagreement colour
(`SystemScreen.swift:214–216`). Scroll so a disagreeing axis is above the fold — if the visible
axes all agree, the shot has lost its point.

Why fourth: nothing else on either store does this. It is the single most defensible answer to
*"how is this meaningfully different"*, and it is the frame to put in the review notes as well
as the listing.

---

### Slot 5 — Alma refusing to predict

**Screen:** `ThreadScreen` (`Screens/Alma/ThreadScreen.swift`).

**State:** a real chat turn, captured live. Ask the question in the store locale and screenshot
the answer that comes back.

**Must be visible:** the question, the answer, and the `Read from` block under the answer
(`ThreadScreen.swift:72`); the free-questions counter (`sky.questionsLeft`).

**The question to ask:** the decision question — *"Should I take the job abroad?"* and its
equivalent in each locale. `backend/alma/ai/voice.py:57–63` forbids predicting the outcome of a
decision and requires her to say the decision is theirs, so this is a reproducible behaviour
rather than a lucky answer. A live test on 6 Aug 2026 returned *"Nothing in the chart tells you
to go or to stay — that choice is yours to make."*

**Do not paste that sentence in.** Ask the question in each language and use what comes back.
If a locale returns something weaker, that is a product finding, not a screenshot problem.

---

### Slot 6 — The eight systems

**Screen:** `Systems` hub, full list (`Screens/Systems/SystemsScreen.swift`).

**Must be visible:** all eight system rows with their group labels; the `n/8 calculated`
counter (`SystemsScreen.swift:82–87`); the free-chapter note
(`L10nCabinet.freeChapterNote`, `SystemsScreen.swift:41`); and the mix of states — `calculated`,
`open`, `needs birth time`, `add a person` — because the honesty of the states is the product.

**Must not be visible:** a price.

Why last: it is the "and there's more" frame, and it is the one that carries the purchase
disclosure into the tail of the carousel where a reviewer scrolling for 2.3.2 compliance will
find it.

### If the remaining slots get used

Apple allows ten. Two more that would earn their place, in this order: **the birth-time
honesty screen** (a system showing *needs birth time* with `errors.needsBirthTime` — "an assumed
noon would put your Ascendant in the wrong sign"), and **astrocartography lines on the map**,
which is visually unlike anything else in the set. Both are free surfaces. Neither is in the
six because six is a story and eight is a catalogue.

---

## 3. Captions

Two lines per shot: a **caption** (the claim) and a **sub-caption** (the qualifier, smaller).
Both are burned into the image, not device text, so they must be set in the same type as the
app — `AlmaFonts.display` for the caption, the meta face for the sub-caption.

German is the constraint. Slot 4's German caption is 59 characters and **will** run to two
lines; design the caption band for two lines in every locale rather than shrinking German type
to fit one. A shrunken German caption reads as an afterthought, which is precisely the thing
these six languages exist to avoid.

Strings marked **[i18n]** are lifted verbatim from the shipping dictionary — the file and key
is given so a copy change in the app can be traced to a screenshot that now disagrees with it.

---

### Slot 1 — The sky and the date

| | Caption | Sub-caption |
|---|---|---|
| **en** | Today's sky, read from your chart | Free, every day |
| **es** | El cielo de hoy, leído en tu carta | Gratis, todos los días |
| **de** | Der Himmel heute, aus deinem Horoskop | Kostenlos, jeden Tag |
| **it** | Il cielo di oggi, letto dal tuo tema | Gratis, ogni giorno |
| **fr** | Le ciel du jour, lu dans ton thème | Gratuit, tous les jours |
| **pt-BR** | O céu de hoje, lido no seu mapa | De graça, todo dia |

Built from `cabinet.dailySky` / `cabinet.todayInFull` in each locale.

---

### Slot 2 — The portrait, with a real chart

| | Caption | Sub-caption |
|---|---|---|
| **en** | Eight systems answer in under a minute | NASA JPL DE440s ephemeris |
| **es** | Ocho sistemas responden en menos de un minuto | Efemérides DE440s de la NASA JPL |
| **de** | Acht Systeme antworten in unter einer Minute | Ephemeride DE440s der NASA JPL |
| **it** | Otto sistemi rispondono in meno di un minuto | Effemeridi DE440s della NASA JPL |
| **fr** | Huit systèmes répondent en moins d'une minute | Éphémérides DE440s de la NASA JPL |
| **pt-BR** | Oito sistemas respondem em menos de um minuto | Efemérides DE440s da NASA JPL |

**[i18n]** Captions are `final.sub`, second sentence, in each locale (`en.ts:260`, and the same
key in the other five).

---

### Slot 3 — A chapter, citing its factors

| | Caption | Sub-caption |
|---|---|---|
| **en** | Every paragraph names a real position | One chapter of every system is free. The rest unlock with a purchase. |
| **es** | Cada párrafo nombra una posición real | Un capítulo de cada sistema es gratis. El resto se abre con una compra. |
| **de** | Jeder Absatz nennt eine echte Position | Ein Kapitel je System ist kostenlos. Der Rest wird gekauft. |
| **it** | Ogni paragrafo nomina una posizione reale | Un capitolo per sistema è gratis. Il resto si apre con un acquisto. |
| **fr** | Chaque paragraphe nomme une position réelle | Un chapitre par système est gratuit. Le reste s'ouvre avec un achat. |
| **pt-BR** | Cada parágrafo nomeia uma posição real | Um capítulo de cada sistema é de graça. O resto abre com uma compra. |

**[i18n]** Captions are `voice.title` (`en.ts:169`). The sub-captions are new and are the 2.3.2
disclosure — they are the one place a screenshot is allowed to be a little bureaucratic, and
they must not be cut for layout.

---

### Slot 4 — Cross-synthesis: where they disagree

| | Caption | Sub-caption |
|---|---|---|
| **en** | Three agreeing is the closest thing to proof | Two disagreeing is more useful still |
| **es** | Que tres coincidan es lo más parecido a una prueba | Que dos discrepen es aún más útil |
| **de** | Wenn drei übereinstimmen, kommt das einem Beweis am nächsten | Wenn zwei sich widersprechen, ist das noch nützlicher |
| **it** | Tre che concordano sono la cosa più vicina a una prova | Due che si contraddicono servono ancora di più |
| **fr** | Trois qui s'accordent, c'est ce qui ressemble le plus à une preuve | Deux qui se contredisent, c'est encore plus utile |
| **pt-BR** | Três concordando é o mais perto de uma prova que existe | Dois discordando é ainda mais útil |

**[i18n]** Both lines are `synthesis.leadShort` and the second sentence of `synthesis.leadLong`
(`en.ts:143–145`).

The German caption is the longest line in the whole set. If two lines genuinely will not sit,
the fallback — and only for `de` — is `synthesis.title`: **"Wo acht Traditionen sich über dich
einig sind"**. Do not invent a shorter German sentence; use one that is already in the product.

---

### Slot 5 — Alma refusing to predict

| | Caption | Sub-caption |
|---|---|---|
| **en** | I don't tell you what will happen. I tell you what you're made of. | Three questions a day, free, always |
| **es** | No te digo lo que va a pasar. Te digo de qué estás hecho. | Tres preguntas al día, gratis, siempre |
| **de** | Ich sage dir nicht, was passieren wird. Ich sage dir, woraus du gemacht bist. | Drei Fragen am Tag, kostenlos, immer |
| **it** | Non ti dico cosa succederà. Ti dico di cosa sei fatto. | Tre domande al giorno, gratis, sempre |
| **fr** | Je ne te dis pas ce qui va arriver. Je te dis de quoi tu es fait. | Trois questions par jour, gratuites, toujours |
| **pt-BR** | Não digo o que vai acontecer. Digo do que você é feito. | Três perguntas por dia, de graça, sempre |

**[i18n]** Captions are `hero.quote` (`en.ts:52`) — the line the whole product is built around,
and the single best answer to a reviewer wondering whether this is a fortune-telling app.

Sub-captions are true against `backend/alma/config.py:262` (`free_questions_per_day = 3`) and
`api/routers/readings.py:117`. If that default ever changes, this caption is wrong in six
languages — grep for it.

---

### Slot 6 — The eight systems

| | Caption | Sub-caption |
|---|---|---|
| **en** | Four questions, eight ways to answer | Every one of the eight is calculated free |
| **es** | Cuatro preguntas, ocho maneras de responder | Los ocho se calculan gratis |
| **de** | Vier Fragen, acht Wege zur Antwort | Alle acht werden kostenlos berechnet |
| **it** | Quattro domande, otto modi di rispondere | Tutti e otto sono calcolati gratis |
| **fr** | Quatre questions, huit façons de répondre | Les huit sont calculés gratuitement |
| **pt-BR** | Quatro perguntas, oito jeitos de responder | Todos os oito são calculados de graça |

**[i18n]** Captions are `eight.titleA` + `eight.titleB` joined (`en.ts:115–116`); sub-captions
are the second sentence of `eight.tail` (`en.ts:118–119`).

> **Read this sub-caption against `PREVIEW_FIELDS` before rendering.** *"Every one of the
> eight is calculated free"* is true in the sense it was written in — all eight systems are
> computed for everybody, from static local files, at no cost to the reader — and it is the
> one sentence in this file that a reviewer could hear as *"every calculation is free"*,
> which is **not** true of the shipped app: a locked natal returns six keys and no bodies,
> houses or aspects, and a locked astrocartography returns only `birthplace`
> (`backend/alma/api/routers/systems.py:47–78`). The same overstatement was live in all
> twelve store descriptions until 7 August 2026 and has been replaced there with an
> enumeration.
>
> The screen this caption sits under shows `n/8 calculated`, so the claim reads as being
> about the count and survives. But it is a shipped i18n string, the safer reading is one
> sentence away, and if `PREVIEW_FIELDS` is *not* widened it should be narrowed to something
> like *"All eight are computed before anything is sold"* in all six languages.
> `APP-CHANGES-NEEDED.md` §4 carries it as a dependent edit rather than an independent one:
> widen the paywall and the sentence is unambiguously true, so decide that first.

---

## 4. Feature graphic — Play only, 1024 × 500, required

Wordless, so one file serves all six locales. The night-sky field the app already draws
(`DesignSystem/Sky/`) with the Alma star mark (`DesignSystem/Brand/AlmaStar.swift`) — flatten
it, no alpha, and check it at 250 px wide, which is roughly how it appears in a Play search
result.

If the owner would rather it carry a line, it becomes six files and the line should be the
locale's Play short description, trimmed. That is a real cost for a small gain; the
recommendation is wordless.

---

## 5. App preview videos

Optional on both stores and **not recommended for launch**. Apple allows up to three previews
of up to 30 seconds each; Play takes a YouTube URL. Every second of a preview is a second of
localisation and a second that has to be re-shot when a screen changes. The six stills carry
the argument. Revisit after the first release.

---

## 6. Checklist before upload

- [ ] All 72 images render, at exactly 1320 × 2868 and 1080 × 1920.
- [ ] No alpha channel on any file (`sips -g hasAlpha <file>` on macOS; must be `no`).
- [ ] Every frame captured with the device language set to that locale, not just the in-app one.
- [ ] The same fictional person, and the same degrees, in every frame of every locale.
- [ ] Slot 3 and slot 4 carry the purchase sub-caption. Slot 6 shows the lock states.
- [ ] No price anywhere in any frame.
- [ ] No `states.sample`, no `states.offline`, no loading spinner in any frame.
- [ ] Slot 5's answer was captured live in that language, not pasted.
- [ ] Apple set and Play set in separate folders; no Android frame in the Apple set.
- [ ] Feature graphic exported at 1024 × 500, no alpha, legible at 250 px wide.
