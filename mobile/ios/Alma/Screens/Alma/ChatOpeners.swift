import Foundation

/// The three questions offered on an empty conversation.
///
/// **They are this person's, not a brochure's.** A blank field under the words
/// "Ask Alma" tells somebody nothing about what she can do, and three generic
/// prompts tell them only slightly more. The natal preview already names their
/// sun, moon and rising — it is free, it is computed from the ephemeris the
/// moment a birth exists, and every other cabinet screen already shows it — so
/// the opening questions can be about *them* at no cost and with nothing
/// invented.
///
/// **Nothing is guessed.** Each opener needs a sign the payload actually
/// carries; a missing one drops its line rather than substituting a plausible
/// one, exactly as `ChartFacts` does everywhere else. Somebody with no birth
/// time has no rising sign, so they get two chart questions and one that needs
/// no chart at all. Somebody whose chart could not be fetched gets the three
/// written ones, which is the state this screen shipped with.
enum ChatOpeners {

    /// The written three. Also the fallback, because an opening with no
    /// questions in it is worse than an opening with general ones.
    static var written: [String] {
        ScreenL10n.chatPrompts.map { String(localized: $0) }
    }

    /// Read the three signs out of a natal payload and phrase a question about
    /// each. `nil` fields are dropped; the list is topped up from `written` so
    /// the opening always offers three.
    ///
    /// The sign arrives from the engine in English in every locale — it is a
    /// key, not prose — and `JourneyL10n.sign` is the same lookup the journey's
    /// portrait uses, so "Virgo" is "Vergine" in Italian here and there both.
    static func fromChart(_ data: JSONValue) -> [String] {
        var questions: [String] = []

        if let moon = data["moon_sign"]?.stringValue {
            questions.append(String(localized: ScreenL10n.chatPromptMoon(JourneyL10n.sign(moon))))
        }
        if let sun = data["sun_sign"]?.stringValue {
            questions.append(String(localized: ScreenL10n.chatPromptSun(JourneyL10n.sign(sun))))
        }
        if let rising = data["rising_sign"]?.stringValue {
            questions.append(String(localized: ScreenL10n.chatPromptRising(JourneyL10n.sign(rising))))
        }

        // Topped up rather than padded with more chart lines: three questions
        // about the same three signs would be one question asked three ways.
        for fallback in written where questions.count < 3 {
            questions.append(fallback)
        }
        return Array(questions.prefix(3))
    }
}
