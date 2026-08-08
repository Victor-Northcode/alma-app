import Foundation
import OSLog

/// The client for the Alma backend, and the only thing in the app that knows a
/// URL.
///
/// Its responsibilities are exactly the three the web client has, and nothing
/// else lives here.
///
/// **The guest token.** Every request carries it; the first request that has
/// none gets one back in `X-Alma-Token` and stores it in the keychain. That is
/// what makes the product usable before anyone has signed in — and why the
/// token is captured from *every* response rather than only from the sign-in
/// call. Signing in later attaches an identity to the same account instead of
/// replacing it.
///
/// **Typed failures.** A locked chapter is 402, a missing birth time is 422
/// with `birth_time_required`, a daylight-saving ambiguity is 409 with two
/// candidate instants. Each of those is something the interface has to *say*,
/// so they come back as `AlmaError` cases rather than as a thrown `NSError`
/// with a sentence in it. The methods use typed `throws(AlmaError)`, which
/// means a screen's `catch` is exhaustive and the compiler tells an agent about
/// the paywall case they forgot.
///
/// **Nothing else.** No caching, no retries, no astrology, no view state. A
/// screen that needs a chart asks for one.
///
/// It is a `final class` conforming to `Sendable` rather than an `actor`: it has
/// no mutable state to protect (the token lives behind its own lock in
/// `TokenStoring`), and an actor would serialise eight independent system
/// calculations that the backend is perfectly happy to answer in parallel.
final class AlmaClient: Sendable {

    let baseURL: URL
    private let session: URLSession
    private let tokens: any TokenStoring
    private let installation: any InstallationIdentifying
    private let log = Logger(subsystem: "ai.pazl.alma", category: "api")

    /// The header the backend mints tokens in. Lowercased because
    /// `HTTPURLResponse.value(forHTTPHeaderField:)` is case-insensitive but
    /// direct dictionary reads are not, and this constant has been copied wrong
    /// before.
    static let tokenHeader = "X-Alma-Token"

    /// The header this app *sends* to say which installation it is, while it
    /// has no account. The server never mints one and never sends one back —
    /// there is nothing to read off a response — because a server that issued
    /// them would issue one per tokenless request and turn one launch into four
    /// visitors.
    static let anonHeader = "X-Alma-Anon"

    /// The header this app sends to say what clock the phone is on. An IANA
    /// zone identifier — "Europe/Warsaw", never an offset, because an offset
    /// cannot survive a daylight-saving change and a daily is a thing about a
    /// day. See the note where it is set.
    static let timezoneHeader = "X-Alma-Timezone"

    /// Whether this device already has an account.
    ///
    /// Read by `AlmaSessionModel.start()`, which must not call `session()`
    /// without one: that route's whole job is "mint or read the account", so
    /// calling it on every launch is what made opening the app an act of
    /// enrolment. Exposed here rather than handing the token store to the
    /// session model, so that nothing above this file ever sees the credential.
    var hasAccount: Bool { tokens.read() != nil }

    init(
        baseURL: URL = AlmaClient.configuredBaseURL,
        // The shared store, not a fresh one. See `KeychainTokenStore.shared`:
        // two instances hold two in-memory caches and drift apart.
        tokens: any TokenStoring = KeychainTokenStore.shared,
        // And the shared installation id, for the sharper version of the same
        // reason: two instances racing to mint at first launch produce two ids
        // for one install, which is two rows at the top of the funnel.
        installation: any InstallationIdentifying = DefaultsInstallationId.shared,
        session: URLSession = .almaDefault
    ) {
        self.baseURL = baseURL
        self.tokens = tokens
        self.installation = installation
        self.session = session
    }

    /// Where the backend is, from `ALMAAPIBase` in the Info.plist, which is
    /// `$(ALMA_API_BASE)` and therefore a build setting: localhost:8018 in
    /// Debug, the production host in Release. Pointing a build at staging is a
    /// configuration change, not a code change.
    static var configuredBaseURL: URL {
        let raw = Bundle.main.object(forInfoDictionaryKey: "ALMAAPIBase") as? String
        guard let raw, let url = URL(string: raw.trimmingTrailingSlash()) else {
            // A build that cannot find its own backend is a broken build, and
            // failing at launch is better than every screen showing "offline".
            preconditionFailure("ALMAAPIBase is missing or unreadable in Info.plist")
        }
        return url
    }

    // MARK: — identity

    /// Mint or read the account.
    ///
    /// **Not safe to call on every launch, which is what it used to say.** This
    /// is the one route whose entire job is "mint or read": with a token it
    /// identifies the existing account and creates nothing, and *without* one it
    /// creates a row. `AlmaSessionModel.start()` called it unconditionally, so
    /// opening the app was the act that created the account — on 100% of
    /// installs, before anybody had typed anything, which is exactly what the
    /// owner's rule ("not on a page view") forbids. The route is correct as it
    /// is; the caller was not, and `hasAccount` is what the caller checks now.
    ///
    /// There is one place it is still called deliberately without a token, and
    /// it is the one this file should keep: verifying a purchase, where the
    /// account has to exist *before* the request goes out or the money lands on
    /// a row nobody can reach. A purchase is an act.
    func session() async throws(AlmaError) -> AlmaSessionInfo {
        try await get("/v1/auth/session")
    }

    func refresh() async throws(AlmaError) -> AlmaSessionInfo {
        try await post("/v1/auth/refresh", body: EmptyBody())
    }

    /// Sign in with Apple.
    ///
    /// The identity token is handed straight over and is never decoded here: a
    /// token verified in the app is a token verified by whoever controls the
    /// app. The signature check against Apple's published keys, and the
    /// audience check that it was minted for *us*, both happen in
    /// `alma/auth/providers.py`.
    func signInWithApple(
        identityToken: String,
        fullName: String? = nil
    ) async throws(AlmaError) -> AlmaSessionInfo {
        try await post("/v1/auth/apple", body: AppleSignIn(identityToken: identityToken, fullName: fullName))
    }

    func signInWithGoogle(credential: String) async throws(AlmaError) -> AlmaSessionInfo {
        try await post("/v1/auth/google", body: GoogleSignIn(credential: credential))
    }

    func requestMagicLink(email: String, locale: AppLocale) async throws(AlmaError) -> MagicLinkSent {
        try await post("/v1/auth/magic-link", body: MagicLinkRequest(email: email, locale: locale.rawValue))
    }

    func consumeMagicLink(token: String) async throws(AlmaError) -> AlmaSessionInfo {
        try await post("/v1/auth/magic-link/consume", body: MagicLinkConsume(token: token))
    }

    func account() async throws(AlmaError) -> AlmaAccount {
        try await get("/v1/account")
    }

    func setLocale(_ locale: AppLocale) async throws(AlmaError) -> LocaleUpdated {
        try await request("/v1/account", method: "PATCH", body: LocalePatch(locale: locale.rawValue))
    }

    func setDisplayName(_ name: String) async throws(AlmaError) -> LocaleUpdated {
        try await request("/v1/account", method: "PATCH", body: DisplayNamePatch(displayName: name))
    }

    /// Everything we hold about this account, as one document.
    func exportAccount() async throws(AlmaError) -> JSONValue {
        try await get("/v1/account/export")
    }

    /// Erase the account and everything in it. `confirm` must equal the
    /// account's own email address — the route destroys paid readings that
    /// cannot be regenerated identically, and a mistyped tap should not reach it.
    func deleteAccount(confirm: String) async throws(AlmaError) -> AccountDeleted {
        try await post("/v1/account/delete", body: DeleteConfirm(confirm: confirm))
    }

    // MARK: — places

    func searchPlaces(_ query: String) async throws(AlmaError) -> [Place] {
        try await get("/v1/places/search", query: ["q": query, "limit": "8"])
    }

    /// The zone at a coordinate, on a date — because a zone's *offset* depends
    /// on the day, and a birth in 1978 is not in the same offset as one today.
    func timezone(
        latitude: Double,
        longitude: Double,
        on date: String? = nil
    ) async throws(AlmaError) -> TimezoneAt {
        var query = ["latitude": String(latitude), "longitude": String(longitude)]
        if let date { query["on"] = date }
        return try await get("/v1/places/timezone", query: query)
    }

    // MARK: — profiles

    func profiles() async throws(AlmaError) -> [Profile] {
        try await get("/v1/profiles")
    }

    func profile(id: String) async throws(AlmaError) -> Profile {
        try await get("/v1/profiles/\(id)")
    }

    /// Save a birth.
    ///
    /// `isSelf` defaults to `nil`, meaning "not said", which the backend
    /// resolves to the first birth an account saves and to nobody after that.
    /// Sending `true` while adding a partner *deletes* the account owner's own
    /// chart and every reading keyed to it, so the safe value is the default
    /// here as well as there.
    func saveProfile(
        _ birth: BirthInput,
        isSelf: Bool? = nil,
        relation: String? = nil,
        gender: String? = nil
    ) async throws(AlmaError) -> Profile {
        try await post(
            "/v1/profiles",
            body: ProfileInput(
                birth: birth,
                isSelf: isSelf,
                relation: relation,
                gender: gender,
                locale: AppLocale.current.rawValue
            )
        )
    }

    func deleteProfile(id: String) async throws(AlmaError) {
        _ = try await requestVoid("/v1/profiles/\(id)", method: "DELETE")
    }

    // MARK: — the eight systems

    /// Compute one system. Free, always — what is sold is the writing.
    ///
    /// `profileId` names whose chart; omitting it uses the account's own.
    /// `extra` carries the per-system arguments (`days` for transits, `year` for
    /// the solar return, `other_profile_id` for compatibility) as loose JSON,
    /// because four of the eight take different ones and a single struct with
    /// every optional field would let a caller send `days` to numerology — which
    /// the backend refuses outright, since its request models forbid extra keys.
    /// Keys may be written either way: the encoder converts camelCase to
    /// snake_case and leaves an already-snake_case key alone.
    func compute(
        _ system: SystemSlug,
        profileId: String? = nil,
        houseSystem: String = "placidus",
        locale: AppLocale = .current,
        extra: [String: JSONValue] = [:]
    ) async throws(AlmaError) -> CalcResult {
        var body: [String: JSONValue] = extra
        body["house_system"] = .string(houseSystem)
        body["locale"] = .string(locale.rawValue)
        if let profileId { body["profile_id"] = .string(profileId) }
        return try await post("/v1/systems/\(system.path)", body: JSONValue.object(body))
    }

    /// Every system and its state, in one request. What Today and Systems open on.
    func hub() async throws(AlmaError) -> Hub {
        try await get("/v1/systems/hub")
    }

    // MARK: — readings

    /// The table of contents for a system, in the reader's language.
    ///
    /// The locale is not optional decoration here. This list is where somebody
    /// decides what to read: the title is the largest type on the screen and
    /// the question underneath is the reason anybody taps. Both were English
    /// on every device until this parameter existed — a German reader with a
    /// German interface, a German store listing and a chapter written in
    /// German opened the list and read *"Core — What am I actually like,
    /// underneath?"*.
    ///
    /// It defaults to `.current` and not to `.en`, because the fallback is
    /// already inside `AppLocale.current` and it is a deliberate one: the
    /// device's preferred languages, narrowed to the six we ship, with a
    /// Portuguese phone landing on Brazilian rather than on English. The
    /// backend narrows again on its side — it has to, since it cannot trust a
    /// client — and reports which of the six it answered in.
    func chapters(
        of system: SystemSlug,
        locale: AppLocale = .current
    ) async throws(AlmaError) -> ChapterList {
        try await get("/v1/readings/\(system.path)/chapters", query: ["locale": locale.rawValue])
    }

    /// The free natal preview: five spheres, two sentences each, written once
    /// per chart and cached server-side. Slow only the first time anybody asks.
    func natalSpheres(locale: AppLocale = .current) async throws(AlmaError) -> SpheresResponse {
        try await get("/v1/natal/spheres", query: ["locale": locale.rawValue])
    }

    /// Fetch a chapter, writing it the first time it is asked for.
    ///
    /// This is the only slow call in the app — the first read of a chapter is a
    /// model generating three hundred words — and the only one that can take a
    /// double-digit number of seconds. `URLSession.almaDefault` gives it room;
    /// the screen shows `states.writing` while it waits, and says so honestly.
    func reading(
        system: SystemSlug,
        chapter: String,
        profileId: String? = nil,
        partnerProfileId: String? = nil,
        locale: AppLocale = .current,
        houseSystem: String = "placidus"
    ) async throws(AlmaError) -> ReadingResponse {
        try await post(
            "/v1/readings",
            body: ReadingRequest(
                profileId: profileId,
                system: system.rawValue,
                chapter: chapter,
                locale: locale.rawValue,
                houseSystem: houseSystem,
                partnerProfileId: partnerProfileId
            )
        )
    }

    // MARK: — conversation

    func ask(
        _ message: String,
        threadId: String? = nil,
        profileId: String? = nil,
        locale: AppLocale = .current
    ) async throws(AlmaError) -> ChatReply {
        try await post(
            "/v1/chat",
            body: ChatRequest(
                message: message, threadId: threadId, profileId: profileId, locale: locale.rawValue
            )
        )
    }

    func threads() async throws(AlmaError) -> ChatThreadList {
        try await get("/v1/chat/threads")
    }

    func thread(id: String) async throws(AlmaError) -> ChatThread {
        try await get("/v1/chat/threads/\(id)")
    }

    // MARK: — the ladder

    /// The price list.
    ///
    /// On iOS the *numbers* come from StoreKit, because Apple is the merchant
    /// of record and its localised price is what the buyer is charged. This
    /// call is still needed for the shape of the ladder: which keys are on the
    /// shelf for this account, what each one grants, and whether the archive
    /// has been substituted by the upgrade.
    func catalogue(country: String? = nil) async throws(AlmaError) -> Catalogue {
        try await get("/v1/billing/catalogue", query: country.map { ["country": $0] } ?? [:])
    }

    /// What this account holds. The one call that decides what is behind a
    /// paywall, and the one that must be re-read after a purchase.
    func entitlements(country: String? = nil) async throws(AlmaError) -> Entitlements {
        try await get("/v1/billing/entitlements", query: country.map { ["country": $0] } ?? [:])
    }

    /// Stop the next charge and keep everything already paid for.
    ///
    /// Takes no identifier deliberately: the account is the identifier. A
    /// subscription id in this body would be an IDOR against a payment
    /// processor, and the endpoint refuses one.
    ///
    /// Note for whoever wires in-app purchase: a StoreKit subscription is
    /// cancelled in the App Store, not here. This route stays for accounts that
    /// subscribed on the web.
    func cancelSubscription() async throws(AlmaError) -> SubscriptionCancelled {
        try await post("/v1/billing/subscription/cancel", body: EmptyBody())
    }

    // MARK: — the daily

    /// Hand this device's push token to the server.
    ///
    /// **The path is `/devices`, plural, and that is not a detail.** This used
    /// to post to `/v1/notifications/device` — a route that does not exist —
    /// and the failure was swallowed at `log.debug`, so the app looked like it
    /// had registered and nothing had. The mounted routes are
    /// `POST /v1/notifications/devices`,
    /// `POST /v1/notifications/devices/delete` and
    /// `GET|PATCH /v1/notifications`; all three of the old paths answered 404.
    ///
    /// `environment` is on the body rather than inferred server-side because
    /// `PUSH.md §1.8` turns on it: a TestFlight build carries a *production*
    /// APNs token and a debug build a sandbox one, they are indistinguishable
    /// as strings, and sending a sandbox token to the production endpoint gets
    /// `400 BadDeviceToken` from a device that is working perfectly.
    @discardableResult
    func registerDevice(_ body: DeviceRegistration) async throws(AlmaError) -> DeviceRegistered {
        try await post("/v1/notifications/devices", body: body)
    }

    /// Forget this device.
    ///
    /// Sent when the person turns the daily off, and when the OS reports the
    /// permission revoked. `PUSH.md §6.2(6)`: off deletes the row rather than
    /// setting a flag consulted before sending, because the row is the simplest
    /// possible proof that off means off, and it is the withdrawal-of-consent
    /// obligation 4.5.4 puts on us.
    ///
    /// A POST with the token in the **body**. A `DELETE` with a body is legal
    /// and inconsistently supported by proxies, and the token in a URL path
    /// ends up in every access log between here and the database — on the one
    /// route whose whole purpose is to stop us holding it.
    func forgetDevice(platform: String = "ios", token: String) async throws(AlmaError) {
        _ = try await requestVoid(
            "/v1/notifications/devices/delete",
            method: "POST",
            body: DeviceForget(platform: platform, token: token)
        )
    }

    /// The three positions, the delivery hour and the timezone override.
    ///
    /// These belong on the **user** and not the profile — a person has one
    /// phone and several charts — which is the ask `THE-DAILY.md §6.8` makes of
    /// `alma/auth/accounts.py`, a file another workflow owns. Until it lands
    /// this call 404s and the preference lives on the device alone, which is
    /// survivable in exactly one direction: a preference that never reaches the
    /// server means nothing is ever sent, and nothing being sent is the safe
    /// failure.
    /// **`PATCH /v1/notifications`, which nothing was calling at all.**
    ///
    /// This used to post to `/v1/account/daily`, which does not exist. That
    /// route is the only writer of `User.daily_push`, so the server-side
    /// preference column could never leave null and `tokens.forget` on the
    /// off path was unreachable — meaning "off" never reached the server by
    /// any route. Masked only because registration 404'd too, so there was
    /// nothing stored to delete; whoever fixed registration alone would have
    /// shipped a working sender with a non-working off switch, which is the
    /// worst possible ordering.
    ///
    /// Answers `402 locked` for a free reader turning it *on*, which is the
    /// paywall the settings screen already knows how to show. Turning it
    /// **off** is always allowed.
    @discardableResult
    func setDailyPreference(_ body: DailySettingsBody) async throws(AlmaError) -> DailySettings {
        try await request("/v1/notifications", method: "PATCH", body: body)
    }

    /// What the settings screen shows, including why it says what it says.
    func dailySettings() async throws(AlmaError) -> DailySettings {
        try await get("/v1/notifications")
    }

    // MARK: — the funnel

    /// Report a funnel stage. Fire-and-forget by design.
    ///
    /// It swallows its own failures because a beacon that can fail a screen is
    /// worse than a beacon that misses a row.
    ///
    /// **A beacon mints nothing now, and there is no token on the response to
    /// capture.** This used to say the opposite, and it was true: `POST
    /// /v1/events` answered every tokenless caller with a fresh account, so the
    /// paragraph here argued that the header had to be picked up or every
    /// beacon would enrol somebody. The route takes `deps.Visitor` today — it
    /// reads an account from the bearer token if there is one and creates
    /// nothing if there is not — and what joins a stage recorded before the
    /// account to the account that appears later is the installation id on
    /// `X-Alma-Anon`, which the request builder puts on every call. A stage sent
    /// with neither identity is answered 422 `anonymous_id_required` and
    /// swallowed here, which is why the id is minted by the request builder
    /// rather than by anything on this path.
    func track(_ stage: FunnelStage, meta: [String: JSONValue] = [:]) async {
        do {
            let _: JSONValue = try await post(
                "/v1/events",
                body: FunnelEvent(stage: stage.rawValue, meta: meta.isEmpty ? nil : .object(meta))
            )
        } catch {
            log.debug("funnel beacon \(stage.rawValue, privacy: .public) dropped: \(String(describing: error))")
        }
    }

    // MARK: — the request

    private func get<Response: Decodable>(
        _ path: String,
        query: [String: String] = [:]
    ) async throws(AlmaError) -> Response {
        try await request(path, method: "GET", query: query, body: Optional<EmptyBody>.none)
    }

    private func post<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body
    ) async throws(AlmaError) -> Response {
        try await request(path, method: "POST", body: body)
    }

    private func request<Body: Encodable, Response: Decodable>(
        _ path: String,
        method: String,
        query: [String: String] = [:],
        body: Body?
    ) async throws(AlmaError) -> Response {
        let data = try await perform(path, method: method, query: query, body: body)

        // 204 and an empty body: the caller asked for `Void`-ish work and there
        // is nothing to decode. `JSONValue.null` is the honest stand-in.
        if data.isEmpty, let empty = JSONValue.null as? Response { return empty }

        do {
            return try Self.decoder.decode(Response.self, from: data)
        } catch {
            throw .malformedResponse(detail: "\(path): \(error)")
        }
    }

    private func requestVoid(
        _ path: String,
        method: String
    ) async throws(AlmaError) -> Data {
        try await perform(path, method: method, query: [:], body: Optional<EmptyBody>.none)
    }

    private func requestVoid<Body: Encodable>(
        _ path: String,
        method: String,
        body: Body
    ) async throws(AlmaError) -> Data {
        try await perform(path, method: method, query: [:], body: body)
    }

    private func perform<Body: Encodable>(
        _ path: String,
        method: String,
        query: [String: String],
        body: Body?
    ) async throws(AlmaError) -> Data {
        guard var components = URLComponents(
            url: baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false
        ) else {
            throw .malformedResponse(detail: "cannot build a URL for \(path)")
        }
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components.url else {
            throw .malformedResponse(detail: "cannot build a URL for \(path)")
        }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = method
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = tokens.read() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        // On **every** request, not only on the beacons, and that is the whole
        // mechanism rather than belt and braces. The request that finally mints
        // an account — `saveProfile`, a sign-in, `iap/verify` — is the one the
        // server claims this id on, because it is the one moment "that
        // installation became this account" is something we watched happen
        // rather than inferred. Send it only on beacons and the minting request
        // arrives bare, nothing is claimed, and the stages before the account
        // and the stages after it are two people for ever.
        urlRequest.setValue(installation.ensure(), forHTTPHeaderField: Self.anonHeader)
        // The device's own IANA zone, on every request.
        //
        // `Profile.timezone` is the **birth** timezone — it is derived from the
        // birthplace — so a person born in Lisbon and living in Toronto would be
        // sent their daily at 03:00 if that were the only clock we had. There is
        // no other source: nothing in this app has ever told the server where
        // the phone is.
        //
        // `deps.py` is owned by another workflow and does not read this header
        // yet; sending it now costs one line and means the day it starts
        // reading, every build already in the field is supplying it. Ignored
        // silently when unrecognised, exactly as the country header is —
        // `docs/PUSH.md §3` and `THE-DAILY.md §6.8` both ask for that shape.
        //
        // It rides on every call rather than only on device registration
        // because a person who travels re-registers nothing: the requests they
        // make are the only evidence the clock moved.
        urlRequest.setValue(TimeZone.current.identifier, forHTTPHeaderField: Self.timezoneHeader)
        // The device's language, set explicitly rather than left to CFNetwork's
        // automatic header. The server reads it in one place: the request that
        // mints a guest, so `user.locale` starts as the phone's language
        // instead of English-until-the-locale-PATCH-lands.
        urlRequest.setValue(
            Locale.preferredLanguages.first ?? "en", forHTTPHeaderField: "Accept-Language"
        )
        if let body {
            do {
                urlRequest.httpBody = try Self.encoder.encode(body)
            } catch {
                throw .malformedResponse(detail: "cannot encode the body for \(path): \(error)")
            }
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: urlRequest)
        } catch {
            // A dead network and a dead backend look the same from here, and
            // the interface says the same thing about both. A cancelled task is
            // not a failure to report, but it is also not a success, so it
            // travels as `offline` and the screen that cancelled it is gone by
            // the time it lands.
            throw .offline
        }

        guard let http = response as? HTTPURLResponse else {
            throw .malformedResponse(detail: "\(path): not an HTTP response")
        }

        // Any response may mint a guest token — the very first one usually does.
        if let issued = http.value(forHTTPHeaderField: Self.tokenHeader), !issued.isEmpty {
            tokens.write(issued)
        }

        if (200..<300).contains(http.statusCode) { return data }
        throw classify(status: http.statusCode, data: data)
    }

    /// Turn a failed response into the state the interface has to render.
    ///
    /// The `error` string in the body outranks the status code, because the
    /// backend uses one status for several distinct situations — 422 is both a
    /// missing birth time and a malformed date, and those are two different
    /// screens.
    private func classify(status: Int, data: Data) -> AlmaError {
        let payload = try? Self.decoder.decode(JSONValue.self, from: data)
        // FastAPI wraps our structured errors in `detail`; a plain `raise
        // HTTPException(..., detail="…")` puts a bare string there instead.
        let detail = payload?["detail"]
        let object = detail?.objectValue != nil ? detail : payload
        let message =
            detail?.stringValue
            ?? object?["message"]?.stringValue
            ?? object?["detail"]?.stringValue
            ?? "something went wrong"

        switch object?["error"]?.stringValue {
        case "locked":
            return .locked(
                system: object?["system"]?.stringValue ?? "",
                chapter: object?["chapter"]?.stringValue,
                message: message
            )
        case "birth_time_required":
            return .needsBirthTime(message: message)
        case "email_required":
            return .needsEmail(message: message)
        case "ambiguous_birth_time":
            let options = (object?["options"]?.arrayValue ?? []).compactMap { item -> AlmaError.AmbiguityOption? in
                guard let choice = item["choice"]?.stringValue, let utc = item["utc"]?.stringValue
                else { return nil }
                return AlmaError.AmbiguityOption(choice: choice, utc: utc)
            }
            return .ambiguousBirthTime(message: message, options: options)
        case "question_limit":
            return .questionLimit(message: message, allowance: object?["allowance"]?.intValue ?? 0)
        case "ai_unavailable", "billing_unavailable", "budget_exceeded", "place_index_missing":
            return .unavailable(message: message)
        // Not a fault, and the one 422 whose message must never reach a screen.
        // `answer_refused` and `reading_refused` are raised when nothing could
        // be written that only cites real placements — an honest silence, which
        // is what the validator is *for* — and both carry `str(exc)`: English
        // prose written for whoever reads the traceback. Without this branch
        // they landed on `.invalid`, whose message is rendered verbatim, so a
        // Portuguese reader was shown a sentence from `conversation.py`.
        case "answer_refused", "reading_refused":
            return .refused(message: message)
        default:
            break
        }

        switch status {
        case 401:
            return .unauthenticated(message: message)
        case 402:
            return .locked(system: "", chapter: nil, message: message)
        case 410:
            // The account behind this token is gone. Keeping it would make
            // every later request fail the same way with no way out.
            tokens.clear()
            // And the installation id goes with it, always. It is the string
            // the deleted account's funnel rows are keyed to; a device that
            // kept it would carry an identifier belonging to somebody who asked
            // to be erased straight into the next account it makes, and the
            // server would refuse the claim because the id is already spoken
            // for by a row that no longer exists.
            installation.clear()
            return .accountDeleted(message: message)
        case 422:
            return .invalid(message: message)
        case 429:
            return .questionLimit(message: message, allowance: 0)
        case 503:
            return .unavailable(message: message)
        default:
            return .http(status: status, message: message)
        }
    }

    // MARK: — coders

    /// One decoder, configured once. `.convertFromSnakeCase` is why no model in
    /// `APIModels.swift` carries a `CodingKeys` block.
    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()

    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()
}

// MARK: — request bodies

/// These are `private`-by-convention shapes: nothing outside this file should
/// construct one, because the client's methods are the API.

private struct EmptyBody: Encodable {}

private struct AppleSignIn: Encodable {
    let identityToken: String
    let fullName: String?
}

private struct GoogleSignIn: Encodable {
    let credential: String
}

private struct MagicLinkRequest: Encodable {
    let email: String
    let locale: String
}

private struct MagicLinkConsume: Encodable {
    let token: String
}

private struct LocalePatch: Encodable {
    let locale: String
}

private struct DisplayNamePatch: Encodable {
    let displayName: String
}

private struct DeleteConfirm: Encodable {
    let confirm: String
}

private struct ProfileInput: Encodable {
    let birth: BirthInput
    let isSelf: Bool?
    let relation: String?
    let gender: String?
    /// The language a refusal should arrive in — the partner-limit 402 answers
    /// from this rather than the account's stored locale, which on a fresh
    /// guest can still be the minting default.
    let locale: String

    /// Flattened, because the route takes the birth fields at the top level
    /// alongside `is_self` and `relation` rather than nested under `birth`.
    func encode(to encoder: any Encoder) throws {
        try birth.encode(to: encoder)
        var container = encoder.container(keyedBy: Key.self)
        try container.encodeIfPresent(isSelf, forKey: .isSelf)
        try container.encodeIfPresent(relation, forKey: .relation)
        try container.encodeIfPresent(gender, forKey: .gender)
        try container.encode(locale, forKey: .locale)
    }

    /// Written out because `.convertToSnakeCase` does not apply to a manual
    /// `container(keyedBy:)` whose keys are already the wire names.
    private enum Key: String, CodingKey {
        case isSelf = "is_self"
        case relation
        case gender
        case locale
    }
}

private struct ReadingRequest: Encodable {
    let profileId: String?
    let system: String
    let chapter: String?
    let locale: String
    let houseSystem: String
    let partnerProfileId: String?
}

private struct ChatRequest: Encodable {
    let message: String
    let threadId: String?
    let profileId: String?
    let locale: String
}

private struct FunnelEvent: Encodable {
    let stage: String
    let meta: JSONValue?
}

// MARK: — the session

extension URLSession {

    /// The session every request goes through.
    ///
    /// The 120-second resource timeout is not generosity: the first read of a
    /// chapter is a language model writing three hundred words from a chart,
    /// and the default 60 seconds cuts a *successful* generation off at the
    /// knees — the person is charged for a reading the app then reports as
    /// offline. The 30-second request timeout still catches a dead network
    /// quickly, because that one measures the gap between bytes.
    static let almaDefault: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 120
        configuration.waitsForConnectivity = false
        // Responses are per-account and already stored where they need to be
        // (a written chapter lives in the backend's database). A URL cache
        // would serve one account's hub to the next one after a sign-out.
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: configuration)
    }()
}

private extension String {
    func trimmingTrailingSlash() -> String {
        hasSuffix("/") ? String(dropLast()) : self
    }
}
