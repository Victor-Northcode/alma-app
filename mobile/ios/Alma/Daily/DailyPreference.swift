import Foundation

/// One control, three positions. Not a switch, and not five.
///
/// `docs/THE-DAILY.md §5.1` settles both halves of that. Three, because every
/// additional position is a decision the person has no basis for making and a
/// state that has to be tested in six languages. Not a switch, because the
/// distance between "about once a week" and "a few times a year" is the whole
/// difference between somebody who keeps notifications on and somebody who
/// reaches for the uninstall — and a binary control makes the second person's
/// only option the one that costs us the subscription.
///
/// The raw values are what goes over the wire and into `UserDefaults`, so they
/// are written out rather than derived: an enum whose storage is its case order
/// is an enum that silently repoints everybody's setting when a case is
/// inserted.
enum DailyPreference: String, CaseIterable, Codable, Sendable, Identifiable {

    /// No push, ever. **Today still works** — nothing is withheld, this is a
    /// delivery preference and not a feature gate, and the detail line under
    /// this position says so in all six languages because that sentence is what
    /// makes Off a safe choice rather than a loss.
    case off

    /// The measured rule: weight ≥ 0.35 perfecting today, or a slow body
    /// entering orb at ≥ 0.30. Median 45.5 a year over a 24-chart cohort.
    case occasionally

    /// Weight ≥ 0.50, exact hits only. The Saturn returns and the Pluto squares
    /// and nothing else — 7 to 13 a year.
    case onlyWhatMatters = "only_what_matters"

    var id: String { rawValue }

    var title: LocalizedStringResource {
        switch self {
        case .off: DailyL10n.off
        case .occasionally: DailyL10n.occasionally
        case .onlyWhatMatters: DailyL10n.onlyWhatMatters
        }
    }

    var detail: LocalizedStringResource {
        switch self {
        case .off: DailyL10n.offDetail
        case .occasionally: DailyL10n.occasionallyDetail
        case .onlyWhatMatters: DailyL10n.onlyMattersDetail
        }
    }

    /// Whether this position wants a device token at all. Only `off` does not,
    /// and that distinction is why the token is deleted rather than flagged.
    var wantsDelivery: Bool { self != .off }
}

/// Where the clock came from, so the reader can tell.
///
/// `THE-DAILY.md §5.2` asks for the *source* to be shown beside the zone, and
/// the reason is specific rather than decorative: somebody whose notifications
/// arrive at the wrong hour is somebody who moved, and "Lisbon — from your birth
/// data" is the one line that makes them look for the override instead of
/// deciding the app is broken.
enum DailyClockSource: String, Codable, Sendable {
    case device
    case birth
    case chosen

    var label: LocalizedStringResource {
        switch self {
        case .device: DailyL10n.timezoneFromDevice
        case .birth: DailyL10n.timezoneFromBirth
        case .chosen: DailyL10n.timezoneChosen
        }
    }
}

/// What the phone remembers between launches.
///
/// `UserDefaults` and not the keychain: this is a preference, not a credential,
/// and a preference that survives a reinstall would be a preference somebody
/// cannot reset by reinstalling. It is deliberately *not* the source of truth
/// about whether anything is delivered — that is `UNUserNotificationCenter`,
/// read live, because a person who revokes permission in Settings must not be
/// left looking at a switch of ours that still says On.
struct DailyStore {

    // Not `Sendable`, and deliberately not made so with `@unchecked`.
    // `UserDefaults` is thread-safe but is not annotated as `Sendable`, and the
    // honest fix is that nothing here crosses an isolation boundary: every
    // holder of this struct is `@MainActor`. Silencing the checker would be
    // claiming a guarantee about a type we do not own.
    private let defaults: UserDefaults
    private enum Key {
        static let preference = "alma.daily.preference"
        static let hour = "alma.daily.hour"
        static let askedOnToday = "alma.daily.askedOnToday"
        static let lastToken = "alma.daily.lastToken"
        static let registeredAt = "alma.daily.registeredAt"
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    /// What the person chose, or `nil` because they have not.
    ///
    /// **Optional on purpose, and the optionality is load-bearing.**
    /// `THE-DAILY.md §5.1` sets the default to *Occasionally for a subscriber
    /// and Off for everybody else*, which is not a value — it is a rule that
    /// depends on something this store cannot see. Collapsing "never chose" and
    /// "chose Off" into one stored `off` would either enrol every free reader
    /// or leave every subscriber out, depending on which way the collapse went,
    /// and neither is recoverable afterwards because the two states are gone.
    ///
    /// `DailyModel.preference` applies the rule. This just remembers the answer.
    var preference: DailyPreference? {
        get { defaults.string(forKey: Key.preference).flatMap(DailyPreference.init(rawValue:)) }
        nonmutating set {
            if let newValue {
                defaults.set(newValue.rawValue, forKey: Key.preference)
            } else {
                defaults.removeObject(forKey: Key.preference)
            }
        }
    }

    /// 08:00, and editable, because "I get up at 05:30" is a real fact about a
    /// person and the only one they can tell us that we cannot measure.
    var hour: Int {
        get { defaults.object(forKey: Key.hour) as? Int ?? DailyStore.defaultHour }
        nonmutating set { defaults.set(DailyStore.clamp(newValue), forKey: Key.hour) }
    }

    static let defaultHour = 8
    static let quietFrom = 22
    static let quietUntil = 8

    /// Clamped outside quiet hours rather than validated with an error.
    ///
    /// `THE-DAILY.md §5.2`: quiet hours are shown and not editable, because
    /// making them editable invites somebody to set 03:00 and then file a
    /// complaint about a 03:00 notification. The delivery hour is editable, so
    /// it is the thing that has to be kept inside them.
    static func clamp(_ hour: Int) -> Int {
        let wrapped = ((hour % 24) + 24) % 24
        return (wrapped >= quietUntil && wrapped < quietFrom) ? wrapped : defaultHour
    }

    /// Whether the invitation on Today has been answered — either way.
    ///
    /// Our own question, unlike the platform's, may be asked again; but asking
    /// it on every launch is the nagging the owner named twice. Once per
    /// install until they act on it, and then never as a question again.
    var hasAnsweredTheAsk: Bool {
        get { defaults.bool(forKey: Key.askedOnToday) }
        nonmutating set { defaults.set(newValue, forKey: Key.askedOnToday) }
    }

    /// The last token handed to the server, and when it was accepted.
    ///
    /// Both, because the pair answers the only question the settings screen has
    /// to answer honestly: *is anything actually going to arrive?* A token with
    /// no acceptance is a token APNs minted and nobody stored, which is the
    /// state this whole build is in until the backend route exists.
    var lastToken: String? {
        get { defaults.string(forKey: Key.lastToken) }
        nonmutating set { defaults.set(newValue, forKey: Key.lastToken) }
    }

    var registeredAt: Date? {
        get { defaults.object(forKey: Key.registeredAt) as? Date }
        nonmutating set { defaults.set(newValue, forKey: Key.registeredAt) }
    }

    /// Forget everything about delivery, keeping the preference.
    ///
    /// Called when the server has been told to forget the device, so that the
    /// screen stops claiming a registration that no longer exists on the other
    /// end.
    func clearRegistration() {
        defaults.removeObject(forKey: Key.lastToken)
        defaults.removeObject(forKey: Key.registeredAt)
    }
}

// MARK: — the wire

/// What `POST /v1/notifications/device` carries.
///
/// The shape is `docs/PUSH.md §3`'s table, minus the columns the server fills
/// in for itself. Every field earns its place: `environment` is §1.8's whole
/// argument, `timezone` is what lets an hourly job find 08:00 in this person's
/// day, and the two version strings are what makes "it stopped working on the
/// 14th" answerable.
/// What `POST /v1/notifications/devices` carries — the *device* half.
///
/// **`preference` and `hour` are deliberately not here, and they used to be.**
/// The route's `DeviceIn` sets `extra="forbid"`, so sending them answered
/// `422 extra_forbidden` and the registration failed entirely — which the
/// client then swallowed at `log.debug`. They belong on the user rather than
/// the install anyway: a person has one preference and possibly several
/// phones, and two devices disagreeing about the delivery hour is a question
/// with no correct answer. They go through `PATCH /v1/notifications` instead.
struct DeviceRegistration: Codable, Sendable, Equatable {
    let platform: String
    let token: String
    /// `sandbox` or `production`. See `PushService.environment`.
    let environment: String
    /// An IANA identifier. Never an offset.
    let timezone: String
    let appVersion: String
    let osVersion: String
    /// The device's language, which is what decides which `loc-key` translation
    /// the OS will substitute — so the server can log what it is sending into.
    /// `PUSH.md §1.6`: `user.locale` is the fallback, the device is the truth.
    let locale: String

    private enum CodingKeys: String, CodingKey {
        case platform, token, environment, timezone, locale
        case appVersion = "app_version"
        case osVersion = "os_version"
    }
}

/// What the server answers a registration with: the row it kept.
struct DeviceRegistered: Codable, Sendable, Equatable {
    let platform: String
    let token: String
}

/// What `POST /v1/notifications/devices/delete` carries.
///
/// **A body, not a path segment.** The token used to be interpolated into the
/// URL, which writes a persistent device identifier into access logs, proxy
/// logs, TLS-terminator logs and APM traces — none of them covered by the
/// retention rules in `notify/tokens.py`, none of them cleared by
/// `accounts.erase`, and none of them described in the privacy documentation.
/// The route that creates those copies was the one a person hits to *withdraw*
/// consent, which is the worst possible place for it. The backend chose the
/// POST-with-a-body shape and wrote down why; this now matches it.
struct DeviceForget: Codable, Sendable, Equatable {
    let platform: String
    let token: String
}

/// What `PATCH /v1/notifications` carries. The user-level half.
///
/// Every field is optional because the route treats each independently — a
/// person turning the daily off is not also restating their delivery hour.
/// `daily` is the server's name for the position; `preference` was ours and
/// nothing answered to it.
struct DailySettingsBody: Codable, Sendable, Equatable {
    var daily: String?
    var hour: Int?
    /// An override, when the person set one. Null means "use the ladder":
    /// chosen → device → birth, and nothing below that.
    var timezone: String?

    init(daily: String? = nil, hour: Int? = nil, timezone: String? = nil) {
        self.daily = daily
        self.hour = hour
        self.timezone = timezone
    }
}

/// What `GET|PATCH /v1/notifications` answers with.
struct DailySettings: Codable, Sendable, Equatable {
    let daily: String
    let chosen: Bool
    let hour: Int
    let quietHours: [Int]
    let timezone: String?
    let timezoneSource: String
    let entitled: Bool

    private enum CodingKeys: String, CodingKey {
        case daily, chosen, hour, timezone, entitled
        case quietHours = "quiet_hours"
        case timezoneSource = "timezone_source"
    }
}
