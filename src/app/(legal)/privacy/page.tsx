import type { Metadata } from "next";
import Link from "next/link";
import { Blank, DocFoot, DocHead, Para, Points, Sec } from "@/components/legal/Doc";
import {
  BACKUP_WINDOW_DAYS,
  CONTACT,
  FUNNEL_RETENTION_DAYS,
  MERCHANT,
  MIN_AGE,
  OPERATOR,
  STORE_MERCHANTS,
} from "@/lib/legal";

export const metadata: Metadata = {
  title: "Privacy · Alma",
  description: "What Alma holds about you, what leaves the service, and how to take it all back.",
};

/**
 * The one document where the product either keeps its promise or does not.
 *
 * Alma asks for a birth time. There is no more intimate number a stranger can
 * ask you for and no way to make the reading honest without it, so the least
 * this page can do is name every field, every recipient and every reason,
 * without a single sentence of the "we may share with selected partners"
 * hedging that exists to keep options open.
 */
export default function PrivacyPage() {
  return (
    <>
      <DocHead
        title="Privacy"
        lead="Alma is built on the most personal numbers you have. Here is every one of them we hold, everywhere they go, and how to take them back."
      />

      <Sec title="What Alma holds">
        <Para>All of it. Nothing on this list is optional to disclose:</Para>
        <Points>
          {/* This used to end "until then there is a row with an id and no
              address on it, which is what reading Alma without signing in
              actually is" — accurate, and describing a row that was created by
              looking at the page. It is now created by an act, and the sentence
              has to say which act, because "we make an account for you at some
              point" is the kind of vagueness this page exists not to have. */}
          <li>
            Your email address, once you have given us one. It is your account and it is how you
            sign in; until then there is a row with an id and no address on it, which is what
            reading Alma without signing in actually is. On this website that row is created the
            moment you save your birth data or sign in, and not before — reading the page, or
            starting the questions and closing the tab, creates nothing. In the apps it is created
            when the app first reaches the server, because everything the app can show you is
            already something it has to ask for on your behalf.
          </li>
          <li>Your birth date.</li>
          <li>Your birth time, if you gave one. You can use Alma without it; some of the chart is unavailable until you do.</li>
          <li>Your birth place, stored as coordinates and the time zone they fall in.</li>
          <li>Your name, if you gave one. Alma works without it.</li>
          <li>The readings Alma generated for you.</li>
          <li>Your conversations with Alma.</li>
          <li>A small memory of facts you stated about yourself in those conversations, so you do not have to repeat them.</li>
          <li>
            Counters: how many readings were written for your account on a given day, how many
            questions you asked, and what those generations cost us. Two things in the same table
            are not counts and are worth naming: whether you have been shown the one cheaper offer
            we are allowed to show after a refusal, and which renewal letters were sent to you and
            when. They hold numbers, dates and single words — never text of yours.
          </li>
          {/* Kept, narrowed, and worth the sentence that says why: there is no
              checkout in Alma any more. A store's purchase sheet collects no
              consent for us, so this table is written by nothing on the app
              path — but the row type and the card-processor route that fills it
              both still ship, and a policy that stops disclosing a table
              because it is currently empty is a policy that will be wrong the
              day it is not. */}
          <li>
            The exact sentences you ticked at a checkout, with the language you read them in and
            the moment you ticked — where there was a checkout. Buying inside an app is a purchase
            sheet belonging to Apple or Google, which asks you to tick nothing on our behalf, so
            nothing of this kind is recorded for it. Where the record does exist it is the reason
            the confirmation in your inbox can quote your consent back instead of paraphrasing it,
            and it is what the law asks us — not you — to be able to prove. A checkout opened and
            never paid for leaves a record that is deleted with your account, because it is
            evidence of nothing.
          </li>
          <li>
            A sign-in link you asked for: the address it was sent to, when it was made, when it
            expires and whether it has been used. It holds no password, because there is none.
          </li>
          <li>
            What you bought, when, in which currency, and the id the payment processor gave it.
            Not your card — that never reaches us.
          </li>
          <li>
            Which steps of the product were reached: the landing opened, the quiz started, the quiz
            finished, the portrait seen — and, in the apps, the paywall shown and the purchase made.
            Short labels, never a page address, a referrer, an IP address, a user agent, or anything
            you typed — the code that writes these refuses any field that is not on a short list of
            words describing the product rather than the person.
          </li>
          {/* Named as its own item rather than folded into the line above,
              because it is the one thing on this page that exists in somebody's
              browser before there is an account to attach it to. The previous
              version of this page could say "against an account id" and be
              complete, for a bad reason: the funnel beacon minted an account
              for every page view, so two thirds of the accounts were people who
              had never typed anything. Fixing that is what created this. */}
          <li>
            A random id for your browser, or for your copy of the app, kept with those step labels.
            It is the answer to one question — of the people who opened the landing, how many
            finished — which cannot be asked without some way of telling one visit from another, and
            which we would otherwise have answered by creating an account for you before you had
            done anything. It is a random string and nothing more: not built from your device, your
            screen, your address or anything else about you, and it signs you into nothing. If you
            later save a birth or sign in, it is attached to the account created at that moment, so
            that the steps you took before it existed are still yours. Clearing this site&rsquo;s
            data removes it, deleting the app removes it, and it is replaced with a new one after{" "}
            {FUNNEL_RETENTION_DAYS} days in any case. In a browser, if yours sends Do Not Track or
            Global Privacy Control, none of it is created in the first place — no id is stored and
            no step label is sent. In the Android app the same switch is in Settings. On iPhone
            there is no such switch yet, so the id is created there on first launch; nothing else
            about what is collected differs.
          </li>
          {/* The push token, named as its own item rather than folded into
              the random-id line above it, because they are two different
              identifiers with two different lifetimes and only one of them is
              ours. Absent from this page entirely until the daily shipped,
              which made it a category of personal data that was never
              lawfully disclosed. */}
          <li>
            An identifier for your phone, if — and only if — you turn on the daily notification.
            It is issued by Apple or Google, not by us; it is what a notification is addressed to,
            and there is no way to send you one without it. It is held while the daily is switched
            on and deleted the moment you switch it off, the moment your phone tells us the
            permission is gone, and with your account. If you simply stop opening the app it is
            deleted anyway after ninety days, and we stop sending after sixty. It is not an
            advertising identifier, it is never joined with anyone else&rsquo;s data, and it is the
            one thing on this list your export does not contain — it is a live key to your phone,
            and making copies of it to prove we hold it would be the opposite of the point. The
            export names the device instead.
          </li>
        </Points>
        <Para>
          Sign-in is passwordless. There is no password field anywhere in Alma, so there is no
          password stored, no password to leak, and no password of yours that a breach somewhere
          else can be tried against.
        </Para>
      </Sec>

      <Sec title="Why each of them exists">
        <Para>
          The birth date, time and place are the calculation. Without them there is no chart, and
          without a chart there is nothing to read — this is the whole of what Alma does, not a
          convenience.
        </Para>
        <Para>
          The email address is the account. The readings and conversations are the thing you paid
          for and came back for. The memory exists so that Alma does not ask you the same question
          in March that you answered in January.
        </Para>
        <Para>
          The counters exist because a free tier has to be countable and a generation costs us real
          money; they are read to answer &ldquo;has this account had its three questions today&rdquo;
          and nothing else.
        </Para>
        <Para>
          The step labels are how we find out where people give up — whether the quiz is too long,
          whether the offer arrives too early. That question is about the product, so the answer is
          kept as words about the product.
        </Para>
        <Para>
          Nothing here is collected to build a profile of you for anyone else. There is no
          third-party analytics in Alma, no advertising tag, and nobody outside the companies named
          below receives anything about you: what we count, we count in our own database. If
          your browser sends Do Not Track or Global Privacy Control, the step labels are not
          recorded at all and the random id is never created — that is checked on every one of them
          rather than once when the page loads, so turning it on mid-session works, and the id is
          only ever written by the same code that has just checked.
        </Para>
      </Sec>

      <Sec title="What leaves the service">
        <Para>
          Four companies at most, depending on where you bought, and this is the complete list. Only
          one of them ever takes a payment from you, and it is a store.
        </Para>
        <Points>
          <li>
            <strong>Anthropic</strong> generates the readings. What is sent is the calculated chart
            — positions, aspects, the numbers — the question you asked, and the short facts Alma
            remembers about you, because a reading that has forgotten what you said in January is
            the thing you are paying not to get. That last part is free text you typed, which makes
            it the most personal item on this list and the reason it is named here rather than
            folded into &ldquo;the chart&rdquo;. Your email address is not needed for any of it and
            is not part of it.
          </li>
          {/* This list named only the web card processor once, which was wrong
              in both directions at once — it named a company that receives
              nothing from an app buyer and omitted the one that takes their
              money. The stores now go first, because they are the only
              companies that take a payment at all: the web checkout is gone,
              and the processor below sells nothing today. Order matters in a
              list a reviewer reads against a Data safety form. */}
          <li>
            <strong>{STORE_MERCHANTS.map((s) => s.merchant).join(" and ")}</strong> take the
            payments. Everything is bought <em>inside the apps</em>: on{" "}
            {STORE_MERCHANTS[1].platform} the seller is {STORE_MERCHANTS[1].merchant}; on{" "}
            {STORE_MERCHANTS[0].platform} it is {STORE_MERCHANTS[0].merchant}. Your card details go
            to the store and never touch Alma, the receipt comes from them, and cancelling a
            subscription happens in their account settings rather than in ours. What travels the
            other way is one identifier: when you buy, the app hands us the store&rsquo;s purchase
            token and we ask the store to confirm it, because an app that unlocked a reading on its
            own word could be made to unlock it for nothing. That confirmation names the product and
            the order, not you. See the <Link href="/refunds">refund policy</Link> for what all of
            that means when you want money back.
          </li>
          <li>
            <strong>{MERCHANT}</strong> is the card processor Alma is configured with, and it is
            listed here for completeness rather than because it has your data: nothing is sold on
            this website, both apps bill through their store, and no purchase reaches this company
            today. If one ever did — the seam is still shipped and still selectable — they would
            take the payment and hold the money on exactly the terms above, and your card details
            would go to them rather than to us.
          </li>
          {/* This said "one email" and named only the sign-in link. There are
              two senders in `alma/mail.py` now: the second one warns you three
              days before a subscription is charged, and it carries a date and an
              amount as well as your address. A privacy policy that undercounts
              the letters we send is wrong in the direction that flatters us. */}
          <li>
            <strong>Resend</strong> carries every email Alma sends: the sign-in link, the notice
            three days before a subscription renews, and the written confirmation of a purchase.
            They receive your address and what is in the letter — for the renewal notice, that is a
            date and an amount. There is no fourth kind: Alma has no newsletter, no campaign and no
            list, and every message it sends is tied to something you did or to money about to
            leave your account.
          </li>
        </Points>
        <Para>
          Where those companies hold data, and under which transfer terms, is being confirmed:{" "}
          <Blank>data transfer terms per processor</Blank>. Alma itself is hosted in{" "}
          <Blank>hosting region</Blank>.
        </Para>
      </Sec>

      <Sec title="What Alma never does" id="choices">
        <Para>
          Alma does not sell your personal information, and does not share it for advertising or
          cross-context behavioural advertising. There is no opt-out link on this page because
          there is nothing to opt out of. If that ever changes, it changes here first, and the
          address on your account is written to before it takes effect — by a person, because Alma
          has no mailing list and nothing automatic that could send it. An account that has never
          given us an address cannot be written to at all, which is the honest end of that
          sentence.
        </Para>
        <Para>
          Your readings are not used to train anyone&rsquo;s model, and your conversations are not
          read for product research.
        </Para>
      </Sec>

      <Sec title="Cookies" id="cookies">
        <Para>
          Alma sets one cookie: <code>alma.locale</code>, which remembers the language you picked
          so the page arrives in it rather than flickering into it. It holds a language code and
          nothing else.
        </Para>
        <Para>
          Your sign-in token is kept in your browser&rsquo;s local storage rather than a cookie. It
          is sent to Alma and to nowhere else. Signing out removes it.
        </Para>
        <Para>
          The random id described above is kept in the same place, under <code>alma.anon</code>,
          with the date it was made beside it. It is not a cookie either, it is sent to Alma and to
          nowhere else, and it is never created if your browser sends Do Not Track or Global Privacy
          Control. Clearing this site&rsquo;s data removes it, deleting your account removes it, and
          your browser replaces it with a new one once it is {FUNNEL_RETENTION_DAYS} days old — so
          the string itself does not outlive the records it was keeping. In the apps it lives in the
          same kind of ordinary storage, and it is deliberately not kept anywhere a bearer
          credential is kept: it authorises nothing.
        </Para>
        <Para>
          There are no advertising cookies and no third-party cookies to manage. If sign-in with
          Google or Apple is ever switched on, their script is loaded on the sign-in screen and
          they become a fourth recipient — of the fact that you signed in, and of nothing else.
          It is off in this build, and this sentence is here because one configuration value is all
          it takes to make the paragraph above it incomplete.
        </Para>
      </Sec>

      <Sec title="Taking it back">
        <Para>
          Both of these live in Settings and both happen immediately. Neither of them requires
          writing to us, and there is no retention offer in the way.
        </Para>
        {/* This paragraph used to impose a condition the product no longer
            imposes, and the condition was the wrong way round: it asked for an
            email address as the price of removing a birth date and a pair of
            coordinates we had already taken. Both routes now take the current
            user, and a guest confirms with the account id on the screen. What
            is left of the caveat is a client that has not caught up, and that
            is named as a client rather than as a policy. */}
        <Para>
          They work for an account you never signed into. Alma creates one on the server the first
          time an app talks to it, before any sign-in screen, and that account is where your birth
          data lives — so it can be exported and deleted on exactly the same terms, confirmed with
          the account id shown on the screen instead of an address you never gave. If the Settings
          screen in front of you asks you to sign in before it will do either, that app has not
          caught up with this; write to <a href={`mailto:${CONTACT}`}>{CONTACT}</a> and we will do
          it by hand. That is a person and a working day, not a form, and we would rather say so
          than let a button imply otherwise.
        </Para>
        <Points>
          <li>
            <strong>Export.</strong> One JSON file: your account, every profile with its birth
            data, what you bought, every reading, every conversation and everything Alma remembers.
          </li>
          <li>
            <strong>Deletion.</strong> Your birth data, your readings, your conversations, your
            memory, your entitlements and any phone registered for the daily are deleted outright —
            rows removed, not a flag set on rows that stay.
          </li>
        </Points>
        {/* What survives a deletion, said in the policy rather than discovered
            in the schema. The previous version of this paragraph named three
            survivors and was wrong about the first: it said the payment records
            "no longer say who bought", while the processor's webhook body was
            stored verbatim beside them and carried the buyer's name, address and
            our own account id. It also missed the sign-in table, which held the
            raw address for ever. `accounts.erase` now redacts both stored bodies
            and deletes the counters, the step labels and the sign-in rows, so
            this list is down to two and both of them are defensible. */}
        <Para>
          Two things survive, and they are worth naming rather than leaving for you to find. The
          payment records stay, because a record of a sale is a legal obligation and it is the
          other side of somebody else&rsquo;s books as well as ours — but your account is detached
          from them and the processor&rsquo;s own message about the payment, which used to sit
          beside them holding your name and address, is wiped. What is left is what an accountant
          needs: a date, an amount, a currency, a country and the processor&rsquo;s reference. And
          a stub of the account row stays, with your address and name removed, so that a sign-in
          link clicked a minute later gets a clear answer instead of a confusing error.
        </Para>
        {/* The third survivor is not ours at all, and saying so belongs here
            rather than only on the deletion page: somebody who deletes their
            account and then finds the purchase still listed in their Apple or
            Google account has not caught us keeping something. */}
        <Para>
          A third record survives that was never ours to delete: the store&rsquo;s own. If you
          bought through {STORE_MERCHANTS[0].store} or {STORE_MERCHANTS[1].store}, they keep their
          record of that purchase under their own policy, in your account with them, and nothing we
          do here reaches it.
        </Para>
        {/* "The step labels" used to mean the ones filed under the account id,
            which was the whole of them while an account was created on the
            first page view. It no longer is: most of a journey now happens
            under the browser id, before there is an account, and a deletion
            that reached only the rows carrying the account id would leave the
            landing view and the quiz behind — still joined to each other,
            still joined to a string still sitting in that person's browser.
            `funnel.forget` follows the id across. */}
        <Para>
          The counters, the step labels and any sign-in link ever sent to your address go with
          everything else. They used to survive, and this page used to disclose that instead of
          fixing it. That includes the steps recorded before your account existed — the landing you
          opened and the quiz you started are yours, even though at the time there was nothing of
          yours to file them under.
        </Para>
        <Para>
          You can also correct your birth data at any time. A corrected time is a different chart,
          so a chapter opened afterwards is written again from the new one rather than showing you
          the old text; what was written from the old chart stays stored until you delete your
          account.
        </Para>
      </Sec>

      <Sec title="How long it is kept">
        {/* This was a `<Blank>` while `/delete-account` — the page Play
            validates, and reads as the deletion promise — already printed
            thirty days. Two documents disagreeing about how long data survives
            a deletion is the worst shape this fact can take, so both now read
            `BACKUP_WINDOW_DAYS`. It is a commitment about infrastructure rather
            than something this repository can verify; see the constant. */}
        <Para>
          While your account exists. When you delete it, it goes from the live database at once and
          ages out of encrypted backups within {BACKUP_WINDOW_DAYS} days, after which it is gone
          from there too. That window is the one place where deleted data survives for a while, and
          the one thing on this page a person cannot verify from the outside.
        </Para>
        {/* The one item with a shorter life than the account, and it needs its
            own sentence because it is also the one item that can exist without
            an account at all — so "while your account exists" would have been
            not merely incomplete but inapplicable. Deleting only the labels
            from people who never converted would have been the cheaper
            promise; it would also have made every historical conversion rate
            wrong in the direction that flatters us, which is why the code
            deletes the window whole. */}
        <Para>
          The step labels and the browser id are the exception: they are deleted after{" "}
          {FUNNEL_RETENTION_DAYS} days whether or not there is an account, and whether or not
          anybody has asked. All of them from the same period go together, so what is left is
          always a complete picture of a period rather than a flattering part of one. The id in your
          browser or your phone goes on the same clock: it is replaced with a fresh one once it
          reaches that age, so the same person cannot be recognised under the same string in a
          later year. That is the half of this promise that used to be missing — the records
          expired and the identifier did not.
        </Para>
      </Sec>

      <Sec title="Age">
        <Para>
          Alma is for people aged {MIN_AGE} and over. If you are younger, do not use it, and if you
          have already given us your birth data, write to <a href={`mailto:${CONTACT}`}>{CONTACT}</a>{" "}
          and it will be deleted without argument.
        </Para>
      </Sec>

      <Sec title="Your rights, and the short way to use them">
        <Para>
          Depending on where you live, you have the right to see your data, correct it, take it
          elsewhere, and have it deleted. Export and deletion in Settings are the fastest route to
          all four, and they do not require you to prove anything to anyone.
        </Para>
        {/* This used to say "for an account you have signed into", and the
            apps used to enforce exactly that — a guest tapping Delete was told
            to sign in first. Which meant demanding an email address as the
            price of removing a birth date and a pair of coordinates already
            taken. Both the route and this sentence now cover a guest; see
            `alma/api/routers/account.py::delete`. */}
        <Para>
          That includes an account you never signed into. Alma creates one on the server the first
          time the app talks to it, and it holds your birth data whether or not you ever gave us an
          address — so it can be exported and deleted from Settings on exactly the same terms. The
          step-by-step is on <Link href="/delete-account">the deletion page</Link>, which also
          covers what to do if the app is already gone from your phone.
        </Para>
        <Para>
          For anything they do not cover, write to <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. The
          controller is {OPERATOR}; the supervisory authority you may complain to is{" "}
          <Blank>lead supervisory authority</Blank>.
        </Para>
      </Sec>

      <DocFoot />
    </>
  );
}
