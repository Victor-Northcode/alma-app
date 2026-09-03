import type { Metadata } from "next";
import Link from "next/link";
import { DocFoot, DocHead, Para, Points, Sec } from "@/components/legal/Doc";
import { CONTACT, MERCHANT, STORE_MERCHANTS } from "@/lib/legal";
import { APPLE, GOOGLE } from "@/lib/support";

export const metadata: Metadata = {
  title: "Subscription terms · Alma",
  description: "What renews, who charges you, when you are told, what happens if you are not, and where the two taps that stop it are.",
};

/**
 * The plan, stated so that nothing about it can arrive as a surprise.
 *
 * No prices are printed here. The catalogue is the authority on what something
 * costs and the store is the authority on what you will actually be charged in
 * your currency with your tax — a number typed into a legal page is a number
 * that will eventually disagree with both.
 *
 * ── what this page had wrong, and how it was found ────────────────────────
 * Every claim below was read back against the code before it was rewritten,
 * because this page has now been wrong twice in the same direction: the
 * direction that flatters us.
 *
 * The first round: "the subscription is monthly" described a catalogue with two
 * recurring rows; "an email goes out three days before every renewal" described
 * a job that did not exist; "if the price ever changes you are told before"
 * described a notice nothing in this system can send; and the past-due section
 * described a pause that no processor event performs.
 *
 * The second round is this one, and it is the same class of error made by a
 * *change in the world* rather than by wishful writing. The web checkout is
 * gone. Both plans are bought inside the apps, Apple and Google are the
 * merchants of record, and three things this page asserted stopped being true
 * on the day that landed: that a card processor charges you, that cancelling
 * happens on a screen of ours, and that only the yearly plan is on sale.
 * `AlmaStore.swift:491` puts both plan rows on the paywall.
 *
 * The rule the page is written under, unchanged: where the code will not do
 * something, the sentence says what actually happens instead. A promise is
 * never deleted and quietly not kept.
 */
export default function SubscriptionTermsPage() {
  return (
    <>
      <DocHead
        title="Subscription terms"
        lead="What renews, who takes the money, what you are told before they do, and the two taps that stop it. Where something is less tidy than that, it is written down rather than left out."
      />

      <Sec title="What renews">
        <Para>
          There are two recurring plans. The yearly one opens everything Alma has written for you —
          every system, every chapter — for a year. The monthly one opens only the three systems
          that move with the date: transits, the solar return, and compatibility. Renting a natal
          chart would be rent on numbers that have not changed since you were born, so the archive
          is not part of it.
        </Para>
        <Para>
          Both are sold inside the app, and both appear on the same screen with what each one grants
          written on it. Neither has a trial and neither has an introductory price — there is
          nothing that starts cheap and becomes expensive, because the thing this page exists to
          prevent is a charge nobody was expecting.
        </Para>
        <Para>
          Either plan renews on its own cycle until you stop it. A payment opens slightly more than
          the period it is for — thirty-one days for a month, three hundred and sixty-five for a
          year, counted from whichever is later, the day you pay or the day your current access
          ends. The extra days do not stack up; they exist so that a renewal charged a few hours
          late can never lock you out of a period you have already paid for.
        </Para>
      </Sec>

      <Sec title="Who charges you">
        <Para>
          The store you bought in. On {STORE_MERCHANTS[1].platform} that is{" "}
          {STORE_MERCHANTS[1].merchant}; on {STORE_MERCHANTS[0].platform} it is{" "}
          {STORE_MERCHANTS[0].merchant}. They hold the payment method, they take the money on each
          renewal, and the price you were shown was theirs — charged in your own currency with your
          own tax, which is the number that is true.
        </Para>
        <Para>
          We are told that a payment happened, not how. That is why the sections below say &ldquo;we
          ask the store&rdquo; wherever money is involved: it is a description of the plumbing
          rather than a way of declining responsibility. What is ours is the access, and the access
          is opened and closed by us the moment the store tells us either has changed.
        </Para>
      </Sec>

      {/* The one thing a person is most likely to assume wrongly about the
          annual, and the assumption costs them a year later rather than now.
          The `Reading` rows survive the expiry; the entitlement does not, and
          the paywall asks the entitlement. */}
      <Sec title="A plan is rented, not bought">
        <Para>
          The yearly plan opens everything for a year. It is not a purchase of the archive. When
          the year ends and you have not renewed, the readings that were written for you during it
          stay in your account — nothing is deleted — but they stop opening, the same as any
          chapter you have not paid for.
        </Para>
        <Para>
          If what you want is text that is yours whatever happens next, that is the archive, bought
          once. Anything bought outright is permanent and is untouched by a plan starting, ending or
          being cancelled.
        </Para>
      </Sec>

      <Sec title="You are told before you are charged">
        <Para>
          The store tells you. Both of them send their own receipt for every charge and their own
          notice before a renewal, to the address on your Apple or Google account, under their own
          rules — and that is the channel that cannot fail, because it does not depend on our
          knowing who you are.
        </Para>
        <Para>
          We send a second one where we can. If there is an email address on your Alma account, a
          letter goes out three days before a renewal saying what is about to be taken, in the
          currency it will be taken in, and on what date. It is sent once per renewal — not once per
          plan, not once ever — and if our mail provider refuses it, it is not marked as sent and it
          is tried again the following day.
        </Para>
        <Para>
          It never says an amount it is not sure of. If neither the plan nor the payment behind it
          can tell us what is about to be charged, nothing is sent at all rather than a letter with
          a nought in it — a figure in writing that disagrees with the one taken is worse than the
          silence it was meant to prevent.
        </Para>
        <Para>
          It is not a marketing email and there is no unsubscribe on it, because a subscription you
          have forgotten about is the oldest trick in this industry and we would rather not be in
          that business. It belongs to no list and has no preference to set.
        </Para>
        <Para>
          The gap that is left, said plainly: a store does not tell us the address it billed. If you
          have never signed in to Alma, we have nowhere to write, and our letter is not sent —
          you will have the store&rsquo;s own notice and nothing from us. Signing in once removes
          that gap entirely, and it is the single best reason to do so.
        </Para>
      </Sec>

      {/* This section used to promise a price-change notice. Nothing in the
          product sends one — every sender in `mail.py` is transactional and
          tied to an event that has already happened — and now the price of a
          running subscription is not even ours to change: it is a field on a
          product in a store console, and each store has its own consent rule
          for raising one. So the promise is replaced by what is actually true
          in both directions. */}
      <Sec title="The price you agreed to is the price that renews">
        <Para>
          Nothing in Alma can change what an existing plan costs. A new price on the price list
          applies to new purchases; your plan goes on billing what it was opened at.
        </Para>
        <Para>
          If the price of a running plan were ever raised, it would be raised in the store&rsquo;s
          own console, and neither store lets that happen quietly: each has its own rule about
          telling a subscriber first, and about an increase needing their agreement rather than
          their silence. We would write as well, by hand, to any address we have — because there is
          no automatic notice for it and we would rather say so than imply a machine is watching.
        </Para>
      </Sec>

      <Sec title="Cancelling takes two taps" id="cancel">
        <Para>
          A subscription bought inside an app belongs to the store account that paid for it, and the
          store&rsquo;s own screen is the only place it can be stopped. That screen is two taps
          away, from inside Alma:
        </Para>
        <Points>
          <li>
            Settings → the row that names your store —{" "}
            <strong>Manage this subscription in the App Store</strong> on{" "}
            {STORE_MERCHANTS[1].platform}, <strong>Manage in Google Play</strong> on{" "}
            {STORE_MERCHANTS[0].platform}. It opens your subscriptions there.
          </li>
          <li>Cancel on that screen, and confirm.</li>
        </Points>
        <Para>Or open the same screen directly:</Para>
        <Points>
          <li>
            {STORE_MERCHANTS[1].merchant} —{" "}
            <a href={APPLE.subscriptions} target="_blank" rel="noreferrer">
              {APPLE.subscriptions}
            </a>
          </li>
          <li>
            {STORE_MERCHANTS[0].merchant} —{" "}
            <a href={GOOGLE.subscriptions} target="_blank" rel="noreferrer">
              {GOOGLE.subscriptions}
            </a>
            , or{" "}
            <a href={GOOGLE.cancelHelp} target="_blank" rel="noreferrer">
              their step-by-step
            </a>
            .
          </li>
        </Points>
        <Para>
          No email to write, no reason to give, no call, and no offer standing between you and the
          second tap. You cancel from inside the same product you subscribed in, which is what
          California requires of a subscription sold this way — and, more to the point, it is the
          only version of this that is not an obstacle course.
        </Para>
        {/* Cancelling and withdrawing are different acts and the two laws are
            about different ones. AB 2863 is same-medium cancellation, which the
            in-app route to the store screen is. The EU's withdrawal-function
            requirement, in force since 19 June 2026, is a control for
            *withdrawal*, and there is no such control in Alma or in either
            store — so the sentence says what a person actually does instead,
            rather than implying a button that is not there. */}
        <Para>
          Withdrawing is a different act from cancelling, and it has no button anywhere. Inside the
          first fourteen days you can withdraw from a plan outright rather than merely stopping the
          next charge; today that is an email to us, read by a person, and what happens next is on{" "}
          <Link href="/refunds">refunds</Link>.
        </Para>
        <Para>
          What cancelling does: the store stops the next charge and tells us the date your access
          runs to. Nothing is taken away at the moment you cancel — the period you are in was paid
          for and stays open until its last day. If the store&rsquo;s screen did not confirm it,
          nothing has happened yet: a cancellation you believe took place and the store never
          recorded is the failure that ends in a charge you did not expect, so check that their
          screen says the plan is ending before you close it.
        </Para>
        <Para>
          Cancelling is not a refund of the period you are in. What is and is not refundable —
          including the fourteen days in which you can withdraw from a plan outright — is in{" "}
          <Link href="/refunds">refunds</Link>.
        </Para>
      </Sec>

      <Sec title="What you keep afterwards">
        <Para>
          Everything you bought outright. A system, or the whole archive, bought as a one-time
          purchase is permanent and is not affected by a subscription ending.
        </Para>
        <Para>
          Your account, your chart and your conversations stay as they are. Ending a subscription
          is not deleting an account — that is a separate, deliberate act, and it is described on{" "}
          <Link href="/delete-account">the deletion page</Link>.
        </Para>
      </Sec>

      {/* Every number below is the one `auth/entitlements.py` and
          `billing/catalogue.py` actually implement: thirty days, and the shelf
          price less the door already paid. The second half is the one that
          generates a dispute, and this document is what decides it. */}
      <Sec title="One reading first, the rest later">
        <Para>
          If you buy a single system and then decide within thirty days that you want the rest,
          the rest of the archive is offered at its price less what you already paid for that
          reading. Nothing to claim, nothing to refund first — the reduced price is simply what
          you are charged.
        </Para>
        <Para>
          It is set against the price in the currency you paid in, and it is offered while you hold
          one system and nothing wider. After thirty days the offer is gone and the reading you
          bought remains yours. The reduction applies to the archive; a plan is priced on its own.
        </Para>
      </Sec>

      {/* “The subscription does not renew and access pauses” was two errors in
          one sentence, and the store version of it would be a third. A card
          that bounces starts the store's own retry and grace period; nothing on
          our side revokes anything while that is running, because
          `subscription.past_due` was deliberately kept out of the revoking set. */}
      <Sec title="If a payment fails">
        <Para>
          Nothing is taken away. A card that bounces is usually a card that works on the retry, and
          both stores retry for a while and give you a window to fix the payment method — the
          person whose payment failed is the last person who should be locked out while it is being
          sorted out.
        </Para>
        <Para>
          If the retries never succeed, the plan is simply not extended: your access runs to the end
          of the period you already paid for and stops there. Anything you bought outright is
          untouched by any of this. Subscribing again starts a new period from the day it is paid.
        </Para>
      </Sec>

      <Sec title="Invoices and tax">
        <Para>
          The store is the seller of record. They issue the invoice, they handle VAT, GST and sales
          tax where it applies, and their receipt is the document your accountant wants — ours
          confirms what you agreed to and is not a tax invoice. If you need theirs reissued, ask
          them, or ask us at <a href={`mailto:${CONTACT}`}>{CONTACT}</a> and we will ask them.
        </Para>
      </Sec>

      {/* Named once, and last. The card adapters still ship and
          `ALMA_BILLING_PROVIDER` still selects one, so this is a live seam
          rather than history — and the app's own Settings screen has a
          different cancel button for exactly this case: where the store
          supplies no manage URL, the in-app button stops the charge directly
          (`SettingsScreen.kt:459`). A page describing only the store route
          would leave that person looking for a screen they do not have. */}
      <Sec title="If your plan is not a store subscription">
        <Para>
          Then it runs through {MERCHANT}, the card processor Alma is configured with, and it is
          cancelled in Alma&rsquo;s own Settings rather than in a store: the button is there when
          there is no store screen to send you to, and it asks the processor to stop the next
          charge. If they cannot be reached, nothing is changed and the screen says so. Everything
          else on this page applies with their name in place of the store&rsquo;s.
        </Para>
      </Sec>

      <DocFoot />
    </>
  );
}
