# Alma — store listings, six languages

Everything in this file is meant to be pasted into App Store Connect and Play Console as-is.
Each field is a fenced block with an HTML comment above it naming the field and its limit, so
`scripts/check-listing.py` (below) can count characters without anybody trusting an eyeball.

Nothing here is translated from the English. Each locale was written against the voice already
shipping in `/Users/anatoliymikhaylow/alma_project1/src/lib/i18n/` — the sentence rhythm, the
dashes, the refusal to flatter — and then checked back against the English for facts, not for
wording. Where a language would not carry an English construction, the line changed rather
than the language. The French subtitle is the clearest case and is noted where it appears.

---

## What this copy is allowed to claim, and why

Every factual assertion below is traceable. The house rule is that no marketing sentence
survives that cannot be pointed at a file.

| Claim in the copy | Where it is true |
|---|---|
| Eight independent systems | `backend/alma/ai/chapters.py:151–160` — `BY_SYSTEM` has exactly eight keys |
| Forty-one chapters | 16 + 5 + 3 + 3 + 3 + 4 + 3 + 4 = 41, counted from the tuples in `chapters.py:40–148` |
| One free written chapter in every system | one `free=True` chapter per tuple in `chapters.py`; enforced at `backend/alma/auth/entitlements.py:205–206` and `87–88` |
| **The list of what is free** — the three signs, the moon phase and the balance; the life path, birthday and destiny numbers; the birth card; every transit with its exact day and the natal placement it is read against; the solar return and its ruler; the four compatibility weights; the nine axes with each system's factor and the counts | `backend/alma/api/routers/systems.py:47–78` — `PREVIEW_FIELDS`, applied at `:114–121`. **This table row is the copy.** The list in the description is transcribed from that dict and nothing else; if a key is added or removed there, the sentence in all twelve descriptions moves with it |
| NASA JPL DE440s planetary ephemeris | `backend/alma/engine/ephemeris.py:66–83` loads `backend/data/de440s.bsp` (32 MB, present in the repo); which kernel answered is recorded per chart at `engine/natal.py:84,290`. DE421 is the offline CI fallback only — production ships the file, so the claim holds for shipped builds |
| Placidus houses, tropical zodiac | `backend/alma/engine/houses.py:155` `placidus()`; `engine/zodiac.py` |
| Daylight-saving and polar latitudes handled | `engine/timeutil.py` (ambiguous-time path surfaces as `errors.ambiguousTime` in the UI); `houses.py:26,121` raises `PlacidusUndefined` inside the polar circle rather than inventing cusps |
| Historical time zone resolved offline; no geocoder learns a birthplace | `backend/alma/geo.py` + `backend/data/places.sqlite`; confirmed in `DATA-INVENTORY.md` §2 |
| Every paragraph names the placement it was read from | `backend/alma/ai/voice.py:47–52`; the array is checked in `backend/alma/ai/validator.py` |
| A paragraph citing a placement not in the chart is rejected and rewritten | `validator.py:11–16` (`invented`) and `17–19` (`uncited`); `Verdict.complaint()` is the retry instruction |
| It does not predict; no medical, legal or financial advice | `voice.py:57–63` |
| Houses / solar return / map stay unavailable without a birth time | `chapters.py` `time_dependent=True`; `errors.needsBirthTime` in `src/lib/i18n/en.ts:685` |
| Cross-synthesis: **three** systems on nine axes, agreement and disagreement counted | `backend/alma/engine/synthesis.py:29` `AXES` (the nine) and `:355–360` `contributions` (natal, numerology, birth-card, and no others); rendered at `mobile/ios/Alma/Screens/Systems/SystemScreen.swift:274–302`. Every description said *eight* until 7 Aug 2026 and was wrong by 8/3 on the one claim the 4.3(b) argument rests on. `check-listing.py` now fails the build if the word comes back |
| Compatibility is four weights, never one score | `src/lib/i18n/en.ts:360–369`; `engine/synastry.py` |
| Three free questions a day, forever | `backend/alma/config.py:262`; `api/routers/readings.py:117` |
| Questions included with a purchase, as a finite bundle | `config.py:269` (15); `readings.py:133` |
| A monthly allowance of questions with the subscription | `config.py` `subscriber_questions_per_month`; `readings.py:108–116` |
| No free trial, no introductory price | owner decision, 6 Aug 2026; no trial or intro product exists in `billing/catalogue.py` |
| The store takes the payment and a subscription is cancelled in the store's own account settings | `mobile/ios/Alma/Resources/Cabinet.xcstrings` `cab.managedByApple` and `cab.settings.lettersNoteStore` — the app already says this, in six languages; `mobile/android/…/billing/StoreProducts.kt:176–181` links out to `play.google.com/store/account/subscriptions` |
| **Alma's own three-day letter is conditional on an address** | `backend/alma/billing/renewals.py:141–155` — `owner.email or _address_from_the_payment()`, and the notice is *skipped* when both are empty. Store purchases write `buyer_email=None` (`appstore.py:531`, `googleplay.py:638`) and both adapters declare `requires_email = False` (`:835`, `:929`), so a guest buyer has no address and gets no letter. Every description said we write three days before *every* renewal until 7 Aug 2026. The copy now says "add an email … and Alma writes to you three days before", which is what `cab.plan.renewsNoEmail` already says on the phone |
| No advertising identifier, no third-party analytics, no cross-app tracking | `DATA-INVENTORY.md` §4 |
| **A guest can export and delete their own account** | `backend/alma/api/routers/account.py:51,68` both take `CurrentUser`, not `Account`; the confirmation string is the email for a signed-in person and the account id for a guest. Verified live on 7 Aug 2026: a fresh guest token returned HTTP 200 from `/v1/account/export` and from `/v1/account/delete`, and the token was dead afterwards. This row said the opposite until the fix landed the same day — a guest is the *default* state (`deps.py:61–91` mints one on the first call), so "delete your account from Settings, at any time" had been false for most users. Apple Guideline 5.1.1(v) applies to exactly that person, because the reviewer is one. |

### And what is deliberately absent

- **No prices, anywhere.** Apple 2.3.7: metadata *"should not include prices, terms, or
  descriptions that are not specific to the metadata type."* Six locales across thirteen
  currencies would also be wrong in most storefronts within a quarter. The copy says
  *a single purchase*, *a subscription*, *free* — never a number. The numbers live only on the
  in-app purchase records, which is where a store keeps them current for us.
- **No entertainment disclaimer.** Apple 1.1.6 explicitly voids it, and reaching for it is an
  admission the 4.3(b) argument has failed. The only limiting sentence anywhere is the true
  one — *no medical, psychological, legal or financial advice* — which is a statement about
  scope, not a shield.
- **No other platform named.** Apple 2.3.10. The Apple and Play bodies are separate texts and
  neither mentions the other store, a badge, or a device family belonging to the other.
- **The word "purchase" appears in every description.** Apple 2.3.2 requires the description
  and screenshots to make clear that featured content needs additional purchases. The
  *FREE, AND PAID* block is that compliance, and it is also the most persuasive block in the
  listing, which is convenient.
- **No superlatives, no "most accurate", no "#1".** Unverifiable claims are called out by name
  in 2.3.7 as a subtitle problem, and the whole brand is that we do not make them.
- **No sweeping "every calculation is free" any more.** It was in all twelve descriptions and
  it was not true of the shipped app. `PREVIEW_FIELDS` (`api/routers/systems.py:47–78`) hands a
  locked reader six keys of the natal chart — no bodies, no houses, no aspects, `factors: []` —
  and hands astrocartography one key, `birthplace`, with the computed `lines` trimmed away
  entirely. The comment at `entitlements.py:61–64` says calculations stay free; the code that
  runs disagrees with the comment. So the copy now *enumerates* what is free instead of
  generalising, which is both true and better evidence: a reviewer can check a nine-item list
  against the screen in fifteen seconds and a slogan cannot be checked at all.
  If `PREVIEW_FIELDS` is widened (recommended — `APP-CHANGES-NEEDED.md` §4), the list gets
  longer and the argument gets stronger. Understating it is safe; overstating it is 2.3.2.

### URLs used in the copy

All six languages are served from one set of URLs; the site resolves locale from the
`alma.locale` cookie and `Accept-Language` rather than from a path prefix
(`src/lib/i18n/index.ts`), so the same URL is correct in every App Store Connect locale slot.

- Terms of Use (our EULA — linked from the description, as Apple requires for auto-renewing
  subscriptions): `https://alma.pazl.ai/terms`
- Privacy Policy: `https://alma.pazl.ai/privacy`
- Subscription terms: `https://alma.pazl.ai/subscription-terms`
- Refunds: `https://alma.pazl.ai/refunds`
- Imprint: `https://alma.pazl.ai/imprint`

> ### ⛔ The host does not exist. Nothing here can be filed until it does.
>
> On 7 August 2026, `nslookup alma.pazl.ai` and `nslookup api.pazl.ai` both returned
> **NXDOMAIN**. Only the apex `pazl.ai` resolves, to `95.81.101.52`. General network access
> from the same shell was fine (`apple.com` answered 200), so this is the domain and not the
> connection.
>
> That is not "two pages to write". It is *nothing deployed*. `alma.pazl.ai` is the deep-link
> host in `mobile/android/app/src/main/AndroidManifest.xml:41` and the `Site` constant in
> `SettingsScreen.kt:724`; `api.pazl.ai` is the Release API host. Every legal URL printed in all
> twelve descriptions above points at a name that does not resolve, and **Apple fetches the
> Privacy Policy URL during review and rejects on a dead one before anybody opens the build.**
>
> The two routes that used to be missing are **built** — `src/app/(legal)/` now has `support`
> and `delete-account` alongside the five documents, and every one of the seven returns 200
> against `npm run dev`, checked 7 August 2026:
>
> - **Support URL** → `https://<host>/support`. `src/app/(legal)/support/page.tsx`. The one
>   page in the group that is translated, and it renders on the server, so a reviewer opening
>   it cold without JavaScript gets their own language rather than an English first paint.
> - **Account-deletion URL** → `https://<host>/delete-account`.
>   `src/app/(legal)/delete-account/page.tsx`, and it does state the guest limitation
>   (`APP-CHANGES-NEEDED.md` §1) rather than promising what iOS cannot yet do.
>
> So what is left here is only the host. Before either console is opened: stand it up, then
> fetch all seven URLs and confirm each returns 200 — the five above plus `/support` and
> `/delete-account`. Until the host resolves the paths are correct and unreachable, which is
> exactly as unfileable as a missing page.

---

# 1. English (en) — primary locale

<!-- field: en.apple.name | limit: 30 -->
```
Alma: Natal Chart & 8 Systems
```

Also the Play app name. Play has no keyword field and indexes the title heavily, so the same
string does double duty. "Natal Chart" is the search term; "8 Systems" is the 4.3(b) argument
compressed to two words.

<!-- field: en.apple.subtitle | limit: 30 -->
```
Real ephemeris, no predictions
```

<!-- field: en.apple.promotional | limit: 170 -->
```
Eight systems read the same birth data and disagree in public. Positions come from NASA JPL's DE440s ephemeris. Every sentence names the placement it was read from.
```

<!-- field: en.apple.keywords | limit: 100 bytes -->
```
astrology,birth,horoscope,numerology,tarot,transit,synastry,zodiac,solar,return,astrocartography
```

No word here repeats the app name or subtitle — Apple indexes those separately and a repeat is
a wasted byte. "houses" and "placidus" were dropped for length; both appear in the description,
which Apple does not index but Play does.

<!-- field: en.apple.description | limit: 4000 -->
```
Eight independent systems read the same birth data, and Alma shows you where they disagree.

Positions are computed from NASA JPL's DE440s planetary ephemeris — real orbital data, not a lookup table. Placidus houses, tropical zodiac, and the historical time zone of your birthplace resolved offline, daylight-saving changes and polar latitudes included.

THE EIGHT
Natal chart, 16 chapters. Numerology, 5. Birth Card, 3. Transits, 3. Solar return, 3. Compatibility, 4, read against a second chart you add yourself. Astrocartography, 3. Cross-synthesis, 4. Forty-one chapters in all.

WHERE THEY DISAGREE
Cross-synthesis is the part no single tradition can do. Three of the systems — the natal chart, numerology and the tarot birth card — answer the same nine questions independently: direction, character, mind, relationships, resources, work, weak point, growth, rhythms. Where all three agree, that goes to your core. Where two contradict each other, you are looking at a conflict you keep living out rather than a bad reading. Both are shown. Nothing is smoothed into a consensus.

EVERY SENTENCE NAMES ITS SOURCE
Each paragraph carries the exact placement it was read from: "Saturn on your Descendant at 19° Pisces", not "your relationships". A paragraph citing a placement your chart does not contain is rejected and rewritten before you see it, and so is a paragraph that cites nothing. That check is code, and it runs on every chapter.

IT DOES NOT PREDICT
Alma describes what you are made of, not what will happen. No event predictions, no fate language, no medical, psychological, legal or financial advice. Where a question is a decision, she says the decision is yours.

If you don't know your birth time, everything that does not need one still works. Houses, the solar return and the map stay marked unavailable rather than filled in with a guessed noon.

FREE, AND PAID
Free, permanent, no account: your sun, moon and rising signs, the moon phase, the elemental balance; the life path, birthday and destiny numbers; the birth card; every transit in effect, each naming the day it is exact and the natal placement it is read against; the solar return and its ruler; the four compatibility weights; and all nine axes of the cross-synthesis, each showing what every system read and who agreed. One written chapter in each of the eight systems is free too, and it is a complete chapter, not a teaser.

What is purchased is the writing, and the depth behind each system: the twelve houses and the aspects, the pinnacles and cycles, the lines on the map. One system with all its chapters is a single purchase, kept permanently. All forty-one chapters together are a single purchase. A subscription covers the three systems that actually move — transits, solar return, compatibility — as they move, plus a monthly allowance of questions; it is not how the app is unlocked.

No free trial and no introductory price. Nothing converts into a charge. One-time means one-time. Apple takes the payment; a subscription is managed and cancelled in your Apple ID settings. Its next renewal date is in Alma's Settings — add an email there and Alma writes to you three days before, with the date and the amount.

ASK IN YOUR OWN WORDS
Alma answers questions about your own chart and names the position she read from. Three a day are free, always.

YOUR DATA
Birth data is used to calculate and to write, and for nothing else. No advertising identifier, no third-party analytics, no cross-app tracking. Signed in, you can export everything or delete the account and all of it, from Settings — a real deletion, not a deactivation.

Terms of Use: https://alma.pazl.ai/terms
Privacy Policy: https://alma.pazl.ai/privacy
Subscription terms: https://alma.pazl.ai/subscription-terms
```

<!-- field: en.play.short | limit: 80 -->
```
Eight systems on one chart. Real ephemeris. Every sentence names its source.
```

<!-- field: en.play.full | limit: 4000 -->
```
Alma computes eight divination systems from your birth data and writes a reading out of what it computed.

WHAT IT COMPUTES
A full natal chart — ten planets, twelve Placidus houses, the aspects, the angles — from NASA JPL's DE440s planetary ephemeris. Numerology from your date and your full name at birth. Your tarot birth card. Current transits against your natal positions. Your solar return. Compatibility with a second chart you enter, as four separate weights rather than one percentage. Astrocartography lines across a world map. And a cross-synthesis that puts three of those systems — the natal chart, numerology and the birth card — side by side on nine axes and counts where they agree and where they contradict each other.

The historical time zone of your birthplace is resolved from an offline gazetteer, so no geocoding service is ever told where you were born. Daylight-saving changes and polar latitudes are handled rather than approximated: where a chart genuinely cannot be drawn, the app says so instead of guessing.

WHAT IS FREE
Free, permanent, no account: your sun, moon and rising signs, the moon phase, the elemental balance; the life path, birthday and destiny numbers; the birth card; every transit in effect, each naming the day it is exact and the natal placement it is read against; the solar return and its ruler; the four compatibility weights; and all nine axes of the cross-synthesis, each showing what every system read and who agreed. One written chapter in each of the eight systems is free too, and it is a complete chapter, not a teaser.

WHAT IS PURCHASED
The written interpretation of the remaining chapters — forty-one exist in all — and the depth behind each system: the twelve houses and the aspects, the pinnacles and cycles, the lines on the map. One system with every one of its chapters is a single purchase, kept permanently; all forty-one together are a single purchase. A subscription covers the three systems that move — transits, solar return, compatibility — as they move, plus a monthly allowance of questions; it is not how the app is unlocked.

There is no free trial and no introductory offer. Nothing converts into a charge. Google Play takes the payment; a subscription is cancelled in your Google Play account, and the app links straight there. Add an email in Settings and Alma writes to you three days before each renewal, with the date and the amount.

EVERY SENTENCE NAMES ITS SOURCE
Each written paragraph carries the exact placement it was read from — "Saturn on your Descendant at 19° Pisces", not "your relationships". A paragraph citing a placement your chart does not contain is rejected and rewritten before it reaches you. A paragraph citing nothing is rejected too. That check is code, and it runs on every chapter.

IT DOES NOT PREDICT
Alma describes what you are made of, not what will happen. No event predictions, no fate language, no medical, psychological, legal or financial advice. Where a question is a decision, she says the decision is yours.

ASK IN YOUR OWN WORDS
Ask about your own chart and the answer names the position it was read from. Three questions a day are free, always.

IF YOU DON'T KNOW YOUR BIRTH TIME
Everything that does not need one still works: sun, planets by sign, numerology, your birth card, most transits. Houses, the solar return and the map stay marked unavailable rather than filled in with a guessed noon.

YOUR DATA
Birth data is used to calculate and to write, and for nothing else. No advertising identifier, no third-party analytics, no cross-app tracking. Signed in, you can export everything or delete the account and all of it, from Settings — a real deletion, not a deactivation.

Privacy Policy: https://alma.pazl.ai/privacy
Terms of Use: https://alma.pazl.ai/terms
```

---

# 2. Español (es)

<!-- field: es.apple.name | limit: 30 -->
```
Alma: Carta Natal y 8 Sistemas
```

<!-- field: es.apple.subtitle | limit: 30 -->
```
Efemérides reales, no adivina
```

<!-- field: es.apple.promotional | limit: 170 -->
```
Ocho sistemas leen los mismos datos de nacimiento y discrepan a la vista. Las posiciones salen de las efemérides DE440s de la NASA JPL. Cada frase nombra su posición.
```

<!-- field: es.apple.keywords | limit: 100 bytes -->
```
astrologia,horoscopo,numerologia,tarot,transitos,sinastria,zodiaco,casas,revolucion,solar,natal
```

Written without accents on purpose: Apple's keyword field is measured in **bytes**, an accented
character costs two, and Apple matches unaccented queries against unaccented keywords. The
accented forms all appear in the description, where the byte cost is not charged.

<!-- field: es.apple.description | limit: 4000 -->
```
Ocho sistemas independientes leen los mismos datos de nacimiento, y Alma te muestra dónde discrepan.

Las posiciones se calculan con las efemérides planetarias DE440s de la NASA JPL — datos orbitales reales, no una tabla de consulta. Casas Placidus, zodiaco tropical y la zona horaria histórica de tu lugar de nacimiento resuelta sin conexión, cambios de hora incluidos.

LOS OCHO
Carta natal, 16 capítulos. Numerología, 5. Carta de nacimiento, 3. Tránsitos, 3. Revolución solar, 3. Compatibilidad, 4, contra una segunda carta que añades tú. Astrocartografía, 3. Síntesis cruzada, 4. Cuarenta y un capítulos en total.

DONDE DISCREPAN
La síntesis cruzada es lo que ninguna tradición puede hacer sola. Tres de los sistemas — la carta natal, la numerología y la carta de nacimiento del tarot — responden por separado a las mismas nueve preguntas: dirección, carácter, mente, relaciones, recursos, trabajo, punto débil, crecimiento, ritmos. Donde los tres coinciden, eso va a tu núcleo. Donde dos se contradicen, estás mirando un conflicto que sigues viviendo, no una lectura mala. Se muestran los dos. Nada se suaviza hasta volverse consenso.

CADA FRASE NOMBRA SU FUENTE
Cada párrafo lleva la posición exacta de la que se leyó: «Saturno sobre tu Descendente a 19° de Piscis», no «tus relaciones». Un párrafo que cite una posición que tu carta no tiene se rechaza y se reescribe antes de que lo veas, y lo mismo ocurre con un párrafo que no cite nada. Esa comprobación es código y se ejecuta en cada capítulo.

NO PREDICE
Alma describe de qué estás hecho, no lo que va a pasar. Sin predicciones de sucesos, sin lenguaje de destino, sin consejo médico, psicológico, legal ni financiero. Cuando la pregunta es una decisión, dice que la decisión es tuya.

Si no sabes tu hora de nacimiento, todo lo que no la necesita sigue funcionando. Las casas, la revolución solar y el mapa quedan marcados como no disponibles en vez de rellenarse con un mediodía inventado.

GRATIS, Y DE PAGO
Gratis, para siempre y sin cuenta: tu signo solar, tu lunar y tu ascendente, la fase lunar, el equilibrio de elementos; los números de camino de vida, cumpleaños y destino; tu carta de nacimiento; cada tránsito activo, con el día exacto y la posición natal contra la que se lee; tu revolución solar y su regente; los cuatro pesos de compatibilidad; y los nueve ejes de la síntesis cruzada, con lo que leyó cada sistema y quién coincide. Un capítulo escrito de cada uno de los ocho sistemas también es gratis, y es completo, no un anticipo.

Lo que se compra es lo escrito, y la profundidad detrás de cada sistema: las doce casas y los aspectos, los pináculos y los ciclos, las líneas del mapa. Un sistema con todos sus capítulos es una compra única y se queda contigo para siempre. Los cuarenta y un capítulos juntos son una compra única. Una suscripción cubre los tres sistemas que de verdad se mueven — tránsitos, revolución solar, compatibilidad — según se mueven, más una cuota mensual de preguntas; no es la forma de desbloquear la app.

Sin prueba gratuita y sin precio de lanzamiento. Nada se convierte en un cobro. Un pago único es un pago único. Apple cobra, y una suscripción se gestiona y se cancela en los ajustes de tu ID de Apple. La fecha de la próxima renovación está en los Ajustes de Alma; añade allí un correo y Alma te escribe tres días antes, con la fecha y el importe.

PREGUNTA CON TUS PALABRAS
Alma responde preguntas sobre tu propia carta y nombra la posición de la que ha leído. Tres al día son gratis, siempre.

TUS DATOS
Tus datos de nacimiento se usan para calcular y para escribir, y para nada más. Sin identificador publicitario, sin analítica de terceros, sin seguimiento entre apps. Con la sesión iniciada puedes exportarlo todo o borrar la cuenta entera desde los Ajustes: un borrado de verdad, no una desactivación.

Términos de uso: https://alma.pazl.ai/terms
Política de privacidad: https://alma.pazl.ai/privacy
Términos de suscripción: https://alma.pazl.ai/subscription-terms
```

<!-- field: es.play.short | limit: 80 -->
```
Ocho sistemas sobre una carta. Efemérides reales. Cada frase cita su fuente.
```

<!-- field: es.play.full | limit: 4000 -->
```
Alma calcula ocho sistemas de lectura a partir de tus datos de nacimiento y escribe la interpretación a partir de lo que ha calculado.

QUÉ CALCULA
Una carta natal completa — diez planetas, doce casas Placidus, los aspectos, los ángulos — con las efemérides planetarias DE440s de la NASA JPL. Numerología a partir de tu fecha y de tu nombre completo al nacer. Tu carta de nacimiento del tarot. Los tránsitos actuales sobre tus posiciones natales. Tu revolución solar. Compatibilidad con una segunda carta que introduces tú, en cuatro pesos separados y no en un solo porcentaje. Líneas de astrocartografía sobre un mapa del mundo. Y una síntesis cruzada que pone tres de esos sistemas — la carta natal, la numerología y la carta de nacimiento — uno junto a otro sobre nueve ejes y cuenta dónde coinciden y dónde se contradicen.

La zona horaria histórica de tu lugar de nacimiento se resuelve con un callejero sin conexión, así que ningún servicio de geocodificación llega a saber dónde naciste. Los cambios de hora y las latitudes polares se tratan de verdad, no se aproximan: donde una carta realmente no se puede levantar, la app lo dice en vez de inventarla.

QUÉ ES GRATIS
Gratis, para siempre y sin cuenta: tu signo solar, tu lunar y tu ascendente, la fase lunar, el equilibrio de elementos; los números de camino de vida, cumpleaños y destino; tu carta de nacimiento; cada tránsito activo, con el día exacto y la posición natal contra la que se lee; tu revolución solar y su regente; los cuatro pesos de compatibilidad; y los nueve ejes de la síntesis cruzada, con lo que leyó cada sistema y quién coincide. Un capítulo escrito de cada uno de los ocho sistemas también es gratis, y es completo, no un anticipo.

QUÉ SE COMPRA
La interpretación escrita de los capítulos restantes — en total hay cuarenta y uno — y la profundidad detrás de cada sistema: las doce casas y los aspectos, los pináculos y los ciclos, las líneas del mapa. Un sistema con todos sus capítulos es una compra única que se queda contigo; los cuarenta y uno juntos son una compra única. Una suscripción cubre los tres sistemas que se mueven — tránsitos, revolución solar, compatibilidad — según se mueven, más una cuota mensual de preguntas; no es la forma de desbloquear la app.

No hay prueba gratuita ni oferta de lanzamiento. Nada se convierte en un cobro. Google Play cobra, y una suscripción se cancela en tu cuenta de Google Play — la app te lleva directo allí. Añade un correo en los Ajustes y Alma te escribe tres días antes, con la fecha y el importe.

CADA FRASE NOMBRA SU FUENTE
Cada párrafo escrito lleva la posición exacta de la que se leyó: «Saturno sobre tu Descendente a 19° de Piscis», no «tus relaciones». Un párrafo que cite una posición que tu carta no tiene se rechaza y se reescribe antes de llegarte, y uno que no cite nada también. Esa comprobación es código y se ejecuta en cada capítulo.

NO PREDICE
Alma describe de qué estás hecho, no lo que va a pasar. Sin predicciones de sucesos, sin lenguaje de destino, sin consejo médico, psicológico, legal ni financiero. Cuando la pregunta es una decisión, dice que la decisión es tuya.

PREGUNTA CON TUS PALABRAS
Pregunta sobre tu propia carta y la respuesta nombra la posición de la que ha leído. Tres preguntas al día son gratis, siempre.

SI NO SABES TU HORA DE NACIMIENTO
Todo lo que no la necesita sigue funcionando: sol, planetas por signo, numerología, tu carta de nacimiento, casi todos los tránsitos. Las casas, la revolución solar y el mapa quedan marcados como no disponibles en vez de rellenarse con un mediodía inventado.

TUS DATOS
Tus datos de nacimiento se usan para calcular y para escribir, y para nada más. Sin identificador publicitario, sin analítica de terceros, sin seguimiento entre apps. Con la sesión iniciada puedes exportarlo todo o borrar la cuenta entera desde los Ajustes: un borrado de verdad, no una desactivación.

Política de privacidad: https://alma.pazl.ai/privacy
Términos de uso: https://alma.pazl.ai/terms
```

---

# 3. Deutsch (de)

<!-- field: de.apple.name | limit: 30 -->
```
Alma: 8 Systeme, ein Horoskop
```

`Geburtshoroskop` is what the app itself calls the natal chart (`i18n/de.ts`), but
`Alma: Geburtshoroskop & 8 Systeme` is 33 characters and does not fit. `Horoskop` is the term
German buyers actually search, and the app does compute a Geburtshoroskop, so the shorter word
is accurate rather than merely convenient. The long form appears in the first line of the
description, where Play indexes it.

**Changed 7 Aug 2026 from `Alma: Horoskop & 8 Systeme` (26).** Same words, different order, and
the order is the whole point. The person this listing is written for is someone who deleted a
horoscope app; they read the first word, see `Horoskop`, and stop — so the string that would
have made them pause, `8 Systeme`, sat behind the word that disqualified the app. English never
had this problem, because `Natal Chart & 8 Systems` reads as a tool. The search term is still
in the title and still indexed by Play; only the reading order moved.

The differentiator therefore no longer rests on the subtitle alone. `Echte Ephemeriden, kein
Orakel` (30/30) is kept because *kein Orakel* lands immediately and *Echte Ephemeriden* is the
verifiable half of the 4.3(b) claim. If a lay-readable line is ever preferred over the evidence
one, `Berechnet, nicht geraten` (24) is the German of the French subtitle's move and fits with
room to spare — it is a brand call, not a correctness one.

<!-- field: de.apple.subtitle | limit: 30 -->
```
Echte Ephemeriden, kein Orakel
```

<!-- field: de.apple.promotional | limit: 170 -->
```
Acht Systeme lesen dieselben Geburtsdaten und widersprechen sich offen. Die Positionen stammen aus der DE440s-Ephemeride der NASA JPL. Jeder Satz nennt seine Position.
```

<!-- field: de.apple.keywords | limit: 100 bytes -->
```
astrologie,geburtshoroskop,numerologie,tarot,transite,synastrie,tierkreis,haeuser,solar,radix
```

`haeuser` rather than `häuser`: the umlaut costs two bytes and Apple matches the transliteration.

<!-- field: de.apple.description | limit: 4000 -->
```
Acht unabhängige Systeme lesen dieselben Geburtsdaten, und Alma zeigt dir, wo sie sich widersprechen.

Die Positionen werden aus der planetaren Ephemeride DE440s der NASA JPL berechnet — echte Bahndaten, keine Nachschlagetabelle. Placidus-Häuser, tropischer Tierkreis, und die historische Zeitzone deines Geburtsorts offline aufgelöst — samt Zeitumstellungen.

DIE ACHT
Geburtshoroskop, 16 Kapitel. Numerologie, 5. Geburtskarte, 3. Transite, 3. Solarhoroskop, 3. Partnerschaft, 4, gegen ein zweites Horoskop, das du anlegst. Astrokartografie, 3. Quersynthese, 4. Einundvierzig Kapitel insgesamt.

WO SIE SICH WIDERSPRECHEN
Die Quersynthese ist der Teil, den keine einzelne Tradition leisten kann. Drei der Systeme — das Geburtshoroskop, die Numerologie und die Geburtskarte — beantworten dieselben neun Fragen unabhängig voneinander: Richtung, Charakter, Denken, Beziehungen, Mittel, Arbeit, Schwachstelle, Wachstum, Rhythmen. Wo alle drei übereinstimmen, geht das in deinen Kern. Wo zwei sich widersprechen, siehst du einen Konflikt, den du immer wieder lebst, und keine schlechte Deutung. Beides wird gezeigt. Nichts wird zu einem Konsens geglättet.

JEDER SATZ NENNT SEINE QUELLE
Jeder Absatz trägt die genaue Position, aus der er gelesen wurde: „Saturn auf deinem Deszendenten bei 19° Fische“, nicht „deine Beziehungen“. Ein Absatz, der eine Position nennt, die dein Horoskop nicht enthält, wird verworfen und neu geschrieben, bevor du ihn siehst — und einer, der gar nichts nennt, ebenso. Das ist Code, und es läuft bei jedem Kapitel.

SIE SAGT NICHTS VORHER
Alma beschreibt, woraus du gemacht bist, nicht was passieren wird. Keine Ereignisprognosen, keine Schicksalssprache, keine medizinische, psychologische, rechtliche oder finanzielle Beratung. Bei einer Entscheidung sagt sie, dass sie deine ist.

Ohne Geburtszeit bleiben Häuser, Solarhoroskop und Karte als nicht verfügbar markiert, statt mit einem geratenen Mittag gefüllt zu werden.

KOSTENLOS, UND KOSTENPFLICHTIG
Kostenlos, dauerhaft, ohne Konto: Sonne, Mond und Aszendent, Mondphase und Elementeverteilung; Lebenszahl, Geburtstagszahl, Schicksalszahl; die Geburtskarte; jeder laufende Transit samt dem Tag, an dem er exakt wird, und der Radixposition, gegen die er gelesen wird; das Solarhoroskop und sein Herrscher; die vier Partnerschaftsgewichte; und alle neun Achsen der Quersynthese mit dem, was jedes System gelesen hat, und wer zustimmt. Ein geschriebenes Kapitel in jedem der acht Systeme ist ebenfalls kostenlos, und es ist vollständig, kein Anreißer.

Gekauft wird der Text und die Tiefe hinter jedem System: die zwölf Häuser und die Aspekte, die Höhepunkte und Zyklen, die Linien auf der Karte. Ein System mit allen seinen Kapiteln ist ein einmaliger Kauf und bleibt dauerhaft deins. Alle einundvierzig Kapitel zusammen sind ein einmaliger Kauf. Ein Abo deckt die drei Systeme ab, die sich bewegen — Transite, Solarhoroskop, Partnerschaft —, während sie sich bewegen, dazu ein monatliches Kontingent an Fragen; es ist nicht der Weg, die App freizuschalten.

Keine Testphase und kein Einführungspreis. Nichts wird zu einer Abbuchung. Einmalig heißt einmalig. Apple zieht die Zahlung ein; verwaltet und gekündigt wird ein Abo in deinen Apple-ID-Einstellungen. Das Datum der nächsten Verlängerung steht in Almas Einstellungen — mit hinterlegter E-Mail schreibt Alma dir drei Tage vorher, mit Datum und Betrag.

FRAG IN DEINEN WORTEN
Alma beantwortet Fragen zu deinem Horoskop und nennt die Position, aus der sie gelesen hat. Drei am Tag sind kostenlos, immer.

DEINE DATEN
Deine Geburtsdaten werden zum Rechnen und zum Schreiben benutzt, sonst für nichts. Keine Werbe-ID, keine Fremdanalyse, kein App-übergreifendes Tracking. Angemeldet kannst du alles exportieren oder das Konto vollständig löschen — eine echte Löschung, keine Deaktivierung.

Nutzungsbedingungen: https://alma.pazl.ai/terms
Datenschutzerklärung: https://alma.pazl.ai/privacy
Abo-Bedingungen: https://alma.pazl.ai/subscription-terms
```

<!-- field: de.play.short | limit: 80 -->
```
Acht Systeme, ein Horoskop. Echte Ephemeriden. Jeder Satz nennt seine Quelle.
```

<!-- field: de.play.full | limit: 4000 -->
```
Alma berechnet acht Deutungssysteme aus deinen Geburtsdaten und schreibt die Deutung aus dem, was sie berechnet hat.

WAS BERECHNET WIRD
Ein vollständiges Geburtshoroskop — zehn Planeten, zwölf Placidus-Häuser, die Aspekte, die Achsen — aus der planetaren Ephemeride DE440s der NASA JPL. Numerologie aus deinem Datum und deinem vollen Geburtsnamen. Deine Geburtskarte aus dem Tarot. Die aktuellen Transite gegen deine Radixpositionen. Dein Solarhoroskop. Partnerschaft mit einem zweiten Horoskop, als vier getrennte Gewichte statt einer Prozentzahl. Astrokartografie-Linien über einer Weltkarte. Und eine Quersynthese, die drei davon — Geburtshoroskop, Numerologie, Geburtskarte — auf neun Achsen stellt und zählt, wo sie übereinstimmen und wo sie sich widersprechen.

Die historische Zeitzone deines Geburtsorts wird offline aufgelöst, sodass kein Geokodierungsdienst erfährt, wo du geboren wurdest. Zeitumstellungen und polare Breiten werden behandelt statt genähert: wo ein Horoskop nicht gestellt werden kann, sagt die App das, statt es zu erfinden.

WAS KOSTENLOS IST
Kostenlos, dauerhaft, ohne Konto: Sonne, Mond und Aszendent, Mondphase und Elementeverteilung; Lebenszahl, Geburtstagszahl, Schicksalszahl; die Geburtskarte; jeder laufende Transit samt dem Tag, an dem er exakt wird, und der Radixposition, gegen die er gelesen wird; das Solarhoroskop und sein Herrscher; die vier Partnerschaftsgewichte; und alle neun Achsen der Quersynthese mit dem, was jedes System gelesen hat, und wer zustimmt. Ein geschriebenes Kapitel in jedem der acht Systeme ist ebenfalls kostenlos, und es ist vollständig, kein Anreißer.

WAS GEKAUFT WIRD
Die geschriebene Deutung der übrigen Kapitel — insgesamt einundvierzig — und die Tiefe hinter jedem System: die zwölf Häuser und die Aspekte, die Höhepunkte und Zyklen, die Linien auf der Karte. Ein System mit allen seinen Kapiteln ist ein einmaliger Kauf und bleibt dauerhaft deins; alle einundvierzig zusammen sind ein einmaliger Kauf. Ein Abo deckt die drei Systeme ab, die sich bewegen — Transite, Solarhoroskop, Partnerschaft —, während sie sich bewegen, dazu ein monatliches Kontingent an Fragen; es ist nicht der Weg, die App freizuschalten.

Es gibt keine Testphase und kein Einführungsangebot. Nichts wird zu einer Abbuchung. Google Play zieht die Zahlung ein; gekündigt wird ein Abo im Google-Play-Konto, und die App verlinkt direkt dorthin. Mit hinterlegter E-Mail schreibt Alma dir drei Tage vorher, mit Datum und Betrag.

JEDER SATZ NENNT SEINE QUELLE
Jeder geschriebene Absatz trägt die genaue Position, aus der er gelesen wurde — „Saturn auf deinem Deszendenten bei 19° Fische“, nicht „deine Beziehungen“. Ein Absatz, der eine Position nennt, die dein Horoskop nicht enthält, wird verworfen und neu geschrieben, bevor er dich erreicht — und einer, der gar nichts nennt, ebenso. Das ist Code, und es läuft bei jedem Kapitel.

SIE SAGT NICHTS VORHER
Alma beschreibt, woraus du gemacht bist, nicht was passieren wird. Keine Ereignisprognosen, keine Schicksalssprache, keine medizinische, psychologische, rechtliche oder finanzielle Beratung. Bei einer Entscheidung sagt sie, dass sie deine ist.

FRAG IN DEINEN WORTEN
Frag nach deinem eigenen Horoskop, und die Antwort nennt die Position, aus der sie gelesen hat. Drei Fragen am Tag sind kostenlos, immer.

WENN DU DEINE GEBURTSZEIT NICHT KENNST
Alles, was sie nicht braucht, funktioniert weiter: Sonne, Planeten nach Zeichen, Numerologie, Geburtskarte, die meisten Transite. Häuser, Solarhoroskop und Karte bleiben als nicht verfügbar markiert, statt geraten zu werden.

DEINE DATEN
Deine Geburtsdaten werden zum Rechnen und zum Schreiben benutzt, sonst für nichts. Keine Werbe-ID, keine Fremdanalyse, kein App-übergreifendes Tracking. Angemeldet kannst du alles exportieren oder das Konto vollständig löschen — eine echte Löschung, keine Deaktivierung.

Datenschutzerklärung: https://alma.pazl.ai/privacy
Nutzungsbedingungen: https://alma.pazl.ai/terms
```

---

# 4. Italiano (it)

<!-- field: it.apple.name | limit: 30 -->
```
Alma: Tema Natale e 8 Sistemi
```

<!-- field: it.apple.subtitle | limit: 30 -->
```
Effemeridi vere, non predice
```

<!-- field: it.apple.promotional | limit: 170 -->
```
Otto sistemi leggono gli stessi dati di nascita e si contraddicono in chiaro. Le posizioni vengono dalle effemeridi DE440s della NASA JPL. Ogni frase nomina la sua.
```

<!-- field: it.apple.keywords | limit: 100 bytes -->
```
astrologia,oroscopo,numerologia,tarocchi,transiti,sinastria,zodiaco,case,rivoluzione,solare
```

<!-- field: it.apple.description | limit: 4000 -->
```
Otto sistemi indipendenti leggono gli stessi dati di nascita, e Alma ti mostra dove si contraddicono.

Le posizioni sono calcolate dalle effemeridi planetarie DE440s della NASA JPL — dati orbitali veri, non una tabella di consultazione. Case Placidus, zodiaco tropicale e il fuso orario storico del tuo luogo di nascita risolto offline, cambi d'ora compresi.

GLI OTTO
Tema natale, 16 capitoli. Numerologia, 5. Carta di nascita, 3. Transiti, 3. Rivoluzione solare, 3. Affinità, 4, contro un secondo tema che aggiungi tu. Astrocartografia, 3. Sintesi incrociata, 4. Quarantuno capitoli in tutto.

DOVE SI CONTRADDICONO
La sintesi incrociata è la parte che nessuna singola tradizione può fare. Tre dei sistemi — il tema natale, la numerologia e la carta di nascita — rispondono alle stesse nove domande in modo indipendente: direzione, carattere, mente, relazioni, risorse, lavoro, punto debole, crescita, ritmi. Dove tutti e tre concordano, quello va nel tuo nucleo. Dove due si contraddicono, stai guardando un conflitto che continui a vivere, non una lettura sbagliata. Si vedono entrambi. Niente viene ammorbidito fino a diventare consenso.

OGNI FRASE NOMINA LA SUA FONTE
Ogni paragrafo porta la posizione esatta da cui è stato letto: «Saturno sul tuo Discendente a 19° dei Pesci», non «le tue relazioni». Un paragrafo che cita una posizione che il tuo tema non ha viene respinto e riscritto prima che tu lo veda, e lo stesso vale per un paragrafo che non cita niente. Quel controllo è codice, e gira su ogni capitolo.

NON PREDICE
Alma descrive di cosa sei fatto, non cosa succederà. Nessuna previsione di eventi, nessun linguaggio di destino, nessun consiglio medico, psicologico, legale o finanziario. Quando la domanda è una decisione, dice che la decisione è tua.

Se non sai la tua ora di nascita, tutto ciò che non ne ha bisogno funziona lo stesso. Case, rivoluzione solare e mappa restano segnate come non disponibili invece di essere riempite con un mezzogiorno inventato.

GRATIS, E A PAGAMENTO
Gratis, per sempre e senza account: Sole, Luna e Ascendente, la fase lunare, l'equilibrio degli elementi; i numeri di percorso di vita, compleanno e destino; la carta di nascita; ogni transito in corso, col giorno in cui è esatto e la posizione natale contro cui viene letto; la rivoluzione solare e il suo governatore; i quattro pesi dell'affinità; e tutti e nove gli assi della sintesi incrociata, con ciò che ogni sistema ha letto e chi concorda. Anche un capitolo scritto per ognuno degli otto sistemi è gratis, ed è completo, non un assaggio.

Si compra la scrittura, e la profondità dietro ogni sistema: le dodici case e gli aspetti, i pinnacoli e i cicli, le linee della mappa. Un sistema con tutti i suoi capitoli è un acquisto singolo e resta tuo per sempre. I quarantuno capitoli insieme sono un acquisto singolo. Un abbonamento copre i tre sistemi che si muovono davvero — transiti, rivoluzione solare, affinità — mentre si muovono, più una quota mensile di domande; non è il modo di sbloccare l'app.

Nessuna prova gratuita e nessun prezzo di lancio. Niente si trasforma in un addebito. Una tantum vuol dire una tantum. Apple incassa, e un abbonamento si gestisce e si disdice nelle impostazioni del tuo ID Apple. La data del prossimo rinnovo è nelle Impostazioni di Alma; aggiungi lì un'email e Alma ti scrive tre giorni prima, con la data e l'importo.

CHIEDI CON LE TUE PAROLE
Alma risponde a domande sul tuo tema e nomina la posizione da cui ha letto. Tre al giorno sono gratis, sempre.

I TUOI DATI
I tuoi dati di nascita servono a calcolare e a scrivere, e a nient'altro. Nessun identificatore pubblicitario, nessuna analisi di terze parti, nessun tracciamento tra app. Da account puoi esportare tutto o cancellare l'account per intero, dalle Impostazioni: una cancellazione vera, non una disattivazione.

Condizioni d'uso: https://alma.pazl.ai/terms
Informativa privacy: https://alma.pazl.ai/privacy
Condizioni di abbonamento: https://alma.pazl.ai/subscription-terms
```

<!-- field: it.play.short | limit: 80 -->
```
Otto sistemi su un tema. Effemeridi vere. Ogni frase cita la sua fonte.
```

<!-- field: it.play.full | limit: 4000 -->
```
Alma calcola otto sistemi di lettura dai tuoi dati di nascita e scrive l'interpretazione a partire da quello che ha calcolato.

COSA CALCOLA
Un tema natale completo — dieci pianeti, dodici case Placidus, gli aspetti, gli angoli — dalle effemeridi planetarie DE440s della NASA JPL. Numerologia dalla tua data e dal tuo nome completo di nascita. La tua carta di nascita dei tarocchi. I transiti attuali sulle tue posizioni natali. La tua rivoluzione solare. Affinità con un secondo tema che inserisci tu, in quattro pesi separati invece che in una sola percentuale. Linee di astrocartografia su una mappa del mondo. E una sintesi incrociata che mette tre di quei sistemi — tema natale, numerologia, carta di nascita — uno accanto all'altro su nove assi e conta dove concordano e dove si contraddicono.

Il fuso orario storico del tuo luogo di nascita si risolve da un elenco di località offline, così nessun servizio di geocodifica viene mai a sapere dove sei nato. I cambi d'ora e le latitudini polari sono trattati davvero, non approssimati: dove un tema non si può proprio calcolare, l'app lo dice invece di inventarlo.

COSA È GRATIS
Gratis, per sempre e senza account: Sole, Luna e Ascendente, la fase lunare, l'equilibrio degli elementi; i numeri di percorso di vita, compleanno e destino; la carta di nascita; ogni transito in corso, col giorno in cui è esatto e la posizione natale contro cui viene letto; la rivoluzione solare e il suo governatore; i quattro pesi dell'affinità; e tutti e nove gli assi della sintesi incrociata, con ciò che ogni sistema ha letto e chi concorda. Anche un capitolo scritto per ognuno degli otto sistemi è gratis, ed è completo, non un assaggio.

COSA SI COMPRA
L'interpretazione scritta dei capitoli restanti — in tutto sono quarantuno — e la profondità dietro ogni sistema: le dodici case e gli aspetti, i pinnacoli e i cicli, le linee della mappa. Un sistema con tutti i suoi capitoli è un acquisto singolo e resta tuo; tutti e quarantuno insieme sono un acquisto singolo. Un abbonamento copre i tre sistemi che si muovono — transiti, rivoluzione solare, affinità — mentre si muovono, più una quota mensile di domande; non è il modo di sbloccare l'app.

Non c'è prova gratuita né offerta di lancio. Niente si trasforma in un addebito. Google Play incassa, e un abbonamento si disdice nel tuo account Google Play — l'app ti porta dritto lì. Aggiungi un'email nelle Impostazioni e Alma ti scrive tre giorni prima, con la data e l'importo.

OGNI FRASE NOMINA LA SUA FONTE
Ogni paragrafo scritto porta la posizione esatta da cui è stato letto — «Saturno sul tuo Discendente a 19° dei Pesci», non «le tue relazioni». Un paragrafo che cita una posizione che il tuo tema non ha viene respinto e riscritto prima di arrivarti, e così uno che non cita niente. Quel controllo è codice, e gira su ogni capitolo.

NON PREDICE
Alma descrive di cosa sei fatto, non cosa succederà. Nessuna previsione di eventi, nessun linguaggio di destino, nessun consiglio medico, psicologico, legale o finanziario. Quando la domanda è una decisione, dice che la decisione è tua.

CHIEDI CON LE TUE PAROLE
Chiedi del tuo tema e la risposta nomina la posizione da cui ha letto. Tre domande al giorno sono gratis, sempre.

SE NON SAI LA TUA ORA DI NASCITA
Tutto ciò che non ne ha bisogno funziona lo stesso: sole, pianeti per segno, numerologia, la tua carta di nascita, quasi tutti i transiti. Case, rivoluzione solare e mappa restano segnate come non disponibili invece di essere riempite con un mezzogiorno inventato.

I TUOI DATI
I tuoi dati di nascita servono a calcolare e a scrivere, e a nient'altro. Nessun identificatore pubblicitario, nessuna analisi di terze parti, nessun tracciamento tra app. Da account puoi esportare tutto o cancellare l'account per intero, dalle Impostazioni: una cancellazione vera, non una disattivazione.

Informativa privacy: https://alma.pazl.ai/privacy
Condizioni d'uso: https://alma.pazl.ai/terms
```

---

# 5. Français (fr)

<!-- field: fr.apple.name | limit: 30 -->
```
Alma: Thème natal & 8 systèmes
```

The French space before a colon is dropped here for length; it costs a character the field does
not have, and the store renders the name as a label rather than as running prose. It is kept
everywhere in the description, where there is room.

<!-- field: fr.apple.subtitle | limit: 30 -->
```
Calculé, jamais deviné
```

The only subtitle that does not mirror the other five. Every French phrasing of *"real
ephemeris, no predictions"* ran to 32–33 characters, and the versions that fit — *sans magie*,
*zéro voyance* — were either flippant or read as an apology. *Calculé, jamais deviné* is the
same claim from the other side, it is the exact promise `validator.py` enforces, and at 22
characters it leaves the name to say what the app is.

<!-- field: fr.apple.promotional | limit: 170 -->
```
Huit systèmes lisent les mêmes données de naissance et se contredisent ouvertement. Positions issues des éphémérides DE440s de la NASA JPL. Chaque phrase cite la sienne.
```

<!-- field: fr.apple.keywords | limit: 100 bytes -->
```
astrologie,horoscope,numerologie,tarot,transits,synastrie,zodiaque,maisons,revolution,solaire
```

<!-- field: fr.apple.description | limit: 4000 -->
```
Huit systèmes indépendants lisent les mêmes données de naissance, et Alma te montre où ils se contredisent.

Les positions viennent des éphémérides planétaires DE440s de la NASA JPL — de vraies données orbitales, pas une table de correspondance. Maisons Placidus, zodiaque tropical, fuseau horaire historique du lieu de naissance résolu hors ligne, changements d'heure compris.

LES HUIT
Thème natal, 16 chapitres. Numérologie, 5. Carte de naissance, 3. Transits, 3. Révolution solaire, 3. Compatibilité, 4, face à un second thème que tu ajoutes. Astrocartographie, 3. Synthèse croisée, 4. Quarante et un chapitres en tout.

LÀ OÙ ILS SE CONTREDISENT
La synthèse croisée, aucune tradition seule ne peut la faire. Trois des systèmes — le thème natal, la numérologie et la carte de naissance — répondent aux mêmes neuf questions, chacun de son côté : direction, caractère, esprit, relations, ressources, travail, point faible, croissance, rythmes. Là où les trois s'accordent, cela va dans ton noyau. Là où deux se contredisent, tu regardes un conflit que tu continues de vivre, pas une mauvaise lecture. Les deux sont montrés. Rien n'est lissé en consensus.

CHAQUE PHRASE NOMME SA SOURCE
Chaque paragraphe porte la position exacte dont il a été tiré : « Saturne sur ton Descendant à 19° des Poissons », pas « tes relations ». Un paragraphe qui cite une position absente de ton thème est rejeté et réécrit avant que tu le voies, et celui qui ne cite rien aussi. C'est du code, et cela tourne sur chaque chapitre.

ELLE NE PRÉDIT PAS
Alma décrit de quoi tu es fait, pas ce qui va arriver. Aucune prédiction d'événement, aucun langage de destin, aucun conseil médical, psychologique, juridique ou financier. Face à une décision, elle dit qu'elle t'appartient.

Sans heure de naissance, maisons, révolution solaire et carte restent marquées indisponibles plutôt que remplies d'un midi supposé.

GRATUIT, ET PAYANT
Gratuit, définitif, sans compte : ton Soleil, ta Lune et ton Ascendant, la phase lunaire, l'équilibre des éléments ; les nombres de chemin de vie, du jour et d'expression ; ta carte de naissance ; chaque transit en cours, avec le jour où il est exact et la position natale contre laquelle il est lu ; ta révolution solaire et son maître ; les quatre poids de compatibilité ; et les neuf axes de la synthèse croisée, avec ce que chaque système a lu et qui s'accorde. Un chapitre écrit dans chacun des huit systèmes est gratuit lui aussi, et il est complet, pas un avant-goût.

Ce qui s'achète, c'est l'écrit, et la profondeur derrière chaque système : les douze maisons et les aspects, les pinacles et les cycles, les lignes de la carte. Un système avec tous ses chapitres est un achat unique, gardé à vie. Les quarante et un chapitres ensemble sont un achat unique. Un abonnement couvre les trois systèmes qui bougent — transits, révolution solaire, compatibilité — au fil de leur course, plus un quota mensuel de questions ; ce n'est pas la façon de déverrouiller l'app.

Pas d'essai gratuit et pas de prix de lancement. Rien ne se transforme en prélèvement. Un paiement unique reste unique. Apple encaisse ; un abonnement se gère et se résilie dans les réglages de ton identifiant Apple. La date du prochain renouvellement est dans les Réglages d'Alma : ajoutes-y un e-mail et Alma t'écrit trois jours avant, avec la date et le montant.

DEMANDE AVEC TES MOTS
Alma répond aux questions sur ton thème et nomme la position dont vient la réponse. Trois par jour sont gratuites, toujours.

TES DONNÉES
Tes données de naissance servent à calculer et à écrire, et à rien d'autre. Pas d'identifiant publicitaire, pas d'analyse tierce, pas de suivi entre apps. Une fois connecté, tu peux tout exporter ou supprimer le compte entier depuis les Réglages — une vraie suppression, pas une désactivation.

Conditions d'utilisation : https://alma.pazl.ai/terms
Politique de confidentialité : https://alma.pazl.ai/privacy
Conditions d'abonnement : https://alma.pazl.ai/subscription-terms
```

<!-- field: fr.play.short | limit: 80 -->
```
Huit systèmes, un thème. Vraies éphémérides. Chaque phrase cite sa source.
```

<!-- field: fr.play.full | limit: 4000 -->
```
Alma calcule huit systèmes de lecture à partir de tes données de naissance, puis écrit l'interprétation de ce qu'elle a calculé.

CE QU'ELLE CALCULE
Un thème natal complet — dix planètes, douze maisons Placidus, les aspects, les angles — à partir des éphémérides planétaires DE440s de la NASA JPL. La numérologie depuis ta date et ton nom complet de naissance. Ta carte de naissance du tarot. Les transits actuels sur tes positions natales. Ta révolution solaire. La compatibilité avec un second thème, en quatre poids distincts plutôt qu'un pourcentage. Les lignes d'astrocartographie sur une carte du monde. Et une synthèse croisée qui met trois d'entre eux — thème natal, numérologie, carte de naissance — sur neuf axes et compte où ils s'accordent et où ils se contredisent.

Le fuseau horaire historique de ton lieu de naissance est résolu depuis un répertoire hors ligne : aucun service de géocodage n'apprend où tu es né. Changements d'heure et latitudes polaires sont traités, non approximés ; là où un thème ne peut pas être dressé, l'app le dit au lieu de l'inventer.

CE QUI EST GRATUIT
Gratuit, définitif, sans compte : ton Soleil, ta Lune et ton Ascendant, la phase lunaire, l'équilibre des éléments ; les nombres de chemin de vie, du jour et d'expression ; ta carte de naissance ; chaque transit en cours, avec le jour où il est exact et la position natale contre laquelle il est lu ; ta révolution solaire et son maître ; les quatre poids de compatibilité ; et les neuf axes de la synthèse croisée, avec ce que chaque système a lu et qui s'accorde. Un chapitre écrit dans chacun des huit systèmes est gratuit lui aussi, et il est complet, pas un avant-goût.

CE QUI S'ACHÈTE
L'interprétation écrite des chapitres restants — quarante et un en tout — et la profondeur derrière chaque système : les douze maisons et les aspects, les pinacles et les cycles, les lignes de la carte. Un système avec tous ses chapitres est un achat unique, gardé à vie ; les quarante et un ensemble sont un achat unique. Un abonnement couvre les trois systèmes qui bougent — transits, révolution solaire, compatibilité — au fil de leur course, plus un quota mensuel de questions ; ce n'est pas la façon de déverrouiller l'app.

Il n'y a pas d'essai gratuit ni d'offre de lancement. Rien ne se transforme en prélèvement. Google Play encaisse ; un abonnement se résilie dans ton compte Google Play, où l'app t'emmène directement. Ajoute un e-mail dans les Réglages et Alma t'écrit trois jours avant, avec la date et le montant.

CHAQUE PHRASE NOMME SA SOURCE
Chaque paragraphe écrit porte la position exacte dont il a été tiré — « Saturne sur ton Descendant à 19° des Poissons », pas « tes relations ». Un paragraphe qui cite une position absente de ton thème est rejeté et réécrit avant de t'atteindre, et celui qui ne cite rien aussi. C'est du code, et cela tourne sur chaque chapitre.

ELLE NE PRÉDIT PAS
Alma décrit de quoi tu es fait, pas ce qui va arriver. Aucune prédiction d'événement, aucun langage de destin, aucun conseil médical, psychologique, juridique ou financier. Face à une décision, elle dit qu'elle t'appartient.

DEMANDE AVEC TES MOTS
Pose une question sur ton thème : la réponse nomme la position dont elle vient. Trois questions par jour sont gratuites, toujours.

SI TU NE CONNAIS PAS TON HEURE DE NAISSANCE
Tout ce qui n'en a pas besoin fonctionne quand même : soleil, planètes par signe, numérologie, carte de naissance, la plupart des transits. Maisons, révolution solaire et carte restent marquées indisponibles plutôt que remplies d'un midi supposé.

TES DONNÉES
Tes données de naissance servent à calculer et à écrire, et à rien d'autre. Pas d'identifiant publicitaire, pas d'analyse tierce, pas de suivi entre apps. Une fois connecté, tu peux tout exporter ou supprimer le compte entier depuis les Réglages — une vraie suppression, pas une désactivation.

Politique de confidentialité : https://alma.pazl.ai/privacy
Conditions d'utilisation : https://alma.pazl.ai/terms
```

---

# 6. Português do Brasil (pt-BR)

<!-- field: pt-BR.apple.name | limit: 30 -->
```
Alma: Mapa Natal e 8 Sistemas
```

<!-- field: pt-BR.apple.subtitle | limit: 30 -->
```
Efemérides reais, sem palpite
```

<!-- field: pt-BR.apple.promotional | limit: 170 -->
```
Oito sistemas leem os mesmos dados de nascimento e discordam à vista. As posições vêm das efemérides DE440s da NASA JPL. Cada frase nomeia a posição de onde saiu.
```

<!-- field: pt-BR.apple.keywords | limit: 100 bytes -->
```
astrologia,horoscopo,numerologia,taro,transitos,sinastria,zodiaco,casas,revolucao,solar
```

<!-- field: pt-BR.apple.description | limit: 4000 -->
```
Oito sistemas independentes leem os mesmos dados de nascimento, e a Alma mostra onde eles discordam.

As posições são calculadas com as efemérides planetárias DE440s da NASA JPL — dados orbitais de verdade, não uma tabela de consulta. Casas Placidus, zodíaco tropical e o fuso horário histórico do seu lugar de nascimento resolvido offline, com mudanças de horário e latitudes polares incluídas.

OS OITO
Mapa natal, 16 capítulos. Numerologia, 5. Carta de nascimento, 3. Trânsitos, 3. Revolução solar, 3. Compatibilidade, 4, contra um segundo mapa que você adiciona. Astrocartografia, 3. Síntese cruzada, 4. Quarenta e um capítulos no total.

ONDE ELES DISCORDAM
A síntese cruzada é a parte que nenhuma tradição sozinha consegue fazer. Três dos sistemas — o mapa natal, a numerologia e a carta de nascimento — respondem às mesmas nove perguntas de forma independente: direção, caráter, mente, relações, recursos, trabalho, ponto fraco, crescimento, ritmos. Onde os três concordam, aquilo vai para o seu núcleo. Onde dois se contradizem, você está olhando para um conflito que continua vivendo, não para uma leitura ruim. Os dois aparecem. Nada é suavizado até virar consenso.

CADA FRASE NOMEIA SUA FONTE
Cada parágrafo carrega a posição exata de onde foi lido: "Saturno no seu Descendente a 19° de Peixes", não "suas relações". Um parágrafo que cite uma posição que o seu mapa não tem é recusado e reescrito antes de você ver, e o mesmo vale para um parágrafo que não cite nada. Essa checagem é código, e ela roda em todo capítulo.

ELA NÃO PREVÊ
A Alma descreve do que você é feito, não o que vai acontecer. Sem previsão de eventos, sem linguagem de destino, sem conselho médico, psicológico, jurídico ou financeiro. Quando a pergunta é uma decisão, ela diz que a decisão é sua.

Se você não sabe sua hora de nascimento, tudo que não precisa dela continua funcionando. Casas, revolução solar e o mapa ficam marcados como indisponíveis em vez de serem preenchidos com um meio-dia chutado.

DE GRAÇA, E PAGO
De graça, para sempre e sem conta: seu signo solar, o lunar e o ascendente, a fase da lua, o equilíbrio dos elementos; os números de caminho de vida, do dia e de destino; sua carta de nascimento; cada trânsito em curso, com o dia exato e a posição natal contra a qual ele é lido; sua revolução solar e o regente dela; os quatro pesos de compatibilidade; e os nove eixos da síntese cruzada, com o que cada sistema leu e quem concorda. Um capítulo escrito em cada um dos oito sistemas também é de graça, e é completo, não uma amostra.

O que se compra é o texto, e a profundidade por trás de cada sistema: as doze casas e os aspectos, os pináculos e os ciclos, as linhas do mapa-múndi. Um sistema com todos os capítulos dele é uma compra única e fica com você para sempre. Os quarenta e um capítulos juntos são uma compra única. Uma assinatura cobre os três sistemas que de fato se movem — trânsitos, revolução solar, compatibilidade — conforme se movem, mais uma cota mensal de perguntas; ela não é o jeito de desbloquear o app.

Sem teste grátis e sem preço de lançamento. Nada vira cobrança. Uma vez é uma vez. A Apple cobra, e uma assinatura é gerenciada e cancelada nos ajustes do seu ID Apple. A data da próxima renovação está nos Ajustes da Alma; adicione um e-mail lá e a Alma escreve três dias antes, com a data e o valor.

PERGUNTE COM AS SUAS PALAVRAS
A Alma responde perguntas sobre o seu próprio mapa e nomeia a posição de onde leu. Três por dia são de graça, sempre.

SEUS DADOS
Seus dados de nascimento servem para calcular e para escrever, e para mais nada. Sem identificador de publicidade, sem análise de terceiros, sem rastreamento entre apps. Com a conta conectada você pode exportar tudo ou apagar a conta inteira, nos Ajustes: um apagamento de verdade, não uma desativação.

Termos de uso: https://alma.pazl.ai/terms
Política de privacidade: https://alma.pazl.ai/privacy
Termos de assinatura: https://alma.pazl.ai/subscription-terms
```

<!-- field: pt-BR.play.short | limit: 80 -->
```
Oito sistemas num mapa. Efemérides reais. Cada frase cita a fonte dela.
```

<!-- field: pt-BR.play.full | limit: 4000 -->
```
A Alma calcula oito sistemas de leitura a partir dos seus dados de nascimento e escreve a interpretação a partir do que calculou.

O QUE ELA CALCULA
Um mapa natal completo — dez planetas, doze casas Placidus, os aspectos, os ângulos — com as efemérides planetárias DE440s da NASA JPL. Numerologia a partir da sua data e do seu nome completo de nascimento. Sua carta de nascimento do tarô. Os trânsitos atuais sobre as suas posições natais. Sua revolução solar. Compatibilidade com um segundo mapa que você digita, em quatro pesos separados e não em uma única porcentagem. Linhas de astrocartografia sobre um mapa-múndi. E uma síntese cruzada que põe três desses sistemas — mapa natal, numerologia, carta de nascimento — lado a lado em nove eixos e conta onde concordam e onde se contradizem.

O fuso horário histórico do seu lugar de nascimento é resolvido a partir de uma lista de localidades offline, então nenhum serviço de geocodificação chega a saber onde você nasceu. Mudanças de horário e latitudes polares são tratadas, não aproximadas: onde um mapa realmente não pode ser levantado, o app diz isso em vez de inventar.

O QUE É DE GRAÇA
De graça, para sempre e sem conta: seu signo solar, o lunar e o ascendente, a fase da lua, o equilíbrio dos elementos; os números de caminho de vida, do dia e de destino; sua carta de nascimento; cada trânsito em curso, com o dia exato e a posição natal contra a qual ele é lido; sua revolução solar e o regente dela; os quatro pesos de compatibilidade; e os nove eixos da síntese cruzada, com o que cada sistema leu e quem concorda. Um capítulo escrito em cada um dos oito sistemas também é de graça, e é completo, não uma amostra.

O QUE É COMPRADO
A interpretação escrita dos capítulos restantes — no total são quarenta e um — e a profundidade por trás de cada sistema: as doze casas e os aspectos, os pináculos e os ciclos, as linhas do mapa-múndi. Um sistema com todos os capítulos dele é uma compra única e fica com você; os quarenta e um juntos são uma compra única. Uma assinatura cobre os três sistemas que se movem — trânsitos, revolução solar, compatibilidade — conforme se movem, mais uma cota mensal de perguntas; ela não é o jeito de desbloquear o app.

Não existe teste grátis nem oferta de lançamento. Nada vira cobrança. O Google Play cobra, e uma assinatura é cancelada na sua conta do Google Play, para onde o app leva você direto. Adicione um e-mail nos Ajustes e a Alma escreve três dias antes, com a data e o valor.

CADA FRASE NOMEIA SUA FONTE
Cada parágrafo escrito carrega a posição exata de onde foi lido — "Saturno no seu Descendente a 19° de Peixes", não "suas relações". Um parágrafo que cite uma posição que o seu mapa não tem é recusado e reescrito antes de chegar até você, e um que não cite nada também. Essa checagem é código, e ela roda em todo capítulo.

ELA NÃO PREVÊ
A Alma descreve do que você é feito, não o que vai acontecer. Sem previsão de eventos, sem linguagem de destino, sem conselho médico, psicológico, jurídico ou financeiro. Quando a pergunta é uma decisão, ela diz que a decisão é sua.

PERGUNTE COM AS SUAS PALAVRAS
Pergunte sobre o seu próprio mapa e a resposta nomeia a posição de onde saiu. Três perguntas por dia são de graça, sempre.

SE VOCÊ NÃO SABE SUA HORA DE NASCIMENTO
Tudo que não precisa dela continua funcionando: sol, planetas por signo, numerologia, sua carta de nascimento, quase todos os trânsitos. Casas, revolução solar e o mapa ficam marcados como indisponíveis em vez de serem preenchidos com um meio-dia chutado.

SEUS DADOS
Seus dados de nascimento servem para calcular e para escrever, e para mais nada. Sem identificador de publicidade, sem análise de terceiros, sem rastreamento entre apps. Com a conta conectada você pode exportar tudo ou apagar a conta inteira, nos Ajustes: um apagamento de verdade, não uma desativação.

Política de privacidade: https://alma.pazl.ai/privacy
Termos de uso: https://alma.pazl.ai/terms
```

---

# 7. Fields this file does not cover

| Field | Why not here |
|---|---|
| **What's New in This Version** (Apple, 4000, required from v2) | There is no v2. Write it at the second submission, in six languages. |
| **In-app purchase display name (35) and description (55)** | Twelve products × six locales, and 35 characters in German is the tightest field in the whole submission. It belongs with the product setup, not the listing. `STORE-REQUIREMENTS.md` §5. |
| **Promoted in-app purchase art** | Only if we promote a product on the product page. Not planned for launch. |
| **Feature graphic copy** (Play, 1024 × 500) | Design deliverable; the words on it should come from the subtitle of the matching locale. See `SCREENSHOTS.md`. |
| **Apple Search Ads creative** | Not a submission requirement. |
| **Category** | Apple: Lifestyle primary. Reference secondary is arguable given the ephemeris and would keep "astrology" out of the keyword-exclusion set — the owner's call, and it changes nothing in this file. |

---

# 8. Verifying the lengths, and the three claims that already drifted once

`python3 mobile/store/check-listing.py`. The script lives beside this file rather than inside
it — a copy pasted into prose is a copy that goes stale, and this one did. It parses every
`<!-- field: … | limit: … -->` marker and the fenced block after it, counts characters (or
bytes, where the marker says `bytes`), and exits non-zero on any overrun. A field silently
truncated at 30 characters is how a German app name ends up reading `Alma: Horoskop & 8 Syste`.

It now also fails on four content patterns, each of which was live in this file at some point:

| Guard | Why |
|---|---|
| `eight` / `ocho` / `acht` / `otto` / `huit` / `oito` within ten words of `axes` / `ejes` / `Achsen` / `assi` / `eixos` | The cross-synthesis compares **three** systems (`engine/synthesis.py:355–360`). All twelve descriptions claimed eight. Word-bounded, because *weights* contains "eight" and *gemacht* contains "acht" |
| Any currency figure | Apple 2.3.7, and thirteen currencies going stale |
| The other store's name in a body | Apple 2.3.10 and its Play mirror |
| An entertainment disclaimer, in any of the six languages | Apple 1.1.6 — it buys nothing and concedes the 4.3(b) argument |

Current state: **42 fields checked, 0 over limit, 0 content failures.** Run it before anything
is pasted into a console, and wire it into whatever runs before a commit.

What the script cannot check, and a person must:

- that the free-tier list in the copy still matches `PREVIEW_FIELDS` in
  `backend/alma/api/routers/systems.py:47–78`, key for key;
- that all seven URLs resolve and return 200 (see the box in *URLs used in the copy*);
- that the deletion sentence still matches what a **guest** can actually do.
