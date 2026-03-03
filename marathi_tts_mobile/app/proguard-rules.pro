# ── Marathi TTS — ProGuard / R8 rules ────────────────────────────────────────

# Chaquopy: keep all Python bridge classes intact
-keep class com.chaquo.python.** { *; }
-dontwarn com.chaquo.python.**

# App entry points
-keep class com.marathitts.mobile.MainActivity { *; }
-keep class com.marathitts.mobile.service.** { *; }

# Navigation component safe-args generated classes
-keep class com.marathitts.mobile.** { *; }

# AndroidX / Jetpack — keep lifecycle observers
-keep class * extends androidx.lifecycle.ViewModel { *; }
-keep class * implements androidx.lifecycle.LifecycleObserver { *; }

# Google ML Kit — Devanagari text recognition
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }

# Gson — preserve model fields used in JSON deserialisation
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.** { *; }
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer

# General: keep line numbers for crash reports
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
