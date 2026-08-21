package ai.pazl.alma

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * Вторая половина того, что на iOS делает AppDelegate: показ пуша, когда
 * приложение на переднем плане, и тап, ведущий в нужное место.
 *
 * Фоновое notification-сообщение Android показывает сам — сервис для этого не
 * нужен. `onMessageReceived` вызывается для data-сообщений всегда и для
 * notification-сообщений только пока приложение на переднем плане; вот тогда
 * показать уведомление обязаны мы. Тап несёт весь `data` в extras MainActivity,
 * откуда он уходит в Flutter теми же `pushOpened`/`launchPush`, что и на iOS.
 */
class AlmaMessagingService : FirebaseMessagingService() {

    /**
     * Токен обновился, пока приложение работало. Своего движка Flutter у сервиса
     * нет, поэтому канал отсюда не позвать — но `FirebaseMessaging.getToken()`
     * на следующем запуске вернёт уже новый токен, и `AlmaPush.sync` его
     * перечитает и перерегистрирует. Здесь достаточно не мешать: повторная
     * регистрация случится сама, без headless-движка ради редкого события.
     */
    override fun onNewToken(token: String) {
        super.onNewToken(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        ensureChannel()

        val notification = message.notification
        val title = notification?.title ?: message.data["title"] ?: "Alma"
        // Без текста показывать нечего — молчим, а не рисуем пустую строку.
        val body = notification?.body ?: message.data["body"] ?: return

        // Тап несёт весь data наверх; MainActivity вытащит строки и отдаст Dart.
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            for ((key, value) in message.data) putExtra(key, value)
        }
        val pending = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val built = NotificationCompat.Builder(this, CHANNEL_DAILY)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(message.messageId?.hashCode() ?: 0, built)
    }

    /**
     * Канал `alma.daily` — то же имя, что серверный `CHANNEL_DAILY`
     * (`backend/alma/notify/transport.py`). С Android 8 без канала уведомление
     * не покажется вовсе; создаётся идемпотентно.
     */
    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (manager.getNotificationChannel(CHANNEL_DAILY) != null) return
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_DAILY,
                "Daily",
                NotificationManager.IMPORTANCE_DEFAULT,
            ),
        )
    }

    private companion object {
        const val CHANNEL_DAILY = "alma.daily"
    }
}
