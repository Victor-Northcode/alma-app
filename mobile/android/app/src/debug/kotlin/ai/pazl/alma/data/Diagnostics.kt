package ai.pazl.alma.data

import okhttp3.Interceptor
import okhttp3.logging.HttpLoggingInterceptor

/**
 * The debug build's copy. See the release build's for the other half of the pair.
 *
 * `HEADERS`, never `BODY`. A body log prints the bearer token on the way out
 * and the whole of somebody's chart on the way back, into a logcat that a
 * screen recording captures and that anyone with `adb` can read off the device.
 * The two headers that carry the credential are redacted on top of that, so
 * even the header level never puts the token on a line.
 */
internal fun diagnosticInterceptors(): List<Interceptor> = listOf(
    HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.HEADERS
        redactHeader("Authorization")
        redactHeader(AlmaHttp.TOKEN_HEADER)
    }
)
