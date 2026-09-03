import type { Metadata } from "next";
import Link from "next/link";
import { Blank, DocFoot, DocHead, Fact, Para, Sec } from "@/components/legal/Doc";
import { CONTACT, MERCHANT, MIN_AGE, OPERATOR, STORE_MERCHANTS } from "@/lib/legal";
import { MERCHANT_RU } from "@/lib/merchant-ru";

export const metadata: Metadata = {
  title: "Imprint · Alma",
  description: "Who operates Alma, who sells it, and where the numbers come from.",
};

/**
 * Who is behind this, and what it was built out of.
 *
 * The attribution block is not decoration either: the place index is GeoNames
 * data under CC BY 4.0, and CC BY is a licence whose single obligation is the
 * credit. It costs one line, and this is the line.
 */
export default function ImprintPage() {
  return (
    <>
      <DocHead
        title="Imprint"
        lead="Who operates Alma, who sells it, and where the numbers behind every chart come from."
      />

      {/*
       * Four rows, not eight — and the four that went are a decision rather
       * than an oversight.
       *
       * This block was written against a German Impressum, which is the wrong
       * statute. DDG §5 and MStV §18 are what ask a company to name the natural
       * person representing it and a second one responsible for its content,
       * and they bind providers *established in Germany*. Alma's operator is a
       * Wyoming LLC with no establishment in the EU, so neither applies, and
       * publishing a private individual's name to satisfy a law that does not
       * reach us is a real disclosure bought with nothing.
       *
       * The VAT row went for a stronger reason: there is no number. Every sale
       * is an in-app purchase, which makes Apple and Google the deemed supplier
       * under Art. 9a of Implementing Regulation 282/2011 — they are the
       * merchant of record, they calculate and remit the tax, and the operator
       * is not VAT-registered in the EU at all. A blank there implied a number
       * was being withheld. The Seller section below states the true position,
       * and the honest thing is to say it rather than to leave a gap that reads
       * as unfinished paperwork.
       *
       * Registration number went with them: the ECD's trade-register duty binds
       * EU-established providers, and Wyoming's filing id is public record in a
       * registry anyone can search — carrying it here buys no reader anything.
       *
       * What stays is what a reader is actually owed and what the law that does
       * reach us actually asks for: who the company is, where it is, and how to
       * reach a human. All three are published on the App Store and Play
       * listings anyway under the DSA's trader rules, so this page agrees with
       * the stores instead of disagreeing with them.
       */}
      <Sec title="Operator">
        <div className="legal-facts">
          <Fact label="Company">{OPERATOR}</Fact>
          <Fact label="Registered">Wyoming, United States</Fact>
          <Fact label="Address">
            <Blank>registered address</Blank>
          </Fact>
          {/* This one is not in the same family as the rows above and was not
              removed with them. Art. 27 obliges a controller outside the Union
              that offers services to people inside it to appoint a
              representative there, and Art. 13(1)(a) obliges us to publish who
              that is. The Art. 27(2) exemption is for occasional processing;
              birth data and conversations from EU users are neither occasional
              nor incidental. The name that appears here is a service company's,
              not a private person's — so it costs no individual any privacy,
              which is what separates it from the four that went. */}
          <Fact label="EU representative (GDPR Art. 27)">
            <Blank>name and address of the EU representative</Blank>
          </Fact>
          <Fact label="Contact">
            <a href={`mailto:${CONTACT}`}>{CONTACT}</a>
          </Fact>
        </div>
        <Para>
          {OPERATOR} is not VAT-registered in the European Union and has no VAT identification
          number to show. It does not need one: everything is bought inside an app, which makes the
          store the deemed supplier, and the store charges and remits the tax under its own
          registration. That is set out below.
        </Para>
        <Para>
          The two blanks are blank because nobody has supplied those details yet. Both are required
          where Alma is sold, and a plausible-looking address would be worse than an obvious gap.
        </Para>
      </Sec>

      <Sec title="Seller">
        <Para>
          Alma is bought inside the app, and the merchant of record is the store it was bought in:{" "}
          {STORE_MERCHANTS[1].merchant} on {STORE_MERCHANTS[1].platform},{" "}
          {STORE_MERCHANTS[0].merchant} on {STORE_MERCHANTS[0].platform}. They are the seller, the
          invoice issuer and the party that handles tax, and their own company details are on every
          receipt they send.
        </Para>
        <Para>
          A payment made outside a store — the card processor Alma is configured with is{" "}
          {MERCHANT} — makes them the merchant of record for that purchase instead. What either
          case means in practice is set out in <Link href="/refunds">refunds</Link> and{" "}
          <Link href="/subscription-terms">subscription terms</Link>.
        </Para>
        {/* Полные реквизиты продавца рублёвой витрины живут ЗДЕСЬ, а не на
            странице оплаты, — слово владельца от 02.09.2026 («без адреса
            там, адрес в документе»): витрине — короткая строка, документу —
            всё, что требует закон об оферте. Источник — lib/merchant-ru.ts,
            вторых копий этих строк быть не должно. */}
        <div id="ru-seller">
          <Para>
            Покупателям из России веб-оплату (когда она включена) продаёт
            индивидуальный предприниматель — реквизиты продавца:
          </Para>
          <div className="legal-facts" lang="ru">
            <Fact label="Продавец">{MERCHANT_RU.name}</Fact>
            <Fact label="ИНН">{MERCHANT_RU.inn}</Fact>
            <Fact label="ОГРНИП">{MERCHANT_RU.ogrnip}</Fact>
            <Fact label="Адрес">{MERCHANT_RU.address}</Fact>
            <Fact label="Банк">{MERCHANT_RU.bank}</Fact>
            <Fact label="Р/с">{MERCHANT_RU.account}</Fact>
            <Fact label="БИК">{MERCHANT_RU.bik}</Fact>
            <Fact label="К/с">{MERCHANT_RU.corrAccount}</Fact>
          </div>
        </div>
      </Sec>

      <Sec title="The product">
        <Para>
          Alma calculates a chart and writes readings from it. It is for people aged {MIN_AGE} and
          over. It is not medical, legal or financial advice and it does not predict events — a
          commitment enforced where the readings are generated, and stated in full in{" "}
          <Link href="/terms">terms</Link>.
        </Para>
      </Sec>

      <Sec title="Where the numbers come from">
        <Para>
          Positions are computed from the DE440s planetary ephemeris produced by NASA&rsquo;s Jet
          Propulsion Laboratory. It is a work of the United States government and requires no
          attribution; it is credited here because it is the reason the numbers are right.
        </Para>
        <Para>
          Time zones, including their history, come from the IANA time zone database. A birth in
          1978 is converted with the rules that were in force in 1978, not today&rsquo;s.
        </Para>
        <Para>
          Places and their coordinates come from GeoNames. This product includes GeoNames data,
          licensed under{" "}
          <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">
            CC BY 4.0
          </a>
          . © GeoNames,{" "}
          <a href="https://www.geonames.org/" target="_blank" rel="noreferrer">
            geonames.org
          </a>
          .
        </Para>
        <Para>
          Readings are generated by Anthropic&rsquo;s models from that calculated chart. What is
          sent to them, and what is not, is listed in <Link href="/privacy">privacy</Link>.
        </Para>
      </Sec>

      <Sec title="Set in">
        <Para>Playfair Display and Golos Text.</Para>
      </Sec>

      <DocFoot />
    </>
  );
}
