import CoreText
import SwiftUI

/// The type scale, and the answer to the font question the brief asks.
///
/// **The web app sets Playfair Display for display type and Golos Text for UI.**
/// Neither ships with iOS. The brief allows bundling them or choosing a system
/// pairing deliberately, and this is the deliberate choice, with the door left
/// open:
///
/// * **Display — New York** (`.serif`, i.e. `Font.Design.serif`). Playfair is a
///   high-contrast transitional serif with vertical stress and fine hairlines.
///   New York is the only serif Apple ships, it is a transitional design with
///   the same vertical stress, and — the reason it wins over any other
///   substitute — it is an *optical-size* family: at 80pt the hairlines thin out
///   and the contrast rises, which is exactly the quality Playfair is chosen
///   for. Georgia, the CSS fallback, is a screen face with low contrast and
///   would read as a different brand at display sizes.
/// * **UI — SF Pro** (`.default`). Golos Text is a low-contrast humanist
///   grotesque with open apertures and near-vertical terminals. SF Pro is the
///   same species, and it brings Dynamic Type, the optical Text/Display cut at
///   20pt, and tabular figures for the degree readouts — none of which a
///   bundled webfont would give us for free.
///
/// **Bundling later costs no code.** Drop `.otf`/`.ttf` files anywhere in the
/// app bundle and call `AlmaFonts.registerBundledFonts()` — already called at
/// launch — and every call site below switches over, because each one asks for
/// its named family first and falls back to the system design only when that
/// family is not installed. Nothing here hard-codes a face.
enum AlmaFonts {

    /// The display face, in order of preference, resolved once at first use.
    ///
    /// **Why a list and not one name.** The first entry is the real thing, if
    /// somebody has dropped it into the bundle. The rest are the substitutes, in
    /// descending order of how close they are to Playfair — and having them here
    /// as *named families* rather than as `Font.Design.serif` is what makes
    /// Dynamic Type work, which is the whole point of the rewrite below.
    ///
    /// New York is first among the substitutes for the reason in the doc comment
    /// above: it is Apple's only transitional serif and it is optical-size, which
    /// is what Playfair is chosen for at 39pt. Charter and Georgia follow because
    /// both ship on every iOS and both are serifs; Georgia is the CSS fallback
    /// and reads as a different brand, so it is last rather than absent.
    private static let displayFamilies = ["Playfair Display", "New York", "Charter", "Georgia"]

    /// The UI face. Golos if bundled; otherwise nothing here resolves and the
    /// system sans is used at a *scaled* size — see `ui(_:weight:relativeTo:)`.
    /// SF Pro is deliberately not in this list: its real family name is private
    /// (".SF UI Text"), asking for it by name gets a silent fallback, and the
    /// scaled-system path below is both honest and correct.
    private static let uiFamilies = ["Golos Text"]

    /// Registering fonts is a bundle scan, and it must happen before the first
    /// view resolves a face — so `AlmaApp` calls it in its initialiser.
    ///
    /// Registration is done in code rather than through `UIAppFonts` in the
    /// Info.plist for one reason: `Alma/` is a synchronized folder, so a
    /// designer dropping four files into `Alma/Resources/Fonts/` adds them to
    /// the target automatically — and if the plist also had to be edited, the
    /// half that was forgotten would be silent, with the app quietly rendering
    /// in the fallback face.
    static func registerBundledFonts() {
        for ext in ["otf", "ttf"] {
            for url in Bundle.main.urls(forResourcesWithExtension: ext, subdirectory: nil) ?? [] {
                // A failure here is not worth reporting: the only consequence
                // is that `isInstalled` stays false and the system face is used,
                // which is the state the app is designed to survive anyway.
                CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
            }
        }
    }

    /// The first family in a list that is actually installed. Resolved once and
    /// remembered: `UIFont.familyNames` builds an array of every face on the
    /// device, and this is asked on every text view.
    private static let displayFamily: String? = firstInstalled(displayFamilies)
    private static let uiFamily: String? = firstInstalled(uiFamilies)

    private static func firstInstalled(_ families: [String]) -> String? {
        let installed = Set(UIFont.familyNames)
        return families.first { installed.contains($0) }
    }

    /// Display type: the serif.
    static func display(_ size: CGFloat, relativeTo style: Font.TextStyle) -> Font {
        guard let displayFamily else { return scaledSystem(size, style: style, design: .serif) }
        return .custom(displayFamily, size: size, relativeTo: style)
    }

    /// UI type: the sans.
    static func ui(
        _ size: CGFloat,
        weight: Font.Weight = .regular,
        relativeTo style: Font.TextStyle = .body
    ) -> Font {
        guard let uiFamily else {
            return scaledSystem(size, style: style, design: .default).weight(weight)
        }
        return .custom(uiFamily, size: size, relativeTo: style).weight(weight)
    }

    /// The system face at a size that grows with the reader's text setting.
    ///
    /// **This is the branch that actually runs**, and until it was written the
    /// app ignored Dynamic Type entirely. `Font.custom(_:size:relativeTo:)`
    /// scales; `Font.system(size:weight:design:)` does not — it is a fixed point
    /// size, full stop — and because neither Playfair nor Golos is bundled, the
    /// fixed branch was the only one any call site ever reached. Every reader who
    /// had enlarged their text saw Alma at 15.5pt regardless, which is a
    /// regression against the web app (a browser scales) and the kind of thing a
    /// reviewer with large text turned on notices in five seconds.
    ///
    /// `UIFontMetrics` is the documented way to scale a number that is not a
    /// font's own size, and it is `NS_SWIFT_SENDABLE` in the SDK — checked, not
    /// assumed — so this stays callable from a `ButtonStyle.makeBody` that is not
    /// on the main actor.
    ///
    /// The ceiling is deliberate. Left uncapped, `.accessibility5` multiplies a
    /// 39pt hero by about 1.8 and a display title stops being a title; the fixed
    /// heights in the design system (gold button 56, field 54) would then clip
    /// their own labels. 1.6 keeps the largest sizes legible without letting one
    /// word fill a screen, and the smaller sizes never reach it.
    private static func scaledSystem(
        _ size: CGFloat, style: Font.TextStyle, design: Font.Design
    ) -> Font {
        .system(size: scaledSize(size, style: style), weight: .regular, design: design)
    }

    private static func scaledSize(_ size: CGFloat, style: Font.TextStyle) -> CGFloat {
        min(UIFontMetrics(forTextStyle: style.uiTextStyle).scaledValue(for: size), size * 1.6)
    }

    // MARK: — leading

    /// The extra leading that turns a CSS `line-height` into a SwiftUI
    /// `lineSpacing`, measured against the face that actually resolved.
    ///
    /// **The two are not the same quantity, and treating them as one was wrong
    /// in both directions.** CSS `line-height` is the *total* height of a line;
    /// SwiftUI's `lineSpacing` is what is added on top of the font's own natural
    /// line height. So `.almaBody()` asked for 9.6 points "because 15.5 × 1.62 ≈
    /// 9.6 of extra leading" and got 15.5 × 1.62 *plus* the font's own 19 — a
    /// reading set 14% airier than the web's, which is why a paid paragraph
    /// floated instead of holding together. The display sizes had the opposite
    /// problem: no `lineSpacing` at all, so a wrapped title set at the system's
    /// default 1.32 against a design that specifies 0.98 and 1.08. In English a
    /// display title almost never wraps, so it was invisible in the language it
    /// was tested in and 21% loose in the other five.
    ///
    /// This asks the resolved `UIFont` for its real line height rather than
    /// carrying a measured constant, so it stays correct if somebody drops
    /// Playfair into the bundle — a different face has a different natural
    /// leading, and a hard-coded number would silently become wrong the moment
    /// the migration everyone is told costs no code actually happens.
    static func leading(
        _ size: CGFloat, ratio: CGFloat, family: Family, relativeTo style: Font.TextStyle
    ) -> CGFloat {
        let scaled = scaledSize(size, style: style)
        let resolved: UIFont
        if let name = family == .display ? displayFamily : uiFamily,
           let named = UIFont(name: name, size: scaled) {
            resolved = named
        } else if family == .display,
                  let serif = UIFont.systemFont(ofSize: scaled)
                    .fontDescriptor.withDesign(.serif) {
            resolved = UIFont(descriptor: serif, size: scaled)
        } else {
            resolved = .systemFont(ofSize: scaled)
        }
        // Negative is legitimate and is what the display sizes need: SwiftUI
        // tightens on a negative `lineSpacing`, and 0.98 line-height is by
        // definition tighter than any face's natural leading.
        return scaled * ratio - resolved.lineHeight
    }

    enum Family: Sendable { case display, ui }
}

private extension Font.TextStyle {
    /// SwiftUI's text styles and UIKit's are the same set with two names. The
    /// mapping is written out rather than bridged because there is no public
    /// conversion, and a wrong row here is a font that scales on the wrong curve
    /// — which looks fine at the default size and wrong at every other one.
    var uiTextStyle: UIFont.TextStyle {
        switch self {
        case .largeTitle: .largeTitle
        case .title: .title1
        case .title2: .title2
        case .title3: .title3
        case .headline: .headline
        case .subheadline: .subheadline
        case .body: .body
        case .callout: .callout
        case .footnote: .footnote
        case .caption: .caption1
        case .caption2: .caption2
        // `.extraLargeTitle` and friends arrived for visionOS and have no UIKit
        // equivalent on iOS. Nothing in the scale asks for one; if something ever
        // does, the largest curve is the right approximation.
        @unknown default: .largeTitle
        }
    }
}

/// The scale, named for what each row *is* rather than for its size — a screen
/// asking for `.almaDisplayXL` cannot accidentally set 39pt on a caption.
///
/// Sizes are the web app's mobile values (`globals.css`); the desktop step-ups
/// are not carried over, because a phone is a phone.
extension Font {

    /// Section eyebrows: 11.5pt, .22em tracking, uppercase, gold.
    /// Tracking and case are applied by `almaOverline()`, not here — a `Font`
    /// cannot carry either.
    static let almaOverline = AlmaFonts.ui(11.5, weight: .semibold, relativeTo: .caption)

    /// The hero. One per screen, at most.
    static let almaDisplayXL = AlmaFonts.display(39, relativeTo: .largeTitle)

    /// Screen and section titles.
    static let almaDisplayL = AlmaFonts.display(29, relativeTo: .title)

    /// Row and card titles.
    static let almaHeadingM = AlmaFonts.display(17.5, relativeTo: .headline)

    /// Alma speaking. Italic is applied by `almaVoice()`.
    static let almaVoiceFont = AlmaFonts.display(21, relativeTo: .title3)

    /// Body copy — the reading itself.
    static let almaBodyFont = AlmaFonts.ui(15.5, relativeTo: .body)

    /// Secondary lines under a title.
    static let almaMetaFont = AlmaFonts.ui(13, relativeTo: .footnote)

    /// Chapter numerals and degree readouts — set in the serif, because a
    /// position is type in this design and not an icon.
    static let almaNumeral = AlmaFonts.display(14, relativeTo: .footnote)

    /// Button labels.
    static let almaButton = AlmaFonts.ui(16.5, weight: .semibold, relativeTo: .body)

    /// Tags: 10.5pt, .12em tracking, uppercase.
    static let almaTag = AlmaFonts.ui(10.5, weight: .regular, relativeTo: .caption2)
}

extension View {

    /// Section eyebrow: gold, uppercase, widely tracked.
    func almaOverline() -> some View {
        self.font(.almaOverline)
            .textCase(.uppercase)
            .tracking(2.5)
            .foregroundStyle(Color.almaGold)
    }

    /// The hero line. `line-height: 0.98` in `globals.css`.
    func almaDisplayXL() -> some View {
        self.font(.almaDisplayXL)
            .tracking(-1.1)
            .lineSpacing(AlmaFonts.leading(39, ratio: 0.98, family: .display, relativeTo: .largeTitle))
            .foregroundStyle(Color.almaInkLight)
    }

    /// `line-height: 1.08`. It only shows when a title wraps, which in English
    /// is almost never and in German and French is most of the time.
    func almaDisplayL() -> some View {
        self.font(.almaDisplayL)
            .lineSpacing(AlmaFonts.leading(29, ratio: 1.08, family: .display, relativeTo: .title))
            .foregroundStyle(Color.almaInkLight)
    }

    func almaHeadingM() -> some View {
        self.font(.almaHeadingM)
            .lineSpacing(AlmaFonts.leading(17.5, ratio: 1.24, family: .display, relativeTo: .headline))
            .foregroundStyle(Color.almaInkLight)
    }

    /// Alma speaking: serif, italic, roomy. Used for her sentences only —
    /// never for UI copy that happens to want emphasis.
    func almaVoice() -> some View {
        self.font(.almaVoiceFont.italic())
            .lineSpacing(AlmaFonts.leading(21, ratio: 1.5, family: .display, relativeTo: .title3))
            .foregroundStyle(Color.almaInkLight)
    }

    /// The day text on Today — Alma's voice, but set for reading standing up:
    /// smaller, lighter, and not italic. The owner's finding on the italic
    /// serif at 21 points was «неудобно читать», and a morning note has no
    /// business being hard work.
    func almaDayVoice() -> some View {
        self.font(AlmaFonts.display(17.5, relativeTo: .body))
            .fontWeight(.light)
            .lineSpacing(AlmaFonts.leading(17.5, ratio: 1.55, family: .display, relativeTo: .body))
            .foregroundStyle(Color.almaInkLight.opacity(0.95))
    }

    /// The reading — the thing that is sold. `line-height: 1.62`.
    func almaBody() -> some View {
        self.font(.almaBodyFont)
            .lineSpacing(AlmaFonts.leading(15.5, ratio: 1.62, family: .ui, relativeTo: .body))
            .foregroundStyle(Color.almaBody)
    }

    func almaMeta() -> some View {
        self.font(.almaMetaFont).foregroundStyle(Color.almaMuted2)
    }

    /// A chart position — always gold, always the serif, so that a factor
    /// citation is recognisable as one wherever it appears.
    func almaPositions() -> some View {
        self.font(.almaNumeral).foregroundStyle(Color.almaGoldBright)
    }

    func almaTag(_ tone: AlmaTagTone = .gold) -> some View {
        self.font(.almaTag)
            .textCase(.uppercase)
            .tracking(1.3)
            .foregroundStyle(tone.colour)
    }
}

/// What a tag can mean.
///
/// **`.muted` is why this has four cases and not three.** `almaTag()` sets its
/// own `foregroundStyle`, so three call sites that wrote `.almaTag(.gold)` and
/// then `.foregroundStyle(.almaMuted3)` after it were overriding nothing: the
/// modifier is applied to the already-styled view and loses. "UNLOCK TO READ",
/// "THIS ONE NEEDS YOUR BIRTH TIME" and the hub's status tags all rendered at
/// full brightness — the first two in gold, so a sixteen-chapter list carried
/// three gold uppercase strings per row and gold stopped meaning "this is the
/// thing"; the third in `.almaAgree`, printing a blocker in the green this
/// design reserves for "the systems agree".
///
/// A case rather than a colour parameter, because the point of the enum is that
/// a tag's colour is one of a closed set of *meanings*. An open parameter is how
/// a fifth colour arrives.
enum AlmaTagTone: Sendable {
    /// The ordinary tag: this is a real, present thing.
    case gold
    /// The systems agree.
    case agree
    /// The systems disagree.
    case disagree
    /// Not yet, locked, missing. Recedes rather than competing — a state that
    /// names something absent must not be the brightest thing on the row.
    case muted

    var colour: Color {
        switch self {
        case .gold: .almaGold
        case .agree: .almaAgree
        case .disagree: .almaDisagree
        case .muted: .almaMuted3
        }
    }
}
