import SwiftUI

/// The four buttons the product has, as `ButtonStyle`s.
///
/// They are styles rather than wrapper views for one reason that matters to the
/// agents building screens on top of this: a `Button` keeps its own semantics,
/// its own accessibility traits, and its own `.disabled` handling, and a screen
/// can attach any label it likes — a price, a glyph, a progress view — without
/// this file needing a new initialiser for each shape.
///
/// The hierarchy is height as much as fill: gold 56, outline 54, veil 50. That
/// is deliberate and comes from the web app — three controls at the same height
/// read as three equal choices, and the offer screen is precisely where they
/// must not.
enum AlmaButtonStyleKind: Sendable {
    /// The one action on the screen. Never two on one screen.
    case gold
    /// The considered alternative — "not now", "this chapter only".
    case outline
    /// A quiet action in a list.
    case veil
    /// Deleting an account, cancelling a plan. Outlined, never filled: a filled
    /// red button is a button somebody taps by reflex.
    case danger
}

struct AlmaButtonStyle: ButtonStyle {

    let kind: AlmaButtonStyleKind
    /// Whether the button stretches. Almost always true on a phone.
    var fills: Bool = true

    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(font)
            .foregroundStyle(foreground)
            .frame(maxWidth: fills ? .infinity : nil)
            .frame(height: height)
            .padding(.horizontal, 28)
            .background(background(pressed: configuration.isPressed))
            .clipShape(Capsule())
            .overlay(border)
            .shadow(
                color: kind == .gold ? AlmaShadow.button : .clear,
                radius: kind == .gold ? AlmaShadow.buttonRadius : 0,
                y: kind == .gold ? 6 : 0
            )
            // The press is a 1-point settle, not a scale. A gold button that
            // shrinks reads as plastic; one that sinks reads as a key.
            .offset(y: configuration.isPressed && kind == .gold ? 1 : 0)
            .opacity(isEnabled ? 1 : 0.45)
            .animation(AlmaMotion.tap, value: configuration.isPressed)
    }

    private var height: CGFloat {
        switch kind {
        case .gold: AlmaMetrics.buttonHeight
        case .outline: AlmaMetrics.buttonHeightOutline
        case .veil: AlmaMetrics.buttonHeightVeil
        case .danger: 44
        }
    }

    private var font: Font {
        switch kind {
        case .gold: .almaButton
        case .outline: AlmaFonts.ui(16, weight: .medium)
        case .veil: AlmaFonts.ui(15, weight: .medium)
        case .danger: AlmaFonts.ui(14.5, weight: .medium)
        }
    }

    private var foreground: Color {
        switch kind {
        case .gold: .almaInkOnGold
        case .outline: .almaGoldBright
        case .veil: .almaBody
        case .danger: .almaDisagree
        }
    }

    @ViewBuilder
    private func background(pressed: Bool) -> some View {
        switch kind {
        case .gold:
            if pressed { AlmaGradient.goldButtonPressed } else { AlmaGradient.goldButton }
        case .veil:
            Color.almaBody.opacity(pressed ? 0.13 : 0.07)
        case .outline:
            Color.almaGold.opacity(pressed ? 0.14 : 0)
        case .danger:
            Color.clear
        }
    }

    @ViewBuilder
    private var border: some View {
        switch kind {
        case .outline:
            Capsule().stroke(Color.almaGold.opacity(0.5), lineWidth: 1)
        case .danger:
            Capsule().stroke(Color(hex: 0x8C3A2B).opacity(0.5), lineWidth: 1)
        case .gold, .veil:
            EmptyView()
        }
    }
}

extension ButtonStyle where Self == AlmaButtonStyle {
    static var almaGold: AlmaButtonStyle { AlmaButtonStyle(kind: .gold) }
    static var almaOutline: AlmaButtonStyle { AlmaButtonStyle(kind: .outline) }
    static var almaVeil: AlmaButtonStyle { AlmaButtonStyle(kind: .veil) }
    static var almaDanger: AlmaButtonStyle { AlmaButtonStyle(kind: .danger) }

    /// A button that hugs its label instead of filling the width — the only
    /// case a screen has to ask for explicitly.
    static func alma(_ kind: AlmaButtonStyleKind, fills: Bool) -> AlmaButtonStyle {
        AlmaButtonStyle(kind: kind, fills: fills)
    }
}

#Preview("Buttons") {
    VStack(spacing: 14) {
        Button("Open this chapter") {}.buttonStyle(.almaGold)
        Button("Not now") {}.buttonStyle(.almaOutline)
        Button("Add my birth time") {}.buttonStyle(.almaVeil)
        Button("Delete my account") {}.buttonStyle(.almaDanger)
        Button("Open this chapter") {}.buttonStyle(.almaGold).disabled(true)
    }
    .almaPadding()
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .nightSky()
}
