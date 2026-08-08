# Where the shipped privacy policy disagrees with what we are about to declare

`mobile/store/APP-PRIVACY.md` and `mobile/store/DATA-SAFETY.md` say what Alma collects.
This file lists every place the shipped policy says something else, with the exact sentence
and what it should say instead. **Where they disagree the page is usually the one that is
wrong** — the declarations were derived from the code, the pages were written earlier.

**There are two policies, not one, and a reviewer reads a different one on each store.**

| Store | The policy the reviewer opens | Where it lives |
|---|---|---|
| **Google Play** | the web page | `src/app/(legal)/privacy/page.tsx` — Android's Settings screen opens `$Site/privacy` in the browser (`mobile/android/.../ui/screens/SettingsScreen.kt:586–596`) |
| **Apple** | a second copy, compiled into the binary | `mobile/ios/Alma/Screens/Settings/LegalText.swift:245–378` |

The iOS copy exists for a good reason, stated in its own header comment: a link out to a
website is a link that can be down on the afternoon the review happens
(`LegalText.swift:5–12`). The cost is two documents that can drift, and they have. Part 2
below is the drift, and it contains the single worst sentence in either document.

Ordered by consequence, not by file order.

---

## Part 1 — the web page (`src/app/(legal)/privacy/page.tsx`)

### 1.1 · ~~The recipient list names a company the app never touches, and omits the two it does~~ — **FIXED**

**Line 112:** *"Three companies, and this is the complete list."*
**Line 124:** *"**{MERCHANT}** takes the payments. They are the seller, not us, so your card
details go to them and never touch Alma."*

`MERCHANT` resolves to `"Paddle.com Market Ltd"` or `"Dodo Payments"` (`src/lib/legal.ts:44–50`).
On a Play build neither receives anything: both `open_session` implementations refuse, and
`POST /v1/billing/checkout` is the only route that reaches them. Meanwhile **Google** is the
merchant of record, and our backend sends Google a package name and a purchase token over the
Play Developer API on every purchase (`billing/googleplay.py:102`), receiving back an order
id, a product id and a `regionCode` (`:610–612`). Apple is the merchant of record on iOS.
Neither is named. Line 102–104 makes it worse by generalising — *"nobody outside the three
companies named below receives anything about you"*.

**Should say:** the list must be conditional on where the reader is. Four recipients, and say
which applies where: Anthropic (every build), Apple *or* Google *or* the card processor
(whichever sold this copy), Resend, and the hosting provider — which the iOS text already
names as a recipient (`LegalText.swift:317–319`) and this page does not. If the page cannot
branch on platform, name all of them and say plainly: *"Which one takes your money depends on
where you got Alma. Inside the App Store it is Apple; inside Google Play it is Google; on the
web it is {MERCHANT}."*

**What was done.** `src/lib/legal.ts` gained `STORE_MERCHANTS` — Google for Google Play,
Apple for the App Store, as constants rather than another environment lookup, because an app
on the Play Store cannot bill through anyone but Google whatever a variable says. The privacy
page now opens the section with *"Four companies at most, depending on where you bought"*,
keeps the card processor scoped to *"payments made on this website"*, and adds a paragraph
naming both stores as the seller for payments made inside the apps — including the one thing
that travels the other way, which is the purchase token our server hands the store to verify.

**Consequence if unfixed (kept for the record):** this is the policy URL on the Play listing.
It tells Google's reviewer that a card processor Google has never heard of is the seller of a
Play in-app
purchase.

---

### 1.2 · What is sent to Anthropic is understated by the four most sensitive fields

**Lines 114–122:** *"**Anthropic** generates the readings. What is sent is the calculated
chart — positions, aspects, the numbers — the question you asked, and the short facts Alma
remembers about you… Your email address is not needed for any of it and is not part of it."*

`ai/writer.py:152–164` builds a `THE PERSON` block into **every chapter prompt** containing,
verbatim and un-derived:

- `- born {birth_date}` and, when a birth time is known, `at {HH:MM}`
- `- birth time known: yes/no`
- `- birthplace: {place_label}`
- `- name: {name}`

Those are the stored strings, not the chart computed from them. The page describes them as
folded into "the chart"; they are not. (The page is right that the email address is not
sent — neither prompt builder has access to a `User` row.)

**Should say**, as a replacement for the first sentence: *"**Anthropic** generates the
readings. What is sent is your birth date, your birth time to the minute, the name of your
birthplace and your name if you gave one — the four things the reading is written from, sent
as they are stored, not as a summary — together with the calculated chart, the question you
asked, and the short facts Alma remembers about you. Your email address is not part of it and
is not needed for any of it. Your birthplace coordinates are not sent either: they are used
here to compute the chart, and only the result travels."*

It is also worth adding the one thing that distinguishes a chat turn, because it is the more
alarming of the two and is currently invisible: *"A question you ask Alma carries the last
twelve messages of that conversation, both sides, so that turn six makes sense after turn
one. It carries no birth date, time or place — a conversation is answered from the chart, not
from the birth."* (`ai/conversation.py:120–145`, `MAX_HISTORY = 12`.)

**Consequence if unfixed:** Apple 5.1.2(i) requires explicit disclosure where personal data is
shared *"including with third-party AI"*, and consent. This is that disclosure, and today it
omits the birth time.

---

### 1.3 · The page is written entirely in "your", and a profile may be somebody else's

Every item in **"What Alma holds" (lines 29–72)** is possessive: *"Your birth date."*
*"Your birth time."* *"Your birth place."*

A compatibility reading requires a second birth (`routers/readings.py:375–401`), stored as its
own `profile` row with its own `birth_date`, `birth_time`, coordinates, `place_label`, `name`
and a `relation` label — and `is_self` distinguishes the account holder from everyone else
(`db/models.py:134–164`). Nothing asks whether that person consented. The page does not
mention this anywhere, so a reader has no way to learn that Alma stores birth data about
people who are not its users.

**Should say**, as a new item in the list: *"The birth details of anybody else you have added
— a partner, a friend — with whatever word you used to describe them. Compatibility needs two
births and there is no way around that. They are stored exactly like yours and deleted
exactly like yours, and they are the one thing on this page that is about somebody who never
agreed to any of it. Add someone only if you would be comfortable telling them you had."*

**Consequence if unfixed:** it is a collection of personal data about a data subject who has
not been informed, disclosed nowhere. Both store forms are answered on the basis that this
happens (APP-PRIVACY → Contact Info: Name; DATA-SAFETY → Personal info: Name, Other info).

---

### 1.4 · "Two things survive" is four

**Lines 220–229:** *"Two things survive, and they are worth naming rather than leaving for you
to find. The payment records stay… And a stub of the account row stays…"*

`auth/accounts.py:erase` leaves four things behind:

1. `purchase` — detached, `payload` replaced with a redaction marker (`:360–364`). ✔ named
2. `webhook_event` — detached, payload redacted, **kept indefinitely** (`:365–369`). ✘ not named, and not in the holdings list at lines 29–72 either
3. `consent` rows a payment claimed — detached rather than deleted (`:370–374`). ✘ not named; line 54–55 names only the *unpaid* case, which is deleted
4. the `user` tombstone (`:386–390`). ✔ named

**Should say:** *"Four things survive"*, with the two missing ones added — the processor's
delivery notes, redacted and detached, kept because they are the audit trail of a payment that
is itself a legal record; and the consent sentences a payment claimed, detached, kept for the
same reason the payment is. Both are defensible; neither is currently disclosed.

**Consequence if unfixed:** Apple 5.1.1(i) requires the policy to explain retention and
deletion. A policy that lists the survivors and gets the list wrong is worse than one that
does not try.

---

### 1.5 · Export is offered as the fastest route to a right it does not fully serve

**Lines 260–267:** *"Export and deletion in Settings are the fastest route to all four for an
account you have signed into."*

`accounts.export:220–321` returns account, profiles, entitlements, purchases, readings,
conversations and memory. The same page's holdings list also names **the counters** (43–49),
**the consent statements** (50–56), **the sign-in links** (57–60) and **the funnel step
labels** (65–71). None of the four is in the export. GDPR Art. 15 covers all of it.

**Should say:** either put the four categories into `accounts.export` — which is the better
fix and is four more `select` statements — or change the sentence: *"Deletion in Settings
covers everything on this page. Export covers most of it: your account, your birth data, what
you bought, every reading, every conversation and everything Alma remembers. The counters, the
consent sentences, the sign-in links and the step labels are not in the file yet; ask and you
get them by return."*

---

### 1.6 · The Do Not Track promise has no equivalent in either app, and one app points here

**Lines 104–108:** *"If your browser sends Do Not Track or Global Privacy Control, the step
labels are not recorded at all — that is checked on every one of them rather than once when
the page loads, so turning it on mid-session works."*

True on the web (`src/lib/track.ts:106–120`). Not true in the apps: `AlmaClient.track` posts
unconditionally on iOS (`Networking/AlmaClient.swift:308–318`) and on Android
(`data/AlmaClient.kt`, `data/AlmaService.kt:229`). The sentence is scoped to "your browser",
so it is not false — but **this page is the Android app's privacy policy**, opened from the
Android Settings screen, and a person reading it there would reasonably conclude they have an
opt-out they do not have.

**Should say**, appended: *"There is no such signal on a phone to read, so inside the Alma
apps the step labels are always recorded. There are nine of them, they hold no text of yours,
and this sentence exists because the paragraph above it would otherwise read like a promise
we only keep in a browser."*

**Or** ship the toggle. `DATA-SAFETY.md` declares App interactions as **Required** precisely
because there is no off switch; a Settings toggle that suppresses `POST /v1/events` turns that
answer to Optional and makes the sentence above unnecessary.

---

### 1.7 · The page describes a browser and is read inside an app

**Lines 166–183 ("Cookies")** describe `alma.locale`, `localStorage` and third-party cookies.
Android has none of those. What it has is a bearer token in `SharedPreferences`, encrypted
with an `AndroidKeyStore` key (`data/TokenStore.kt:20–80`), `allowBackup="false"` and
`fullBackupContent="false"` (`AndroidManifest.xml`) — so nothing goes to Google's backup
service — and **no birth data, no readings and no messages on the device at all** (grepped:
no Room, no DataStore, no `SharedPreferences` outside the token store).

**Should say:** a short section headed something like *"On your phone"*, stating those three
facts. The last one is the strongest sentence available to us on this page and it is currently
missing: nothing about your chart is stored on your device. Say it.

---

### 1.8 · The blanks

Four `<Blank>` renders, and each of them now blocks something concrete.

| Line | Blank | What it blocks |
|---|---|---|
| 144 | *data transfer terms per processor* | The Play "Shared: No" answer rests on Anthropic and Resend being processors under agreement (DATA-SAFETY §Sharing). Same fact, two places. |
| 145 | *hosting region* | The Apple Diagnostics answer and the Play in-app-search answer are both contingent on what the host logs (APP-PRIVACY → Other Diagnostic Data). **And the iOS text already asserts an answer** — see 2.3. |
| 248 | *backup retention window* | The one place deleted data survives. It cannot stay blank on the Play deletion page, which is the page Google's reviewer reads as the deletion promise. |
| 271 | *lead supervisory authority* | Required by the GDPR notice itself. Note the iOS text leaves a *different* blank — an Art. 27 EU representative (`LegalText.swift:372–375`). Those are two obligations, not one, and neither document has both. |

---

### 1.9 · "Not used to train anyone's model" is a claim about a contract

**Lines 160–163:** *"Your readings are not used to train anyone's model, and your conversations
are not read for product research."*

The second half is ours to promise. The first half is a statement about Anthropic's commercial
terms and nothing in this codebase can assert it. It is almost certainly true under a standard
commercial agreement — but it should rest on the agreement, not on the sentence.

**Should say:** the same claim with its basis attached — *"…not used to train anyone's model,
under the terms we hold with the company that runs it"* — once the agreement is confirmed. If
it is not confirmed, remove the clause rather than soften it.

---

### 1.10 · Age is stated and unenforced

**Line 254:** *"Alma is for people aged {MIN_AGE} and over."* `src/lib/legal.ts:65` sets 16 and
three legal pages repeat it. `api/schemas.py:63–70` accepts any birth date from 1900 to 2100
and no screen asks. A date implying a nine-year-old saves without complaint.

This is not primarily a wording problem — it is the age declaration on both store forms, and
both stores' children's-data rules turn on whether the product knowingly collects data from
children. Either add the gate or file the number the app actually behaves like. **The page and
the form and the code have to agree, and right now only two of the three do.**

---

## Part 2 — the policy compiled into the iOS binary (`LegalText.swift:245–378`)

This is the document Apple's reviewer opens, and it drifts from the web page in both
directions — it is better on hosting and worse on Anthropic.

### 2.1 · The worst sentence in either document

**Lines 303–307:** *"Anthropic, who run the model that writes the readings. Your chart factors
and the chapter's question are sent; your email address and your name are not."*

**Your name is sent.** `ai/writer.py:163–164`:

```python
if subject.get("name"):
    lines.append(f"- name: {subject['name']}")
```

So are the birth date and the birth time to the minute and the birthplace label
(`writer.py:152–160`). So are the eight most recent remembered facts, in the system prompt of
every generation (`ai/voice.py:112–119`, `routers/readings.py:458–467`). So are the last twelve
messages of a conversation, both sides, on every chat turn (`ai/conversation.py:128–133`).

The email address really is not sent — that half is right, and it is the half that makes the
other half read as a considered statement rather than an omission.

**Should say:** *"Anthropic, who run the model that writes the readings. Your birth date, your
birth time, the name of your birthplace and your name if you gave one are sent, as they are
stored — they are what the reading is written from. So are the calculated chart, the question
you asked, and the short facts Alma remembers. A question you ask carries the last twelve
messages of that conversation so it makes sense in context. Your email address is not sent and
is not needed. Your birthplace coordinates are not sent either: the chart is computed here and
only the result travels."*

**Consequence if unfixed:** Apple 5.1.2(i) — *"You must clearly disclose where personal data
will be shared with third parties, including with third-party AI"*. The app's own privacy
policy currently states the opposite of the truth on the field the guideline names. Fix this
one first, in every language it ships in.

---

### 2.2 · The memory table is not in the collection list at all

**Lines 252–282, "What is collected"**, lists six things: birth data, email, readings,
questions and answers, purchases, funnel events. It does not list **memory** — short strings
the model extracted from what a person stated about their life, stored as free text
(`models.py:491–508`, `ai/conversation.py:58–67`), inspectable at `GET /v1/memory` and
individually deletable at `DELETE /v1/memory/{id}` (`routers/readings.py:890–912`).

This is the field the web page correctly calls *"the most personal item on this list"*
(`page.tsx:118–120`), and the iOS document omits it while sending it to Anthropic on every
single generation.

The same list also omits the counters, the sign-in link rows and the consent records — all of
which the web page discloses.

**Should say:** add the item, in the voice the rest of the list is written in — *"A small
memory of things you said about your own life, in your words, so Alma does not ask you in
March what you answered in January. You can read all of it and delete any of it, one line at a
time."* — and add a line for the counters and the sign-in links.

---

### 2.3 · The app asserts a hosting region the web page leaves blank

**Line 328:** *"On servers in the European Union."*

`page.tsx:145` renders `<Blank>hosting region</Blank>`. One of the two documents is wrong, and
the one that committed to an answer did it without the owner having answered it — DATA-INVENTORY
§1.17 and open question 1 both record it as unresolved. If the EU is right, fill the web
blank. If it is not, this sentence is a false statement about international transfers in a
document Apple reads.

Same section, **lines 326–331** say readings are kept while the account exists and *"funnel
events are kept as counts"* — the funnel events are rows with a stage name and an account id
(`models.py:537–576`), and the *counters* are the counts. Two different tables, described as
one.

---

### 2.4 · "There is nothing to opt out of because there is nothing running"

**Lines 290–294:** *"No advertising identifiers, no third-party analytics, no tracking across
other apps or websites, no location beyond the birthplace you typed. There is nothing to opt
out of because there is nothing running."*

The first sentence is true and every clause of it is provable (DATA-INVENTORY §4) — including
the location clause, which is exactly the sentence that makes the Precise Location declaration
on the App Privacy form legible instead of alarming. Keep it.

The second sentence is false. Nine funnel beacons post unconditionally from this binary
(`Networking/AlmaClient.swift:308–318`), and `APP-PRIVACY.md` declares Product Interaction with
Analytics as a purpose. First-party analytics is running, and there is no switch.

**Should say:** *"What is running is our own: nine short labels — the quiz was started, the
portrait was seen — against your account id, with no text of yours in them and nowhere else to
go. There is no way to turn them off inside the app, and rather than pretend otherwise: that
is what we count and this is where you can read what it is."* Or ship the toggle and say so.

---

### 2.5 · Deletion is described as total and is not

**Lines 344–349:** *"Delete everything, from Settings. It is immediate and it is real: the rows
are deleted rather than flagged."*

True of profiles, readings, conversations, memory, entitlements, counters, funnel events and
sign-in links. Not true of the payment records, the webhook deliveries, the consent rows a
payment claimed, or the account tombstone — see 1.4. The web page names two of the four; this
document names none.

It also omits the condition the web page states plainly (`page.tsx:190–199`): **the button
needs an account.** `require_account` rejects a guest (`api/deps.py:97–104`) and the
confirmation is compared against `user.email`, which a guest has not got. A person who bought
through the App Store without signing in cannot use this button.

**Should say:** both facts. Apple 5.1.1(i) requires the policy to *"explain its data
retention/deletion policies"*, and Apple's account-deletion guidance says *"all users should be
allowed to delete their accounts, regardless of where they're located"* — so the second route
(write to `hello@pazl.ai`) belongs in this document and beside the button on the Settings
screen, not only on the web page.

---

### 2.6 · Two smaller ones, in a document whose whole claim is precision

**Lines 312–316:** *"Our mail provider, for the two letters Alma sends: a sign-in link, and —
for a plan bought outside the App Store — a notice before a renewal."* There are **three**
senders in `alma/mail.py`: `send_magic_link:115`, `send_renewal_notice:220` and
`send_receipt:928`. The web page was fixed for exactly this and carries a comment saying so
(`page.tsx:129–133`); the iOS port reintroduced the undercount.

**Lines 255–257:** *"…everything else Alma does is arithmetic on these five numbers."* The item
names four things — birth date, birth time, birth place, name — and one of them is not a
number. Either say four, or count the place as two (latitude and longitude) and say six.

**Line 260–262:** *"Sign in with Apple may give us a relay address instead."* Both identity
providers are disabled by configuration today (DATA-INVENTORY §2.4). A policy describing a
sign-in method the build does not offer is harmless until a reviewer looks for the button.

---

## Part 3 — the two that are not sentences

### 3.1 · A dead table would hold birth data outside every deletion path

`CalcCacheEntry` (`models.py:441–454`) has no `user_id`, is not in `accounts.erase`'s walk, and
would store `CalcResult.payload` — which includes `subject`: birth date, birth time,
coordinates, timezone, place label and name (`calc/contract.py:99–109`). **Nothing writes to
it** — `grep -rn CalcCacheEntry alma` returns the model and the re-export and nothing else — so
no promise is broken yet. It is one wiring change from being a table of birth data that
survives account deletion, in a schema whose own docstring calls that "a promise this project
has broken without noticing".

Delete the model, or give it a `user_id` and a line in `erase`, before anyone switches the
cache over. Do it before submission, because the fix is five minutes now and a disclosure
incident later.

Related and much smaller: the live cache is in-process, bounded at 2048 entries and lost on
restart (`api/cache.py:16–18`, `calc/cache.py:65–103`), and it holds `CalcResult`s — so birth
data does sit in RAM keyed by a content hash, and outlives an account deletion until the entry
is evicted. That is transient technical fact rather than storage, and it does not need to be on
the policy; it needs to be true that it stays transient.

### 3.2 · The birthplace search term travels in a URL

`GET /v1/places/search?q=…` (`api/routers/places.py:17–27`). Nothing stores it — no search
table, no request-logging middleware in `api/app.py` — which is why APP-PRIVACY answers Search
History **No** and DATA-SAFETY answers In-app search history **No**. But a birthplace name in a
query string is written into any default access log, and nobody has answered what the
production host retains.

Two ways to make both answers unconditional: get the hosting answer, or move the query into a
POST body so a place name never reaches a log line at all. The second is a smaller change than
the first is a conversation.

---

## The order to fix them in

Everything above is real, but four of them are the ones that change an outcome rather than a
paragraph.

1. **2.1** — the iOS policy says the name is not sent to Anthropic, and it is. This is the
   sentence Apple 5.1.2(i) is about. Fix before anything else.
2. **1.1** — the web policy names the wrong merchant and omits Google. This is the policy URL
   on the Play listing.
3. **1.2** — the web policy folds the birth time into "the chart". Same guideline as 2.1, other
   platform.
4. **2.5 / 1.4** — deletion is described as total in one document and as two-thirds true in the
   other. Apple 5.1.1(i) asks for this explicitly, and the Play deletion page (DATA-SAFETY
   §Account deletion) has to be built on top of whichever version is right.

Then the blanks (**1.8**), because they gate filing and are the owner's to answer; then the
rest.

One structural recommendation, offered once and not pressed: two hand-maintained copies of the
same policy will drift again — this list is the evidence, and the drift happened inside one
release cycle. The facts in both documents are already enumerated in `DATA-INVENTORY.md`. If
there is ever a third client, generate both from one source rather than porting sentence by
sentence a second time.
