import java.io.File

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

// ─────────────────────────────────────────────────────────────────────────────
// The version, and where the two numbers come from
//
// `versionName` is the marketing string a customer reads. It lives in
// mobile/version.properties, one directory above this Gradle build, because iOS
// reads the same file and two files drift. `providers.fileContents` rather than
// `File.readText`: this build has the configuration cache on, and a plain read
// at configuration time is invisible to it — edit the version, and a cached
// configuration would hand you yesterday's string with no warning at all.
//
// `versionCode` is the integer Play compares against the last upload, and it is
// deliberately *not* stored anywhere. `release.sh` computes it and passes it in
// as `-Palma.versionCode=…`; a Gradle property is an input the configuration
// cache tracks, so a new number invalidates the cache rather than being ignored
// by it. A build that is not given one gets 1 — fine for the debug APK on a
// desk, and refused outright for anything Play could accept, below.
// ─────────────────────────────────────────────────────────────────────────────

val versionFileText: String? = providers
    .fileContents(rootProject.layout.projectDirectory.file("../version.properties"))
    .asText
    .orNull

fun versionProperty(key: String): String? = versionFileText
    ?.lineSequence()
    ?.map { it.trim() }
    ?.firstOrNull { it.startsWith("$key=") }
    ?.substringAfter('=')
    ?.trim()
    ?.takeIf { it.isNotEmpty() }

val almaVersionName: String =
    providers.gradleProperty("alma.versionName").orNull
        ?: versionProperty("MARKETING_VERSION")
        ?: "0.0.0-unversioned"

val almaVersionCode: Int? = providers.gradleProperty("alma.versionCode").orNull?.toIntOrNull()

// ─────────────────────────────────────────────────────────────────────────────
// Where the release build thinks the backend is
//
// This used to be the literal "https://api.pazl.ai", compiled in. That host has
// never resolved — NXDOMAIN, checked repeatedly on 7 August 2026 — so the
// release build was silently producing an app that cannot create a session,
// cannot calculate a chart and cannot load a price list, and nothing anywhere
// said so. iOS refuses to archive against its placeholder; Android had no such
// guard, and the asymmetry was the whole problem: the value here *looked* real.
//
// So it is now given, per build, and a release build without one is refused
// below. The same environment variable that the iOS script reads,
// deliberately: one host, one name, two platforms.
// ─────────────────────────────────────────────────────────────────────────────

val almaApiBase: String? =
    (providers.gradleProperty("alma.apiBase").orNull
        ?: providers.environmentVariable("ALMA_API_BASE").orNull)
        ?.trim()?.takeIf { it.isNotEmpty() }

// ─────────────────────────────────────────────────────────────────────────────
// Release signing
//
// Nothing secret is in this repository and nothing secret can be put in it by
// accident: every value below is read from the environment, or from Gradle
// properties, which for a person on a laptop means ~/.gradle/gradle.properties —
// a file in the home directory that no `git add .` can reach.
//
// Environment first and properties second, because CI has environment variables
// and a person has a file, and the machine that has both is a person's laptop
// running a one-off command who means the environment to win.
//
// The signing config is *created only when all four values are present*. An
// empty one that AGP silently accepts is how a build produces an unsigned
// artefact that looks finished; `checkReleasePrerequisites` below turns the
// absence into a sentence naming what is missing, and hangs itself off the
// release tasks so it fails in a second rather than after R8 has run.
// ─────────────────────────────────────────────────────────────────────────────

fun secret(environmentVariable: String, gradleProperty: String): String? =
    (providers.environmentVariable(environmentVariable).orNull
        ?: providers.gradleProperty(gradleProperty).orNull)
        ?.trim()
        ?.takeIf { it.isNotEmpty() }

val keystorePath = secret("ALMA_UPLOAD_KEYSTORE", "almaUploadKeystore")
val keystorePassword = secret("ALMA_UPLOAD_KEYSTORE_PASSWORD", "almaUploadKeystorePassword")
val uploadKeyAlias = secret("ALMA_UPLOAD_KEY_ALIAS", "almaUploadKeyAlias")
val uploadKeyPassword = secret("ALMA_UPLOAD_KEY_PASSWORD", "almaUploadKeyPassword")

// Gradle does not expand `~`, and a keystore path is exactly the kind of value
// somebody writes with one. Left alone it becomes a literal directory named "~"
// beside the project and the error is "keystore file not found", pointing at a
// path that looks right.
val keystoreFile: File? = keystorePath?.let { raw ->
    val expanded = if (raw.startsWith("~/")) System.getProperty("user.home") + raw.substring(1) else raw
    File(expanded).absoluteFile
}

val signingIsComplete =
    keystoreFile != null && keystoreFile.isFile &&
        keystorePassword != null && uploadKeyAlias != null && uploadKeyPassword != null

val releaseProblems: List<String> = buildList {
    if (keystorePath == null) {
        add("ALMA_UPLOAD_KEYSTORE (or the Gradle property almaUploadKeystore) — the path to the upload keystore")
    } else if (keystoreFile != null && !keystoreFile.isFile) {
        add("a keystore at ${keystoreFile.path} — the path is set but there is no file there")
    }
    if (keystorePassword == null) add("ALMA_UPLOAD_KEYSTORE_PASSWORD (or almaUploadKeystorePassword)")
    if (uploadKeyAlias == null) add("ALMA_UPLOAD_KEY_ALIAS (or almaUploadKeyAlias)")
    if (uploadKeyPassword == null) add("ALMA_UPLOAD_KEY_PASSWORD (or almaUploadKeyPassword)")
    if (almaVersionCode == null) {
        add("-Palma.versionCode=<integer> — Play refuses an upload whose version code is not higher than the last one")
    }
    when {
        almaApiBase == null ->
            add("ALMA_API_BASE (or -Palma.apiBase=<origin>) — the https origin of the production backend. There is no default: api.pazl.ai does not resolve, so the old hardcoded value shipped an app that could not reach anything")
        !almaApiBase.startsWith("https://") ->
            add("an ALMA_API_BASE that starts with https:// — it is \"$almaApiBase\", and the release network config permits nothing else")
        almaApiBase.endsWith("/") ->
            add("an ALMA_API_BASE without a trailing slash — it is \"$almaApiBase\", and Retrofit joins paths onto it directly, so every request would go to //v1/…")
    }
}

val releaseRefusal: String? =
    if (releaseProblems.isEmpty()) null
    else buildString {
        appendLine("This release build was stopped before it produced anything, because what it would have produced")
        appendLine("cannot be uploaded to Google Play. Missing:")
        appendLine()
        releaseProblems.forEach { appendLine("  · $it") }
        appendLine()
        appendLine("Run mobile/android/release.sh instead of calling Gradle directly — it computes the version code,")
        appendLine("checks the keystore before it starts, and tells you what to put in ~/.gradle/gradle.properties.")
        append("mobile/RELEASE.md explains how to create the keystore in the first place.")
    }

android {
    namespace = "ai.pazl.alma"
    compileSdk = 36

    defaultConfig {
        applicationId = "ai.pazl.alma"
        minSdk = 26
        targetSdk = 36
        versionCode = almaVersionCode ?: 1
        versionName = almaVersionName

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (signingIsComplete) {
            create("release") {
                storeFile = keystoreFile
                storePassword = keystorePassword
                keyAlias = uploadKeyAlias
                keyPassword = uploadKeyPassword
                // The APK signature schemes are left at AGP's defaults on
                // purpose: it turns v1 off by itself at minSdk 26 and turning
                // knobs here only creates a way to be wrong. An .aab is jar
                // signed whatever these say — Play re-signs the APKs it
                // generates with its own key.
            }
        }
    }

    androidResources {
        // The app is translated into exactly seven languages. Without this, every
        // androidx string in ~80 more is dragged into the APK, and Play's
        // listing claims support for languages nothing in the app speaks.
        //
        // `localeFilters` and not `resourceConfigurations`: AGP 8.13 deprecated
        // the latter, and the warning it prints on every single build is the
        // kind that teaches people to ignore warnings.
        localeFilters += listOf("en", "es", "de", "it", "fr", "pt-rBR", "ru")
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
            // 10.0.2.2 is the host as seen from inside the emulator. It is a
            // build-type field rather than a constant in Kotlin because the
            // release build must never be able to reach a developer laptop,
            // and a constant with an `if (BuildConfig.DEBUG)` around it is a
            // constant somebody can delete the `if` from.
            //
            // The same `alma.apiBase` / `ALMA_API_BASE` override the release
            // block reads, with 10.0.2.2:8018 as the default rather than as the
            // only possibility. It was hardcoded, and that made one particular
            // check impossible without editing this file: pointing a debug
            // build at a *throwaway* backend on an empty database, launching a
            // wiped emulator and counting the rows in `user` — which is how the
            // iOS half of the account-minting blocker was found, and the only
            // way to show that the Android half really is clean rather than
            // clean-looking. A build file that has to be edited to run a test
            // is a test that gets skipped.
            //
            // Release keeps its refusal: the fallback here is a developer
            // laptop, which is exactly what a debug build should reach and
            // exactly what a release build must not, and the two blocks say so
            // separately rather than sharing a default.
            buildConfigField(
                "String",
                "API_BASE",
                "\"${almaApiBase ?: "http://10.0.2.2:8018"}\"",
            )
        }
        release {
            // Null when the four secrets are not all present. That is not a
            // silent fallback to debug signing — `checkReleasePrerequisites`
            // has already stopped the build by the time this would matter.
            signingConfig = signingConfigs.findByName("release")

            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            // Not a fallback anybody should ever ship: when the base is absent,
            // `checkReleasePrerequisites` has already stopped the build, and
            // this value only exists so that *configuring* the build succeeds
            // far enough to reach that refusal with a readable message.
            buildConfigField("String", "API_BASE", "\"${almaApiBase ?: "https://unset.invalid"}\"")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.androidx.navigation.compose)

    // Sign in with Google, through the platform's Credential Manager. Both
    // Apache-2.0; the button only appears when `google_web_client_id` is
    // filled in, so shipping the libraries costs nothing while it is not.
    implementation(libs.androidx.credentials)
    implementation(libs.androidx.credentials.play)
    implementation(libs.googleid)

    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization)
    implementation(libs.okhttp)
    debugImplementation(libs.okhttp.logging)

    // No androidx.security here on purpose. The bearer token is encrypted with
    // an AndroidKeyStore key directly — see data/TokenStore.kt for why
    // `EncryptedSharedPreferences` was taken back out.

    implementation(libs.billing.ktx)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
}

// The refusal. It is a task rather than a `throw` at configuration time so that
// `./gradlew tasks`, `test`, and every debug build still work on a machine with
// no keystore on it — only the four tasks that can produce something uploadable
// are blocked, and they are blocked before R8 spends forty seconds.
//
// The message is copied into a *local* first, and that detail is not cosmetic.
// A top-level `val` in a .kts file is a property of the script object, so
// reading it from inside `doLast` makes the task hold a reference to the build
// script itself, and the configuration cache refuses to serialize that:
//
//   cannot serialize Gradle script object references
//
// A local captured by value is just a String, which serializes.
val checkReleasePrerequisites = tasks.register("checkReleasePrerequisites") {
    group = "verification"
    description = "Refuses a release build that would come out unsigned or unnumbered."
    val refusal = releaseRefusal
    doLast {
        if (refusal != null) throw GradleException(refusal)
    }
}

tasks.matching {
    it.name in setOf("assembleRelease", "bundleRelease", "packageRelease", "packageReleaseBundle")
}.configureEach {
    dependsOn(checkReleasePrerequisites)
}
