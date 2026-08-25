package ai.pazl.alma

import android.content.ContentValues
import android.content.Intent
import android.os.Build
import android.provider.MediaStore
import com.google.firebase.messaging.FirebaseMessaging
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

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

        // Канал загрузок: «Сохранить файл» на Android кладёт файл в системные
        // «Загрузки» через MediaStore (владелец, 25.08.2026: «кнопка должна
        // его скачивать»). Разрешений не нужно: с API 29 MediaStore.Downloads
        // принимает записи от приложения без WRITE_EXTERNAL_STORAGE. Старее
        // API 29 коллекции нет — канал честно отказывает, и Dart открывает
        // системный лист «поделиться» вместо тихой ямы.
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, DOWNLOADS)
            .setMethodCallHandler { call, result ->
                if (call.method != "save") {
                    result.notImplemented()
                    return@setMethodCallHandler
                }
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
                    // До API 29 у MediaStore нет коллекции Downloads, а прямой
                    // путь требует опасного разрешения. Dart на этот отказ
                    // откатывается в системный лист «поделиться».
                    result.error("save_unsupported", "needs API 29", null)
                    return@setMethodCallHandler
                }
                try {
                    val path = call.argument<String>("path")!!
                    val name = call.argument<String>("name")!!
                    val mime = call.argument<String>("mime") ?: "application/octet-stream"
                    val values = ContentValues().apply {
                        put(MediaStore.Downloads.DISPLAY_NAME, name)
                        put(MediaStore.Downloads.MIME_TYPE, mime)
                    }
                    val resolver = contentResolver
                    val target = resolver.insert(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI, values,
                    ) ?: throw IllegalStateException("MediaStore refused the row")
                    resolver.openOutputStream(target)!!.use { out ->
                        File(path).inputStream().use { it.copyTo(out) }
                    }
                    result.success(null)
                } catch (error: Exception) {
                    result.error("save_failed", error.message, null)
                }
            }
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
        const val DOWNLOADS = "ai.pazl.alma/downloads"
    }
}
