import UIKit

/// The product's whole vocabulary of touch, in one place.
///
/// Three gestures, used rarely, and that is the design: a vibration is the
/// most intimate channel a phone has, and an app that buzzes on every tap has
/// spent it before anything mattered. Alma touches the hand at the moments the
/// sky does something — a system finishing its calculation, a chart arriving,
/// a purchase opening — and at no other time.
///
/// `prepare()` is called just before the moment when the caller knows it is
/// coming, because an unprepared Taptic Engine can miss its first hit by
/// enough to feel detached from what it is confirming.
enum AlmaHaptics {

    /// One soft tick — a system lighting up during the ceremony, a step
    /// falling into place. Soft rather than light: `.soft` is the rounded
    /// impact, and rounded is the only kind of tick that reads as a star
    /// arriving rather than as a keyboard.
    @MainActor
    static func tick() {
        let generator = UIImpactFeedbackGenerator(style: .soft)
        generator.impactOccurred(intensity: 0.6)
    }

    /// The arrival — the portrait revealed, the journey saved. A rigid impact
    /// followed by nothing: a single, certain touch, not a celebration.
    @MainActor
    static func arrival() {
        let generator = UIImpactFeedbackGenerator(style: .rigid)
        generator.impactOccurred(intensity: 0.9)
    }

    /// Something opened that was closed — a purchase confirmed by the server.
    /// The system's success notification, which is two beats and is the one
    /// pattern people already know means "done, and well".
    @MainActor
    static func unlocked() {
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }
}
