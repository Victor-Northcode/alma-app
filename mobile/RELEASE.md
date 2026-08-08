# Releasing Alma to the App Store and Google Play

Written 7 August 2026 by whoever ran every command in it. Nothing below is quoted from
documentation without having been executed on this machine first; where something could not be
run — because it needs an Apple team, a Play account, or a backend that exists — the sentence
says so rather than pretending.

Read `TOOLCHAIN.md` in this directory before the first build. It names two different
`ANDROID_HOME` values and the JDK trap where both obvious choices are wrong, and the release
scripts check for that trap but cannot fix it for you.

---

## What you run

```bash
export ALMA_API_BASE=https://<the production backend>     # both platforms

# Android
export ALMA_UPLOAD_KEYSTORE=~/keys/alma-upload.jks        # see "Creating the upload key"
export ALMA_UPLOAD_KEYSTORE_PASSWORD=…
export ALMA_UPLOAD_KEY_ALIAS=upload
export ALMA_UPLOAD_KEY_PASSWORD=…
export JAVA_HOME=/opt/homebrew/opt/openjdk@21
export ANDROID_HOME="$HOME/Library/Android/sdk"
mobile/android/release.sh --check        # verifies everything, builds nothing
mobile/android/release.sh                # → build/release/alma-<v>-<n>.aab

# iOS
export ALMA_TEAM_ID=A1B2C3D4E5                            # see "The two blanks"
mobile/ios/release.sh --check
mobile/ios/release.sh                    # → build/release/Alma-<v>-<n>.ipa
```

Both scripts refuse before they build anything. `--check` runs every precondition and stops, so
the answer to "have I got everything?" costs a second rather than a forty-second build.

---

## The two numbers

Both stores reject a build whose number is not higher than the last one they accepted, and both
of them mean a different number by "version". There are two, and only one of them is written by
a person.

**The marketing version** — `1.0.0` — is the string a customer reads on the store page. It lives
in `mobile/version.properties`, one file for both platforms, and it is edited deliberately when
somebody decides that this release is a 1.1 rather than a 1.0.1. Android's Gradle build reads
that file directly; Xcode has no equivalent hook, so `mobile/ios/release.sh` passes it to
`xcodebuild` as `MARKETING_VERSION`. The `1.0` sitting in `Alma.xcodeproj` is what an unscripted
build in the Xcode UI produces and is not what ships.

**The build number** — `versionCode` on Play, `CFBundleVersion` on Apple — is not written
anywhere at all. Both scripts compute it as

```
(now − 2026-01-01T00:00:00Z) in whole minutes
```

which was `314530` at midday on 7 August 2026. It rises on its own, two builds a minute apart
cannot collide, a release of both apps on the same afternoon carries numbers within a minute of
each other so a crash report from one lines up against the other, and nobody has to remember
anything. The ceiling is Play's 2,100,000,000, which this reaches in the year 5900.

The obvious alternative — a counter in a file, incremented by the script — was rejected for two
reasons. The smaller one is that a forgotten increment is exactly the failure this is meant to
remove, and a counter reintroduces it whenever somebody builds from a stale checkout. The larger
one is that **this project is not under version control**: `git rev-parse` in the repository root
answers *not a git repository*, so there is no commit count to derive from and no mechanism that
would stop two machines producing the same number for different builds. A clock is the only
shared monotonic thing left.

The consequence to know about: rebuilding the same source twice gives two different build
numbers. That is fine for both stores — they only demand *higher* — but it means an artefact is
not reproducible byte for byte from its number alone. `mobile/RELEASES.log` is appended to by
both scripts on every successful build, so the number can at least be traced back to a time, a
version, and (on Android) the signing certificate it went out under.

---

## Android

### Why the release build could not be published before today

There was no `signingConfigs` block anywhere in the project. `./gradlew :app:bundleRelease`
succeeded, took forty seconds, printed `BUILD SUCCESSFUL`, and produced an artefact that
`jarsigner -verify` describes as

```
jar is unsigned.
```

Play rejects that at upload. Nothing in the build said so, which is the part worth fixing rather
than the missing block itself.

### Creating the upload key

```bash
keytool -genkeypair -v \
  -keystore ~/keys/alma-upload.jks \
  -alias upload \
  -keyalg RSA -keysize 4096 -validity 10000 \
  -dname "CN=Pazl LLC, O=Pazl LLC, C=US"
```

It asks for the keystore password twice and then for a key password; give the key the same
password unless you have a reason not to, because Gradle needs both and two different secrets in
two variables is two chances to mix them up.

`-validity 10000` is about 27 years. Play requires a certificate valid until at least 22 October
2033 and refuses anything shorter, and the failure arrives at upload time when the release is
otherwise finished. RSA 4096 rather than 2048 because this key is generated once and then lives
for the life of the product; the extra milliseconds per build are not a consideration.

Then, once and only once:

```bash
mkdir -p ~/keys && chmod 700 ~/keys && chmod 600 ~/keys/alma-upload.jks
```

and put the four values in `~/.gradle/gradle.properties`:

```properties
almaUploadKeystore=/Users/you/keys/alma-upload.jks
almaUploadKeystorePassword=…
almaUploadKeyAlias=upload
almaUploadKeyPassword=…
```

**`~/.gradle/gradle.properties` and not a file in the repository.** That is the whole design:
the build reads the environment first and Gradle properties second, and it reads nothing from
this project, so there is no path by which `git add .` commits a secret. If you would rather use
the environment — CI has no home directory worth speaking of — the four variables are
`ALMA_UPLOAD_KEYSTORE`, `ALMA_UPLOAD_KEYSTORE_PASSWORD`, `ALMA_UPLOAD_KEY_ALIAS`,
`ALMA_UPLOAD_KEY_PASSWORD`, and they win over the properties.

A build with none of them does not quietly produce an unsigned bundle. It stops, in about a
second, before R8 runs, with this:

```
* What went wrong:
Execution failed for task ':app:checkReleasePrerequisites'.
> This release build was stopped before it produced anything, because what it would have produced
  cannot be uploaded to Google Play. Missing:

    · ALMA_UPLOAD_KEYSTORE (or the Gradle property almaUploadKeystore) — the path to the upload keystore
    · ALMA_UPLOAD_KEYSTORE_PASSWORD (or almaUploadKeystorePassword)
    · ALMA_UPLOAD_KEY_ALIAS (or almaUploadKeyAlias)
    · ALMA_UPLOAD_KEY_PASSWORD (or almaUploadKeyPassword)
    · -Palma.versionCode=<integer> — Play refuses an upload whose version code is not higher than the last one
    · ALMA_API_BASE (or -Palma.apiBase=<origin>) — the https origin of the production backend…
```

That refusal is a task hung off `bundleRelease`, `assembleRelease` and the two packaging tasks,
and off nothing else — `test`, every debug build, and `./gradlew tasks` still work on a machine
that has never seen the keystore.

### If the key is lost

This is the part that is usually stated as an absolute, and the absolute is only true of the
older arrangement. Both halves matter:

* **The key you create above is an *upload* key.** Play App Signing is mandatory for apps
  published as bundles, which this one is, so Google generates and holds the actual *app signing
  key* and re-signs every APK it delivers. If you lose the upload key you generate a new one and
  ask Play support to register its certificate; you keep the app, the users, and the update
  path. It is days of waiting and an identity check, not the end.
* **The app signing key Google holds cannot be lost by you**, and cannot be exported. That is
  the trade: you give up custody and get a key that survives a stolen laptop.
* **The absolute is true of an app signed outside Play App Signing** — the legacy arrangement,
  and any APK you distribute yourself, from your own site or a third-party store. There, the
  signing key *is* the identity of the app: lose it and no upgrade can ever be installed over
  the existing one, because Android refuses an update signed by a different key. The only
  recovery is a new package name, which is a new listing, with none of the reviews or installs.

Back the keystore up anyway, in two places that do not fail together, and record the passwords
in the same password manager as the Play account. The recovery path above exists, but it costs
days at the worst possible moment.

Confirm you have the right key before an upload: the script prints the SHA-256 of the
certificate it signed with, and Play shows the certificate it expects under **Release → Setup →
App integrity → Upload key certificate**. If they differ, the upload is rejected with *"Your
Android App Bundle is signed with the wrong key"*, which does not tell you which key it wanted.

### What was actually built

With a **throwaway keystore** — generated in a scratch directory for this proof, never used for
anything, and deleted afterwards; it is not the key you will publish with, and no key in this
repository is:

```
$ ALMA_API_BASE=https://api.example.com mobile/android/release.sh

Android release
  application id   ai.pazl.alma
  version name     1.0.0        (mobile/version.properties)
  version code     314530           (minutes since 2026-01-01T00:00:00Z)
  API base         https://api.example.com
  key alias        throwaway
  key SHA-256      03:D7:4D:98:83:50:69:72:C9:6E:90:73:95:7C:56:0D:80:04:FD:DE:86:0F:A9:0D:9D:6B:9A:04:BF:35:F2:20
  JDK              21 at /opt/homebrew/opt/openjdk@21
  product prefix   alma.

BUILD SUCCESSFUL in 47s

Done.
  bundle    …/mobile/android/build/release/alma-1.0.0-314530.aab
            4.3M, signed, verified
  mapping   …/mobile/android/build/release/alma-1.0.0-314530-mapping.txt
```

and, checked independently of the script:

```
$ jarsigner -verify alma-1.0.0-314530.aab
jar verified.
$ aapt2 dump badging app-release.apk | head -1
package: name='ai.pazl.alma' versionCode='314521' versionName='1.0.0' …
$ apksigner verify -v app-release.apk
Verified using v2 scheme (APK Signature Scheme v2): true
```

v1 is off and v3 is off, which are AGP's defaults at `minSdk 26` and are correct here: v1 is only
needed below API 24, and v3 exists for key rotation on APKs you sign yourself — Play re-signs
everything it delivers with its own key and applies the schemes it wants.

### The mapping file

`isMinifyEnabled` is true, so every stack trace Play shows you is obfuscated until the matching
`mapping.txt` is uploaded beside the bundle, on the same screen, under **ReTrace mapping file**.
Play keeps no copy of one you did not give it, and a mapping from a different build is worse than
none. The script copies it out next to the `.aab` with the same name so the pair cannot be
separated.

### Where the backend URL comes from now

`app/build.gradle.kts` used to compile `https://api.pazl.ai` into the release build as a literal.
That host returns NXDOMAIN — verified repeatedly on 7 August 2026 — so the release build was
silently producing an app that cannot create a session, cannot calculate a chart and cannot load
a price list, while printing `BUILD SUCCESSFUL`. iOS already refused to archive against its
placeholder; Android had no such guard, and the asymmetry was the danger, because the Android
value *looked* real.

It is now required per build, from the same `ALMA_API_BASE` the iOS script reads, validated for
`https://` and for a trailing slash, and absent it the build refuses. The debug build is
untouched: it still carries `http://10.0.2.2:8018`, the host as seen from inside the emulator.

---

## iOS

### The two blanks

Everything is filled in except two values, and neither can be guessed by anybody who is not the
owner of the Apple account.

**`ALMA_TEAM_ID`** — the ten-character Apple Developer Team ID for Pazl LLC, from
developer.apple.com/account under Membership details. It reaches `DEVELOPMENT_TEAM` and the
`teamID` in the export options. Without it `xcodebuild` fails with *"Signing for 'Alma' requires
a development team"*. The script checks the shape, because the value people paste by mistake is
the Issuer ID from the App Store Connect API page, which is a UUID.

**`ALMA_API_BASE`** — the https origin of the production backend. The Release configuration
carries the deliberate placeholder `https://api.pazl.ai.INVALID-SET-THIS-BEFORE-TESTFLIGHT`, and
a build phase inside the project turns that into a hard error on the `install` action, which is
the action `xcodebuild archive` runs. Verified:

```
$ xcodebuild archive … -archivePath /tmp/alma-placeholder.xcarchive
error: ALMA_API_BASE is still the placeholder (https://api.pazl.ai.INVALID-SET-THIS-BEFORE-TESTFLIGHT).
       Set the real production host in the Release configuration before archiving …
** ARCHIVE FAILED **
```

Treat that as an open question and not a formality. `api.pazl.ai` does not resolve, so the answer
is not "the placeholder with the suffix removed" — it is whatever host the backend is actually
deployed at, and that same decision has to reach the twelve store descriptions, which currently
link to `alma.pazl.ai`, which does not resolve either.

### Sign in with Apple — it needed a file, and there was none

`Alma/Screens/Settings/SignInScreen.swift` puts a `SignInWithAppleButton` on the sign-in screen
and hands the credential to `AlmaSessionModel.signInWithApple`. There was **no entitlements file
in the project at all**, and no `CODE_SIGN_ENTITLEMENTS` build setting. The button draws either
way; it then fails at the moment of tapping with `ASAuthorizationError` code 1000, a message that
names nothing, and on a device the app will not install at all because the profile does not carry
a capability the binary asks for.

`mobile/ios/Alma.entitlements` now exists, with one key, and both build configurations point at
it. It sits beside `Info.plist` rather than inside `Alma/` for the reason that file gives: `Alma/`
is a file-system synchronized group and a plist dropped in there is copied into the bundle as a
stray resource.

Verified on a simulator build — the entitlement reaches the binary:

```
$ plutil -p …/Alma.build/Alma.app-Simulated.xcent
{
  "application-identifier" => "FAKETEAMID.ai.pazl.alma"
  "com.apple.developer.applesignin" => [ 0 => "Default" ]
}
```

`FAKETEAMID` is what a simulator build with no team produces, and it is why the *other* generated
file, `Alma.app.xcent`, is still empty: the real entitlement is granted by a provisioning
profile, and there is no profile until there is a team.

**The other half is not in this repository and cannot be.** The App ID `ai.pazl.alma` must have
Sign In with Apple enabled in the developer portal — Certificates, Identifiers & Profiles →
Identifiers → `ai.pazl.alma` → Sign In with Apple → Enable. Automatic signing will then put it in
the profile it generates. If it is not enabled, the archive fails with *"Provisioning profile
doesn't include the com.apple.developer.applesignin entitlement"*, which at least names the
thing.

There is deliberately **no Associated Domains entitlement**. Android's manifest claims
`https://alma.pazl.ai/sign-in` with `autoVerify`, so an emailed magic link opens the Android app;
nothing in the iOS sources handles an incoming URL or `NSUserActivity` — no `onOpenURL`, no
`CFBundleURLTypes` — so the same link opens the website on an iPhone. That is an app-source
asymmetry rather than a build one, and it is listed under "What is still missing" rather than
papered over with an entitlement for a capability that is not implemented.

### Archive and export

`mobile/ios/release.sh` does both. The archive step:

```
xcodebuild archive -project Alma.xcodeproj -scheme Alma -configuration Release \
  -destination 'generic/platform=iOS' -archivePath <out>.xcarchive \
  -allowProvisioningUpdates \
  DEVELOPMENT_TEAM=$ALMA_TEAM_ID ALMA_API_BASE=$ALMA_API_BASE \
  MARKETING_VERSION=$version CURRENT_PROJECT_VERSION=$build
```

`-allowProvisioningUpdates` lets Xcode create the distribution certificate and the App Store
profile if the account has none; it needs an Apple ID under Xcode → Settings → Accounts, or an
App Store Connect API key in `~/.appstoreconnect/private_keys`.

The version numbers go in as build settings rather than being written into `.pbxproj`, so a
release needs no edit to any tracked file and two releases cannot collide in one. The script then
reads `CFBundleShortVersionString` and `CFBundleVersion` back out of the archived `Info.plist` and
refuses if they are not the numbers it asked for — a build setting that does not reach the plist
fails silently, and the number App Store Connect compares is the one inside the binary.

The export options live in `mobile/ios/ExportOptions.plist`, which is read but never used
directly: the script copies it into the output directory and writes the real Team ID into the
copy, because the checked-in value is a placeholder and a placeholder reaching `xcodebuild`
produces *"No signing certificate iOS Distribution found"*, which sounds like a certificate
problem and is not one. Two of its keys are worth knowing:

* `method` is `app-store-connect`, the spelling Xcode 15.3 introduced. `app-store` still works and
  prints a deprecation notice.
* `manageAppVersionAndBuildNumber` is **false**. Left at its default, Xcode replaces
  `CFBundleVersion` during export with a number of its own, and the whole scheme above would be
  silently discarded.

The script exports an `.ipa` and stops rather than uploading. Uploading needs an App Store Connect
API key or an Apple ID password, and nothing in this repository should ever be in a position to
hold one; it prints the `xcrun altool --upload-app` command for a person to run, and the Organizer
route works equally well.

### What was actually built

The full archive-and-export could not be run: it needs an Apple team, and this machine has none.
What *was* run is the same archive with signing disabled, which exercises everything except the
signature — the API-base build phase, the version injection, the asset catalogue, the six
localisations, whole-module optimisation:

```
$ xcodebuild archive -project Alma.xcodeproj -scheme Alma -configuration Release \
    -destination 'generic/platform=iOS' -archivePath /tmp/alma-unsigned.xcarchive \
    ALMA_API_BASE=https://api.example.com MARKETING_VERSION=1.0.0 CURRENT_PROJECT_VERSION=314525 \
    CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY=
** ARCHIVE SUCCEEDED **

$ PlistBuddy -c 'Print :CFBundleShortVersionString' …/Alma.app/Info.plist   → 1.0.0
$ PlistBuddy -c 'Print :CFBundleVersion'            …/Alma.app/Info.plist   → 314525
$ PlistBuddy -c 'Print :ALMAAPIBase'                …/Alma.app/Info.plist   → https://api.example.com
$ ls …/Alma.app
Alma  AppIcon60x60@2x.png  AppIcon76x76@2x~ipad.png  Assets.car  Info.plist
PkgInfo  PrivacyInfo.xcprivacy  de.lproj  en.lproj  es.lproj  fr.lproj  it.lproj  pt-BR.lproj
$ ls /tmp/alma-unsigned.xcarchive/dSYMs
Alma.app.dSYM
```

So: **everything up to the signature is proven, and the signature is not.** The two blanks are
the only things between that output and an `.ipa`.

---

## Icons and store assets

### iOS icons — complete, and verified by looking inside the archive

The asset catalogue holds one 1024 × 1024 PNG with no alpha channel, declared `universal`. That
is the modern single-size form and it is not missing anything: Xcode derives every other size at
build time. The archived app contains `AppIcon60x60@2x.png`, `AppIcon76x76@2x~ipad.png` and
`Assets.car`, with `CFBundleIcons → CFBundlePrimaryIcon → CFBundleIconName = AppIcon` written
into `Info.plist`. Nothing to add.

`swift tools/make_app_icon.swift` regenerates it. After the refactor described below it still
produces the same file byte for byte — SHA-256
`da38136d68f09519c6e1c80be7ea4029156b2daa011486cb25368eb50536f33c` before and after.

### Android launcher icon — complete on the device, and it was not obvious

`res/mipmap-anydpi-v26/ic_launcher.xml` and `ic_launcher_round.xml` are adaptive icons over two
vector drawables, with a `<monochrome>` layer for Android 13 themed icons. There are **no PNG
mipmaps at any density**, and that would normally be a bug — but `minSdk` is 26, adaptive icons
arrived in 26, so every device that can install this app can render them. Verified by building
the release APK: `lintVitalRelease` passes and the icon resource resolves.

### Play store graphics — two were missing, and now exist

Play refuses to publish a listing without a **feature graphic**, and the only PNG in the entire
project was the iOS icon. Both required files are now generated:

```
$ swift tools/make_app_icon.swift --all ../store/assets
wrote …/AppIcon.appiconset/AppIcon.png            — 1024×1024, 521896 bytes
wrote …/store/assets/play-icon-512.png            — 512×512,   175633 bytes
wrote …/store/assets/play-feature-graphic-1024x500.png — 1024×500, 188647 bytes
```

They are drawn by the same script as the iOS icon rather than by a second one under
`mobile/android/`, because the mark is a nine-segment quadratic path that already exists in four
places — `AlmaStar.swift`, `Star.tsx`, `ic_launcher_foreground.xml`, and this script — and a fifth
copy is a fifth thing that drifts. Every coordinate in the script is now a fraction of 1024, so
the same composition lands on a square and on a wide frame; on a non-square canvas the scale
follows the shorter side, which is what stops the mark being cropped.

The alpha rules are opposite and the script honours both, which is why these three files cannot be
made from each other with `sips`:

| file | size | alpha | checked with |
|---|---|---|---|
| `AppIcon.png` (in the binary) | 1024 × 1024 | **no** — App Store Connect rejects an icon that has one | `sips -g hasAlpha` → `no` |
| `play-icon-512.png` | 512 × 512 | **yes** — Play wants 32-bit, ≤ 1024 KB | `samplesPerPixel: 4`, 172 KB |
| `play-feature-graphic-1024x500.png` | 1024 × 500 | **no** — Play requires 24-bit here | `samplesPerPixel: 3` |

The feature graphic is wordless, which is what `store/SCREENSHOTS.md` §4 asks for: one file
serves all six Play locales, where a graphic carrying a sentence becomes six files.

### What is still missing

**Screenshots. All of them.** Neither store will accept a listing without them, and there are
none in this repository — `find` over the whole project returns exactly one PNG outside
`_reference/uploads`, and it is the iOS icon. `store/SCREENSHOTS.md` specifies the work in full:
6 shots × 6 locales × 2 aspect ratios = **72 images**, at 1320 × 2868 for Apple and 1080 × 1920
for Play, no alpha on any of them. They cannot be produced here because every frame has to be
captured against a running backend with a real chart on screen.

**iPad screenshots, or a decision not to need them.** `TARGETED_DEVICE_FAMILY` is `"1,2"` and
`Info.plist` declares four iPad orientations, so the binary ships for iPad, and App Store Connect
then requires a 13-inch set — 2064 × 2752, another 36 images. `SCREENSHOTS.md` records this as
"undecided", but the build has decided: it ships for iPad today. If the intent is iPhone only,
the change is one line in both configurations of `Alma.xcodeproj` (`TARGETED_DEVICE_FAMILY = "1"`)
and it must be made *before* the first submission — dropping iPad support later removes the app
from the iPads that already have it.

**Nothing else.** Both apps have every icon size, and both store graphic requirements are now met.

---

## The one thing to get right before either upload

The product identifiers. `mobile/store/PRODUCTS.md` recommends `ai.pazl.alma.natal`; both
binaries ask for `alma.natal` — `LadderKey.prefix` in Swift, `StoreProducts.PREFIX` in Kotlin, and
both scripts now print the prefix they found in the source as part of the pre-build summary, so
it is in front of you at the moment it matters.

Typing one into a console while the binary asks for the other gives an empty paywall and a
Guideline 2.1 rejection, and **neither store lets a product id be edited or reused** — not even
after deleting the product. Decide which prefix, change the constant if it is the other one, and
only then type anything into App Store Connect or the Play Console.

Related and just as unproven: no purchase has ever completed on either platform. StoreKit's
simulator slice is absent and `simctl` ignores a scheme's StoreKit configuration, so everything
past the tap is verified by construction only. The first real evidence will be a sandbox purchase
on a device, which needs the products to exist, which needs the prefix decided.
