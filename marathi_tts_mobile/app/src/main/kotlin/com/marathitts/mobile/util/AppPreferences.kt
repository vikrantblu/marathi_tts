package com.marathitts.mobile.util

import android.content.Context
import android.content.SharedPreferences
import androidx.appcompat.app.AppCompatDelegate

/**
 * Centralized SharedPreferences wrapper for app-wide settings.
 * All keys match the preference XML keys in preferences.xml.
 */
object AppPreferences {

    private const val PREFS_NAME = "marathi_tts_prefs"

    // Theme
    const val KEY_THEME_MODE = "theme_mode"

    // TTS defaults
    const val KEY_DEFAULT_ENGINE = "default_engine"
    const val KEY_DEFAULT_SPEED = "default_speed"
    const val KEY_DEFAULT_PITCH = "default_pitch"
    const val KEY_DEFAULT_VOLUME = "default_volume"

    // Draft persistence
    const val KEY_TTS_DRAFT = "tts_draft_text"

    // Developer mode
    const val KEY_DEV_MODE = "dev_mode_enabled"

    private fun prefs(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    // ── Theme ───────────────────────────────────────────────────────────

    fun getThemeMode(context: Context): Int {
        val value = prefs(context).getString(KEY_THEME_MODE, "system") ?: "system"
        return when (value) {
            "light" -> AppCompatDelegate.MODE_NIGHT_NO
            "dark"  -> AppCompatDelegate.MODE_NIGHT_YES
            else    -> AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM
        }
    }

    fun getThemeModeString(context: Context): String =
        prefs(context).getString(KEY_THEME_MODE, "system") ?: "system"

    fun setThemeMode(context: Context, mode: String) {
        prefs(context).edit().putString(KEY_THEME_MODE, mode).apply()
        val nightMode = when (mode) {
            "light" -> AppCompatDelegate.MODE_NIGHT_NO
            "dark"  -> AppCompatDelegate.MODE_NIGHT_YES
            else    -> AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM
        }
        AppCompatDelegate.setDefaultNightMode(nightMode)
    }

    // ── TTS defaults ────────────────────────────────────────────────────

    fun getDefaultEngine(context: Context): String =
        prefs(context).getString(KEY_DEFAULT_ENGINE, "auto") ?: "auto"

    fun setDefaultEngine(context: Context, engine: String) {
        prefs(context).edit().putString(KEY_DEFAULT_ENGINE, engine).apply()
    }

    fun getDefaultSpeed(context: Context): Float =
        prefs(context).getFloat(KEY_DEFAULT_SPEED, 1.0f)

    fun setDefaultSpeed(context: Context, speed: Float) {
        prefs(context).edit().putFloat(KEY_DEFAULT_SPEED, speed).apply()
    }

    fun getDefaultPitch(context: Context): Float =
        prefs(context).getFloat(KEY_DEFAULT_PITCH, 1.0f)

    fun setDefaultPitch(context: Context, pitch: Float) {
        prefs(context).edit().putFloat(KEY_DEFAULT_PITCH, pitch).apply()
    }

    fun getDefaultVolume(context: Context): Float =
        prefs(context).getFloat(KEY_DEFAULT_VOLUME, 1.0f)

    fun setDefaultVolume(context: Context, volume: Float) {
        prefs(context).edit().putFloat(KEY_DEFAULT_VOLUME, volume).apply()
    }

    // ── Draft persistence ───────────────────────────────────────────────

    fun getTtsDraft(context: Context): String =
        prefs(context).getString(KEY_TTS_DRAFT, "") ?: ""

    fun setTtsDraft(context: Context, text: String) {
        prefs(context).edit().putString(KEY_TTS_DRAFT, text).apply()
    }

    // ── Developer mode ──────────────────────────────────────────────────

    fun isDevModeEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_DEV_MODE, false)

    fun setDevMode(context: Context, enabled: Boolean) {
        prefs(context).edit().putBoolean(KEY_DEV_MODE, enabled).apply()
    }

    // ── Cache / data management ─────────────────────────────────────────

    fun clearAllPrefs(context: Context) {
        prefs(context).edit().clear().apply()
    }
}
