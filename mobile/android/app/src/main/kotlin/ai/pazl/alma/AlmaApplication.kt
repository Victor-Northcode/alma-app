package ai.pazl.alma

import ai.pazl.alma.core.AppContainer
import android.app.Application

/**
 * The process. Its only job is to own the [AppContainer].
 *
 * The container is created lazily rather than in `onCreate` for one measurable
 * reason: `TokenStore` opens a keystore-backed preference file, which on a cold
 * start of a mid-range device is tens of milliseconds of the time before the
 * first frame. Nothing needs it until the first composition asks, and by then
 * we are off the critical path.
 */
class AlmaApplication : Application() {

    val container: AppContainer by lazy { AppContainer(this) }

    override fun onTerminate() {
        super.onTerminate()
        container.close()
    }
}
