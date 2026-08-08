import SwiftUI

/// VIII · the offer, and IX · the handoff.

// MARK: — VIII · the offer

/// The sale, and it happens here rather than after registration.
///
/// Somebody who arrived from an ad has decided to spend five dollars; they have
/// not decided to fill in a form. Putting an account first spends that decision
/// on paperwork and loses most of it — so this comes straight after the
/// portrait, while the person is still looking at their own chart. What is
/// offered is what they asked for in the very first question.
///
/// **Two things the web app does here are deliberately not done here, and both
/// are Apple's doing rather than ours.**
///
/// There is no price on the button. Apple is the merchant of record and sets
/// the price per storefront from a tier, so the only honest number is
/// StoreKit's own localised one for this device — the catalogue's `$5.99` is
/// what a card processor would have charged and is wrong in most countries.
///
/// There is no email field and no pair of consent tick boxes. Both exist on the
/// web because a card processor needs an address to open a session and because
/// Art. 16(m) requires the withdrawal waiver to be agreed and confirmed on a
/// durable medium. Through the App Store neither is ours to collect: Apple
/// takes the payment, Apple sends the receipt, and Apple's own terms cover the
/// consent. Reproducing the form here would be asking for personal data we have
/// no use for, in front of a sheet that will not use it.
///
/// **So what this screen does is make the case and then get out of the way.**
/// The gold button leaves the journey and opens the offer screen, which is the
/// app's one purchase surface — the StoreKit sheet, the localised price, the
/// restore path and the server-side verification all live there. Duplicating a
/// purchase flow inside the journey would mean two places that can grant an
/// entitlement, and the second one is always the one that ships broken.
struct StepOffer: View {

    let journey: JourneyModel
    /// Take the offer: leave the journey for the ladder, carrying the system
    /// the quiz matched so the right door is the one on screen.
    let onBuy: (SystemSlug) -> Void
    let onSkip: () -> Void

    @Environment(AlmaSessionModel.self) private var session

    var body: some View {
        JourneyScene(
            // Half the height of the other scenes, and measured rather than
            // guessed: the star gives up the empty sky around it so that the
            // button is never below the fold. A visitor who has to scroll to
            // find the button is a visitor who did not see the offer.
            artHeight: 152,
            title: JourneyL10n.offerTitle(journey.matchedSystem),
            sub: JourneyL10n.offerSub
        ) {
            OfferArt()
        } controls: {
            Button {
                onBuy(journey.matchedSystem)
            } label: {
                Text(JourneyL10n.offerCta)
            }
            .buttonStyle(.almaGold)

            JourneySkipButton(title: JourneyL10n.offerSkip) {
                // Tapping past the offer is the plainest refusal there is, and
                // it was the one the funnel could not see: without it,
                // everybody who never opened a sheet looks identical to
                // everybody who abandoned mid-journey.
                Task { await session.client.track(.offerDeclined, meta: meta) }
                onSkip()
            }

            JourneyFineprint(text: JourneyL10n.offerFine)
        }
        .task {
            await session.client.track(.offerView, meta: meta)
        }
    }

    /// The catalogue slug for a door is the system it opens, so the thing the
    /// quiz matched is the thing that gets counted, priced and bought — with no
    /// mapping table to fall out of step.
    private var meta: [String: JSONValue] {
        ["product": .string(journey.matchedSystem.rawValue)]
    }
}

// MARK: — IX · the handoff

/// Three rules, and the door into the cabinet.
///
/// It is the only onboarding the product ever gives, which is why it is three
/// sentences and not a carousel — and why it comes *after* somebody has been
/// given something, when "one chapter at a time" is advice about a thing they
/// now have rather than a rule about a thing they have not seen.
struct StepHandoff: View {

    let onFinish: () -> Void

    var body: some View {
        JourneyDocument {
            VStack(alignment: .leading, spacing: 0) {
                AlmaPresence(size: 96)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 24)

                Text(JourneyL10n.handoffTitle)
                    .font(AlmaFonts.display(30, relativeTo: .title))
                    .foregroundStyle(Color.almaInkLight)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 24)

                Text(JourneyL10n.handoffSub)
                    .font(AlmaFonts.ui(15))
                    .lineSpacing(5)
                    .foregroundStyle(Color.almaMuted2)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 12)

                VStack(alignment: .leading, spacing: 20) {
                    ForEach(1...3, id: \.self) { number in
                        if number > 1 {
                            Rectangle()
                                .fill(
                                    LinearGradient(
                                        colors: [Color.almaGold.opacity(0.26), .clear],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .frame(height: AlmaMetrics.hairline)
                        }

                        HStack(alignment: .top, spacing: 18) {
                            Text(verbatim: ["I", "II", "III"][number - 1])
                                .font(AlmaFonts.display(24, relativeTo: .title3))
                                .foregroundStyle(Color.almaGoldDeep)
                                .frame(width: 26, alignment: .leading)

                            Text(JourneyL10n.rule(number))
                                .font(AlmaFonts.ui(15))
                                .lineSpacing(5)
                                .foregroundStyle(Color.almaBody.opacity(0.78))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .accessibilityElement(children: .combine)
                    }
                }
                .padding(.top, 28)

                // **Asked here, where it will actually be answered.**
                //
                // The same question lives on Today and in Settings, and the
                // owner's point about both is correct: nobody scrolls to the
                // bottom of a settings screen to turn on notifications. This is
                // the one moment the answer is cheap — a person who has just
                // watched eight systems be computed from their own birth
                // already knows what "something in your chart is exact" means,
                // and thirty seconds later they never will again.
                //
                // It is our question and not the platform's, which is why it
                // can be asked at all: iOS gives an app exactly one permission
                // dialog and a denial is close to permanent, so the system
                // prompt is only raised for somebody who has already said yes
                // to this one. Declining here costs one tap and leaves both
                // doors open.
                DailyInvitation()
                    .padding(.top, 8)
            }
        } controls: {
            Button(action: onFinish) {
                Text(JourneyL10n.openToday)
            }
            .buttonStyle(.almaGold)
        }
    }
}
