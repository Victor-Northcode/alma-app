import AuthenticationServices
import CryptoKit
import Foundation

/// Sign in with Google, without Google's SDK.
///
/// The SDK is a large dependency whose whole job here would be one OAuth
/// round trip, and this product's house rule is that identity tokens are
/// verified on the server, never in the app — `alma/auth/providers.py` checks
/// the signature against Google's published keys and the audience against
/// `GOOGLE_CLIENT_ID`. So the app only has to *obtain* an ID token, and the
/// system gives us everything needed: `ASWebAuthenticationSession` for the
/// browser leg, PKCE for the code exchange (an iOS OAuth client has no secret;
/// PKCE is what replaces it), and one `URLSession` call for the token.
///
/// **Configuration is one Info.plist key.** `GIDClientID` — the same key
/// Google's own SDK reads, so the owner configures it once whichever way this
/// is ever built. While the key is absent the button simply is not shown:
/// a sign-in button that opens an error is worse than no button.
enum GoogleAuth {

    /// The iOS OAuth client id, if the owner has configured one.
    static var clientID: String? {
        (Bundle.main.object(forInfoDictionaryKey: "GIDClientID") as? String)
            .flatMap { $0.isEmpty ? nil : $0 }
    }

    /// Whether the button should exist at all.
    static var isConfigured: Bool { clientID != nil }

    enum Failure: Error {
        case cancelled
        case misconfigured
        case noToken
    }

    /// The whole round trip: browser → code → ID token.
    ///
    /// Runs on the main actor because `ASWebAuthenticationSession` presents UI
    /// and its anchor has to be resolved from the key window.
    @MainActor
    static func idToken() async throws -> String {
        guard let clientID else { throw Failure.misconfigured }

        // Google's iOS redirect scheme is the client id reversed — that is
        // their convention, not ours, and it is what the token endpoint
        // expects to see again at the exchange.
        let scheme = clientID.split(separator: ".").reversed().joined(separator: ".")
        let redirect = "\(scheme):/oauth2redirect"

        let verifier = randomURLSafe(64)
        let challenge = Data(SHA256.hash(data: Data(verifier.utf8)))
            .base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")

        var authorize = URLComponents(string: "https://accounts.google.com/o/oauth2/v2/auth")!
        authorize.queryItems = [
            URLQueryItem(name: "client_id", value: clientID),
            URLQueryItem(name: "redirect_uri", value: redirect),
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "scope", value: "openid email profile"),
            URLQueryItem(name: "code_challenge", value: challenge),
            URLQueryItem(name: "code_challenge_method", value: "S256"),
        ]

        let callback: URL = try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(
                url: authorize.url!,
                callbackURLScheme: scheme
            ) { url, error in
                if let url {
                    continuation.resume(returning: url)
                } else if let error, (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin {
                    continuation.resume(throwing: Failure.cancelled)
                } else {
                    continuation.resume(throwing: error ?? Failure.noToken)
                }
            }
            session.presentationContextProvider = Anchor.shared
            // An ephemeral session would forget the Google account between
            // sign-ins and force the password every time; the default shares
            // Safari's cookies, which is the one-tap experience people expect.
            session.start()
        }

        guard let code = URLComponents(url: callback, resolvingAgainstBaseURL: false)?
            .queryItems?.first(where: { $0.name == "code" })?.value
        else { throw Failure.noToken }

        // The exchange. No client secret — PKCE's verifier is the proof.
        var request = URLRequest(url: URL(string: "https://oauth2.googleapis.com/token")!)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = [
            "client_id=\(clientID)",
            "code=\(code)",
            "code_verifier=\(verifier)",
            "grant_type=authorization_code",
            "redirect_uri=\(redirect)",
        ].joined(separator: "&").data(using: .utf8)

        let (data, _) = try await URLSession.shared.data(for: request)
        struct TokenReply: Decodable { let idToken: String? }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        guard let token = try decoder.decode(TokenReply.self, from: data).idToken else {
            throw Failure.noToken
        }
        return token
    }

    private static func randomURLSafe(_ length: Int) -> String {
        let alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        return String((0..<length).compactMap { _ in alphabet.randomElement() })
    }

    /// The presentation anchor: the key window, resolved when asked.
    private final class Anchor: NSObject, ASWebAuthenticationPresentationContextProviding {
        static let shared = Anchor()
        func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
            UIApplication.shared.connectedScenes
                .compactMap { ($0 as? UIWindowScene)?.keyWindow }
                .first ?? ASPresentationAnchor()
        }
    }
}
