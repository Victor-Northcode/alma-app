import SwiftUI

/// The four questions that come before the sky is built: what is loudest, what
/// to call you, when, and at what time.
///
/// Each is a `JourneyScene` and nothing else. They hold no state of their own
/// beyond what a control needs to be a control — everything they collect is
/// written straight into `JourneyModel`, so stepping back and forward finds the
/// answers still there, and closing the journey and reopening it does not.

// MARK: — I · what's loudest

/// The only question in the journey whose answer is worth money.
///
/// It is asked first, before any birth data, and it decides what is offered at
/// the end. Choosing one advances immediately — a "continue" under four radio
/// buttons is a second tap for a decision that has already been made.
// MARK: — I · a name isn't an account

/// A name, and the sentence that says what it is not.
///
/// **The web app's "or faster — continue with Google" is deliberately not
/// here.** That button calls `onNext()` and signs nobody in; it is a control
/// whose gesture and effect differ, which is the one thing the sign-in step was
/// rewritten to stop doing. Sign in with Apple belongs on the sign-in screen,
/// where it actually attaches an identity, and it is not needed to get through
/// this: the account is real from the first request and the token is in the
/// keychain, so the chart survives the app being closed either way.
struct StepName: View {

    @Bindable var journey: JourneyModel
    let onNext: () -> Void

    var body: some View {
        JourneyScene(
            artHeight: 302,
            title: JourneyL10n.nameTitle,
            sub: JourneyL10n.nameSub
        ) {
            OrbitArt()
        } controls: {
            JourneyTextField(
                text: $journey.name,
                placeholder: nil,
                label: JourneyL10n.nameAria,
                onSubmit: onNext
            )
            .textContentType(.givenName)

            // **A name is required now, and that is a product decision.**
            //
            // It used to be optional — "a name isn't an account" is still true
            // and still on the screen — and the owner's ruling is that nothing
            // in this sequence may be skipped except the birth time. The
            // argument is not about data: an app that lets somebody through
            // four screens without asking anything has nothing to show them at
            // the end, and half a chart is what makes the whole product look
            // broken. Either we ask, or we do not ask; asking and then
            // shrugging is the worst of the three.
            Button(action: onNext) {
                Text(JourneyL10n.continueCta)
            }
            .buttonStyle(.almaGold)
            .disabled(journey.name.trimmingCharacters(in: .whitespaces).isEmpty)
        }
    }
}

// MARK: — III · when

/// Three fields, none of them pre-filled.
struct StepDate: View {

    @Bindable var journey: JourneyModel
    let onNext: () -> Void

    /// Ninety-two years, newest first, starting ten years ago. The same window
    /// the web app offers: a birth in the last decade is somebody entering
    /// their child's data into an app written for adults, and 1934 is far
    /// enough back that the ephemeris and the historical time-zone tables are
    /// still solid.
    private static let years: [Int] = {
        let thisYear = Calendar(identifier: .gregorian).component(.year, from: .now)
        return (0..<92).map { thisYear - 10 - $0 }
    }()

    /// Whether the three answers name a day that exists. February the 30th is
    /// selectable in three independent fields and is nobody's birthday.
    private var dateExists: Bool {
        guard let day = journey.day, let month = journey.month, let year = journey.year
        else { return false }
        return JourneyDate.isReal(day: day, month: month, year: year)
    }

    private var impossible: Bool { journey.dateComplete && !dateExists }

    var body: some View {
        JourneyScene(
            artHeight: 300,
            title: JourneyL10n.dateTitle,
            sub: JourneyL10n.dateSub
        ) {
            DialArt()
        } controls: {
            // Wheels, not menus — the owner's reference: three spinning
            // columns under a big title, a value always in the window.
            HStack(spacing: 0) {
                JourneyWheel(
                    label: JourneyL10n.day,
                    options: Array(1...31),
                    title: { String($0) },
                    selection: $journey.day
                )
                JourneyWheel(
                    label: JourneyL10n.month,
                    options: Array(1...12),
                    title: { JourneyL10n.monthName($0) },
                    selection: $journey.month
                )
                .frame(maxWidth: .infinity)
                JourneyWheel(
                    label: JourneyL10n.year,
                    options: Self.years,
                    title: { String($0) },
                    selection: $journey.year
                )
            }

            if impossible {
                Text(JourneyL10n.impossibleDate)
                    .font(AlmaFonts.ui(13.5))
                    .foregroundStyle(Color.almaGoldBright)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 6)
            }

            Button(action: onNext) {
                Text(JourneyL10n.continueCta)
            }
            .buttonStyle(.almaGold)
            .disabled(!dateExists)
        }
    }
}

// MARK: — IV · at what time

/// The birth time, with not knowing as a first-class answer.
///
/// Two things here are load-bearing. The toggle produces a *null* birth time
/// and never a noon, because the backend treats null as a real state and
/// refuses the systems that need a horizon — where a fabricated noon would hand
/// back confident, wrong houses. And the note under the toggle appears both for
/// a declared unknown *and* for a step tapped straight through, because those
/// are the same fact and only one of them used to say so.
struct StepTime: View {

    @Bindable var journey: JourneyModel
    let onNext: () -> Void

    var body: some View {
        JourneyScene(
            title: JourneyL10n.timeTitle,
            sub: nil
        ) {
            ClockArt()
        } controls: {
            HStack(spacing: 0) {
                JourneyWheel(
                    label: JourneyL10n.hourLabel,
                    // 1–12 with a meridiem beside it, or 0–23 with nothing.
                    // See `JourneyModel.usesTwelveHourClock`.
                    options: JourneyModel.usesTwelveHourClock
                        ? Array(1...12) : Array(0...23),
                    title: { String(format: "%02d", $0) },
                    selection: $journey.hour
                )
                JourneyWheel(
                    label: JourneyL10n.minuteLabel,
                    options: Array(0...59),
                    title: { String(format: "%02d", $0) },
                    selection: $journey.minute
                )
                if JourneyModel.usesTwelveHourClock {
                    MeridiemField(selection: $journey.meridiem)
                        .frame(width: 110)
                }
            }
            .opacity(journey.timeUnknown ? 0.4 : 1)
            .disabled(journey.timeUnknown)
            .animation(AlmaMotion.ui, value: journey.timeUnknown)

            HStack(alignment: .center, spacing: 14) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(JourneyL10n.unknownTime)
                        .font(AlmaFonts.ui(15))
                        .foregroundStyle(Color.almaBody.opacity(0.8))
                        .fixedSize(horizontal: false, vertical: true)

                    if !journey.hasTime {
                        Text(JourneyL10n.lockedWithoutTime)
                            .font(AlmaFonts.ui(13))
                            .foregroundStyle(Color.almaMuted2)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                JourneyToggle(isOn: $journey.timeUnknown, label: JourneyL10n.unknownTime)
            }
            .padding(.horizontal, 6)
            .padding(.vertical, 4)

            Button(action: onNext) {
                Text(JourneyL10n.continueCta)
            }
            .buttonStyle(.almaGold)
            // **A half-answered time is refused; an unanswered one is not.**
            //
            // Tapping straight through is a real answer — it means what the
            // toggle means, and the note under the toggle already says so. But
            // an hour and a minute with no AM/PM makes `hasTime` false, which
            // makes `twentyFourHour` nil, which throws away the 11:10 somebody
            // just entered: they reach a portrait with no Ascendant and no
            // explanation, having told us their birth time. Refusing the
            // half-filled state is the rule the date step already follows.
            .disabled(journey.timePartiallyGiven)
        }
    }
}

/// AM or PM.
///
/// A field of its own rather than a third `JourneyMenuField`, because that one
/// carries an `Int` — and the two halves of a twelve-hour clock are not a
/// number, they are an enum whose raw values happen to be the same two tokens
/// in all six languages.
private struct MeridiemField: View {

    @Binding var selection: Meridiem?

    var body: some View {
        Menu {
            Picker(selection: $selection) {
                ForEach(Meridiem.allCases) { half in
                    Text(verbatim: half.rawValue).tag(Meridiem?.some(half))
                }
            } label: {
                Text(JourneyL10n.meridiemLabel)
            }
            .pickerStyle(.inline)
        } label: {
            HStack(spacing: 7) {
                // **The placeholder is not "AM".** It was, and a placeholder
                // that is also a valid answer is indistinguishable from a chosen
                // one to anybody who is not comparing two greys: somebody born
                // at 11:10 in the evening sees "AM" in the third field and taps
                // on. That is the default-birth-data rule the whole journey is
                // built on, in the one field where getting it wrong moves the
                // Ascendant half a circle. "AM/PM" cannot be mistaken for an
                // answer, exactly as "Day" and "Month" cannot.
                Text(verbatim: selection?.rawValue ?? "AM/PM")
                    .font(AlmaFonts.ui(16.5))
                    .foregroundStyle(selection == nil ? Color.almaMuted3 : Color.almaBody)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                Text(verbatim: "▾")
                    .font(.system(size: 9))
                    .foregroundStyle(Color.almaGold)
            }
            .frame(maxWidth: .infinity)
            .frame(minHeight: 54)
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(Capsule().fill(Color.almaVeil))
            .overlay(
                Capsule().stroke(
                    Color.almaGold.opacity(selection == nil ? 0 : 0.28), lineWidth: 1)
            )
        }
        .accessibilityLabel(Text(JourneyL10n.meridiemLabel))
    }
}


/// One spinning column — the pickers the owner's reference uses: a value is
/// always in the window, the neighbours fade above and below, and choosing is
/// a flick rather than a menu. `nil` shows the first option in the window
/// without committing it; the first movement commits.
struct JourneyWheel<Value: Hashable>: View {

    let label: LocalizedStringResource
    let options: [Value]
    let title: (Value) -> String
    @Binding var selection: Value?

    var body: some View {
        Picker(selection: Binding(
            get: { selection ?? options[0] },
            set: { selection = $0 }
        )) {
            ForEach(options, id: \.self) { option in
                Text(verbatim: title(option))
                    .font(AlmaFonts.display(19, relativeTo: .title3))
                    .foregroundStyle(Color.almaInkLight)
                    .tag(option)
            }
        } label: {
            Text(label)
        }
        .pickerStyle(.wheel)
        .frame(height: 148)
        .clipped()
        .accessibilityLabel(Text(label))
    }
}


/// II · who this is for. Volunteered, never required — the option to say
/// nothing is a first-class card, not a small grey link. With an answer,
/// Alma's Russian agrees with the reader («ты родилась»); without one she
/// keeps the genderless register she has always used.
struct StepAbout: View {

    @Bindable var journey: JourneyModel
    let onNext: () -> Void

    var body: some View {
        JourneyScene(
            artHeight: 260,
            title: JourneyL10n.aboutTitle,
            sub: JourneyL10n.aboutSub
        ) {
            DialArt()
        } controls: {
            VStack(spacing: 10) {
                genderCard("female", label: JourneyL10n.genderFemale)
                genderCard("male", label: JourneyL10n.genderMale)
                genderCard(nil, label: JourneyL10n.genderSkip)
            }

            Button(action: onNext) {
                Text(JourneyL10n.continueCta)
            }
            .buttonStyle(.almaGold)
            .padding(.top, 12)
        }
    }

    private func genderCard(_ value: String?, label: LocalizedStringResource) -> some View {
        let selected = journey.gender == value && (value != nil || journey.aboutAnswered)
        return Button {
            journey.gender = value
            journey.aboutAnswered = true
            AlmaHaptics.tick()
        } label: {
            HStack {
                Text(label)
                    .font(.almaBodyFont)
                    .foregroundStyle(Color.almaInkLight)
                Spacer()
                if selected {
                    Text(verbatim: "✦")
                        .font(.system(size: 14))
                        .foregroundStyle(Color.almaGoldBright)
                }
            }
            .padding(.horizontal, 20)
            .frame(minHeight: AlmaMetrics.fieldHeight)
            .background(
                Capsule().fill(selected ? Color.almaGold.opacity(0.18) : Color.almaVeil)
            )
            .overlay(
                Capsule().strokeBorder(
                    selected ? Color.almaGold.opacity(0.7) : Color.almaBody.opacity(0.12),
                    lineWidth: 1
                )
            )
            .contentShape(Capsule())
        }
        .buttonStyle(AlmaCardPressStyle())
    }
}
