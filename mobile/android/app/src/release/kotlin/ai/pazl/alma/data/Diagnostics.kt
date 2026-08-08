package ai.pazl.alma.data

import okhttp3.Interceptor

/**
 * The release build's copy: nothing.
 *
 * This is the point of splitting the function across source sets rather than
 * guarding it with `if (BuildConfig.DEBUG)`. A runtime guard still compiles the
 * logging code into the store binary and still links `okhttp-logging` — which
 * would then have to be an `implementation` dependency, shipped to every user
 * so that a branch could decline to call it. Here the release APK contains
 * neither.
 */
internal fun diagnosticInterceptors(): List<Interceptor> = emptyList()
