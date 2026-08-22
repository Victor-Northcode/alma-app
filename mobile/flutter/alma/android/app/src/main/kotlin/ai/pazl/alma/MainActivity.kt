package ai.pazl.alma

import android.content.Intent
import android.os.Build
import com.google.firebase.messaging.FirebaseMessaging
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Канал `ai.pazl.alma/push` — та же труба, что на iOS отдаёт `apnsToken`, плюс
 * разбор тапа по уведомлению теми же именами методов, что у AppDelegate.
 *
 * **Почему нативно, а не пакетом `firebase_messaging`.** `docs/PUSH.md §2.1`
 * решает не гонять iOS через FCM, а §7.1 отдельно защищает строку «iOS links no
 * third-party framework at all». Flutter-плагин тянет `firebase_core` и в
 * iOS-сборку, требует там `GoogleService-Info.plist` и перехватывает делегата
 * APNs — то есть ломает ровно то, что §2.1 защищает. Нативная зависимость живёт
 * только в Android-сборке и iOS не касается.
 */
class MainActivity : FlutterActivity() {

    private var pushChannel: MethodChannel? = null

    /**
     * Пуш, открывший мёртвое приложение, — пока Dart не начал слушать. Тап
     * будит процесс раньше движка Flutter; payload ждёт здесь, и Dart забирает
     * его методом `launchPush`, ровно как `pendingOpen` на iOS.
     */
    private var pendingOpen: Map<String, String>? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        channel.setMethodCallHandler { call, result ->
            when (call.method) {
                "fcmToken" -> token(result)
                "launchPush" -> {
                    // Отдаётся один раз: второй вопрос получает null, и Dart не
                    // насчитает два открытия из одного тапа.
                    result.success(pendingOpen)
                    pendingOpen = null
                }
                else -> result.notImplemented()
            }
        }
        pushChannel = channel
        // Холодный старт по тапу: payload ждёт launchPush.
        openedFrom(intent)?.let { pendingOpen = it }
    }

    /**
     * Тап по уведомлению, когда активность уже живёт (`singleTop`). Dart уже
     * слушает — отдаём сразу через `pushOpened`, как живой тап на iOS.
     */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        openedFrom(intent)?.let { opened ->
            val channel = pushChannel
            if (channel != null) channel.invokeMethod("pushOpened", opened) else pendingOpen = opened
        }
    }

    /**
     * Строковые extras уведомления FCM — тот же верхний уровень строк, что iOS
     * снимает с `userInfo`. FCM кладёт поля `data` в extras запускающего
     * Intent; сервер шлёт тип пуша строкой (`type`), и большего каналу знать не
     * нужно. Обычный запуск с иконки extras не несёт и даёт `null`.
     */
    private fun openedFrom(intent: Intent?): Map<String, String>? {
        val extras = intent?.extras ?: return null
        val opened = HashMap<String, String>()
        for (key in extras.keySet()) {
            extras.getString(key)?.let { opened[key] = it }
        }
        return if (opened.isEmpty()) null else opened
    }

    /**
     * Токен регистрации FCM.
     *
     * Отказ — не исключение приложения: на устройстве без Google Play services
     * токена не будет никогда, и это свойство устройства, а не ошибка.
     * `PushDevices._identity` читает `error` как «транспорта здесь нет» и
     * молчит, ровно как на симуляторе iOS.
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
