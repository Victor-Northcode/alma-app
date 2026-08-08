# kotlinx.serialization writes its serializers as synthetic members of the
# classes it generates them for, and R8 cannot see that the reflection-free
# lookup in `SerializersKt` reaches them. Without these two rules a release
# build parses every response into an empty object — which is the worst kind of
# failure, because it is silent and only happens in the build nobody debugs.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**

-keepclassmembers class ai.pazl.alma.data.dto.** {
    *** Companion;
}
-keepclasseswithmembers class ai.pazl.alma.data.dto.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class ai.pazl.alma.data.dto.**$$serializer { *; }

# Retrofit's interface methods keep their generic signatures only if these
# attributes survive; the failure mode is a runtime "Unable to create converter"
# on the first call of the first release build.
-keepattributes Signature, RuntimeVisibleAnnotations, AnnotationDefault
-keep,allowobfuscation interface ai.pazl.alma.data.AlmaService
-keep,allowobfuscation,allowshrinking class retrofit2.Response

# OkHttp names two optional dependencies it works without. They are absent by
# design and the warnings are noise.
-dontwarn okhttp3.internal.platform.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**
