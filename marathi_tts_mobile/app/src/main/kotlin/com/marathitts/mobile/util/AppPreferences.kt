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

    // Engine success tracking (FEAT-49)
    private const val KEY_ENGINE_SUCCESS_PREFIX = "engine_success_"

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

    // ── Engine preference learning (FEAT-49) ────────────────────────────

    /**
     * Record a successful TTS generation for the given engine name.
     * Called after every successful generate() result.
     */
    fun recordEngineSuccess(context: Context, engineName: String) {
        val key = KEY_ENGINE_SUCCESS_PREFIX + engineName.lowercase().replace(" ", "_")
        val current = prefs(context).getInt(key, 0)
        prefs(context).edit().putInt(key, current + 1).apply()
    }

    /**
     * Returns the engine name that has succeeded most often,
     * or null if no history exists (= use Auto).
     */
    fun getLearnedPreferredEngine(context: Context): String? {
        val p = prefs(context)
        val engines = listOf("gtts", "edge", "system_tts", "sherpa")
        var bestEngine: String? = null
        var bestCount = 0
        for (eng in engines) {
            val count = p.getInt(KEY_ENGINE_SUCCESS_PREFIX + eng, 0)
            if (count > bestCount) {
                bestCount = count
                bestEngine = eng
            }
        }
        // Only recommend if we have at least 3 data points
        return if (bestCount >= 3) bestEngine else null
    }

    /**
     * Returns the engine success counts for display (e.g. in Settings).
     */
    fun getEngineStats(context: Context): Map<String, Int> {
        val p = prefs(context)
        return listOf("gtts", "edge", "system_tts", "sherpa").associateWith { eng ->
            p.getInt(KEY_ENGINE_SUCCESS_PREFIX + eng, 0)
        }
    }

    // ── Cache / data management ─────────────────────────────────────────

    fun clearAllPrefs(context: Context) {
        prefs(context).edit().clear().apply()
    }
}
