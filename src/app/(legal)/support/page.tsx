import type { Metadata } from "next";
import Link from "next/link";
import { LanguagePicker } from "@/components/landing/LanguagePicker";
import { Para, Points, Sec } from "@/components/legal/Doc";
import { dictionary } from "@/lib/i18n";
import { currentLocale } from "@/lib/locale-server";
import { CONTACT, OPERATOR } from "@/lib/legal";
import { APPLE, GOOGLE } from "@/lib/support";

/**
 * The page App Store Connect will not accept a submission without.
 *
 * Apple's Support URL is a required field and must *"lead to actual contact
 * info"*. That is the low bar. The bar this page is written to is the one that
 * decides whether the letter it produces is answerable: **Apple and Google are
 * the merchants of record, so we cannot refund anybody ourselves.** A support
 * page that implies we can generates the angriest email in the product — a
 * person who has been charged twice, has read a page telling them we will fix
 * it, and is then told to go and ask a company they did not think they were
 * buying from. So the sentence "we cannot refund you" is above the fold rather
 * than in a footnote, and the two places that *can* refund are named with their
 * real addresses.
 *
 * ── why this one is translated when the five documents are not ────────────
 * The legal route group is English-only, deliberately, and its layout says why:
 * a consumer-law argument has to be reviewed against the law of the country it
 * is read in, and six confident unreviewed translations are worse than one
 * original. None of that applies here. This is an address, a list of what to
 * put in a letter, and directions to two other companies' screens — and it is
 * read by somebody who is already annoyed and should not also have to work in
 * English. `lang` is set on the wrapper below, which overrides the group
 * layout's `lang="en"` for this subtree exactly as nested `lang` is meant to.
 *
 * ── why it renders on the server with no client JavaScript ────────────────
 * The reader we cannot afford to lose is a store reviewer opening a URL cold.
 * `useT()` would have worked for a person and produced an English first paint
 * for anybody whose language came from a header. `currentLocale()` reads the
 * cookie and `Accept-Language` on the server, so the translated text is in the
 * HTML that arrives.
 *
 * ── why no sentence contains a link ───────────────────────────────────────
 * Every destination is its own line with the address as the link text. An
 * anchor buried inside a sentence has to move when the sentence is translated,
 * and the failure is silent: the link survives, wrapped around the wrong two
 * words. See the note above `support` in `i18n/en.ts`.
 */
export async function generateMetadata(): Promise<Metadata> {
  const t = dictionary(await currentLocale()).support;
  return { title: `${t.title} · Alma`, description: t.lead };
}

export default async function SupportPage() {
  const locale = await currentLocale();
  const d = dictionary(locale);
  const t = d.support;

  return (
    <div lang={d.meta.htmlLang}>
      <div className="legal-eyebrow">Alma · {OPERATOR}</div>
      <h1 className="legal-title">{t.title}</h1>
      <div className="legal-rule" />
      <p className="legal-lead">{t.lead}</p>

      <Sec title={t.writeTitle}>
        <Para>{t.write1}</Para>
        {/* The address, alone on a line and large enough to be the answer to
            the question the page was opened with. Everything below it is
            detail; this is the contact information Apple asks for. */}
        <Para>
          <a href={`mailto:${CONTACT}`}>{CONTACT}</a>
        </Para>
        <Para>{t.write2}</Para>
      </Sec>

      <Sec title={t.includeTitle}>
        <Points>
          <li>{t.include1}</li>
          <li>{t.include2}</li>
          <li>{t.include3}</li>
          <li>{t.include4}</li>
        </Points>
        <Para>{t.includeNote}</Para>
      </Sec>

      <Sec title={t.moneyTitle} id="refunds">
        <Para>{t.money1}</Para>
        <Para>{t.money2}</Para>
        <Points>
          <li>
            {t.refundApple}
            <br />
            <a href={APPLE.refund} target="_blank" rel="noreferrer">
              {APPLE.refund}
            </a>
          </li>
          <li>
            {t.refundGoogle}
            <br />
            <a href={GOOGLE.refund} target="_blank" rel="noreferrer">
              {GOOGLE.refund}
            </a>
          </li>
        </Points>
        <Para>{t.money3}</Para>
      </Sec>

      <Sec title={t.cancelTitle} id="cancel">
        <Para>{t.cancel1}</Para>
        <Points>
          <li>
            <a href={APPLE.subscriptions} target="_blank" rel="noreferrer">
              {APPLE.subscriptions}
            </a>
          </li>
          <li>
            <a href={GOOGLE.subscriptions} target="_blank" rel="noreferrer">
              {GOOGLE.subscriptions}
            </a>
          </li>
        </Points>
        <Para>{t.cancel2}</Para>
      </Sec>

      <Sec title={t.dataTitle}>
        <Para>{t.data1}</Para>
        <Points>
          <li>
            <Link href="/delete-account">{d.footer.deleteAccount}</Link>
          </li>
        </Points>
      </Sec>

      <Sec title={t.readingTitle}>
        <Para>{t.reading1}</Para>
        <Para>{t.reading2}</Para>
      </Sec>

      <Sec title={t.whoTitle}>
        <Para>{t.who1}</Para>
      </Sec>

      {/* The five documents, by the names the footer already gives them in
          this language. The note says they are in English before the reader
          clicks, rather than after. */}
      <Sec title={t.moreTitle}>
        <Points>
          <li>
            <Link href="/refunds">{d.footer.refunds}</Link>
          </li>
          <li>
            <Link href="/subscription-terms">{d.footer.subscriptionTerms}</Link>
          </li>
          <li>
            <Link href="/privacy">{d.footer.privacy}</Link>
          </li>
          <li>
            <Link href="/terms">{d.footer.terms}</Link>
          </li>
          <li>
            <Link href="/imprint">{d.footer.imprint}</Link>
          </li>
        </Points>
        <Para>{t.moreNote}</Para>
      </Sec>

      {/* The one control on this page, and the only page in this route group
          that gets one.

          `/support` is the URL Apple requires in order to reach a human, so it
          is opened by people who are already stuck — and it honours the locale
          cookie, which means it arrives in whatever language was negotiated
          from `Accept-Language` on whichever device the person happened to
          open it on. The picker lives in the landing's footer, four routes
          away, on a page they have navigated off. That is the Briton in Spain
          again, relocated rather than solved, on the page where being unable to
          read costs the most.

          The five *documents* beside it deliberately do not get one: the group
          layout renders them under `lang="en"` by policy — a consumer-law
          argument has to be reviewed per jurisdiction before it can be
          translated — so a picker there would offer a choice the page cannot
          honour. This page is translated, which is exactly why it can be
          switched. */}
      <div className="legal-lang">
        <LanguagePicker />
      </div>

      {/* Not `DocFoot`: that foot is two sentences of English about legal
          wording, on a page whose whole point is that it is not in English. The
          address and the operator are the parts that belong here, and neither
          needs translating. */}
      <div className="legal-foot">
        <a href={`mailto:${CONTACT}`}>{CONTACT}</a>
        <br />
        {OPERATOR} · Wyoming, United States
      </div>
    </div>
  );
}
