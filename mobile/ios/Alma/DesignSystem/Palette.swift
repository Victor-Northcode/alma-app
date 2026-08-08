import SwiftUI

/// The Alma palette, lifted from `src/app/globals.css` so that the two clients
/// cannot drift apart by a hex digit.
///
/// Two decisions are worth stating, because both were tempting to get wrong.
///
/// **These are literals, not asset-catalog colours.** A colour set can carry a
/// light variant and a dark one, and the moment it can, somebody fills in the
/// light one — which is precisely the failure mode the brand book names: night
/// is the canvas, not a dark theme over a light design. There is one appearance
/// and the numbers are in the source where a reviewer can see them beside the
/// CSS they came from. (`Assets.xcassets` still carries two entries: the accent
/// colour UIKit reads for system controls, and the launch-screen background,
/// because neither can be expressed in Swift.)
///
/// **One gold, aged.** `gold`, `goldDeep`, `goldBright` and `starFill` are four
/// values on a single ramp, not four accents. Nothing in this file introduces a
/// second hue that competes with it; `agree` and `disagree` are semantic and are
/// only ever used to mark where systems agree and disagree, never as decoration.
extension Color {

    // MARK: — night & indigo

    /// The colour behind everything. Every screen starts here.
    static let almaNight = Color(hex: 0x0A0D1C)
    static let almaNight850 = Color(hex: 0x090C1A)
    static let almaNight900 = Color(hex: 0x070A16)
    static let almaVoid = Color(hex: 0x04060E)
    static let almaNight700 = Color(hex: 0x101636)

    static let almaIndigo = Color(hex: 0x3A3484)
    static let almaIndigoBright = Color(hex: 0x604EC4)
    static let almaIndigoDeep = Color(hex: 0x1E3A96)

    // MARK: — the one gold

    static let almaGold = Color(hex: 0xC9AE6B)
    static let almaGoldDeep = Color(hex: 0xA8873C)
    static let almaGoldBright = Color(hex: 0xE4D3A2)
    static let almaStarFill = Color(hex: 0xF6E7BC)

    // MARK: — light & ink

    /// Display type on night.
    static let almaInkLight = Color(hex: 0xF6F1E4)
    /// Body copy on night.
    static let almaBody = Color(hex: 0xEDE7DA)
    /// Type on a gold button.
    static let almaInkOnGold = Color(hex: 0x141019)
    /// The one light surface — used only where a document is earned.
    static let almaParchment = Color(hex: 0xF1E9D6)
    static let almaParchmentA = Color(hex: 0xF6EEDB)
    static let almaParchmentB = Color(hex: 0xE8DBBE)
    /// Type on parchment.
    static let almaInk = Color(hex: 0x1C1A17)

    // MARK: — semantic

    /// Where systems agree. Never used as an accent.
    static let almaAgree = Color(hex: 0x8FBF9A)
    /// Where systems disagree, and destructive actions.
    static let almaDisagree = Color(hex: 0xE0917F)

    // MARK: — surfaces

    /// The faintest raised surface. "No boxes" means this is the exception.
    static let almaVeil = Color.almaBody.opacity(0.07)
    static let almaVeilStrong = Color.almaBody.opacity(0.09)
    static let almaHairline = Color.almaBody.opacity(0.10)
    static let almaHairlineGold = Color.almaGold.opacity(0.16)

    // MARK: — muted ink, hard floor 62%

    /// Muted body copy. The floor is 62%: anything fainter fails contrast on
    /// night, and the brand book fixes it here rather than leaving it to taste.
    static let almaMuted = Color.almaBody.opacity(0.72)
    static let almaMuted2 = Color.almaBody.opacity(0.68)
    static let almaMuted3 = Color.almaBody.opacity(0.62)
    static let almaInkMuted = Color.almaInk.opacity(0.72)
    static let almaInkMuted2 = Color.almaInk.opacity(0.62)
}

/// The gradients. Kept apart from the flat colours because a gradient is a
/// component decision — a gold button, the mark, the parchment band — and not a
/// token a screen should be reaching for on its own.
enum AlmaGradient {

    /// The one button fill. Top-lit, so the control reads as struck metal
    /// rather than as a coloured rectangle.
    static let goldButton = LinearGradient(
        colors: [Color(hex: 0xDCC48A), Color(hex: 0xA8873C)],
        startPoint: .top,
        endPoint: .bottom
    )

    static let goldButtonPressed = LinearGradient(
        colors: [Color(hex: 0xC6A659), Color(hex: 0x8F7233)],
        startPoint: .top,
        endPoint: .bottom
    )

    /// The mark's fill and any gold that has to look aged rather than yellow.
    static let goldLeaf = LinearGradient(
        stops: [
            .init(color: Color(hex: 0xFBEDC4), location: 0.00),
            .init(color: Color(hex: 0xE0C077), location: 0.34),
            .init(color: Color(hex: 0xB3913F), location: 0.70),
            .init(color: Color(hex: 0x8A6F2E), location: 1.00),
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// The one light surface.
    static let parchment = LinearGradient(
        stops: [
            .init(color: Color.almaParchmentA, location: 0.0),
            .init(color: Color(hex: 0xEFE3C9), location: 0.6),
            .init(color: Color.almaParchmentB, location: 1.0),
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// A hairline that fades at both ends — the rule between sections.
    static let fadedRule = LinearGradient(
        colors: [.clear, Color.almaGold.opacity(0.34), .clear],
        startPoint: .leading,
        endPoint: .trailing
    )
}

/// The shadows. "Depth is light, not shadow" — so there are only two, both of
/// them a glow rather than a drop, and neither is ever stacked.
enum AlmaShadow {
    static let goldGlowRadius: CGFloat = 20.0
    static let goldGlow = Color.almaGold.opacity(0.16)
    static let buttonRadius: CGFloat = 15.0
    static let button = Color(hex: 0xB4923F).opacity(0.38)
}

extension Color {
    /// `0xRRGGBB` in sRGB. The initialiser exists so the tokens above can be
    /// read against the CSS they were copied from without mentally converting
    /// each channel to a fraction.
    init(hex: UInt32, opacity: Double = 1.0) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255.0,
            green: Double((hex >> 8) & 0xFF) / 255.0,
            blue: Double(hex & 0xFF) / 255.0,
            opacity: opacity
        )
    }
}
