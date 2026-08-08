#!/usr/bin/env bash
#
# Build the Android release bundle that goes to Google Play.
#
# Read this before running it. It is short on purpose: every check below exists
# because the thing it checks for produces a failure that reads as a broken
# project rather than a missing setting, and each one prints what is wrong in a
# sentence rather than a stack trace.
#
#   ./release.sh              build the .aab
#   ./release.sh --check      run every precondition and stop, building nothing
#
# What comes out:
#
#   mobile/android/build/release/alma-<version>-<build>.aab       upload this
#   mobile/android/build/release/alma-<version>-<build>-mapping.txt   and this
#
# The second file is not optional. R8 is on for release builds, so every crash
# Play shows you is obfuscated until the matching mapping is uploaded beside the
# bundle, and Play keeps no copy of one you did not give it.
#
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mobile="$(cd "$here/.." && pwd)"

check_only=0
if [[ "${1:-}" == "--check" ]]; then check_only=1; fi

bold=$'\033[1m'; plain=$'\033[0m'; red=$'\033[31m'

die() { printf '%s\n' "${red}${bold}release.sh stopped.${plain} $*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }

# ── 1. The JDK ───────────────────────────────────────────────────────────────
#
# Both of the JDKs a person is most likely to already have are wrong, and both
# fail with a message about something else. mobile/TOOLCHAIN.md has the long
# version; this is the check.

if [[ -z "${JAVA_HOME:-}" ]]; then
  die "JAVA_HOME is not set. Android Gradle Plugin 8.13 needs a JDK between 17 and 21.
  The java on the default PATH of this machine is 1.8 and fails with a class-file-version stack
  trace; the JDK inside Android Studio is 25 and fails with the bare string \"25.0.2\". Use:

      export JAVA_HOME=/opt/homebrew/opt/openjdk@21"
fi

java_major="$("$JAVA_HOME/bin/java" -version 2>&1 | head -1 | sed -E 's/.*"([0-9]+)([.].*)?".*/\1/')"
if [[ ! "$java_major" =~ ^[0-9]+$ ]] || (( java_major < 17 || java_major > 21 )); then
  die "JAVA_HOME points at Java $java_major ($JAVA_HOME).
  AGP 8.13 with Gradle 8.14.3 accepts 17 through 21 and nothing else here.
  openjdk@17 and openjdk@21 are both installed under /opt/homebrew/opt."
fi

# ── 2. The Android SDK ───────────────────────────────────────────────────────
#
# Gradle is happy with either of the two SDK roots on this machine — only the
# emulator cares which — so this checks that one of them exists and has a
# platform in it, not which one it is.

if [[ -z "${ANDROID_HOME:-}" && -z "${ANDROID_SDK_ROOT:-}" ]]; then
  die "Neither ANDROID_HOME nor ANDROID_SDK_ROOT is set. Use:

      export ANDROID_HOME=\"\$HOME/Library/Android/sdk\""
fi
sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
[[ -d "$sdk/platforms" ]] || die "\$ANDROID_HOME is $sdk but there is no platforms/ directory inside it.
  That is not an SDK installation, or it is one with nothing installed in it."

# ── 3. The version ───────────────────────────────────────────────────────────
#
# The marketing string is edited by a person in mobile/version.properties. The
# build number is not edited by anybody: it is the number of whole minutes since
# 2026-01-01T00:00:00Z, so it rises on its own and two builds a minute apart can
# never collide. mobile/RELEASE.md, "The two numbers", says why this rather than
# a counter in a file.

version_file="$mobile/version.properties"
[[ -f "$version_file" ]] || die "$version_file is missing. It holds MARKETING_VERSION, the only
  version string in this project a human writes."

version_name="$(sed -n 's/^MARKETING_VERSION=//p' "$version_file" | tr -d '[:space:]')"
[[ -n "$version_name" ]] || die "$version_file has no MARKETING_VERSION= line."

epoch_2026=1767225600
version_code=$(( ( $(date -u +%s) - epoch_2026 ) / 60 ))
(( version_code > 0 )) || die "The computed version code is $version_code, which means this machine's
  clock is set before 2026. Fix the clock; Play will not take a version code of zero or less."

# ── 4. The backend ───────────────────────────────────────────────────────────
#
# The one blank in this script that is not a secret. It used to be a literal in
# app/build.gradle.kts and the literal was a host that has never resolved, so a
# release build produced an app that opened to an error on every screen and said
# nothing about it while building. It is now required, by name, here.

[[ -n "${ALMA_API_BASE:-}" ]] || die "ALMA_API_BASE is not set.

  This is the production backend origin compiled into the release build. There is no default
  and there cannot be one: nothing in this repository knows where the API is deployed, and
  api.pazl.ai — the value that used to be hardcoded here — returns NXDOMAIN. The iOS script
  reads the same variable, so one export covers both platforms.

      export ALMA_API_BASE=https://api.example.com"

case "$ALMA_API_BASE" in
  https://*) ;;
  *) die "ALMA_API_BASE is \"$ALMA_API_BASE\". It must start with https://. The release build
  has no cleartext permission — only the debug build reaches 10.0.2.2 over plain HTTP." ;;
esac
case "$ALMA_API_BASE" in
  */) die "ALMA_API_BASE ends in a slash. Retrofit joins paths onto it directly, so a trailing
  slash produces //v1/... and a 404 from every request." ;;
esac

api_host="${ALMA_API_BASE#https://}"; api_host="${api_host%%/*}"
if ! host "$api_host" >/dev/null 2>&1 && ! dig +short "$api_host" | grep -q . ; then
  say "${red}warning${plain}: $api_host does not resolve from this machine. If that is still true"
  say "         when the app is reviewed, every screen in it fails. Continuing anyway."
fi

# ── 5. The signing key ───────────────────────────────────────────────────────
#
# Read from the environment first, then from ~/.gradle/gradle.properties, which
# is the same order the Gradle build uses. Nothing is read from the repository
# and nothing is written to it.
#
# Reading the properties file here as well as in Gradle looks like duplication,
# and it buys one specific thing: a wrong password is caught by keytool in under
# a second, instead of by the packaging task after R8 has run.

gradle_props="${GRADLE_USER_HOME:-$HOME/.gradle}/gradle.properties"
from_props() {
  [[ -f "$gradle_props" ]] || return 0
  sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$gradle_props" | tail -1
}

keystore="${ALMA_UPLOAD_KEYSTORE:-$(from_props almaUploadKeystore)}"
store_pass="${ALMA_UPLOAD_KEYSTORE_PASSWORD:-$(from_props almaUploadKeystorePassword)}"
key_alias="${ALMA_UPLOAD_KEY_ALIAS:-$(from_props almaUploadKeyAlias)}"
key_pass="${ALMA_UPLOAD_KEY_PASSWORD:-$(from_props almaUploadKeyPassword)}"
keystore="${keystore/#\~/$HOME}"

missing=()
[[ -n "$keystore"   ]] || missing+=("ALMA_UPLOAD_KEYSTORE / almaUploadKeystore")
[[ -n "$store_pass" ]] || missing+=("ALMA_UPLOAD_KEYSTORE_PASSWORD / almaUploadKeystorePassword")
[[ -n "$key_alias"  ]] || missing+=("ALMA_UPLOAD_KEY_ALIAS / almaUploadKeyAlias")
[[ -n "$key_pass"   ]] || missing+=("ALMA_UPLOAD_KEY_PASSWORD / almaUploadKeyPassword")

if (( ${#missing[@]} > 0 )); then
  die "The upload key is not configured. Missing (environment variable / Gradle property):

$(printf '      · %s\n' "${missing[@]}")
  Put the four Gradle properties in $gradle_props — a file outside this repository, which is
  the point: no secret can be committed by accident. mobile/RELEASE.md, \"Creating the upload
  key\", is a five-line keytool command and an explanation of what happens if you lose it."
fi

[[ -f "$keystore" ]] || die "There is no keystore at $keystore.
  The path is configured, so this is either a typo or a key that lives on another machine."

if ! "$JAVA_HOME/bin/keytool" -list -keystore "$keystore" -alias "$key_alias" \
      -storepass "$store_pass" >/dev/null 2>&1; then
  die "The keystore at $keystore will not open with the configured password, or it has no key
  under the alias \"$key_alias\". Nothing was built. keytool -list -v -keystore \"$keystore\"
  will show you which aliases are actually in there."
fi

fingerprint="$("$JAVA_HOME/bin/keytool" -list -keystore "$keystore" -alias "$key_alias" \
  -storepass "$store_pass" -v 2>/dev/null | sed -n 's/.*SHA256: //p' | head -1)"

# ── 6. Say what is about to happen ───────────────────────────────────────────

# Read out of the source rather than written here, so the two cannot disagree.
# This is on the summary because it is the last irreversible decision before an
# upload: mobile/store/PRODUCTS.md recommends "ai.pazl.alma." and the binary
# asks for "alma.", and a product id typed into the console that the binary
# never asks for produces an empty paywall and a Guideline 2.1 rejection.
# Neither store lets an id be edited or reused afterwards.
store_prefix="$(sed -n 's/.*const val PREFIX: String = "\(.*\)".*/\1/p' \
  "$here/app/src/main/kotlin/ai/pazl/alma/billing/StoreProducts.kt" | head -1)"

out_dir="$here/build/release"
artefact="$out_dir/alma-$version_name-$version_code.aab"

cat <<EOF

${bold}Android release${plain}
  application id   ai.pazl.alma
  version name     $version_name        (mobile/version.properties)
  version code     $version_code           (minutes since 2026-01-01T00:00:00Z)
  API base         $ALMA_API_BASE
  keystore         $keystore
  key alias        $key_alias
  key SHA-256      $fingerprint
  JDK              $java_major at $JAVA_HOME
  product prefix   $store_prefix   ← every in-app product id in the Play console must start with this
  bundle           $artefact

EOF

if (( check_only )); then
  say "--check: everything above is in place. Nothing was built."
  exit 0
fi

say "Confirm the key SHA-256 above is the one Google Play shows under"
say "Release → Setup → App integrity → Upload key certificate. A bundle signed with any other"
say "key is rejected at upload with \"Your Android App Bundle is signed with the wrong key\"."
say ""

# ── 7. Build ─────────────────────────────────────────────────────────────────
#
# The unit tests run first because a release bundle that fails them is a release
# nobody wants to have uploaded. ALMA_SKIP_TESTS=1 exists for the second attempt
# at a build that already passed them a minute ago.

cd "$here"

if [[ "${ALMA_SKIP_TESTS:-0}" != "1" ]]; then
  say "${bold}› unit tests${plain}"
  ./gradlew --console=plain :app:testReleaseUnitTest
fi

say ""
say "${bold}› bundleRelease${plain}"
./gradlew --console=plain :app:bundleRelease \
  "-Palma.versionCode=$version_code" \
  "-Palma.versionName=$version_name" \
  "-Palma.apiBase=$ALMA_API_BASE"

built="$here/app/build/outputs/bundle/release/app-release.aab"
[[ -f "$built" ]] || die "Gradle reported success but $built does not exist. Something in the
  build configuration changed where the bundle lands; nothing was copied."

# ── 8. Prove it is signed ────────────────────────────────────────────────────
#
# AGP without a signing config produces an unsigned bundle and calls the build
# successful, which is exactly the failure this whole file exists to prevent, so
# the artefact is checked rather than trusted. `jarsigner -verify` on an
# unsigned bundle prints "jar is unsigned".

verify="$("$JAVA_HOME/bin/jarsigner" -verify "$built" 2>&1 || true)"
if ! grep -q "jar verified" <<<"$verify"; then
  die "The bundle at $built is not signed. jarsigner said:

      $verify

  Do not upload it. This should be unreachable — the signing config was present a moment ago."
fi

mkdir -p "$out_dir"
cp "$built" "$artefact"

mapping="$here/app/build/outputs/mapping/release/mapping.txt"
mapping_out="$out_dir/alma-$version_name-$version_code-mapping.txt"
if [[ -f "$mapping" ]]; then
  cp "$mapping" "$mapping_out"
else
  say "warning: no R8 mapping at $mapping. Every crash report from this build will be"
  say "         unreadable. Check that isMinifyEnabled is still true for the release type."
fi

printf '%s  android  %s  %s  %s\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$version_name" "$version_code" "$fingerprint" \
  >> "$mobile/RELEASES.log"

cat <<EOF

${bold}Done.${plain}
  bundle    $artefact
            $(du -h "$artefact" | cut -f1), signed, verified
  mapping   $mapping_out

Upload both at Play Console → Release → Production (or Internal testing) → Create new release.
The bundle goes in the App bundles box; the mapping goes under "ReTrace mapping file" on the
same screen. Recorded in mobile/RELEASES.log.
EOF
