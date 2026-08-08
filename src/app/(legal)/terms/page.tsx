import type { Metadata } from "next";
import Link from "next/link";
import { Blank, DocFoot, DocHead, Para, Points, Sec } from "@/components/legal/Doc";
import { CONTACT, MIN_AGE, OPERATOR, STORE_MERCHANTS } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Terms · Alma",
  description: "What Alma is, what it refuses to be, and what we each owe the other.",
};

/**
 * Terms, written as what they actually are: the short list of things we
 * promise and the short list of things we ask.
 *
 * The "not advice" section is the one that matters and it is deliberately not
 * at the bottom in small type. It describes a rule the generation layer
 * enforces on every reading, so it belongs where a person will read it, stated
 * as a commitment rather than as a shield.
 */
export default function TermsPage() {
  return (
    <>
      <DocHead
        title="Terms"
        lead="What you get, what Alma will not do, and the few things we ask of you. Nothing here is a trick, and there is no clause below that contradicts a sentence above it."
      />

      <Sec title="What Alma is">
        <Para>
          Alma calculates a chart from your birth date, time and place, and writes readings from
          it. The calculation is arithmetic and is the same for everyone. The readings are written
          by a language model that is given your chart and is allowed to cite only what is in it.
        </Para>
        {/* This said "{MERCHANT} sells it" while the web had a checkout. It
            has not sold anything since: the ladder is bought inside the apps,
            and the seller is whichever store took the money. Naming the card
            processor here made the first factual sentence of the terms wrong
            for every actual buyer. */}
        <Para>
          {OPERATOR} operates Alma and writes it. It is bought inside the app, and the seller is the
          store you bought in — {STORE_MERCHANTS[1].merchant} on {STORE_MERCHANTS[1].platform},{" "}
          {STORE_MERCHANTS[0].merchant} on {STORE_MERCHANTS[0].platform}. They take the money and
          issue the receipt; we open what it bought. See{" "}
          <Link href="/subscription-terms">subscription terms</Link>. Nothing is sold on this
          website.
        </Para>
      </Sec>

      <Sec title="What Alma is not">
        <Para>
          Alma is not medical, legal or financial advice, and it does not predict events. It will
          not tell you whether to take the job, leave the person, or have the operation.
        </Para>
        <Para>
          This is not a disclaimer bolted to the end of a page. It is a rule enforced where the
          readings are generated: Alma is instructed never to diagnose, never to advise on money or
          law, and never to state that something will happen. A reading that does any of those
          things is a fault in our system, not fine print you failed to read. Tell us at{" "}
          <a href={`mailto:${CONTACT}`}>{CONTACT}</a> and we will fix it.
        </Para>
        <Para>
          If you are unwell, in danger, or making a decision with money or law in it, talk to
          someone qualified. Alma is for self-knowledge, and self-knowledge is not a second
          opinion.
        </Para>
      </Sec>

      <Sec title="Who may use it">
        <Para>
          Anyone aged {MIN_AGE} or over. You can read your chart, and even buy, without giving us
          an address: an unsigned-in visitor is already an account with an id, and what signing in
          adds is durability rather than permission.
        </Para>
        <Para>
          But an account with no address is an account nobody can get back into, and one we cannot
          write to about a renewal. Sign-in is a passwordless link to an inbox, so the inbox is the
          account — lose access to it and you lose access to Alma. See{" "}
          <Link href="/subscription-terms">subscription terms</Link> for what a missing address
          costs you specifically.
        </Para>
      </Sec>

      <Sec title="What we ask of you">
        <Points>
          <li>
            Enter your own birth data honestly. A guessed birth time produces a chart that is
            entirely plausible and completely wrong, and Alma cannot tell the difference.
          </li>
          <li>
            If you enter someone else&rsquo;s birth data for a compatibility reading, ask them
            first. It is their birth data, not yours.
          </li>
          <li>
            Do not scrape Alma, resell its readings, or present them as a product of your own. What
            Alma writes for you is yours to keep, print, quote and share.
          </li>
          <li>Do not attack the service or try to reach other people&rsquo;s charts.</li>
        </Points>
      </Sec>

      <Sec title="What we owe you">
        <Para>
          The readings you bought outright, kept available while your account exists. One-time
          purchases are permanent; they do not expire when a subscription does.
        </Para>
        <Para>
          A plan is the other case, and it is worth being exact about: readings written for you
          while a plan is running stay in your account when the plan ends, but they stop opening,
          because what a plan sells is the year rather than the text. That is set out in{" "}
          <Link href="/subscription-terms">subscription terms</Link>, and it is the reason the
          archive is sold separately at all.
        </Para>
        <Para>
          Alma will not be up every second of every year. Nobody&rsquo;s service is. If it is down
          when you want it, it will come back — and if an outage of ours cost you a month you paid
          for, we will ask the store that took the money to refund it, because they are who holds
          it. See <Link href="/refunds">refunds</Link>.
        </Para>
        {/* The promise stays; what changed is that it now says who sends it and
            admits who it cannot reach. Alma sends exactly two automated emails —
            the sign-in link and the notice before a renewal — and a terms change
            is neither. It happens rarely enough to be a letter a person writes,
            and saying that is better than implying a machine is watching. */}
        <Para>
          If we change these terms, you get an email before the change takes effect, not a silently
          updated date at the top of a page. That letter is written by hand and sent to the address
          on your account, because Alma has no mailing list and nothing automatic that could send
          it.
        </Para>
        <Para>
          Which means: if you have never given us an address, there is no channel that reaches you,
          and the date at the top of this page is the only notice there is. That is a reason to
          sign in, not a loophole we are pleased with.
        </Para>
      </Sec>

      <Sec title="If something goes wrong">
        <Para>
          If we cause you loss, our responsibility is limited to what you paid for the thing that
          went wrong. Alma is a reading, not a professional service, and it should not be relied on
          as one — which is the same sentence as the section above, in the language of liability.
        </Para>
        <Para>
          Nothing here removes a right your own country gives you. Where the two disagree, your
          country wins.
        </Para>
      </Sec>

      <Sec title="Ending it">
        {/* This paragraph used to say deletion needs a signed-in account,
            because it did: the route was behind `require_account` and the
            confirmation was compared against an address a guest has not got.
            That meant demanding more personal data as the price of removing the
            birth date and coordinates already taken. `account.py` now takes the
            current user and confirms against `user.email or user.id`. */}
        <Para>
          You can delete your account in Settings, at any moment, without asking us and without
          explaining. It takes effect immediately and it takes your data with it — see{" "}
          <Link href="/privacy">privacy</Link> for the list, and{" "}
          <Link href="/delete-account">the deletion page</Link> for the steps.
        </Para>
        <Para>
          That includes an account you never signed into. Reading without one is allowed and so is
          buying without one, so a guest account is where most of the birth data in Alma lives; it
          is deleted on the same terms, confirmed with the account id shown on the screen instead of
          an address. Where an app has not caught up with that yet, its Settings screen asks you to
          sign in first — <Link href="/delete-account">the deletion page</Link> says which, and in
          that case write to <a href={`mailto:${CONTACT}`}>{CONTACT}</a> and we do it by hand. That
          is a person and a working day rather than a button, and stating it is better than a
          sentence promising otherwise on a screen where the button is greyed out.
        </Para>
        <Para>
          We may close an account that is attacking the service or using it against other people.
          If we do, you get the email and the reason — or, where there is no address on the
          account, the reason on request at <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </Para>
      </Sec>

      <Sec title="Law">
        <Para>
          These terms are governed by the law of <Blank>governing law</Blank>, and disputes are
          heard in <Blank>venue</Blank>. Both are being confirmed and are left blank rather than
          guessed at.
        </Para>
      </Sec>

      <DocFoot />
    </>
  );
}
