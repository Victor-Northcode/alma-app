"""Outbound email — three messages, sent well.

Alma sends a sign-in link, a receipt for a purchase, and a warning three days
before a subscription is charged. Nothing else, and that is deliberate. A
product that emails people about their horoscope every morning is a product
people mute, and a muted sender is a sign-in link that lands in spam when it
finally matters.

None of the three is marketing and none of them carries an unsubscribe. Two of
them are about money that has left, or is about to leave, somebody's account,
and an unsubscribe on either would turn a promise back into the trick it was
made against.

The receipt is the newest and the only one that is a legal instrument rather
than a courtesy — see the block comment above `Receipt`. It is also why these
three now share a shape: one banner, one lede, one gold-bordered action, one
line of fine print saying why the letter exists. A fourth message that looks
like none of the others is a maintenance trap, and the way that happens is one
message at a time.

Delivery is best-effort and never blocks a request. If the provider is not
configured or is having a bad day, the caller finds out via the return value
and decides what to tell the user — which in development means showing the
link on screen rather than pretending an email is in flight.
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from .config import settings

log = logging.getLogger("alma.mail")

RESEND_ENDPOINT = "https://api.resend.com/emails"

SUBJECTS = {
    "en": "Your Alma sign-in link",
    "es": "Tu enlace de acceso a Alma",
    "de": "Dein Alma-Anmeldelink",
    "it": "Il tuo link di accesso ad Alma",
    "fr": "Votre lien de connexion Alma",
    "pt-BR": "Seu link de acesso ao Alma",
    "ru": "Твоя ссылка для входа в Alma",
}

BODIES = {
    "en": ("Open Alma", "This link works once and expires in {minutes} minutes.",
           "If you did not ask for this, nothing happens — ignore it."),
    "es": ("Abrir Alma", "Este enlace funciona una vez y caduca en {minutes} minutos.",
           "Si no lo has pedido, no ocurre nada — puedes ignorarlo."),
    "de": ("Alma öffnen", "Dieser Link funktioniert einmal und läuft in {minutes} Minuten ab.",
           "Falls du das nicht warst, passiert nichts — ignoriere die Nachricht."),
    "it": ("Apri Alma", "Questo link funziona una volta e scade tra {minutes} minuti.",
           "Se non sei stato tu, non succede nulla — puoi ignorarlo."),
    # `tu`, like the rest of the French product. These three messages were the
    # only French Alma writes in `vous`, so the brand switched register exactly
    # when it started talking about sign-ins, money and rights — which reads as
    # a lawyer taking the voice over.
    "fr": ("Ouvrir Alma", "Ce lien fonctionne une fois et expire dans {minutes} minutes.",
           "Si ce n'est pas toi qui l'as demandé, rien ne se passe."),
    "pt-BR": ("Abrir o Alma", "Este link funciona uma vez e expira em {minutes} minutos.",
              "Se não foi você, nada acontece — pode ignorar."),
    # «ты», like the rest of the Russian product — and «Если это не ты» keeps
    # the reassurance impersonal rather than «если вы не запрашивали».
    "ru": ("Открыть Alma", "Ссылка сработает один раз и истечёт через {minutes} минут.",
           "Если это не ты — ничего не произойдёт, просто пропусти письмо."),
}


def _html(url: str, locale: str, minutes: int) -> str:
    action, note, ignore = BODIES.get(locale, BODIES["en"])
    return f"""\
<div style="background:#0A0D1C;color:#F1E9D6;font-family:Georgia,serif;padding:48px 24px">
  <div style="max-width:480px;margin:0 auto">
    <div style="font-size:22px;letter-spacing:.18em;color:#C9AE6B">ALMA</div>
    <p style="font-size:17px;line-height:1.6;margin:28px 0 32px">{note.format(minutes=minutes)}</p>
    <a href="{url}" style="display:inline-block;padding:14px 28px;border:1px solid #C9AE6B;
       color:#E4D3A2;text-decoration:none;letter-spacing:.06em">{action}</a>
    <p style="font-size:13px;line-height:1.6;color:#8b8578;margin-top:32px">{ignore}</p>
  </div>
</div>"""


async def _post(payload: dict) -> bool:
    """Hand one message to the provider. Returns whether it took it.

    The three senders had a byte-identical copy of this between them, which is
    the shape in which a timeout handler gets fixed in one place and left broken
    in the other two. What is deliberately *not* in here is the decision about
    an unconfigured provider: that is different for each message — a sign-in
    link is printed to the log so development still works, and a receipt that
    was never sent is a legal fact somebody has to be told about — so each
    sender answers it in its own words before calling this.
    """
    key = settings().resend_api_key
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                RESEND_ENDPOINT, json=payload, headers={"Authorization": f"Bearer {key}"}
            )
    except httpx.HTTPError as exc:
        # Nothing here may raise into a caller: a sign-in must not 500 because a
        # mail provider timed out, and a webhook must not fail — and be retried
        # into a second grant — because a receipt did not go out.
        log.error("mail provider unreachable: %s", exc)
        return False

    if response.status_code >= 400:
        log.error("mail provider refused: %s %s", response.status_code, response.text[:300])
        return False
    return True


async def send_magic_link(*, to: str, token: str, locale: str = "en") -> bool:
    """Send the sign-in link. Returns whether it actually went out."""
    config = settings()
    url = f"{config.web_url}/sign-in?token={token}"

    if not config.resend_api_key:
        # Not an error in development; the caller surfaces the link instead.
        log.info("mail not configured — sign-in link for %s: %s", to, url)
        return False

    return await _post({
        "from": config.mail_from,
        "to": [to],
        "subject": SUBJECTS.get(locale, SUBJECTS["en"]),
        "html": _html(url, locale, config.magic_link_minutes),
    })


# ── the notice before a renewal ────────────────────────────────────────────

RENEWAL_SUBJECTS = {
    "en": "Alma renews on {date}",
    "es": "Alma se renueva el {date}",
    "de": "Alma verlängert sich am {date}",
    "it": "Alma si rinnova il {date}",
    "fr": "Alma se renouvelle le {date}",
    "pt-BR": "O Alma renova em {date}",
    "ru": "Alma продлевается {date}",
}

#: (what is about to happen, what to do about it, the button)
RENEWAL_BODIES = {
    "en": (
        "Your Alma plan renews on {date} and {amount} will be charged to the card you used.",
        "Nothing is needed if you want to keep it. If you would rather not, cancel "
        "before that date and the plan runs to the end of the period you have paid for.",
        "Manage your plan",
    ),
    "es": (
        "Tu plan de Alma se renueva el {date} y se cobrarán {amount} a tu tarjeta.",
        "No hace falta hacer nada si quieres seguir. Si prefieres no continuar, "
        "cancela antes de esa fecha y el plan durará hasta el final del periodo pagado.",
        "Gestionar mi plan",
    ),
    "de": (
        "Dein Alma-Abo verlängert sich am {date}, und {amount} werden abgebucht.",
        "Wenn du bleiben möchtest, musst du nichts tun. Andernfalls kündige vorher — "
        "das Abo läuft dann bis zum Ende des bezahlten Zeitraums.",
        "Abo verwalten",
    ),
    "it": (
        "Il tuo piano Alma si rinnova il {date} e verranno addebitati {amount}.",
        "Non serve fare nulla se vuoi continuare. Altrimenti disdici prima di quella "
        "data: il piano resta attivo fino alla fine del periodo già pagato.",
        "Gestisci il piano",
    ),
    "fr": (
        "Ton abonnement Alma se renouvelle le {date} et {amount} seront débités.",
        "Rien à faire si tu souhaites le garder. Sinon, résilie avant cette date : "
        "l'abonnement court jusqu'à la fin de la période déjà payée.",
        "Gérer mon abonnement",
    ),
    "pt-BR": (
        "Seu plano Alma renova em {date} e {amount} serão cobrados no seu cartão.",
        "Não é preciso fazer nada se quiser continuar. Caso contrário, cancele antes "
        "dessa data e o plano vai até o fim do período já pago.",
        "Gerenciar meu plano",
    ),
    "ru": (
        "Твой план Alma продлевается {date}, и с твоей карты спишется {amount}.",
        "Если хочешь остаться — ничего делать не нужно. Если нет, отмени до этой "
        "даты: план действует до конца уже оплаченного периода.",
        "Управлять планом",
    ),
}

#: Why this letter exists, said in the letter. Not a legal footer and not an
#: unsubscribe: it is the reason somebody is reading an email they did not ask
#: for, and leaving it out is how a promise reads as spam.
RENEWAL_REASON = {
    "en": "We send this before every renewal. There is nothing to unsubscribe from — "
          "a subscription you have forgotten about is not a business we want to be in.",
    "es": "Enviamos este aviso antes de cada renovación. No hay nada de lo que darse "
          "de baja: no queremos vivir de suscripciones olvidadas.",
    "de": "Diese Nachricht kommt vor jeder Verlängerung. Es gibt nichts abzubestellen — "
          "von vergessenen Abos wollen wir nicht leben.",
    "it": "Inviamo questo avviso prima di ogni rinnovo. Non c'è nulla da disdire: non "
          "vogliamo vivere di abbonamenti dimenticati.",
    "fr": "Nous envoyons ce message avant chaque renouvellement. Il n'y a rien à "
          "désabonner : vivre d'abonnements oubliés ne nous intéresse pas.",
    "pt-BR": "Enviamos este aviso antes de cada renovação. Não há nada para cancelar "
             "aqui — não queremos viver de assinaturas esquecidas.",
}


def _renewal_html(*, date: str, amount: str, url: str, locale: str) -> str:
    happening, choice, action = RENEWAL_BODIES.get(locale, RENEWAL_BODIES["en"])
    reason = RENEWAL_REASON.get(locale, RENEWAL_REASON["en"])
    return f"""\
<div style="background:#0A0D1C;color:#F1E9D6;font-family:Georgia,serif;padding:48px 24px">
  <div style="max-width:480px;margin:0 auto">
    <div style="font-size:22px;letter-spacing:.18em;color:#C9AE6B">ALMA</div>
    <p style="font-size:17px;line-height:1.6;margin:28px 0 16px">
      {happening.format(date=date, amount=amount)}</p>
    <p style="font-size:15px;line-height:1.6;margin:0 0 32px;color:#c8bfa8">{choice}</p>
    <a href="{url}" style="display:inline-block;padding:14px 28px;border:1px solid #C9AE6B;
       color:#E4D3A2;text-decoration:none;letter-spacing:.06em">{action}</a>
    <p style="font-size:13px;line-height:1.6;color:#8b8578;margin-top:32px">{reason}</p>
  </div>
</div>"""


async def send_renewal_notice(notice) -> bool:
    """Warn one person that their plan is about to be charged.

    Takes a `billing.renewals.Notice` rather than an `Entitlement` and a `User`,
    so that what goes in the envelope is decided by the caller and this function
    only puts it in one — which is what makes the decision testable without a
    mail provider.

    The amount is formatted by the catalogue's own `format_price`, because a
    Brazilian shown "R$78.99" is being shown something that is not a price, and
    the number in this email is the number that will appear on a statement.

    Returns whether it went out, and the caller records nothing when it did not:
    a notice marked sent and never delivered is somebody charged with no warning,
    which is precisely the outcome this exists to prevent.
    """
    from .billing.catalogue import format_price

    config = settings()
    url = f"{config.web_url}{RECEIPT_PLAN_PATH}"
    locale = notice.locale if notice.locale in RENEWAL_SUBJECTS else "en"
    when = written_date(notice.renews_at, locale)
    amount = format_price(notice.amount_cents, notice.currency)

    if not config.resend_api_key:
        log.info(
            "mail not configured — %s renews %s for %s (no notice sent)",
            notice.email, when, amount,
        )
        return False

    return await _post({
        "from": config.mail_from,
        "to": [notice.email],
        "subject": RENEWAL_SUBJECTS[locale].format(date=when),
        "html": _renewal_html(date=when, amount=amount, url=url, locale=locale),
    })


# ── the receipt, which is the third leg of a lawful waiver ─────────────────
#
# **This letter is not a courtesy.** The Consumer Rights Directive lets a buyer
# lose the 14-day right of withdrawal on digital content only when three things
# have happened (Art. 16(m)): they gave prior express consent, they acknowledged
# that the right is lost, and the trader confirmed the contract **on a durable
# medium** (Art. 8(7)). Two checkboxes at a checkout are two of the three. Ship
# the ladder without this email and the waiver is void in four of our six
# locales and in the UK — which means a buyer can read the whole archive and
# still withdraw, and be right.
#
# So the content of this letter is decided by law rather than by taste. It has
# to carry, in the buyer's own language: what was bought, what was paid
# including tax, when, who legally sold it, the consent they gave at the
# checkout, and how to cancel or ask for the money back.
#
# Two more rules are baked into the copy rather than into the code:
#
# * **A year is not a reading.** Art. 16(a) does not extinguish withdrawal on a
#   twelve-month plan until the service has been fully performed, so a plan
#   cannot hide behind the same waiver as a chapter that was written and
#   delivered in one second. Somebody who withdraws from the annual on day ten
#   is owed a pro-rata refund under Art. 14(3), and the letter says so out loud
#   rather than leaving them to discover a right we were hoping they would not
#   use.
# * **The seller is not us.** The processor is the merchant of record; it takes
#   the payment, issues the tax invoice and holds the money. This is our
#   confirmation of the contract, not the invoice, and saying otherwise would
#   put a wrong seller in front of the card issuer who reads it in a dispute.
#   The name is passed in rather than written here, for the same reason
#   `/billing/catalogue` publishes it: which processor is running is a
#   configuration decision.

#: Where a person cancels, and where the refunds policy lives. Both are pages we
#: already ship, and the cancel link is the *same medium the contract was
#: entered into* — which is what California AB 2863 has required of contracts
#: formed since 1 July 2025 and what the EU's withdrawal-function requirement
#: has required since 19 June 2026. "Reply to this email" is not the same
#: medium.
#:
#: It was `/settings`, and before that `/?plan=1`. Both were wrong in the same
#: way and the second is the one worth remembering: nothing ever read that query
#: parameter, so the button labelled "Manage your plan" put a subscriber who
#: wanted to stop a charge on the page that tries to sell them the product,
#: which is the definition of a cancellation obstacle.
#:
#: `/settings` was right while the web had a cabinet with a cancel button in it.
#: The web is a storefront now — the cabinet is deleted, everything sells through
#: Apple and Google, and a subscription bought in a store is cancelled in that
#: store's own account settings, which is a screen no link of ours can reach.
#: So this points at the section of the subscription terms that names the two
#: taps and says where they are. That is a worse button than the one that used
#: to exist and a much better one than a 404: the reader lands on a paragraph
#: that tells them exactly what to do, in the language they bought in.
#:
#: The alternative was to link to `apps.apple.com/account/subscriptions`, which
#: is a real page — but only one of the two stores, chosen by us on behalf of a
#: reader whose platform this letter does not know, and wrong for anybody who
#: paid the card processor this module still supports.
RECEIPT_PLAN_PATH = "/subscription-terms#cancel"
RECEIPT_REFUNDS_PATH = "/refunds"

#: Month names, so that a letter written by six people does not print a date
#: like a machine. `2026-08-06` in the middle of a German sentence is the one
#: place these three messages read as generated rather than written, and the
#: receipt is the one we ask people to keep.
MONTHS: dict[str, tuple[str, ...]] = {
    "en": ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
    "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"),
    "it": ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
           "agosto", "settembre", "ottobre", "novembre", "dicembre"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"),
    "pt-BR": ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
              "agosto", "setembro", "outubro", "novembro", "dezembro"),
    # Genitive, because a Russian date puts the month after the day: «7 августа
    # 2026». The nominative «август» in that position is the machine showing.
    "ru": ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
           "августа", "сентября", "октября", "ноября", "декабря"),
}

#: How each language puts a day, a month and a year together. A format string
#: rather than a `strftime` because the differences are not decoration: German
#: needs the ordinal point, Spanish and Portuguese need their two "de"s, and
#: `%B` would hand us an English month whatever the process locale happens to be
#: — which on a server is whatever the container was built with.
DATE_FORMATS: dict[str, str] = {
    "en": "{day} {month} {year}",
    "es": "{day} de {month} de {year}",
    "de": "{day}. {month} {year}",
    "it": "{day} {month} {year}",
    "fr": "{day} {month} {year}",
    "pt-BR": "{day} de {month} de {year}",
    "ru": "{day} {month} {year}",
}


def written_date(value: datetime, locale: str) -> str:
    """One date, written the way the reader writes dates.

    Falls back to English rather than to ISO, because the fallback lands inside
    a sentence: "You paid for the whole archive on 2026-08-06" is a letter
    nobody wrote, and it is the letter we ask people to keep.
    """
    language = locale if locale in MONTHS else "en"
    return DATE_FORMATS[language].format(
        day=value.day, month=MONTHS[language][value.month - 1], year=value.year
    )


@dataclass(frozen=True, slots=True)
class Receipt:
    """One payment, and everything the confirmation of it has to carry.

    A record rather than an `Entitlement`, a `Purchase` and a `User`, for the
    same reason `renewals.Notice` is one: what goes in the envelope is decided
    by the caller, and this module only puts it in one. That is what makes the
    six translations testable without a database, a processor or a mail account.

    `product` is a catalogue **key** rather than a display name, because the
    name has to be written in the buyer's language and the catalogue is in
    English. `recurring` decides which of the two withdrawal paragraphs is
    true — see the block comment above.
    """

    email: str
    locale: str
    product: str
    amount_cents: int
    currency: str
    paid_at: datetime
    #: The merchant of record, as the running adapter names it.
    merchant: str
    #: The processor's transaction id — what the buyer quotes when they write
    #: to the merchant, and the only string in this letter that lets a support
    #: conversation find the money in under a minute.
    reference: str
    recurring: bool
    #: The lines this buyer actually ticked, `(key, text)` each, **verbatim**,
    #: or `None` where no consent was recorded against the purchase.
    #:
    #: This field is the difference between a confirmation and a fabrication.
    #: The letter used to print "What you ticked at the checkout" over two
    #: sentences taken from a per-locale template, unconditionally, for every
    #: payment — including the ones opened from surfaces that show no boxes at
    #: all. A buyer who never saw a checkbox then held a document from us
    #: asserting they ticked one, which converts a missing waiver into a
    #: misrepresentation on the exact medium a regulator reads. `None` prints no
    #: quotes, no heading, and the paragraph that says the withdrawal right
    #: still stands — which is what is true when nobody was asked to give it up.
    consent: tuple[tuple[str, str], ...] | None = None


#: What each catalogue key is called, in the language the buyer reads. Taken
#: word for word from `src/lib/i18n/*.ts` — `eight.names`, `cabinet.wholeArchive`
#: and `pricing.everythingYear` — because a receipt that names the purchase
#: differently from the button that bought it is a receipt somebody reads twice
#: and then disputes. The catalogue's own English `name` is the fallback: an
#: unnamed product would be a receipt that cannot say what was bought, which is
#: the one element it may not omit.
RECEIPT_PRODUCTS: dict[str, dict[str, str]] = {
    "en": {
        "natal": "Natal chart", "numerology": "Numerology", "birth-card": "Birth Card",
        "transits": "Transits", "solar-return": "Solar return",
        "compatibility": "Compatibility", "astrocartography": "Astrocartography",
        "synthesis": "Cross-synthesis", "archive": "The whole archive",
        "archive-bump": "The rest of the archive",
        "archive-upgrade": "The rest of the archive",
        "monthly": "Everything that changes, monthly", "annual": "Everything, for a year",
    },
    "es": {
        "natal": "Carta natal", "numerology": "Numerología",
        "birth-card": "Carta de nacimiento", "transits": "Tránsitos",
        "solar-return": "Revolución solar", "compatibility": "Compatibilidad",
        "astrocartography": "Astrocartografía", "synthesis": "Síntesis cruzada",
        "archive": "El archivo completo", "archive-bump": "El resto del archivo",
        "archive-upgrade": "El resto del archivo",
        "monthly": "Todo lo que cambia, cada mes", "annual": "Todo, durante un año",
    },
    "de": {
        "natal": "Geburtshoroskop", "numerology": "Numerologie",
        "birth-card": "Geburtskarte", "transits": "Transite",
        "solar-return": "Solarhoroskop", "compatibility": "Partnerschaft",
        "astrocartography": "Astrokartografie", "synthesis": "Quersynthese",
        "archive": "Das ganze Archiv", "archive-bump": "Der Rest des Archivs",
        "archive-upgrade": "Der Rest des Archivs",
        "monthly": "Alles, was sich bewegt, monatlich", "annual": "Alles, für ein Jahr",
    },
    "it": {
        "natal": "Tema natale", "numerology": "Numerologia",
        "birth-card": "Carta di nascita", "transits": "Transiti",
        "solar-return": "Rivoluzione solare", "compatibility": "Affinità",
        "astrocartography": "Astrocartografia", "synthesis": "Sintesi incrociata",
        "archive": "L'archivio intero", "archive-bump": "Il resto dell'archivio",
        "archive-upgrade": "Il resto dell'archivio",
        "monthly": "Tutto ciò che cambia, ogni mese", "annual": "Tutto, per un anno",
    },
    "fr": {
        "natal": "Thème natal", "numerology": "Numérologie",
        "birth-card": "Carte de naissance", "transits": "Transits",
        "solar-return": "Révolution solaire", "compatibility": "Compatibilité",
        "astrocartography": "Astrocartographie", "synthesis": "Synthèse croisée",
        "archive": "L'archive entière", "archive-bump": "Le reste de l'archive",
        "archive-upgrade": "Le reste de l'archive",
        "monthly": "Tout ce qui change, chaque mois", "annual": "Tout, pendant un an",
    },
    "pt-BR": {
        "natal": "Mapa natal", "numerology": "Numerologia",
        "birth-card": "Carta de nascimento", "transits": "Trânsitos",
        "solar-return": "Revolução solar", "compatibility": "Compatibilidade",
        "astrocartography": "Astrocartografia", "synthesis": "Síntese cruzada",
        "archive": "O arquivo inteiro", "archive-bump": "O resto do arquivo",
        "archive-upgrade": "O resto do arquivo",
        "monthly": "Tudo que muda, todo mês", "annual": "Tudo, por um ano",
    },
    "ru": {
        "natal": "Натальная карта", "numerology": "Нумерология",
        "birth-card": "Карта рождения", "transits": "Транзиты",
        # «Соляр» is what Russian-language astrology prints; «солнечное
        # возвращение» is the calque nobody uses.
        "solar-return": "Соляр", "compatibility": "Совместимость",
        "astrocartography": "Астрокартография", "synthesis": "Перекрёстный синтез",
        "archive": "Весь архив", "archive-bump": "Остаток архива",
        "archive-upgrade": "Остаток архива",
        "monthly": "Вся Alma — на месяц", "annual": "Вся Alma — на год",
    },
}


@dataclass(frozen=True, slots=True)
class ReceiptCopy:
    """One language's worth of the receipt.

    A record rather than the tuple the other two messages use. Three strings
    read fine as `(happening, choice, action)`; seventeen do not, and a receipt
    whose fifth and sixth elements have been swapped in one locale is a legal
    document that is wrong in a language nobody on the team reads.
    """

    subject: str
    lede: str
    #: The five labels of the fact block, in the order they are printed.
    what: str
    paid: str
    tax_note: str
    when: str
    seller: str
    reference: str
    seller_note: str
    #: The line that introduces the buyer's own words — and only that line.
    #:
    #: The sentences themselves used to live here too, one copy per locale,
    #: kept equal to `checkout.consentDeliver` / `consentWaive` in
    #: `src/lib/i18n/*.ts` by a test. That was the best available answer while
    #: the letter had nothing else to print, and it was still the wrong shape:
    #: two copies of a legal sentence in two languages of source code, held
    #: together by a pin, on a document whose entire value is being evidence of
    #: what one particular person read. Now the receipt quotes what was recorded
    #: at the checkout, so the sentences cannot drift from the screen — there is
    #: only one copy of them and it is the buyer's.
    consent_title: str
    #: What those two lines mean for this purchase — Art. 16(m)...
    consent: str
    #: ...and for a plan, which Art. 16(a) does not extinguish.
    consent_plan: str
    #: And what is true when nothing was ticked at all: the right stands. A
    #: paragraph rather than silence, because CRD Art. 6(1)(h) asks for the
    #: withdrawal conditions either way, and because a buyer who was never
    #: shown a box is owed the good news rather than left to find it.
    withdrawal_stands: str
    cancel: str
    refund: str
    #: The label on the link to `/refunds`, worded as the footer words it.
    refunds_page: str
    action: str
    action_plan: str
    reason: str


RECEIPT_COPY: dict[str, ReceiptCopy] = {
    "en": ReceiptCopy(
        subject="Your Alma receipt — {product}",
        lede="You paid for {product} on {date}. This is your written copy of what "
             "that was and what you agreed to — worth keeping.",
        what="What you bought",
        paid="Paid",
        tax_note="tax included",
        when="When",
        seller="Sold by",
        reference="Reference",
        seller_note="The merchant of record: they took the payment, they issue the "
                    "invoice and they hold the money — which is why a refund comes "
                    "from them and not from us.",
        consent_title="What you ticked at the checkout",
        consent="That is the 14-day right of withdrawal an online purchase carries in "
                "the EU and the UK. What opened the second this payment went through is "
                "access; each chapter is written the first time you open it, from your "
                "own positions. Our own policy is more generous than the waiver you "
                "gave, and it is the one we honour: ask within fourteen days and the "
                "whole price comes back.",
        consent_plan="That is the 14-day right of withdrawal an online purchase carries "
                     "in the EU and the UK. The plan itself is another matter: it is "
                     "not fully performed until the period you paid for ends, so the "
                     "right stands for the plan. Withdraw within 14 days and you are "
                     "refunded for the part of the period you have not used, and the "
                     "plan ends there.",
        withdrawal_stands="An online purchase carries a 14-day right of withdrawal in "
                          "the EU and the UK, and nothing at this checkout asked you to "
                          "give it up — so it stands. Ask within fourteen days and the "
                          "money comes back.",
        cancel="Cancelling is two taps in Settings, in the app you bought it in, and "
               "it stops the next charge. What you have already paid for runs to the "
               "end of its period.",
        refund="A refund is asked of {merchant}, who hold the money — their own "
               "receipt has the link. Or write to us and we ask for you; the whole of "
               "how that works is on the refunds page.",
        refunds_page="Refunds",
        action="Open Alma",
        action_plan="Manage your plan",
        reason="This goes out once for every payment. It is not marketing and there "
               "is nothing to unsubscribe from — what you agreed to and what you paid "
               "is something you are owed in writing, and this is it.",
    ),
    "es": ReceiptCopy(
        subject="Tu recibo de Alma — {product}",
        lede="Pagaste {product} el {date}. Esta es tu copia por escrito de qué fue y "
             "de lo que aceptaste — conviene guardarla.",
        what="Qué compraste",
        paid="Pagado",
        tax_note="impuestos incluidos",
        when="Cuándo",
        seller="Vendido por",
        reference="Referencia",
        seller_note="Es el vendedor legal: cobró el pago, emite la factura y tiene el "
                    "dinero — por eso el reembolso sale de ahí y no de nosotros.",
        consent_title="Lo que marcaste al pagar",
        consent="Ese es el plazo de desistimiento de 14 días que lleva una compra por "
                "internet en la UE y el Reino Unido. Lo que se abrió en el segundo en "
                "que se hizo el cobro es el acceso; cada capítulo se escribe la primera "
                "vez que lo abres, a partir de tus propias posiciones. Nuestra política "
                "es más generosa que esa renuncia y es la que cumplimos: pídelo dentro "
                "de catorce días y se devuelve el precio entero.",
        consent_plan="Ese es el plazo de desistimiento de 14 días que lleva una compra "
                     "por internet en la UE y el Reino Unido. El plan es otra cosa: no "
                     "queda ejecutado hasta que acaba el periodo que pagaste, así que "
                     "para el plan el derecho sigue en pie. Si desistes dentro de 14 "
                     "días, se te devuelve la parte del periodo que no has usado y el "
                     "plan termina ahí.",
        withdrawal_stands="Una compra por internet lleva un plazo de desistimiento de "
                          "14 días en la UE y el Reino Unido, y aquí nadie te pidió que "
                          "renunciaras a él: sigue en pie. Pídelo dentro de catorce "
                          "días y el dinero vuelve.",
        cancel="Cancelar son dos toques en Ajustes, en la misma app donde compraste, y "
               "detiene el siguiente cobro. Lo ya pagado dura hasta el final de su "
               "periodo.",
        refund="El reembolso se pide a {merchant}, que tiene el dinero — su propio "
               "recibo lleva el enlace. O escríbenos y lo pedimos por ti; cómo funciona "
               "está entero en la página de reembolsos.",
        refunds_page="Reembolsos",
        action="Abrir Alma",
        action_plan="Gestionar mi plan",
        reason="Esto sale una vez por cada pago. No es marketing y no hay nada de lo "
               "que darse de baja: tener por escrito lo que aceptaste y lo que pagaste "
               "es algo que se te debe, y esto es eso.",
    ),
    "de": ReceiptCopy(
        subject="Dein Alma-Beleg — {product}",
        lede="Du hast am {date} für {product} bezahlt. Das hier ist deine schriftliche "
             "Kopie davon, was es war und wozu du zugestimmt hast — heb sie auf.",
        what="Gekauft",
        paid="Bezahlt",
        tax_note="inkl. Steuern",
        when="Wann",
        seller="Verkauft von",
        reference="Referenz",
        seller_note="Der rechtliche Verkäufer: Er hat die Zahlung eingezogen, stellt "
                    "die Rechnung aus und hält das Geld — deshalb kommt eine Erstattung "
                    "von dort und nicht von uns.",
        consent_title="Was du beim Bezahlen angehakt hast",
        consent="Gemeint ist das 14-tägige Widerrufsrecht, das ein Onlinekauf in der EU "
                "und im Vereinigten Königreich mit sich bringt. Freigeschaltet wurde in "
                "der Sekunde der Zahlung der Zugang; jedes Kapitel wird beim ersten "
                "Öffnen geschrieben, aus deinen eigenen Positionen. Unsere eigene Regel "
                "ist großzügiger als dieser Verzicht, und sie gilt: Melde dich "
                "innerhalb von vierzehn Tagen, und der volle Preis kommt zurück.",
        consent_plan="Gemeint ist das 14-tägige Widerrufsrecht, das ein Onlinekauf in "
                     "der EU und im Vereinigten Königreich mit sich bringt. Das Abo "
                     "selbst ist etwas anderes: Es ist erst mit dem Ende des bezahlten "
                     "Zeitraums vollständig erbracht, also bleibt das Widerrufsrecht "
                     "dafür bestehen. Widerrufst du innerhalb von 14 Tagen, bekommst du "
                     "den nicht genutzten Teil des Zeitraums zurück, und das Abo endet "
                     "damit.",
        withdrawal_stands="Ein Onlinekauf bringt in der EU und im Vereinigten "
                          "Königreich ein 14-tägiges Widerrufsrecht mit sich, und hier "
                          "hat dich niemand gebeten, darauf zu verzichten — es bleibt "
                          "also bestehen. Melde dich innerhalb von vierzehn Tagen, und "
                          "das Geld kommt zurück.",
        cancel="Kündigen sind zwei Taps in den Einstellungen, in derselben App, in der "
               "du gekauft hast, und es stoppt die nächste Abbuchung. Was schon bezahlt "
               "ist, läuft bis zum Ende seines Zeitraums.",
        refund="Eine Erstattung wird bei {merchant} beantragt — dort liegt das Geld, "
               "und in deren eigener Rechnung steht der Link. Oder schreib uns, dann "
               "fragen wir für dich; wie das läuft, steht vollständig auf der "
               "Erstattungsseite.",
        refunds_page="Rückerstattung",
        action="Alma öffnen",
        action_plan="Abo verwalten",
        reason="Das kommt einmal zu jeder Zahlung. Es ist keine Werbung und es gibt "
               "nichts abzubestellen — was du zugestimmt und was du bezahlt hast, steht "
               "dir schriftlich zu, und das hier ist es.",
    ),
    "it": ReceiptCopy(
        subject="La tua ricevuta Alma — {product}",
        lede="Hai pagato {product} il {date}. Questa è la tua copia scritta di che "
             "cos'era e di cosa hai accettato — vale la pena conservarla.",
        what="Cosa hai acquistato",
        paid="Pagato",
        tax_note="tasse incluse",
        when="Quando",
        seller="Venduto da",
        reference="Riferimento",
        seller_note="È il venditore legale: ha incassato il pagamento, emette la "
                    "fattura e tiene il denaro — per questo il rimborso arriva da lì e "
                    "non da noi.",
        consent_title="Cosa hai spuntato al pagamento",
        consent="È il termine di recesso di 14 giorni che un acquisto online porta con "
                "sé nell'UE e nel Regno Unito. Quello che si è aperto nel secondo in "
                "cui il pagamento è andato a buon fine è l'accesso; ogni capitolo viene "
                "scritto la prima volta che lo apri, dalle tue posizioni. La nostra "
                "politica è più generosa di quella rinuncia ed è quella che "
                "rispettiamo: chiedi entro quattordici giorni e torna indietro l'intero "
                "prezzo.",
        consent_plan="È il termine di recesso di 14 giorni che un acquisto online porta "
                     "con sé nell'UE e nel Regno Unito. L'abbonamento è un'altra cosa: "
                     "non è eseguito per intero finché non finisce il periodo che hai "
                     "pagato, quindi per l'abbonamento il diritto resta. Se recedi "
                     "entro 14 giorni ti viene rimborsata la parte di periodo non "
                     "utilizzata e l'abbonamento finisce lì.",
        withdrawal_stands="Un acquisto online porta con sé un termine di recesso di 14 "
                          "giorni nell'UE e nel Regno Unito, e qui nessuno ti ha "
                          "chiesto di rinunciarci: resta valido. Chiedi entro "
                          "quattordici giorni e i soldi tornano indietro.",
        cancel="Disdire sono due tocchi nelle Impostazioni, nella stessa app in cui hai "
               "acquistato, e ferma il prossimo addebito. Quello che hai già pagato "
               "resta fino alla fine del suo periodo.",
        refund="Il rimborso si chiede a {merchant}, che tiene il denaro — il link è "
               "nella loro ricevuta. Oppure scrivici e lo chiediamo noi per te; come "
               "funziona è tutto sulla pagina dei rimborsi.",
        refunds_page="Rimborsi",
        action="Apri Alma",
        action_plan="Gestisci il piano",
        reason="Questo messaggio parte una volta per ogni pagamento. Non è marketing e "
               "non c'è nulla da disdire: avere per iscritto ciò che hai accettato e "
               "ciò che hai pagato ti è dovuto, ed è questo.",
    ),
    # The one locale that was written in `vous` while the French app says `tu`
    # throughout — including the two consent sentences quoted inside this very
    # letter. The same brand became formal exactly when it started talking about
    # money and rights, which reads as a lawyer taking the voice over, and it
    # reads that way in the document we ask people to keep. `tu`, like the rest
    # of the French product.
    "fr": ReceiptCopy(
        subject="Ton reçu Alma — {product}",
        lede="Tu as payé {product} le {date}. Voici ton exemplaire écrit de ce que "
             "c'était et de ce que tu as accepté — à garder.",
        what="Ce que tu as acheté",
        paid="Payé",
        tax_note="taxes comprises",
        when="Quand",
        seller="Vendu par",
        reference="Référence",
        seller_note="C'est le vendeur légal : il a encaissé le paiement, il émet la "
                    "facture et il détient l'argent — c'est donc de lui que vient un "
                    "remboursement, et pas de nous.",
        consent_title="Ce que tu as coché au paiement",
        consent="C'est le délai de rétractation de 14 jours qu'un achat en ligne "
                "comporte dans l'UE et au Royaume-Uni. Ce qui s'est ouvert à la seconde "
                "où le paiement est passé, c'est l'accès ; chaque chapitre est rédigé "
                "la première fois que tu l'ouvres, à partir de tes propres positions. "
                "Notre propre règle est plus généreuse que cette renonciation, et c'est "
                "elle que nous appliquons : demande-le dans les quatorze jours et tout "
                "le prix revient.",
        consent_plan="C'est le délai de rétractation de 14 jours qu'un achat en ligne "
                     "comporte dans l'UE et au Royaume-Uni. L'abonnement, lui, est "
                     "autre chose : il n'est pleinement exécuté qu'à la fin de la "
                     "période payée, le droit de rétractation vaut donc pour "
                     "l'abonnement. Rétracte-toi dans les 14 jours et la part de la "
                     "période non utilisée t'est remboursée ; l'abonnement s'arrête là.",
        withdrawal_stands="Un achat en ligne comporte un délai de rétractation de 14 "
                          "jours dans l'UE et au Royaume-Uni, et personne ici ne t'a "
                          "demandé d'y renoncer : il tient toujours. Demande-le dans "
                          "les quatorze jours et l'argent revient.",
        cancel="Résilier, c'est deux taps dans les Réglages, dans l'application où tu "
               "as acheté, et cela arrête le prochain prélèvement. Ce qui est déjà payé "
               "court jusqu'à la fin de sa période.",
        refund="Un remboursement se demande à {merchant}, qui détient l'argent — le "
               "lien figure sur leur propre reçu. Ou écris-nous et nous le demandons "
               "pour toi ; tout est expliqué sur la page des remboursements.",
        refunds_page="Remboursements",
        action="Ouvrir Alma",
        action_plan="Gérer mon abonnement",
        reason="Ce message part une fois pour chaque paiement. Ce n'est pas du "
               "marketing et il n'y a rien à désabonner : ce que tu as accepté et ce "
               "que tu as payé t'est dû par écrit, et le voici.",
    ),
    "pt-BR": ReceiptCopy(
        subject="Seu recibo do Alma — {product}",
        lede="Você pagou por {product} em {date}. Esta é a sua via escrita do que foi "
             "e do que você aceitou — vale guardar.",
        what="O que você comprou",
        paid="Pago",
        tax_note="impostos incluídos",
        when="Quando",
        seller="Vendido por",
        reference="Referência",
        seller_note="É o vendedor legal: recebeu o pagamento, emite a nota e fica com o "
                    "dinheiro — por isso o reembolso sai de lá e não de nós.",
        consent_title="O que você marcou no pagamento",
        consent="Esse é o prazo de arrependimento de 14 dias que uma compra pela "
                "internet tem na UE e no Reino Unido. O que abriu no segundo em que o "
                "pagamento passou foi o acesso; cada capítulo é escrito na primeira vez "
                "que você abre, a partir das suas próprias posições. A nossa política é "
                "mais generosa do que essa renúncia, e é ela que a gente cumpre: peça "
                "dentro de catorze dias e o preço inteiro volta.",
        consent_plan="Esse é o prazo de arrependimento de 14 dias que uma compra pela "
                     "internet tem na UE e no Reino Unido. O plano é outra coisa: só "
                     "está cumprido por inteiro quando termina o período que você "
                     "pagou, então para o plano o direito continua valendo. Se desistir "
                     "dentro de 14 dias, a parte do período que você não usou é "
                     "devolvida e o plano acaba ali.",
        withdrawal_stands="Uma compra pela internet tem prazo de arrependimento de 14 "
                          "dias na UE e no Reino Unido, e aqui ninguém pediu que você "
                          "abrisse mão dele: ele continua valendo. Peça dentro de "
                          "catorze dias e o dinheiro volta.",
        cancel="Cancelar são dois toques nos Ajustes, no mesmo app em que você comprou, "
               "e para a próxima cobrança. O que já foi pago vai até o fim do período.",
        refund="O reembolso é pedido à {merchant}, que está com o dinheiro — o link "
               "está no recibo deles. Ou escreva para a gente e pedimos por você; como "
               "funciona está inteiro na página de reembolsos.",
        refunds_page="Reembolsos",
        action="Abrir o Alma",
        action_plan="Gerenciar meu plano",
        reason="Isto sai uma vez a cada pagamento. Não é marketing e não há nada para "
               "cancelar aqui: ter por escrito o que você aceitou e o que pagou é um "
               "direito seu, e é isto.",
    ),
    # No past-tense first-person verbs anywhere in this letter: «ты оплатил»
    # would gender the buyer on a legal document. Everything hangs on the
    # payment, the purchase and the consent — nouns with genders of their own.
    "ru": ReceiptCopy(
        subject="Твой чек Alma — {product}",
        lede="{date} прошла оплата за {product}. Это письменная копия того, что "
             "это было и на что дано согласие — её стоит сохранить.",
        what="Что куплено",
        paid="Оплачено",
        tax_note="налог включён",
        when="Когда",
        seller="Продавец",
        reference="Номер операции",
        seller_note="Это официальный продавец: он принял платёж, он выставляет "
                    "счёт, и деньги находятся у него — поэтому возврат приходит "
                    "от него, а не от нас.",
        consent_title="Что было отмечено при оплате",
        consent="Это 14-дневное право на отказ, которое в ЕС и Великобритании "
                "есть у любой онлайн-покупки. В секунду оплаты открылся доступ; "
                "каждая глава пишется при первом открытии, из твоих собственных "
                "позиций. Наши собственные правила щедрее отданного отказа, и "
                "следуем мы именно им: попроси в течение четырнадцати дней — и "
                "вся сумма вернётся.",
        consent_plan="Это 14-дневное право на отказ, которое в ЕС и "
                     "Великобритании есть у любой онлайн-покупки. С планом "
                     "иначе: он не исполнен полностью, пока не закончится "
                     "оплаченный период, поэтому для плана право сохраняется. "
                     "Откажись в течение 14 дней — вернутся деньги за "
                     "неиспользованную часть периода, и на этом план кончится.",
        withdrawal_stands="У онлайн-покупки в ЕС и Великобритании есть "
                          "14-дневное право на отказ, и ничто при этой оплате "
                          "не просило от него отказаться — оно сохраняется. "
                          "Попроси в течение четырнадцати дней, и деньги "
                          "вернутся.",
        cancel="Отмена — два касания в настройках, в том же приложении, где "
               "была покупка, и она останавливает следующее списание. Уже "
               "оплаченное действует до конца своего периода.",
        refund="Возврат запрашивается у {merchant} — деньги у них, и ссылка "
               "есть в их собственном чеке. Или напиши нам, и мы попросим за "
               "тебя; как всё это устроено — на странице возвратов.",
        refunds_page="Возвраты",
        action="Открыть Alma",
        action_plan="Управлять планом",
        reason="Это письмо приходит один раз за каждый платёж. Это не реклама, "
               "и отписываться не от чего: то, на что дано согласие и что "
               "оплачено, положено иметь в письменном виде — и вот оно.",
    ),
}


def receipt_locale(locale: str) -> str:
    """The language this receipt is written in. English when we have no other.

    Its own function because falling back silently is exactly what must not
    happen quietly here: a confirmation nobody can read is not a confirmation,
    and the log line is how a locale we forgot to translate becomes visible
    before a regulator finds it.
    """
    if locale in RECEIPT_COPY:
        return locale
    log.warning("no receipt copy for locale %r — sending it in English", locale)
    return "en"


def receipt_product_name(product: str, locale: str) -> str:
    """What to call the thing that was bought, in the reader's language.

    Never empty and never the raw key if we can help it: "what was bought" is
    the one element of a confirmation that cannot be omitted, so an untranslated
    product falls back to the catalogue's English name and says so in the log.
    A test pins the two tables together, which is what stops a new rung on the
    ladder from ever reaching this line.
    """
    from .billing.catalogue import PRODUCTS

    named = RECEIPT_PRODUCTS.get(locale, {}).get(product)
    if named:
        return named
    item = PRODUCTS.get(product)
    log.warning("no %s name for product %r in the receipt copy", locale, product)
    return item.name if item is not None else product


def _text(value: str) -> str:
    """One value, safe to drop into the body of an element.

    `quote=False` on purpose: quotes and apostrophes are ordinary characters in
    running text, and escaping them turns four of the six translations into
    `&#x27;` soup in any client that shows a plain-text alternative. Nothing
    here is ever interpolated into an *attribute*, which is the only place the
    quote form is needed — the two URLs in this letter are ours.
    """
    return html.escape(value, quote=False)


def _fact(label: str, value: str) -> str:
    return (
        '<p style="font-size:15px;line-height:1.5;margin:0 0 14px">'
        f'<span style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;'
        f'color:#8b8578">{_text(label)}</span><br>{_text(value)}</p>'
    )


def _receipt_html(
    receipt: Receipt, *, locale: str, product: str, amount: str, when: str
) -> str:
    """The letter itself.

    Every value that comes from outside this file goes through `_text`. None of
    them is written by the buyer today — the transaction id and the
    merchant name are the processor's — but this is a document we generate from
    a webhook payload and mail to a person, and "the field it arrives in cannot
    contain a tag" is a property of somebody else's API rather than of ours.
    """
    config = settings()
    copy = RECEIPT_COPY[locale]
    # Three states, not two. A recorded consent gets the paragraph that explains
    # what it did — one for a purchase, another for a plan Art. 16(a) does not
    # extinguish. **No** recorded consent gets neither: the buyer was not asked
    # to give the right up, so it stands, and the letter says that instead of
    # asserting a waiver nobody agreed to.
    if receipt.consent is None:
        consent = copy.withdrawal_stands
    else:
        consent = copy.consent_plan if receipt.recurring else copy.consent
    action = copy.action_plan if receipt.recurring else copy.action
    url = config.web_url + (RECEIPT_PLAN_PATH if receipt.recurring else "")
    facts = "".join((
        _fact(copy.what, product),
        _fact(copy.paid, f"{amount} ({copy.tax_note})"),
        _fact(copy.when, when),
        _fact(copy.seller, receipt.merchant),
        _fact(copy.reference, receipt.reference),
    ))
    # The cancellation paragraph is printed only for a plan. On a one-time
    # purchase there is no next charge to stop, and a "how to cancel" on a
    # permanent purchase reads as though the thing might be taken away.
    cancelling = (
        f'<p style="font-size:14px;line-height:1.6;margin:0 0 16px;color:#c8bfa8">'
        f'{_text(copy.cancel)}</p>'
        if receipt.recurring
        else ""
    )
    refund = _text(copy.refund.format(merchant=receipt.merchant))
    # The lines the buyer ticked, set apart so they read as *their* words rather
    # than as more of ours, and quoted from what was recorded at the checkout
    # rather than from this file's own copy. Art. 16(m) asks for the consent
    # itself to be confirmed, and the checkout promises outright that "the
    # receipt in your inbox repeats both lines back" — a promise that can only
    # be kept by printing the sentences that were on the screen.
    #
    # Empty when nothing was recorded, and then the whole block goes: the
    # heading, the quotes, and the waiver paragraph. A letter headed "what you
    # ticked at the checkout" above two sentences from a template, sent to
    # somebody who was never shown a box, is not a weaker confirmation — it is a
    # manufactured one, and it converts a missing waiver into a
    # misrepresentation on the medium a regulator reads.
    ticked = "".join(
        f'<p style="font-size:15px;line-height:1.5;margin:0 0 8px">{_text(text)}</p>'
        for _key, text in (receipt.consent or ())
    )
    quoted = (
        f'<p style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;'
        f'color:#8b8578;margin:0 0 10px">{_text(copy.consent_title)}</p>'
        f'<div style="border-left:2px solid #C9AE6B;padding-left:14px;margin:0 0 16px">'
        f'{ticked}</div>'
        if ticked
        else ""
    )
    return f"""\
<div style="background:#0A0D1C;color:#F1E9D6;font-family:Georgia,serif;padding:48px 24px">
  <div style="max-width:480px;margin:0 auto">
    <div style="font-size:22px;letter-spacing:.18em;color:#C9AE6B">ALMA</div>
    <p style="font-size:17px;line-height:1.6;margin:28px 0 24px">
      {_text(copy.lede.format(product=product, date=when))}</p>
    <div style="border-top:1px solid #2a2b3d;border-bottom:1px solid #2a2b3d;padding:20px 0 6px;
         margin:0 0 20px">{facts}</div>
    <p style="font-size:13px;line-height:1.6;margin:0 0 24px;color:#8b8578">
      {_text(copy.seller_note)}</p>
    {quoted}
    <p style="font-size:14px;line-height:1.6;margin:0 0 16px;color:#c8bfa8">
      {_text(consent)}</p>
    {cancelling}
    <p style="font-size:14px;line-height:1.6;margin:0 0 28px;color:#c8bfa8">{refund}
      <a href="{config.web_url}{RECEIPT_REFUNDS_PATH}"
         style="color:#E4D3A2">{_text(copy.refunds_page)} →</a></p>
    <a href="{url}" style="display:inline-block;padding:14px 28px;border:1px solid #C9AE6B;
       color:#E4D3A2;text-decoration:none;letter-spacing:.06em">{_text(action)}</a>
    <p style="font-size:13px;line-height:1.6;color:#8b8578;margin-top:32px">
      {_text(copy.reason)}</p>
  </div>
</div>"""


async def send_receipt(receipt: Receipt) -> bool:
    """Confirm one purchase on a durable medium. Returns whether it went out.

    The rule this enforces is Art. 16(m): a buyer loses the 14-day withdrawal
    right on digital content only if the trader has *also* confirmed the
    contract, including the consent they gave, on a durable medium. So this
    letter carries the six things that confirmation has to contain, and it
    carries them in the language the buyer bought in.

    A `False` is a legal fact and not merely a failed send: the waiver behind
    that purchase has not been completed, and the caller has to log it as such
    rather than retrying into a second copy. Which is why the amount is
    formatted here from the catalogue's own `format_price` — the number in this
    letter is the number on the buyer's statement — and why an unconfigured mail
    provider says so at `error` rather than at `info` the way a sign-in link
    does. In development that is noise; in production it is the sentence that
    tells somebody the ladder is selling without a receipt behind it.
    """
    from .billing.catalogue import format_price

    config = settings()
    locale = receipt_locale(receipt.locale)
    product = receipt_product_name(receipt.product, locale)
    amount = format_price(receipt.amount_cents, receipt.currency)
    when = written_date(receipt.paid_at, locale)

    if not config.resend_api_key:
        log.error(
            "mail not configured — no receipt for %s (%s, %s, %s): the withdrawal "
            "waiver for this purchase is not complete",
            receipt.email, receipt.product, amount, receipt.reference,
        )
        return False

    return await _post({
        "from": config.mail_from,
        "to": [receipt.email],
        "subject": RECEIPT_COPY[locale].subject.format(product=product),
        "html": _receipt_html(
            receipt, locale=locale, product=product, amount=amount, when=when
        ),
    })
