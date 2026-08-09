package ai.pazl.alma.ui.components

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

/**
 * The product's whole vocabulary of touch, in one place — the Android half of
 * the iOS `AlmaHaptics`.
 *
 * Three gestures, used rarely, and that is the design: a vibration is the most
 * intimate channel a phone has, and an app that buzzes on every tap has spent
 * it before anything mattered. Alma touches the hand at the moments the sky
 * does something — a system finishing its calculation, a chart arriving, a
 * purchase opening — and at no other time.
 *
 * Predefined effects rather than hand-rolled waveforms, because the predefined
 * set is tuned per device by the vendor and a waveform that feels right on one
 * motor feels like a dying fly on another.
 */
object AlmaHaptics {

    /** One soft tick — a system lighting up during the ceremony. */
    fun tick(context: Context) {
        play(context, VibrationEffect.EFFECT_TICK)
    }

    /** The arrival — the portrait revealed, the journey saved. */
    fun arrival(context: Context) {
        play(context, VibrationEffect.EFFECT_CLICK)
    }

    /** Something opened that was closed — a purchase confirmed by the server. */
    fun unlocked(context: Context) {
        play(context, VibrationEffect.EFFECT_DOUBLE_CLICK)
    }

    /**
     * Buzz, and never take the app down doing it.
     *
     * **Why a `try` around something this small.** `Vibrator.vibrate` is
     * permission-checked on the far side of a Binder call, so a missing
     * `VIBRATE` throws `SecurityException` on the caller's thread — and this is
     * called from the ceremony, on the main thread, which means the app dies at
     * the last step of onboarding. The manifest now declares the permission and
     * that is the real fix; this is the belt, because the failure mode is so
     * much worse than the feature. A device with a broken motor, a vendor that
     * throws on an effect it does not know, a future policy that revokes a
     * normal permission — none of those are worth a crash.
     *
     * Silent rather than logged: nothing here is actionable, and a decoration
     * that failed should not become a line in a log the next person greps.
     */
    private fun play(context: Context, effect: Int) {
        try {
            vibrator(context)?.vibrate(VibrationEffect.createPredefined(effect))
        } catch (_: SecurityException) {
        } catch (_: RuntimeException) {
        }
    }

    private fun vibrator(context: Context): Vibrator? {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)
                ?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }
        return vibrator?.takeIf { it.hasVibrator() }
    }
}
