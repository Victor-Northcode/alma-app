#!/usr/bin/env bash
#
# Archive the iOS app and export the .ipa that goes to App Store Connect.
#
#   ./release.sh              archive, then export
#   ./release.sh --check      run every precondition and stop, building nothing
#
# ── The two blanks ───────────────────────────────────────────────────────────
#
# Everything in this repository is filled in except two values, and neither can
# be guessed by anybody who is not the owner of the Apple account:
#
#   ALMA_TEAM_ID    The ten-character Apple Developer Team ID for Pazl LLC.
#                   developer.apple.com/account → Membership details. Looks
#                   like A1B2C3D4E5.
#
#   ALMA_API_BASE   The https origin of the production backend. The Release
#                   configuration currently carries the deliberate placeholder
#                   "https://api.pazl.ai.INVALID-SET-THIS-BEFORE-TESTFLIGHT",
#                   and a build phase inside the project refuses to archive
#                   while it is still there. Read that as a real open question,
#                   not a formality: as of 7 August 2026 api.pazl.ai does not
#                   resolve — NXDOMAIN — so this value is not simply "the
#                   obvious one with the placeholder removed". Whoever deploys
#                   the backend decides what it is, and then it goes here and
#                   into the twelve store listings, which point at
#                   alma.pazl.ai, which does not resolve either.
#
#   export ALMA_TEAM_ID=A1B2C3D4E5
#   export ALMA_API_BASE=https://api.example.com
#   ./release.sh
#
# What comes out:
#
#   mobile/ios/build/release/Alma-<version>-<build>.ipa      upload this
#   mobile/ios/build/release/Alma-<version>-<build>.xcarchive   keep this
#
# Keep the archive. It holds the dSYMs, and the day a crash report arrives from
# a build you no longer have the archive for is the day the report is useless.
#
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mobile="$(cd "$here/.." && pwd)"

check_only=0
if [[ "${1:-}" == "--check" ]]; then check_only=1; fi

bold=$'\033[1m'; plain=$'\033[0m'; red=$'\033[31m'
die() { printf '%s\n' "${red}${bold}release.sh stopped.${plain} $*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }

# ── 1. Xcode ─────────────────────────────────────────────────────────────────

command -v xcodebuild >/dev/null || die "xcodebuild is not on the PATH. This needs a full Xcode,
  not the Command Line Tools: archiving and exporting are not in the CLT package. If Xcode is
  installed, point at it once with

      sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"

xcode_version="$(xcodebuild -version | head -1)"

# ── 2. The two blanks ────────────────────────────────────────────────────────

[[ -n "${ALMA_TEAM_ID:-}" ]] || die "ALMA_TEAM_ID is not set.

  Automatic signing needs to know which Apple Developer account to ask for a distribution
  certificate and a provisioning profile. Without it xcodebuild fails at the signing step with
  'Signing for \"Alma\" requires a development team', which reads like a missing certificate.

      export ALMA_TEAM_ID=A1B2C3D4E5      # developer.apple.com/account → Membership details"

if [[ ! "$ALMA_TEAM_ID" =~ ^[A-Z0-9]{10}$ ]]; then
  die "ALMA_TEAM_ID is \"$ALMA_TEAM_ID\", which is not a Team ID. They are exactly ten characters,
  uppercase letters and digits. You may be looking at the Issuer ID from the App Store Connect
  API page, which is a UUID and is a different thing."
fi

[[ -n "${ALMA_API_BASE:-}" ]] || die "ALMA_API_BASE is not set.

  This is the production backend origin compiled into the binary. There is no default and there
  cannot be one: nothing in this repository knows where the API is deployed, and api.pazl.ai
  does not resolve today. A build pointed at a host that does not answer cannot create a
  session, cannot calculate a chart and cannot load the price list — the app opens to an error
  on a device the reviewer is holding.

      export ALMA_API_BASE=https://api.example.com"

case "$ALMA_API_BASE" in
  https://*) ;;
  *) die "ALMA_API_BASE is \"$ALMA_API_BASE\". It must start with https://. App Transport
  Security refuses plain HTTP everywhere except localhost, and the exception in Info.plist is
  scoped to localhost alone." ;;
esac
case "$ALMA_API_BASE" in
  *INVALID-SET-THIS-BEFORE-TESTFLIGHT*)
    die "ALMA_API_BASE is still the placeholder. See the note at the top of this file." ;;
esac
case "$ALMA_API_BASE" in
  */) die "ALMA_API_BASE ends in a slash. AlmaClient joins paths onto it directly, so a trailing
  slash produces //v1/... and a 404 from every request." ;;
esac

# A courtesy, not a gate: a host that does not resolve on this machine may still
# resolve on a phone, and a DNS failure is not a reason to refuse to build.
api_host="${ALMA_API_BASE#https://}"; api_host="${api_host%%/*}"
if ! host "$api_host" >/dev/null 2>&1 && ! dig +short "$api_host" | grep -q . ; then
  say "${red}warning${plain}: $api_host does not resolve from this machine. If that is still true"
  say "         when the app is reviewed, every screen in it fails. Continuing anyway."
fi

# ── 3. The version ───────────────────────────────────────────────────────────
#
# Same two numbers as Android, computed the same way, so a release of both apps
# on the same afternoon carries build numbers a minute or two apart and a crash
# report from one can be lined up against the other. mobile/RELEASE.md explains
# the scheme.

version_file="$mobile/version.properties"
[[ -f "$version_file" ]] || die "$version_file is missing. It holds MARKETING_VERSION."
version_name="$(sed -n 's/^MARKETING_VERSION=//p' "$version_file" | tr -d '[:space:]')"
[[ -n "$version_name" ]] || die "$version_file has no MARKETING_VERSION= line."

epoch_2026=1767225600
build_number=$(( ( $(date -u +%s) - epoch_2026 ) / 60 ))
(( build_number > 0 )) || die "The computed build number is $build_number, so this machine's clock
  is set before 2026. App Store Connect will not take it."

# ── 4. Say what is about to happen ───────────────────────────────────────────

# Read out of the source rather than written here, so the two cannot disagree.
# The last irreversible decision before an upload: mobile/store/PRODUCTS.md
# recommends "ai.pazl.alma." and the binary asks for "alma.". A product id
# created in App Store Connect that the binary never asks for is an empty
# paywall and a Guideline 2.1 rejection, and Apple does not allow an id to be
# edited or reused — not even after deleting it.
store_prefix="$(sed -n 's/.*static let prefix = "\(.*\)".*/\1/p' \
  "$here/Alma/Billing/LadderKey.swift" | head -1)"

out_dir="$here/build/release"
archive="$out_dir/Alma-$version_name-$build_number.xcarchive"
ipa_dir="$out_dir/export-$version_name-$build_number"
export_options="$out_dir/ExportOptions-$version_name-$build_number.plist"

cat <<EOF

${bold}iOS release${plain}
  bundle id        ai.pazl.alma
  version          $version_name        (mobile/version.properties → CFBundleShortVersionString)
  build            $build_number           (minutes since 2026-01-01T00:00:00Z → CFBundleVersion)
  team             $ALMA_TEAM_ID
  API base         $ALMA_API_BASE
  entitlements     Alma.entitlements — Sign In with Apple
  toolchain        $xcode_version
  product prefix   $store_prefix   ← every in-app purchase id in App Store Connect must start with this
  archive          $archive

EOF

if (( check_only )); then
  say "--check: everything above is in place. Nothing was built."
  exit 0
fi

say "The App ID ai.pazl.alma must have Sign In with Apple enabled in the developer portal before"
say "this can sign. If it does not, the failure is \"Provisioning profile doesn't include the"
say "com.apple.developer.applesignin entitlement\" — enable it under Certificates, Identifiers &"
say "Profiles → Identifiers → ai.pazl.alma, and run this again."
say ""

mkdir -p "$out_dir"
rm -rf "$archive" "$ipa_dir"

# ── 5. Archive ───────────────────────────────────────────────────────────────
#
# -allowProvisioningUpdates lets Xcode create the distribution certificate and
# the App Store profile if the account has none. It needs an Apple ID signed in
# under Xcode → Settings → Accounts, or an App Store Connect API key in
# ~/.appstoreconnect/private_keys. Without either, it fails with a message about
# no accounts, which at least names the problem.
#
# The version numbers are passed as build settings rather than written into the
# .pbxproj, so that nothing in the repository has to be edited to make a release
# and two releases cannot collide in a file.

say "${bold}› archive${plain}"
xcodebuild archive \
  -project "$here/Alma.xcodeproj" \
  -scheme Alma \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$archive" \
  -allowProvisioningUpdates \
  DEVELOPMENT_TEAM="$ALMA_TEAM_ID" \
  ALMA_API_BASE="$ALMA_API_BASE" \
  MARKETING_VERSION="$version_name" \
  CURRENT_PROJECT_VERSION="$build_number" \
  | grep -Ev '^\s*(export|cd |builtin-|/Applications/Xcode)' || {
      die "The archive failed. The full log is above; the line that matters usually contains
  \"error:\" and is near the top of the failure, not the bottom."
  }

[[ -d "$archive" ]] || die "xcodebuild reported success but there is no archive at $archive."

# Read the numbers back out of the archive rather than trusting that they were
# applied. A build setting that does not reach Info.plist is silent.
plist="$archive/Products/Applications/Alma.app/Info.plist"
got_version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$plist")"
got_build="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$plist")"
[[ "$got_version" == "$version_name" && "$got_build" == "$build_number" ]] || die \
  "The archived app says version $got_version build $got_build, but this script asked for
  $version_name build $build_number. Do not upload it — the number App Store Connect compares
  against the last upload is the one inside the binary, not the one on the command line."

# ── 6. Export ────────────────────────────────────────────────────────────────

cp "$here/ExportOptions.plist" "$export_options"
/usr/libexec/PlistBuddy -c "Set :teamID $ALMA_TEAM_ID" "$export_options"

say ""
say "${bold}› export${plain}"
xcodebuild -exportArchive \
  -archivePath "$archive" \
  -exportOptionsPlist "$export_options" \
  -exportPath "$ipa_dir" \
  -allowProvisioningUpdates \
  | grep -Ev '^\s*(export|cd |builtin-)' || die "The export failed."

ipa="$(find "$ipa_dir" -name '*.ipa' -maxdepth 1 | head -1)"
[[ -n "$ipa" ]] || die "The export reported success but produced no .ipa in $ipa_dir."

final="$out_dir/Alma-$version_name-$build_number.ipa"
mv "$ipa" "$final"

printf '%s  ios      %s  %s  %s\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$version_name" "$build_number" "$ALMA_API_BASE" \
  >> "$mobile/RELEASES.log"

cat <<EOF

${bold}Done.${plain}
  ipa       $final
            $(du -h "$final" | cut -f1)
  archive   $archive
  dSYMs     $archive/dSYMs

Upload it with an App Store Connect API key — .p8 in ~/.appstoreconnect/private_keys, key id and
issuer id from App Store Connect → Users and Access → Integrations:

  xcrun altool --upload-app -f "$final" -t ios \\
    --apiKey <KEY_ID> --apiIssuer <ISSUER_ID>

or open Xcode → Window → Organizer, select this archive, and press Distribute App. Recorded in
mobile/RELEASES.log.
EOF
