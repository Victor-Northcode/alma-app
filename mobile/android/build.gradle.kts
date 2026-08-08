// The root build declares plugins without applying them, so that the version
// catalogue is the only place a version is written and :app decides what it
// actually uses.

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
}
