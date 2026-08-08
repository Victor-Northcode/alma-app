import Foundation

/// Every string the skeleton itself shows, named.
///
/// **Why a constant per string rather than `Text("state.offline")` at the call
/// site.** A key spelled at the call site is a key that can be misspelled at the
/// call site, and a misspelled key in a String Catalog does not fail to build —
/// it renders the key, in English, in production, in Brazil. Here the key exists
/// once and every use of it is a compile-checked reference.
///
/// **Why `LocalizedStringResource` and not `String`.** It defers the lookup
/// until the view draws, which is what lets SwiftUI re-resolve everything when
/// the language changes, and what lets a `Text` participate in Xcode's string
/// extraction. A `String(localized:)` resolved at initialisation would freeze
/// the language at whatever it was when the constant was first touched.
///
/// The wording is not invented here. Everything below already exists in
/// `src/lib/i18n/` and is copied across so the two clients say the same thing;
/// the three that are new to the app — the offline, unavailable and
/// account-deleted lines — are written in the same voice, because the web app's
/// versions of those talk about sample data, and this app shows none.
enum L10n {

    // MARK: — the cabinet

    static let tabToday = LocalizedStringResource("tab.today", defaultValue: "Today")
    static let tabSystems = LocalizedStringResource("tab.systems", defaultValue: "My systems")
    static let tabAlma = LocalizedStringResource("tab.alma", defaultValue: "Alma")
    static let tabSettings = LocalizedStringResource("tab.settings", defaultValue: "Settings")

    /// The accessibility label on the tab bar itself.
    static let cabinetSections = LocalizedStringResource("cabinet.sections", defaultValue: "Sections")
    static let cabinetBack = LocalizedStringResource("cabinet.back", defaultValue: "Back")

    // MARK: — the three states

    /// The wait while a chart is computed. Not "Loading…": the wait has a
    /// reason and the sentence says what it is.
    static let stateLoading = LocalizedStringResource("state.loading", defaultValue: "Reading your sky…")
    static let stateLoadingShort = LocalizedStringResource("state.loadingShort", defaultValue: "One moment")

    /// The much longer wait while a chapter is written for the first time.
    static let stateWriting = LocalizedStringResource("state.writing", defaultValue: "Alma is writing this chapter…")

    static let stateRetry = LocalizedStringResource("state.retry", defaultValue: "Try again")

    static let stateOffline = LocalizedStringResource(
        "state.offline",
        defaultValue: "Alma is not answering right now. Nothing here is guessed, so there is nothing to show until she does."
    )

    static let stateUnavailable = LocalizedStringResource(
        "state.unavailable",
        defaultValue: "Something on our side is not working. It is not you, and it is not your chart."
    )

    static let stateAccountDeleted = LocalizedStringResource(
        "state.accountDeleted",
        defaultValue: "This account has been deleted. Nothing of it is kept."
    )

    static let stateLocked = LocalizedStringResource("state.locked", defaultValue: "Unlock to read")

    static let stateNeedsBirthTime = LocalizedStringResource(
        "state.needsBirthTime",
        defaultValue: "This one needs your birth time."
    )

    static let stateSomethingWrong = LocalizedStringResource(
        "state.somethingWrong",
        defaultValue: "Something went wrong. Nothing was lost."
    )

    /// `answer_refused` / `reading_refused`. Alma had nothing she could write
    /// that only cited real placements, and the backend's own message for it is
    /// untranslated engineering prose. This is what a reader sees instead — and
    /// it says what happened rather than apologising for a fault, because it is
    /// not one: an honest silence is the behaviour the validator exists to
    /// produce.
    static let stateNothingToSay = LocalizedStringResource(
        "state.nothingToSay",
        defaultValue: "There was nothing here I could read from your chart, and I will not invent it."
    )
}
