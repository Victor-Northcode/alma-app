# The build environments, verified on this machine

Not a list of what ought to work — every line below was run and its output checked on
6 August 2026. Two of the defaults on this machine are wrong for Android, and both fail in
ways that read as a broken project rather than a broken environment.

## iOS

```
Xcode 26.6 (build 17F113) · simulators: iPhone 17, iPhone 17 Pro, iPhone 17 Pro Max
```

Builds and runs here. No setup needed beyond opening the project.

## Android

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$JAVA_HOME/bin:$PATH"
```

**`JAVA_HOME` is the one that matters.** Two JDKs on this machine are the obvious choice and
both are wrong:

* `java` on the default `PATH` is **1.8**. The Android Gradle Plugin needs 17 or newer, and
  the failure arrives as a stack trace about class file versions rather than as "wrong JDK".
* Android Studio bundles **JDK 25** at `/Applications/Android Studio.app/Contents/jbr`. It is
  too *new*: Gradle 8.14 with AGP 8.13 refuses it, and the entire error message is the string
  `25.0.2` under "What went wrong", which tells a reader nothing at all.

`openjdk@21` is installed via Homebrew and builds cleanly. `openjdk@17` is there too and also
works.

Installed SDK: platform **android-37.0**, build-tools **36.0.0**, platform-tools with `adb`,
and the emulator image `system-images;android-36;google_apis;arm64-v8a`.

### The emulator — and the second `ANDROID_HOME`

An AVD named **`alma_pixel`** exists (Pixel 7, android-36, arm64), and **booting it needs a
different `ANDROID_HOME` from the one Gradle uses**:

```bash
# Gradle is happy with either root. The emulator is not.
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
emulator -avd alma_pixel -no-snapshot-save -no-audio &
adb wait-for-device
adb shell getprop sys.boot_completed   # "1" when it is actually ready
```

There are two SDK installations on this machine and the system images are only in one of
them. `$HOME/Library/Android/sdk` has **no `system-images` directory at all** — verified —
so with the `ANDROID_HOME` at the top of this file the emulator dies with:

```
Cannot find AVD system path. Please define ANDROID_SDK_ROOT
```

which reads as a broken AVD rather than as a wrong variable, and costs about half an hour
per person who meets it. The image the AVD needs lives at
`/opt/homebrew/share/android-commandlinetools/system-images/android-36`.

`adb devices` reporting the device is not the same as the device being ready; installing
before `sys.boot_completed` is `1` fails intermittently, which looks like a flaky build.

**The emulator has no GPU.** Its boot log reports `vulkan_mode_selected:lavapipe` and
`gles_mode_selected:swangle`, both software rasterisers, so the ambient sky measures ~3 fps
and 100 % janky frames here no matter what it does. That number says nothing about a real
device — with animations disabled the app renders literally zero frames over ten seconds
when idle, so there is no background work to blame. **Do not tune the sky against this
machine**; judge it on hardware.

**Driving it.** `uiautomator dump` reports node bounds from underneath the IME, so a tap
that looks correct in the dump lands on the keyboard. Dismiss the keyboard first — with
`input keyevent 111` (ESC), never `4` (BACK), which exits the app when no keyboard is up.

### Reaching the backend from inside the emulator

The backend runs on the host at `http://localhost:8018`. Inside the Android emulator
`localhost` is the emulator itself, so the host is **`http://10.0.2.2:8018`**. On the iOS
simulator, which shares the host's network stack, plain `localhost` is correct. The two
platforms genuinely differ here; a shared constant would be wrong on one of them.

### Proof this works

A minimal Kotlin/AGP project built to a real APK on this exact setup:

```
gradle -p probe :app:assembleDebug
→ app/build/outputs/apk/debug/app-debug.apk   810691 bytes
```

Gradle itself came from `https://services.gradle.org/distributions/gradle-8.14-bin.zip`.
A real project should carry its own wrapper (`gradlew`) so the version is committed rather
than inherited from whatever is on the machine.
