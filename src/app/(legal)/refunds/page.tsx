import type { Metadata } from "next";
import Link from "next/link";
import { DocFoot, DocHead, Para, Points, Sec } from "@/components/legal/Doc";
import { CONTACT, MERCHANT, STORE_MERCHANTS } from "@/lib/legal";
import { APPLE, GOOGLE } from "@/lib/support";

export const metadata: Metadata = {
  title: "Refunds · Alma",
  description: "Why a refund is asked of Apple or Google rather than of us, when we ask on your behalf, and why we do not treat the 14-day withdrawal right as waived.",
};

/**
 * The page most likely to be read by somebody who is annoyed.
 *
 * It therefore leads with the fact that explains everything else about it —
 * somebody else holds the money — rather than burying it under a policy that
 * would otherwise look arbitrary. A person who understands why the answer is
 * what it is will accept a "no" that a person who has been managed will not.
 *
 * ── what changed when the web stopped selling ─────────────────────────────
 * This page used to name a card processor as the seller of everything, because
 * that is what the web checkout made true. The checkout is gone. Every purchase
 * now happens inside an app, through Apple or Google, and they are the
 * merchants of record — which changes the mechanism in the one way that matters
 * to a reader: the request goes to a screen we do not own, and there is a
 * self-service route on each of them that is faster than writing to us. Both
 * addresses are printed here rather than described, because a person who has
 * been charged twice should not also have to search.
 *
 * The card processor is named exactly once, at the bottom, for anybody holding
 * a receipt that did not come from a store. That paragraph is not decoration:
 * the adapters still ship, `ALMA_BILLING_PROVIDER` still selects one, and
 * deleting the paragraph while keeping the code would be deleting a promise to
 * whoever that seam ever serves.
 *
 * ── why the withdrawal section reads the way it does ──────────────────────
 * It used to claim the CRD Art. 16(m) waiver and then give it back in one
 * sentence. Read against the code that sentence was the whole archive:
 * `readings.py` writes a chapter the first time somebody opens it — there is no
 * job that generates the other forty at purchase — so at the moment the money
 * moves, nothing whatsoever has been performed, and a waiver over unperformed
 * content is a waiver over nothing.
 *
 * Under in-app purchase the waiver argument is weaker still, and in a second
 * way: the three things Art. 16(m) needs — express consent, acknowledgement
 * that the right is lost, and confirmation on a durable medium — are collected
 * at a checkout we no longer run. The stores' own purchase sheets do not
 * collect them for us. So this page does not stand on the waiver at all, which
 * is the same policy it had before and is now the only honest one.
 */

/**
 * The Annex I(B) model withdrawal form, in the six languages Alma sells in.
 *
 * Translated rather than left in English because this is the one piece of the
 * pre-contractual information that is a *form* — six fixed sentences with four
 * blanks — rather than an argument that has to be reviewed against the law of
 * the country it is read in. The rest of this page stays in English for the
 * reason the route group's layout gives; a form does not carry that risk, and
 * a form a person cannot read is not a form that has been offered.
 *
 * The addressee is the operator rather than the merchant of record, on purpose:
 * the contract for the content is with us, the money is held by a store, and a
 * buyer should not have to work out which of the two to write to. We forward it.
 */
const WITHDRAWAL_FORM: ReadonlyArray<{ code: string; language: string; body: string }> = [
  {
    code: "en",
    language: "English",
    body:
      "To Pazl LLC, hello@pazl.ai — I hereby give notice that I withdraw from my contract for the supply of the following digital content: [what you bought]. Ordered on [date]. Name of consumer: [your name]. Email address used: [your address]. Date: [today].",
  },
  {
    code: "es",
    language: "Español",
    body:
      "A la atención de Pazl LLC, hello@pazl.ai — Por la presente le comunico que desisto de mi contrato de suministro del siguiente contenido digital: [qué compraste]. Pedido el [fecha]. Nombre del consumidor: [tu nombre]. Correo utilizado: [tu correo]. Fecha: [hoy].",
  },
  {
    code: "de",
    language: "Deutsch",
    body:
      "An Pazl LLC, hello@pazl.ai — Hiermit widerrufe ich den von mir abgeschlossenen Vertrag über die Lieferung des folgenden digitalen Inhalts: [was du gekauft hast]. Bestellt am [Datum]. Name des Verbrauchers: [dein Name]. Verwendete E-Mail-Adresse: [deine Adresse]. Datum: [heute].",
  },
  {
    code: "it",
    language: "Italiano",
    body:
      "Alla cortese attenzione di Pazl LLC, hello@pazl.ai — Con la presente comunico il recesso dal mio contratto di fornitura del seguente contenuto digitale: [che cosa hai acquistato]. Ordinato il [data]. Nome del consumatore: [il tuo nome]. Email utilizzata: [il tuo indirizzo]. Data: [oggi].",
  },
  {
    code: "fr",
    language: "Français",
    body:
      "À l'attention de Pazl LLC, hello@pazl.ai — Je vous notifie par la présente ma rétractation du contrat portant sur la fourniture du contenu numérique suivant : [ce que tu as acheté]. Commandé le [date]. Nom du consommateur : [ton nom]. Adresse e-mail utilisée : [ton adresse]. Date : [aujourd'hui].",
  },
  {
    code: "pt-BR",
    language: "Português (Brasil)",
    body:
      "Aos cuidados de Pazl LLC, hello@pazl.ai — Comunico pela presente que desisto do meu contrato de fornecimento do seguinte conteúdo digital: [o que você comprou]. Pedido em [data]. Nome do consumidor: [seu nome]. E-mail utilizado: [seu endereço]. Data: [hoje].",
  },
];

export default function RefundsPage() {
  return (
    <>
      <DocHead
        title="Refunds"
        lead="Alma is not the seller. Apple and Google are. That single fact decides most of what follows, so it goes first rather than in a footnote."
      />

      <Sec title="The store you bought in is the merchant of record">
        <Para>
          Everything in Alma is bought inside the app. On {STORE_MERCHANTS[1].platform} the seller
          is {STORE_MERCHANTS[1].merchant}; on {STORE_MERCHANTS[0].platform} it is{" "}
          {STORE_MERCHANTS[0].merchant}. They take the payment, they issue the receipt, they
          calculate and remit the tax, and they hold the money. Your card details never reach us —
          we could not find your purchase by them if we tried.
        </Para>
        <Para>
          So a refund is not a button we can press. The money is in their account rather than ours,
          which is why the request goes to them. We can ask on your behalf, and we do, but the
          decision and the transfer are theirs. Nothing on this website sells anything, so there is
          no third case.
        </Para>
      </Sec>

      <Sec title="How to ask" id="how">
        <Para>
          Each store has a self-service route, and it is faster than we are. Sign in with the
          account that made the purchase:
        </Para>
        <Points>
          <li>
            {STORE_MERCHANTS[1].merchant} —{" "}
            <a href={APPLE.refund} target="_blank" rel="noreferrer">
              {APPLE.refund}
            </a>
            . What can be refunded and how long it takes is{" "}
            <a href={APPLE.refundHelp} target="_blank" rel="noreferrer">
              their own page
            </a>
            .
          </li>
          <li>
            {STORE_MERCHANTS[0].merchant} —{" "}
            <a href={GOOGLE.refund} target="_blank" rel="noreferrer">
              {GOOGLE.refund}
            </a>
            , then request a refund on the purchase. Their policy, including the window in which it
            happens automatically, is{" "}
            <a href={GOOGLE.refundHelp} target="_blank" rel="noreferrer">
              here
            </a>
            .
          </li>
          <li>
            Or write to <a href={`mailto:${CONTACT}`}>{CONTACT}</a> with the email address on your
            Alma account — or the account id from Settings if you never signed in — and the order
            number from the store's receipt. We ask them for you, and we tell you what they said
            even when the answer is no.
          </li>
        </Points>
        <Para>
          Which of those to use: the store, if you simply want your money back. Us, if the reason is
          something we did — because then we are the ones with the evidence, and a request that
          arrives from us with the fault described is a different request from an anonymous one.
        </Para>
      </Sec>

      <Sec title="Where we ask for a refund without arguing">
        <Para>These are our faults, or your right, and neither is a judgement call:</Para>
        <Points>
          <li>The reading never generated, or generated and would not open.</li>
          <li>The chart was wrong because of an error on our side rather than a birth time you were unsure of.</li>
          <li>You were charged twice for the same thing.</li>
          <li>You were charged after cancelling.</li>
          <li>An outage of ours cost you a subscription month you had paid for.</li>
          <li>
            You changed your mind within fourteen days — see{" "}
            <a href="#withdrawal">the withdrawal right</a> below, which we do not treat as
            waived.
          </li>
        </Points>
        <Para>
          You do not have to prove any of this. If the record shows it, we ask for the
          refund and we tell you it has been asked for.
        </Para>
      </Sec>

      {/* The factual foundation of everything below it. Put before the legal
          section rather than inside it, because a reader deciding whether to
          ask for their money back needs the mechanism more than the article
          number, and because the article number only means what it means once
          you know when the writing actually happens. */}
      <Sec title="Nothing is written until you open it">
        <Para>
          A chapter is generated the first time you open it, not at the moment you pay. The archive
          is forty-one chapters across eight systems, eight of which are the free samples anybody
          can read; buying it opens the other thirty-three, and opening them is not the same as
          writing them. Each one is written when you go to it, from your chart as it stands then,
          and stored so that it says the same thing every time afterwards.
        </Para>
        <Para>
          That is the reason this page can say what it says next. At the second the store charges
          you, nothing has been delivered — and a promise that you have given up a right over text
          nobody has written yet is not a promise anybody should be asked to keep.
        </Para>
      </Sec>

      <Sec title="The 14-day withdrawal right, which we do not treat as waived" id="withdrawal">
        <Para>
          In the EU and the UK you have fourteen days to change your mind about something bought
          online. Digital content can be an exception to that, but only when three things have
          happened: you expressly agreed that supply starts immediately, you acknowledged that
          starting immediately costs you the right, and you were sent confirmation of both on
          something durable — an email you keep, not a page you passed through.
        </Para>
        <Para>
          None of those three is collected by a store's purchase sheet, and we no longer run a
          checkout that could collect them. So we do not stand on the waiver at all. If you tell us
          within fourteen days of buying that you have changed your mind, we ask the store for the
          whole price back, we do not ask you why, and we do not tell you to read a policy first.
        </Para>
        <Para>
          What we cannot do is pay it ourselves, and this page will not pretend otherwise. The money
          is with Apple or Google. What we can do is ask, say plainly that the right applies, and
          keep asking — and if a store refuses a withdrawal the law gives you, tell us, because that
          is a case we want to know about rather than one we would like you to give up on.
        </Para>
        <Para>
          When the whole price comes back, what it bought closes: the archive stops opening, or the
          system you bought stops opening. Money back with the reading kept is not a refund, it is
          a hundred percent discount, and we would rather refuse the second than pretend it is the
          first.
        </Para>
        <Para>
          We do not deduct for the chapters already written for you, and we do not split the
          purchase into the part that was performed and the part that was not. We could — we know
          exactly which chapters exist — but any figure we set for how much of a book you have read
          would be a number we invented, and one invented number is worse for this document than a
          policy that occasionally costs us a sale. Writing on demand is what makes that question
          arise at all, and the risk of it is ours rather than yours.
        </Para>
        <Para>
          If there is an email address on your Alma account, a confirmation of what you bought is
          sent to it as well as the store's own receipt. Where that letter and this page do not say
          quite the same thing, this one is the more generous of the two and this one is the one
          that is honoured.
        </Para>
        <Para>
          After the fourteen days, the list above is the policy: our faults, asked for without
          argument, and otherwise a request we forward and the store decides.
        </Para>
      </Sec>

      {/* The annual cannot hide behind the section above. Art. 16(a) does not
          extinguish withdrawal on a twelve-month contract until the service is
          *fully performed*, which a year is not on day ten, and Art. 14(3) is
          what decides the number. Which store is asked does not change either
          article; what it changes is who does the arithmetic, and that is said
          rather than smoothed over. */}
      <Sec title="A year is not delivered on the first day">
        <Para>
          The yearly plan is a different case in law and in fact. It is not a thing handed over at
          once — it is twelve months of access to everything, including systems that are rewritten
          as the sky moves, and on day ten of it nothing like the whole has been performed. No
          purchase sheet ends your right to withdraw from a service that has barely started.
        </Para>
        <Para>
          So: withdraw from a plan within fourteen days and what is owed back is the part of the
          year you have not used, worked out on the days that have passed, and the plan ends there
          rather than running on. We close the plan at our end the same day rather than leaving it
          quietly running to its original date; the money is returned by the store, and the
          proportion is the one the law sets rather than one either of us prefers. After fourteen
          days the ordinary rule takes over — cancelling stops the next charge and the period you
          have already paid for runs to its end, with your access intact until it does.
        </Para>
        <Para>
          It is asked for rather than pressed: there is no withdrawal button in Alma, and this page
          will not pretend otherwise. Write to <a href={`mailto:${CONTACT}`}>{CONTACT}</a>, in any
          words, or use the form below. A person answers it.
        </Para>
      </Sec>

      <Sec title="Subscriptions">
        <Para>
          Cancelling stops the next charge. It does not undo the period you are in: that period was
          paid for and it runs to its end, with your access intact until it does. Nothing is taken
          back at the moment you cancel, which is why the screen tells you the date instead.
        </Para>
        <Para>
          Cancelling happens on the store's own account screen, because that is where a subscription
          bought in an app lives. The two taps, and what happens after them, are in{" "}
          <Link href="/subscription-terms#cancel">subscription terms</Link>.
        </Para>
      </Sec>

      <Sec title="One-time purchases">
        <Para>
          A system bought outright is yours permanently. It does not lapse, it is not rented, and
          cancelling a subscription does not take it away.
        </Para>
        <Para>
          If you bought one system and then want the rest within thirty days, the rest of the
          archive is offered at its price less what you paid for that reading. You do not have to
          ask for it and you do not have to refund anything to get it. Two conditions are worth
          knowing rather than discovering: it is offered while you hold one system and nothing
          wider, and it is set against the price in the currency you actually paid in — we do not
          convert what you paid into another currency to work it out.
        </Para>
      </Sec>

      {/* CRD Art. 6(1)(h) asks for the conditions, the deadline, the procedure
          **and** the model form of Annex I(B). The first three were on this page
          in prose; the form was nowhere in the repository. It is short, it is
          the same six sentences in every language, and unlike the rest of this
          document it is a form rather than an argument — so it is the one part
          that can honestly be given in all six without a per-jurisdiction
          review behind it. Nobody is required to use it: an email saying "I
          withdraw" is a withdrawal, and that is said before the form rather
          than after it. */}
      <Sec title="The withdrawal form, if you would rather use one" id="form">
        <Para>
          You do not need this. An email to <a href={`mailto:${CONTACT}`}>{CONTACT}</a> saying you
          have changed your mind is a withdrawal, in any words and in any language, and we answer
          it the same way. The form exists because European law says a trader has to offer one, and
          because some people would rather fill in a form than write a letter.
        </Para>
        <Para>
          Copy the version in your own language, fill in the four blanks, and send it to{" "}
          <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. We act on it and we forward it to the store
          that took the payment, so that you do not have to send it twice.
        </Para>
        {WITHDRAWAL_FORM.map((form) => (
          <div key={form.language} className="legal-form" lang={form.code}>
            <p className="legal-form-lang">{form.language}</p>
            <p className="legal-form-body">{form.body}</p>
          </div>
        ))}
      </Sec>

      <Sec title="How the money comes back">
        <Para>
          To the payment method you bought with, by the store that took it. How long it then takes
          to appear is between their systems and your bank, and any number we printed here would be
          a guess about somebody else&rsquo;s.
        </Para>
      </Sec>

      {/* Named once, at the bottom, and only for somebody whose receipt does
          not come from a store. The adapters still ship and the seam still
          selects one, so this is a live path rather than history — but it sells
          nothing today, and putting it any higher would tell the overwhelming
          majority of readers that their money is somewhere it is not. */}
      <Sec title="If your receipt did not come from Apple or Google">
        <Para>
          Then the payment went through {MERCHANT}, the card processor Alma is configured with, and
          they are the merchant of record for it: same principle, different company. Their receipt
          carries their own support link, and everything above applies with their name in place of
          the store&rsquo;s. If you are not sure which of the three you paid, send us the receipt
          and we will tell you.
        </Para>
      </Sec>

      <DocFoot />
    </>
  );
}
