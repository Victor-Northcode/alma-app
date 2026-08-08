import type { Metadata } from "next";
import Link from "next/link";
import { DocFoot, DocHead, Para, Points, Sec } from "@/components/legal/Doc";
import { BACKUP_WINDOW_DAYS, CONTACT, OPERATOR, STORE_MERCHANTS } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Delete your account · Alma",
  description:
    "How to delete your Alma account and everything in it, from inside the app or by writing to us.",
};

/**
 * The page Google Play's Data deletion field points at.
 *
 * ── Why this exists as a *page* rather than only as a button ───────────────
 * Play Console → App content → Data deletion requires a URL a reviewer can
 * open in a browser, signed out, without installing the app. It is a required
 * field: the submission cannot be completed without one, and a URL that 404s
 * or redirects to a sign-in is a rejection rather than a note. Apple asks for
 * the same thing in different words.
 *
 * ── Why there is no form on it ────────────────────────────────────────────
 * The obvious version of this page is a box that takes an email address and a
 * "delete my account" button. That would be worse in two separate ways. It
 * collects personal data from an unauthenticated visitor, which is a new
 * collection to declare on the very form this page exists to satisfy; and an
 * unauthenticated deletion endpoint keyed on an email address is a way to
 * delete somebody else's account. So this page is instructions and an address,
 * and the actual deletion happens where the person is already authenticated —
 * in the app, or in a reply to a letter we can answer.
 *
 * ── Not in LEGAL_DOCS ─────────────────────────────────────────────────────
 * That array is the five-document footer navigation. This is a procedure, not
 * a policy, and adding it there would put a sixth tab across the top of five
 * documents that were reviewed together. It is linked from the privacy policy,
 * the terms, the support page, the site footer, both apps' settings screens,
 * and the store listings — Google's requirement is that the resource be
 * *readily discoverable*, and a URL known only to Play Console is not that.
 */
export default function DeleteAccountPage() {
  return (
    <>
      <DocHead
        title="Delete your account"
        lead="Two ways, and both of them end with the same thing: the row holding your birth date and your birth coordinates is gone, along with everything Alma wrote from it."
      />

      <Sec title="From inside the app">
        <Para>
          This is the fastest route and the one to prefer, because the app already knows which
          account is yours and nobody has to establish that by email.
        </Para>
        {/* Every label below is the string the app actually renders —
            `settings_data_legal`, `settings_delete_account`,
            `settings_delete_confirm_id` in `values/strings.xml`, and the same
            rows in `SettingsScreen.swift`. It said "scroll to Leaving", and
            there is no section called Leaving in either app: a person following
            these steps was looking for a heading that does not exist. */}
        <Points>
          <li>Open Alma.</li>
          <li>
            Go to <strong>Settings</strong> — the last tab.
          </li>
          <li>
            Scroll to <strong>data &amp; legal</strong> and tap <strong>Delete account</strong>.
          </li>
          <li>
            Confirm. If you have signed in with an email address, you will be asked to type it. If
            you have not — which is how Alma works until you choose otherwise — you will be asked to
            type the account id shown on the screen. Either way it is one field and one button, and
            there is nothing to wait for.
          </li>
        </Points>
        <Para>
          It happens immediately. The app returns to its first screen with no account behind it, the
          way it was before you opened it the first time.
        </Para>
        {/* Named rather than smoothed over, and named as a client that has not
            caught up rather than as a policy. The server takes the current user
            and confirms against `user.email or user.id`
            (`api/routers/account.py`); the Android screen does the same; the
            iOS screen still branches on `isGuest` and shows a sign-in prompt
            where the delete flow would be (`AccountModel.swift:220-222`,
            `SettingsScreen.swift:210`). Writing "every app can do this" here
            would be a promise a reader can disprove in thirty seconds. */}
        <Para>
          One exception, while it lasts: on iPhone and iPad, an account that has never signed in is
          still asked to sign in first, and the same is true of the export button beside it. That is
          this app rather than the rule — the server deletes a guest account on the same terms as
          any other — and until it is changed, the letter below does the job with no sign-in of any
          kind.
        </Para>
      </Sec>

      <Sec title="You do not need an email address to do this">
        <Para>
          Worth saying plainly, because it is the thing most likely to go wrong. Alma creates an
          account on the server the first time the app talks to it — before any sign-in screen, and
          before you have typed anything. That account is where your birth date, your birth
          coordinates and your readings are kept. If you never signed in, it has no email address on
          it at all.
        </Para>
        <Para>
          That account can be deleted exactly like any other, and the rule is that you are never
          asked to supply an email address first: asking for more personal data as the price of
          removing the data already taken would be the wrong way round. The one app that has not
          caught up with that rule is named above, and writing to us goes round it.
        </Para>
      </Sec>

      <Sec title="By writing to us">
        <Para>
          If the app is uninstalled, or the phone is gone, or the screen in front of you is asking
          for a sign-in you do not have, or you would simply rather ask a person: write to{" "}
          <a href={`mailto:${CONTACT}`}>{CONTACT}</a> from the address you signed in with and say
          that you want your account deleted. We will do it and reply to confirm. A person reads
          it — <Link href="/support">support</Link> says how long that takes and what to include.
        </Para>
        <Para>
          If you never signed in there is no address to write from, and the account cannot be found
          without the device that holds its token — so please use the in-app route while you still
          have the app. If you have already uninstalled it, write anyway and tell us what you can;
          we will look, and we will tell you honestly whether we found anything.
        </Para>
      </Sec>

      {/* The one thing on this page that costs money if it is left out, and it
          was left out. `accounts.erase` deletes our entitlement rows; it cannot
          touch a subscription that lives in an Apple or Google account, and
          nothing in this product can. Somebody who deletes their account and
          assumes the charges stop finds out a month later, and they find out
          from a bank statement rather than from us. */}
      <Sec title="If you have a subscription, cancel it first">
        <Para>
          Deleting your Alma account does <strong>not</strong> cancel a subscription bought in a
          store. That subscription belongs to your {STORE_MERCHANTS[1].merchant} or{" "}
          {STORE_MERCHANTS[0].merchant} account rather than to your Alma account, and it goes on
          renewing after everything here is gone — paying for access to an account that no longer
          exists.
        </Para>
        <Para>
          So stop it first, on the store&rsquo;s own screen. The two taps are in{" "}
          <Link href="/subscription-terms#cancel">subscription terms</Link>, with both addresses.
          Cancelling there and deleting here are two separate acts, in that order.
        </Para>
      </Sec>

      <Sec title="What is deleted">
        <Para>Everything on this list goes, and it goes for good — none of it is recoverable:</Para>
        <Points>
          <li>Your account row, and your email address if you gave one.</li>
          <li>
            Your birth date, birth time, birth coordinates, time zone and place label — and the same
            fields for anybody else you saved in order to compare charts.
          </li>
          <li>Your name, if you gave one.</li>
          <li>Every reading Alma wrote for you.</li>
          <li>Every conversation you had with Alma, and the short memory kept from them.</li>
          <li>Your sign-in links, used and unused.</li>
          <li>The counters and funnel steps recorded against your account.</li>
          <li>
            Your entitlements. This is the one worth reading twice: deleting the account deletes
            what you bought. A door you paid for permanently is permanent until you delete the
            account it belongs to, and there is no way for us to give it back afterwards.
          </li>
        </Points>
      </Sec>

      <Sec title="What survives, and why">
        <Para>
          Three things, and none of them is a copy of your chart.
        </Para>
        <Points>
          <li>
            <strong>The payment records.</strong> A purchase is a financial record and the law
            requires it to be kept for a number of years that depends on where we and you are. What
            is kept is the money — amount, currency, date, product, the store&rsquo;s or
            processor&rsquo;s own transaction id — with the link to you severed and the message the
            seller sent us about the payment wiped. It is no longer possible to go from those rows
            back to a person.
          </li>
          {/* This list said two and the privacy policy said two, and between
              them they named three different things: the deletion page missed
              the account stub, the privacy page missed the store. Both now name
              the same three, because the one document a reader compares this
              against is that one. `accounts.erase` keeps the stub deliberately;
              see its docstring. */}
          <li>
            <strong>A stub of your account row.</strong> The row itself is kept with your address
            and your name removed and everything hanging off it deleted, so that a sign-in link
            clicked a minute after you deleted the account gets a clear answer rather than silently
            making you a new person.
          </li>
          <li>
            <strong>The store&rsquo;s own record.</strong> If you bought through{" "}
            {STORE_MERCHANTS[0].store} or {STORE_MERCHANTS[1].store}, the store keeps its record of
            that purchase under its own policy and we cannot delete it for you. Their account
            settings are where that lives.
          </li>
        </Points>
        <Para>
          Backups are the honest exception to &ldquo;immediately&rdquo;. Deleted data is removed
          from the live database at once and ages out of encrypted backups within{" "}
          {BACKUP_WINDOW_DAYS} days, after which it is gone from there too. The{" "}
          <Link href="/privacy">privacy policy</Link> states the same window, from the same
          constant, so the two cannot drift apart.
        </Para>
      </Sec>

      <Sec title="If you only want a copy first">
        <Para>
          Settings has an <strong>Export my data</strong> button above the delete one. It writes
          everything Alma holds about you to one file — your account, every profile with its birth
          data, what you bought, every reading, every conversation and everything Alma remembers —
          which is worth doing before deleting rather than after. There is no after.
        </Para>
        <Para>
          The server opens export to a guest account on exactly the same terms as deletion, and for
          the same reason: asking for an email address as the price of seeing what we already took
          would be the wrong way round. The iPhone and iPad exception above applies to this button
          too.
        </Para>
        <Para>
          The full list of what Alma holds and where it goes is in the{" "}
          <Link href="/privacy">privacy policy</Link>.
        </Para>
      </Sec>

      <Sec title="Who this is">
        <Para>
          Alma is operated by {OPERATOR}. The deletion request goes to the same people who built it;
          there is no third party in between and no ticket queue to escalate through.
        </Para>
      </Sec>

      <DocFoot />
    </>
  );
}
