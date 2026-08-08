import SwiftUI

/// The canvas. Every screen in the app sits on one of these.
///
/// Assembled here rather than by each screen so that the brand book's ceilings
/// are structural instead of advisory: one comet, at most two auras, three
/// motes. A screen that wants a different sky picks a different `Mood`; a screen
/// cannot accidentally end up with four auras because there is nowhere to put
/// the fourth.
///
/// Usage is always the same shape — the sky is a background, never a container:
///
/// ```swift
/// ScrollView { … }
///     .background(NightSky(mood: .cabinet))
/// ```
struct NightSky: View {

    /// What kind of screen this is, which decides how much sky it gets.
    enum Mood: Sendable {
        /// The cabinet — Today, Systems, Settings. Full field, one comet, one
        /// aura well away from the copy.
        case cabinet

        /// A chapter or a conversation. The field is dimmed and the comet is
        /// gone: the product on this screen is the words, and a light crossing
        /// the page while somebody reads is the single most irritating thing a
        /// background can do.
        case reading

        /// The journey — the quiz, the ceremony, the portrait. Everything on,
        /// turned up. This is the one screen where the sky *is* the content.
        case ceremony

        var starIntensity: Double {
            switch self {
            case .cabinet: 0.9
            case .reading: 0.45
            case .ceremony: 1.0
            }
        }

        var density: Double {
            switch self {
            case .cabinet: 1.0
            case .reading: 0.6
            case .ceremony: 1.25
            }
        }

        /// **Only the ceremony.** This is a design decision rather than a
        /// tuning, and it is worth the paragraph.
        ///
        /// `Sky.tsx` states the rule the comet has to obey: *one per screen,
        /// never behind body copy*. On the web that is achievable because the
        /// comet is placed per screen and lives in the landing hero, where there
        /// is nothing. On a phone there is no such region on a cabinet screen: a
        /// scaffolded screen puts an eyebrow, a display title and its first
        /// paragraph in the top 45%, everything else scrolls *through* the
        /// middle, and the streak is 180 points long — 45% of the width of a
        /// 402-point screen — so wherever the head is placed the tail is
        /// somewhere else. Hard-coding one trajectory put it through the account
        /// name on Today, through "WHO AM I" on the hub and through the sun-sign
        /// glyph on the portrait; seeding it moved the collision around rather
        /// than removing it.
        ///
        /// The ceremony is different in kind. Its top 40% is a line drawing on
        /// empty night, it is the one screen where the sky *is* the content, and
        /// it is short-lived. So the comet lives there, crossing the art, and
        /// the cabinet keeps the stars, the motes and the aura — which is
        /// already more sky than most of this category ships.
        var hasComet: Bool {
            switch self {
            case .ceremony: true
            case .cabinet, .reading: false
            }
        }

        var hasMotes: Bool {
            switch self {
            case .reading: false
            case .cabinet, .ceremony: true
            }
        }

        var grain: Double {
            switch self {
            case .cabinet: 0.26
            case .reading: 0.18
            case .ceremony: 0.30
            }
        }
    }

    var mood: Mood = .cabinet

    /// Distinguishes one screen's sky from another's. Pass something stable and
    /// screen-specific — `Route.hashValue` is ideal — so that moving between two
    /// screens is visibly moving, not the same stars twice.
    var seed: UInt64 = 0x414C_4D41

    /// Generated once per view identity. `@State` and not a computed property:
    /// computing it would rebuild 160 stars on every frame of every animation
    /// on the screen, and reshuffle them each time.
    @State private var field: SkyField?

    var body: some View {
        // An `.overlay` on a flexible colour, not a `ZStack`.
        //
        // This is not a stylistic preference and it cost a day to find. A
        // `ZStack` sizes itself to its largest child, and `Aura` is a *fixed*
        // 520-point circle — so on a 402-point phone the ZStack measured 520
        // wide, the view holding it inherited that width, and every screen in
        // the app was laid out 118 points too wide and centred, which clipped
        // the first and last tab in the bar and the left edge of every title.
        // An overlay takes its size from the view underneath and lets its
        // children overflow, which is exactly what a bleeding aura should do.
        Color.almaNight
            .overlay {
                if let field {
                    // The aura sits high and off to one side. Never centred: a
                    // centred bloom lands under the first paragraph.
                    Aura(tone: mood == .ceremony ? .violet : .indigo, diameter: 520, drift: .a)
                        .offset(x: -110, y: -220)

                    if mood == .ceremony {
                        Aura(tone: .deep, diameter: 420, drift: .b)
                            .offset(x: 130, y: 260)
                    }

                    Starfield(field: field, intensity: mood.starIntensity)

                    if mood.hasMotes {
                        DriftingMotes(field: field, intensity: mood.starIntensity)
                    }

                    if mood.hasComet {
                        // Seeded, so each screen's comet crosses somewhere
                        // different — and, more to the point, somewhere below
                        // its own headline. See `Trajectory`.
                        Comet(seed: seed)
                    }
                }
            }
            .overlay { Grain(opacity: mood.grain) }
            .ignoresSafeArea()
            .task(id: seed) {
                // Regenerated only when the seed changes, once per screen.
                field = SkyField(seed: seed, density: mood.density)
            }
    }
}

extension View {

    /// The one line a screen writes to sit on the night.
    ///
    /// A modifier rather than a wrapper view, because the sky must be *behind*
    /// the screen's own scroll view — a screen nested inside a `NightSky` would
    /// inherit its `ignoresSafeArea` and lose its top inset.
    func nightSky(_ mood: NightSky.Mood = .cabinet, seed: UInt64 = 0x414C_4D41) -> some View {
        self.background(NightSky(mood: mood, seed: seed))
    }
}

#Preview("Cabinet") {
    VStack(spacing: 12) {
        Text("Eight ways to read yourself.").almaDisplayL()
        Text("One Alma.").almaDisplayL().foregroundStyle(Color.almaGoldBright)
    }
    .almaPadding()
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .nightSky(.cabinet)
}

#Preview("Ceremony") {
    Color.clear.nightSky(.ceremony)
}
