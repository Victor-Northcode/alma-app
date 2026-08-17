import Foundation

/// Everything that can come back instead of an answer.
///
/// This is the iOS twin of the `Failure` union in `src/lib/api.ts`, and the
/// reason it is an enum with associated values rather than an `NSError` with a
/// message in it is the same reason it is one there: **the backend's interesting
/// failures are things the interface has to say, not errors to swallow.** A
/// locked chapter is a paywall. A missing birth time is a form. A daylight-saving
/// ambiguity is a question with two buttons. Flattening those into
/// `Error.localizedDescription` and showing it in an alert throws away the whole
/// design of the funnel.
///
/// Every case that carries a `message` carries the backend's own words, which
/// arrive in the account's locale. `localizedDescription` below is only for the
/// cases where the app should say something of its own — offline, chiefly —
/// because there the backend never spoke at all.
enum AlmaError: Error, Sendable, Equatable {

    /// Whether asking again could honestly change the answer. A refusal, a
    /// lock and a spent limit are answers; a hiccup in the writing layer or
    /// the network is weather. The one automatic retry keys on this.
    var isTransient: Bool {
        switch self {
        case .unavailable, .offline: true
        default: false
        }
    }

    /// 402, or a `locked` error body. The chapter exists and is not paid for.
    /// `system` is the door to offer; `chapter` is which one they reached for.
    case locked(system: String, chapter: String?, message: String)

    /// 422 `birth_time_required`. Solar return and astrocartography need the
    /// minute; the answer is a form, not an apology.
    case needsBirthTime(message: String)

    /// 409 `ambiguous_birth_time`. The clock went back and the local time they
    /// gave happened twice. Both instants are offered; the person picks.
    ///
    /// **A question, not a fault.** It is the one refusal in this enum the
    /// server raises on purpose: it will not flip a coin about a sky, because a
    /// coin flipped here lands in the houses, in the solar return and in a chart
    /// somebody is later asked to pay for.
    case ambiguousBirthTime(message: String, fork: BirthTimeFork)

    /// 422 `partner_required`. A compatibility reading with nobody to read it
    /// against. Its own case because the answer is a door — the people screen —
    /// and `.invalid` renders its message as flat text with nothing to tap.
    case partnerRequired(message: String)

    /// The free three-a-day, or a door's fifteen, are used up.
    case questionLimit(message: String, allowance: Int)

    /// A checkout cannot be created without an address. Kept distinct from
    /// `invalid` because the answer is a field on the offer screen, and a
    /// generic "something went wrong" leaves somebody tapping a button that can
    /// never work.
    case needsEmail(message: String)

    /// 401. The token is not good. On this client that should be impossible
    /// after a successful `session()`, so it means the token was revoked.
    case unauthenticated(message: String)

    /// 410. The account behind the stored token is gone. The client clears the
    /// keychain when it sees this — holding a dead token would make every
    /// later request fail the same way with no way out.
    case accountDeleted(message: String)

    /// 503, or one of `ai_unavailable` / `billing_unavailable` /
    /// `budget_exceeded` / `place_index_missing`. Ours, temporary, and not the
    /// person's fault.
    case unavailable(message: String)

    /// No network, or nothing listening. A dead Wi-Fi and a dead backend look
    /// identical from here and the interface says the same thing about both.
    case offline

    /// 422 `answer_refused` or `reading_refused`. **Not a fault, and not a bug
    /// report.** Alma could not write something that only cites real factors —
    /// either the chart had nothing to read from, or two attempts both tripped
    /// the validator. The backend's message for it is `str(exc)`: English
    /// engineering prose written for whoever is reading the traceback, so it is
    /// deliberately *not* surfaced. `displayText` says it in the reader's own
    /// language instead.
    case refused(message: String)

    /// 422 for any other reason — a malformed date, a birthday in 1600.
    case invalid(message: String)

    /// Anything else the server said, with its status, so a bug report has a
    /// number in it.
    case http(status: Int, message: String)

    /// The response was 200 and was not the shape we expected. Almost always a
    /// backend change that has not reached this client yet, which is worth
    /// distinguishing from a server error.
    case malformedResponse(detail: String)

    /// Which of the two instants a repeated local time refers to.
    struct AmbiguityOption: Sendable, Equatable, Codable {
        /// `"earlier"` or `"later"` — passed straight back as `on_ambiguous`.
        let choice: String
        /// The resolved UTC instant, ISO-8601.
        let utc: String
        /// What the clock was called that night — CEST, CET, EDT.
        ///
        /// The only thing that tells two identical wall-clock times apart on a
        /// screen, and it has to come from the server: a phone carries no
        /// zone-history database to work out which abbreviation was in force in
        /// 1988.
        var abbreviation: String = ""
        /// This instant's offset from UTC, in hours.
        var offsetHours: Double = 0
    }

    /// Everything the fork screen needs to ask its question.
    ///
    /// A type rather than a bare array because the screen needs what a plain
    /// refusal does not carry: two instants with the names the clock wore that
    /// night, and the date it moved. Without it those would be a sentence that
    /// had to be parsed back apart.
    struct BirthTimeFork: Sendable, Equatable, Codable {
        let options: [AmbiguityOption]
        /// `YYYY-MM-DD`, or empty when the server did not name it — the screen
        /// then asks without the date rather than inventing one.
        var transitionLocalDate: String = ""

        var earlier: AmbiguityOption? { options.first { $0.choice == "earlier" } }
        var later: AmbiguityOption? { options.first { $0.choice == "later" } }

        /// How far apart the two instants are, in hours.
        ///
        /// A number and not the word "hour": half-hour transitions exist — Lord
        /// Howe Island and its like — and a caption confidently naming an hour
        /// would simply be untrue there.
        var gapHours: Double? {
            guard let earlier, let later else { return nil }
            return earlier.offsetHours - later.offsetHours
        }
    }
}

extension AlmaError {

    /// The backend's own sentence, where there is one.
    ///
    /// Deliberately not `LocalizedError.errorDescription`: adopting that
    /// protocol makes every one of these renderable in an alert with one line
    /// of code, and the point of the enum is that most of them must *not* be
    /// rendered in an alert.
    var serverMessage: String? {
        switch self {
        case .locked(_, _, let message),
             .needsBirthTime(let message),
             .ambiguousBirthTime(let message, _),
             .partnerRequired(let message),
             .questionLimit(let message, _),
             .needsEmail(let message),
             .unauthenticated(let message),
             .accountDeleted(let message),
             .unavailable(let message),
             .invalid(let message),
             .http(_, let message):
            message
        // `.refused` carries its message for logs and for a bug report, and
        // withholds it from the screen: it is untranslated prose from inside
        // `conversation.py`. Every caller writes `serverMessage ?? displayText`,
        // so returning `nil` here is what routes it to the localised sentence.
        case .refused, .offline, .malformedResponse:
            nil
        }
    }

    /// What a `ScreenState.failed` renders when the screen has nothing more
    /// specific to say. Localised into all six languages.
    var displayText: LocalizedStringResource {
        switch self {
        case .offline:
            L10n.stateOffline
        case .unavailable:
            L10n.stateUnavailable
        case .accountDeleted:
            L10n.stateAccountDeleted
        case .locked:
            L10n.stateLocked
        case .needsBirthTime:
            L10n.stateNeedsBirthTime
        case .refused:
            L10n.stateNothingToSay
        default:
            L10n.stateSomethingWrong
        }
    }

    /// Whether offering a retry button makes sense. A locked chapter does not
    /// unlock by asking again, and a button that cannot work is worse than no
    /// button.
    var isRetryable: Bool {
        switch self {
        case .offline, .unavailable, .http, .malformedResponse: true
        // `.refused` is not retryable: asking the same question again produces
        // the same refusal, and on the chat route it has already been charged.
        case .locked, .needsBirthTime, .ambiguousBirthTime, .partnerRequired,
             .questionLimit, .needsEmail, .unauthenticated, .accountDeleted,
             .invalid, .refused: false
        }
    }
}
