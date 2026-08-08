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
        vibrator(context)?.vibrate(
            VibrationEffect.createPredefined(VibrationEffect.EFFECT_TICK)
        )
    }

    /** The arrival — the portrait revealed, the journey saved. */
    fun arrival(context: Context) {
        vibrator(context)?.vibrate(
            VibrationEffect.createPredefined(VibrationEffect.EFFECT_CLICK)
        )
    }

    /** Something opened that was closed — a purchase confirmed by the server. */
    fun unlocked(context: Context) {
        vibrator(context)?.vibrate(
            VibrationEffect.createPredefined(VibrationEffect.EFFECT_DOUBLE_CLICK)
        )
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
