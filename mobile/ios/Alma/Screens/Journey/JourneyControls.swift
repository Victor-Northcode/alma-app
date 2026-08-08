import SwiftUI

/// The controls the journey needs and the cabinet does not: a choice, a typed
/// answer, three fields on one line, a toggle, a place suggestion, a way past.
///
/// They live here rather than in `DesignSystem/Components` for one reason —
/// three agents are adding files to this project at once, and a component only
/// the journey uses does not need to be in a file two other people are also
/// editing. Anything that turns out to be shared can move later; a merge
/// conflict in a shared file cannot be un-had.
///
/// All of them are measured from `globals.css` and `screens.css` rather than
/// estimated, because the difference between a 54-point control and a 56-point
/// one is invisible in a diff and obvious on a screen where they sit together.

// MARK: — a choice

/// One of the four intents. The web's `.choice`: a capsule on the faintest
/// veil, gold-bordered and gold-lettered once chosen.
///
/// A `ButtonStyle` and not a wrapper view so the label can be anything and so
/// `Button`'s own accessibility traits, hit target and disabled handling all
/// survive — the same argument `AlmaButton` makes for the four house buttons.
struct JourneyChoiceStyle: ButtonStyle {

    var selected: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(AlmaFonts.ui(15.5))
            .foregroundStyle(selected ? Color.almaGoldBright : Color.almaBody.opacity(0.85))
            .multilineTextAlignment(.leading)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
            // **`minHeight`, not `height`.** The web's `.choice` is 54 tall too,
            // but a browser lets text overflow its box where SwiftUI squeezes it
            // into one. In German and French the second intent — "Etwas
            // verschiebt sich und ich weiß nicht warum" — wraps to two lines
            // that nearly touch the top and bottom of a fixed capsule while the
            // other three hold one comfortable line, and a third line (from a
            // longer translation, or from Dynamic Type, or both) clips outright.
            // This is the first screen of the product and the only question in
            // the journey whose answer is worth money.
            .padding(.vertical, 14)
            .frame(minHeight: 54)
            .padding(.horizontal, 22)
            .background(
                Capsule().fill(
                    selected
                        ? Color.almaGold.opacity(0.12)
                        : Color.almaBody.opacity(configuration.isPressed ? 0.10 : 0.06)
                )
            )
            .overlay(
                Capsule().stroke(
                    selected ? Color.almaGold.opacity(0.55) : .clear, lineWidth: 1)
            )
            .animation(AlmaMotion.tap, value: configuration.isPressed)
            .animation(AlmaMotion.ui, value: selected)
    }
}

// MARK: — a typed answer

/// The one text field in the product. Capsule, gold-edged, on the veil.
///
/// It takes its accessibility label separately from its placeholder because
/// they are different sentences: the placeholder is an example ("Milan") and
/// the label is the question ("Where were you born?"). SwiftUI would otherwise
/// read the example out as though it were the instruction.
struct JourneyTextField: View {

    @Binding var text: String
    /// Optional now: the owner's verdict on "Sofia" sitting in the field
    /// where your own name goes was that it reads as somebody else's form.
    /// An empty field with a label above it asks the same question honestly.
    let placeholder: LocalizedStringResource?
    let label: LocalizedStringResource
    var submitLabel: SubmitLabel = .continue
    var onSubmit: () -> Void = {}

    /// A focus binding owned by the step, for the one step that has to *take the
    /// keyboard away*: picking a place has to collapse the suggestions and
    /// resign the field, and only the step knows when that happened.
    ///
    /// Optional, because the name step has no such moment and should not have to
    /// declare a `@FocusState` it never reads. `.focused()` is applied to one
    /// binding or the other rather than to both — two focus bindings on one
    /// field is one of them silently losing.
    var focus: FocusState<Bool>.Binding?

    @FocusState private var owned: Bool

    private var isFocused: Bool { focus?.wrappedValue ?? owned }

    var body: some View {
        field
            .padding(.horizontal, 22)
            // `minHeight` for the same reason as the choice capsule: a field
            // whose height is fixed clips its own text at the larger Dynamic
            // Type sizes.
            .frame(minHeight: 58)
            .background(Capsule().fill(Color.almaVeil))
            .overlay(
                Capsule().stroke(
                    Color.almaGold.opacity(isFocused ? 0.7 : 0.4),
                    lineWidth: 1
                )
            )
            // The focus ring is gold and never blue. It is also a glow rather
            // than a second border, because a two-pixel ring on a capsule reads
            // as a form field on a settings screen.
            .shadow(color: Color.almaGold.opacity(isFocused ? 0.16 : 0), radius: 6)
            .animation(AlmaMotion.ui, value: isFocused)
            .accessibilityLabel(Text(label))
    }

    @ViewBuilder
    private var field: some View {
        let base = TextField(text: $text) {
            if let placeholder {
                Text(placeholder).foregroundStyle(Color.almaMuted3)
            }
        }
        .textFieldStyle(.plain)
        .font(AlmaFonts.ui(17))
        .foregroundStyle(Color.almaInkLight)
        .tint(Color.almaGoldBright)
        .autocorrectionDisabled()
        .submitLabel(submitLabel)
        .onSubmit(onSubmit)

        if let focus {
            base.focused(focus)
        } else {
            base.focused($owned)
        }
    }
}

// MARK: — one of a list

/// A field that opens a list: day, month, year, hour, minute, AM/PM.
///
/// **Why a menu and not a `DatePicker`.** A wheel would be one line of code and
/// would break the rule the whole journey is built on: a `DatePicker` always
/// has a value, so it opens on today's date, and a person who taps past it has
/// silently told us they were born this morning. There is no such thing as an
/// empty `DatePicker`. Three fields that start on their placeholder cannot lie
/// that way, and they are what the web app uses for the same reason.
///
/// The value is `Int` and the label is a closure, so the month field can show
/// "März" while carrying 3 — which is the whole point of the separation.
struct JourneyMenuField: View {

    /// Optional now: the owner's verdict on "Sofia" sitting in the field
    /// where your own name goes was that it reads as somebody else's form.
    /// An empty field with a label above it asks the same question honestly.
    let placeholder: LocalizedStringResource
    let label: LocalizedStringResource
    let options: [Int]
    let title: (Int) -> String
    @Binding var selection: Int?

    @State private var picking = false

    var body: some View {
        Button { picking = true } label: {
            HStack(spacing: 7) {
                Text(selection.map { title($0) } ?? String(localized: placeholder))
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
        .buttonStyle(.plain)
        .accessibilityLabel(Text(label))
        .accessibilityValue(selection.map { Text(title($0)) } ?? Text(""))
        .sheet(isPresented: $picking) {
            JourneyOptionSheet(
                label: label, options: options, title: title, selection: $selection
            )
        }
    }
}

/// The list a date field opens. **This replaces a `Menu`, and the `Menu` was
/// the bug.**
///
/// `Menu` with an inline `Picker` renders as a context menu, and iOS gives a
/// context menu a fixed, small height: the owner tapped *day* and counted
/// twelve of the thirty-one, with no visible way to reach the rest — the list
/// scrolls only while the finger stays down, which on a date field reads as
/// broken rather than as a gesture. Measured on the shipped build.
///
/// A sheet is what the interaction actually is: a list you look through. It
/// opens on the current value, runs top to bottom in the order a person
/// expects — 1 down to 31, January down to December — and closes on the tap
/// that chooses.
private struct JourneyOptionSheet: View {

    let label: LocalizedStringResource
    let options: [Int]
    let title: (Int) -> String
    @Binding var selection: Int?

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(options, id: \.self) { option in
                            Button {
                                selection = option
                                dismiss()
                            } label: {
                                HStack {
                                    Text(title(option))
                                        .font(AlmaFonts.ui(17))
                                        .foregroundStyle(
                                            option == selection
                                                ? Color.almaGoldBright : Color.almaBody)
                                    Spacer()
                                    if option == selection {
                                        Image(systemName: "checkmark")
                                            .font(.system(size: 13, weight: .semibold))
                                            .foregroundStyle(Color.almaGoldBright)
                                    }
                                }
                                // 52 rather than 44: this is a list somebody
                                // scrolls fast and stops in, and a near miss
                                // here costs a wrong birthday.
                                .frame(minHeight: 52)
                                .contentShape(Rectangle())
                                .almaPadding()
                            }
                            .buttonStyle(.plain)
                            .id(option)

                            Rectangle()
                                .fill(Color.almaGold.opacity(0.10))
                                .frame(height: AlmaMetrics.hairline)
                                .almaPadding()
                        }
                    }
                    .padding(.vertical, 6)
                }
                .scrollIndicators(.visible)
                .onAppear {
                    // Opening on the current value, not at the top: a year list
                    // is ninety-two long and scrolling to 1994 every time is
                    // the same complaint in a different field.
                    if let selection { proxy.scrollTo(selection, anchor: .center) }
                }
            }
            .navigationTitle(Text(label))
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationBackground(Color.almaNight)
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }
}

// MARK: — a switch

/// "I don't know my birth time", as a control.
///
/// Hand-drawn rather than `Toggle`, and this is the one place that is worth the
/// code: the system switch is green — a second accent, and the brand book says
/// there is exactly one — and it cannot be tinted into the gold ramp without
/// also tinting every other switch in the app. 52 × 30 with a 24-point knob is
/// the CSS, to the point.
struct JourneyToggle: View {

    @Binding var isOn: Bool
    let label: LocalizedStringResource

    var body: some View {
        Button {
            isOn.toggle()
        } label: {
            Capsule()
                .fill(isOn ? Color.almaGoldDeep : Color.almaBody.opacity(0.14))
                .frame(width: 52, height: 30)
                .overlay(alignment: isOn ? .trailing : .leading) {
                    Circle()
                        .fill(isOn ? Color(hex: 0x0B0F1F) : Color.almaBody)
                        .frame(width: 24, height: 24)
                        .padding(3)
                }
        }
        .buttonStyle(.plain)
        .animation(AlmaMotion.ui, value: isOn)
        .accessibilityLabel(Text(label))
        .accessibilityValue(Text(isOn ? "1" : "0"))
        .accessibilityAddTraits(.isToggle)
    }
}

// MARK: — a place

/// One row of the gazetteer's answer.
///
/// It shows the IANA zone beside the name, because that is the one visible sign
/// that we resolved a real zone rather than guessed from the country, and it is
/// what tells somebody they picked the Milan they meant.
///
/// **The whole identifier, with the underscore spaced out.** The web app prints
/// `place.timezone.split("/").pop()`, which is "New_York" — a machine artefact
/// on a screen where every other character has been typeset — and, worse, "Rome"
/// next to "Milan, Lombardy, Italy" reads as a *second place*, as though we had
/// resolved the wrong city, on the exact step where we are asking to be trusted
/// with the resolution. "Europe/Rome" cannot be misread as a city.
struct JourneySuggestionRow: View {

    let place: Place
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Text(place.label)
                    .font(AlmaFonts.ui(15.5))
                    .foregroundStyle(selected ? Color.almaInkLight : Color.almaMuted)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Text(verbatim: place.timezone.replacingOccurrences(of: "_", with: " "))
                    .font(AlmaFonts.ui(12.5))
                    .foregroundStyle(Color.almaBody.opacity(0.5))
                    .lineLimit(1)
                    .layoutPriority(1)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 13)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(selected ? Color.almaBody.opacity(0.05) : .clear)
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: — a way past

/// "Not now", "Skip the ceremony". Quiet on purpose: it is a real answer and it
/// must be findable, but it is not the thing being offered.
struct JourneySkipButton: View {

    let title: LocalizedStringResource
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(AlmaFonts.ui(13.5))
                .foregroundStyle(Color.almaBody.opacity(0.5))
                .frame(maxWidth: .infinity)
                // 44 points of height around a 13.5-point label, because the
                // tap target is not the ink.
                .frame(height: 44)
        }
        .buttonStyle(.plain)
        .padding(.top, 8)
    }
}

/// The small centred line under a control — what stays free, what a receipt is
/// for, what the toggle costs.
struct JourneyFineprint: View {

    let text: LocalizedStringResource
    var alignment: TextAlignment = .center

    var body: some View {
        Text(text)
            .font(AlmaFonts.ui(13))
            .lineSpacing(3)
            .foregroundStyle(Color.almaBody.opacity(0.5))
            .multilineTextAlignment(alignment)
            .frame(
                maxWidth: .infinity,
                alignment: alignment == .center ? .center : .leading
            )
            .padding(.top, 12)
    }
}
