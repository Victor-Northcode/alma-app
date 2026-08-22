import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    // **Обязан идти после Android-плагина.** Читает
    // `android/app/google-services.json` и кладёт project_id, app_id и api_key
    // в ресурсы; FirebaseApp поднимается из них автоматически.
    id("com.google.gms.google-services")
}

// **Подпись релиза из key.properties, которого нет в гите.** Файл кладёт владелец
// или CI (Codemagic пишет его из своей группы перед сборкой); в нём путь к
// upload-keystore и три пароля, а .gitignore держит и его, и сам .jks вне
// репозитория. Есть файл — подписываем настоящим upload-ключом; нет — debug,
// чтобы `flutter run --release` и первая заливка в Play (которая и регистрирует
// подпись как upload-ключ) всё равно собирались.
val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    namespace = "ai.pazl.alma"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "ai.pazl.alma"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    if (keystorePropertiesFile.exists()) {
        signingConfigs {
            create("upload") {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            // upload-ключ, если владелец/CI дал key.properties; иначе debug —
            // Play примет первый бандл на debug и зарегистрирует его как upload.
            signingConfig = signingConfigs.getByName(
                if (keystorePropertiesFile.exists()) "upload" else "debug"
            )
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

dependencies {
    // **Только `firebase-messaging`, и это не экономия, а условие.**
    // `docs/PUSH.md §7.1`: строка «No third-party analytics SDK» остаётся
    // правдой ровно до тех пор, пока сюда не добавлен `firebase-analytics`.
    // Добавить его — значит переписывать Data safety и §4 таблицы отсутствий.
    //
    // BoM держит версии транзитивных артефактов согласованными; номер сверить
    // с https://firebase.google.com/docs/android/setup перед первой сборкой.
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-messaging")
    // NotificationCompat в AlmaMessagingService (форграунд-показ). firebase-messaging
    // тянет androidx.core транзитивно, но объявляем явно, чтобы сборка не зависела
    // от чужого графа зависимостей.
    implementation("androidx.core:core-ktx:1.13.1")
}

flutter {
    source = "../.."
}
