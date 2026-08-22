pluginManagement {
    val flutterSdkPath =
        run {
            val properties = java.util.Properties()
            file("local.properties").inputStream().use { properties.load(it) }
            val flutterSdkPath = properties.getProperty("flutter.sdk")
            require(flutterSdkPath != null) { "flutter.sdk not set in local.properties" }
            flutterSdkPath
        }

    includeBuild("$flutterSdkPath/packages/flutter_tools/gradle")

    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    id("dev.flutter.flutter-plugin-loader") version "1.0.0"
    id("com.android.application") version "9.0.1" apply false
    id("org.jetbrains.kotlin.android") version "2.3.20" apply false
    // **Плагин Google Services читает google-services.json и генерирует из него
    //   ресурсы, из которых FirebaseApp поднимается сам.** Без него
    //   FirebaseMessaging.getInstance() падает на "Default FirebaseApp is not
    //   initialized" — и падает в рантайме, а не на сборке, то есть тихо.
    //   Версию сверить с https://firebase.google.com/docs/android/setup перед
    //   первой сборкой: AGP здесь 9.0.1, и плагин обязан быть не старше него.
    id("com.google.gms.google-services") version "4.4.2" apply false
}

include(":app")
