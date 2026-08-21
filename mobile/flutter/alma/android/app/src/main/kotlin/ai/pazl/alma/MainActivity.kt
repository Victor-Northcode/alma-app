package ai.pazl.alma

import android.os.Build
import com.google.firebase.messaging.FirebaseMessaging
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Канал `ai.pazl.alma/push` — та же труба, что на iOS отдаёт `apnsToken`.
 *
 * **Почему нативно, а не пакетом `firebase_messaging`.** `docs/PUSH.md §2.1`
 * решает не гонять iOS через FCM, а §7.1 отдельно защищает строку «iOS links no
 * third-party framework at all». Flutter-плагин кроссплатформенный: он тянет
 * `firebase_core` и в iOS-сборку, требует там `GoogleService-Info.plist` и
 * перехватывает делегата APNs — то есть ломает ровно то, что §2.1 защищает.
 * Нативная зависимость живёт только в Android-сборке и iOS не касается.
 */
class MainActivity : FlutterActivity() {

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "fcmToken" -> token(result)
                    else -> result.notImplemented()
                }
            }
    }

    /**
     * Токен регистрации FCM.
     *
     * Отказ — не исключение приложения: на устройстве без Google Play services
     * токена не будет никогда, и это не ошибка, а свойство устройства.
     * `PushDevices._identity` читает `error` как «транспорта здесь нет» и
     * молчит, ровно как молчит на симуляторе iOS.
     */
    private fun token(result: MethodChannel.Result) {
        FirebaseMessaging.getInstance().token
            .addOnCompleteListener { task ->
                if (!task.isSuccessful) {
                    result.error(
                        "fcm_unavailable",
                        task.exception?.message ?: "no FCM token on this device",
                        null,
                    )
                    return@addOnCompleteListener
                }
                result.success(
                    mapOf(
                        "token" to task.result,
                        "app_version" to appVersion(),
                        "os_version" to Build.VERSION.RELEASE,
                    ),
                )
            }
    }

    private fun appVersion(): String? = try {
        packageManager.getPackageInfo(packageName, 0).versionName
    } catch (_: Exception) {
        null
    }

    private companion object {
        const val CHANNEL = "ai.pazl.alma/push"
    }
}
