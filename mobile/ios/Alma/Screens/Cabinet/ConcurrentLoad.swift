import Foundation

/// Start several requests at once and land each of them in a `ScreenState`.
///
/// **Why this exists rather than `async let`.** Every screen in the cabinet
/// makes two to four independent requests, none of them fast, and running them
/// in sequence is that many round trips of latency before anything appears. The
/// obvious spelling —
///
/// ```swift
/// async let sky = ScreenState.load { try await client.compute(.transits) }
/// ```
///
/// — does not compile: without a contextual type on the left, the closure's
/// `throws(AlmaError)` is inferred back to an untyped `throws`, and the typed
/// throw no longer converts. That is the same erasure `AlmaSessionModel.start()`
/// documents from the other direction, and the fix there was to give up the
/// concurrency for one call. A screen with four calls cannot.
///
/// A `Task` keeps both: it starts immediately, so the requests genuinely
/// overlap, and its closure body is an ordinary context where
/// `ScreenState.load` keeps its typed throw. The caller writes
///
/// ```swift
/// let sky = almaLoad { try await client.compute(.transits, locale: locale) }
/// let natal = almaLoad { try await client.compute(.natal, locale: locale) }
/// self.sky = await sky.value
/// self.natal = await natal.value
/// ```
///
/// which reads in the order it happens: both leave, then both land.
///
/// The closure is `@Sendable` because a `Task` outlives the statement that made
/// it. In practice every caller captures the client (which is `Sendable`) and a
/// locale, and nothing else — capturing `self` from a `@MainActor` model would
/// be refused here rather than becoming a data race later.
///
/// **Why the closure is not `throws(AlmaError)` like `ScreenState.load`'s.**
/// A closure literal written inside another closure — which is what the body of
/// a `Task` is — has its thrown type settled as `any Error` before the outer
/// parameter's typed throw is applied, and the conversion is then refused. It
/// happens with the type spelled out, with the generic named, and with the
/// closure signature written in full; the only spellings that survive it are
/// worse to read than this one. So the work is taken as an ordinary throwing
/// closure and the one error that can actually arrive is re-typed below.
///
/// Nothing is lost where it matters: every `AlmaClient` method throws
/// `AlmaError` and nothing else, and the exhaustiveness the typed throw buys is
/// at the *rendering* end — a screen still switches over a
/// `ScreenState.failed(AlmaError)` and the compiler still names the paywall
/// case somebody forgot. The `catch` for the impossible case is honest rather
/// than defensive: if a non-`AlmaError` ever did arrive it would be a
/// programming mistake, and burying it would be worse than reporting it as the
/// malformed response it effectively is.
func almaLoad<Value: Sendable>(
    _ work: @escaping @Sendable () async throws -> Value
) -> Task<ScreenState<Value>, Never> {
    Task {
        do {
            return .loaded(try await work())
        } catch let error as AlmaError {
            return .failed(error)
        } catch {
            return .failed(.malformedResponse(detail: String(describing: error)))
        }
    }
}
