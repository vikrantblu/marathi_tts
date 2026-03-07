package com.marathitts.mobile.service

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

/**
 * Coordinates multiple TTS engines and provides a single generate() API.
 *
 * Engines:
 *  0 = Auto         (Sherpa first → System TTS → gTTS)
 *  1 = gTTS Online  (Google Translate voice via Python bridge)
 *  2 = System TTS   (Android built-in TextToSpeech, works offline)
 *  3 = Sherpa-ONNX  (Offline AI VITS model — downloaded on demand)
 */
class TtsEngineManager(private val context: Context) {

    companion object {
        private const val TAG = "TtsEngineManager"

        /** Display names shown in the engine spinner. */
        val ENGINE_NAMES = listOf(
            "Auto (best available)",
            "gTTS (Online - Google)",
            "System TTS (Device)",
            "Sherpa AI (Offline)"
        )

        /** Short descriptions for each engine. */
        val ENGINE_DESCRIPTIONS = listOf(
            "Picks the best available engine automatically",
            "Google Translate voice — requires internet",
            "Android built-in TTS — works offline if language pack installed",
            "VITS neural voice — best quality, needs model download (~50 MB)"
        )

        val LANGUAGE_NAMES = listOf(
            "मराठी (Marathi)",
            "हिंदी (Hindi)",
            "संस्कृत (Sanskrit)",
            "English"
        )
        val LANGUAGE_CODES = listOf("mr", "hi", "sa", "en")

        val GENDER_NAMES = listOf("स्त्री (Female)", "पुरुष (Male)")
        val GENDER_CODES = listOf("female", "male")

        const val ENGINE_AUTO = 0
        const val ENGINE_GTTS = 1
        const val ENGINE_SYSTEM = 2
        const val ENGINE_SHERPA = 3
    }

    private var systemTts: SystemTtsEngine? = null
    private var sherpaReady = false

    // Lazy-init system TTS
    private suspend fun getSystemTts(): SystemTtsEngine {
        if (systemTts == null) {
            systemTts = SystemTtsEngine(context)
            systemTts!!.init()
        }
        return systemTts!!
    }

    /**
     * Check if Sherpa-ONNX model is downloaded for a language.
     */
    fun isSherpaModelAvailable(langCode: String): Boolean {
        val modelDir = File(context.filesDir, "sherpa-models/$langCode")
        return modelDir.exists() && (modelDir.listFiles()?.isNotEmpty() == true)
    }

    /**
     * Generate TTS audio.
     *
     * @return JSONObject with "success", "audio_path", "engine" keys.
     */
    suspend fun generate(
        text: String,
        engineIndex: Int,
        langCode: String = "mr",
        gender: String = "female",
        speed: Float = 1.0f,
        pitch: Float = 1.0f,
        volume: Float = 1.0f,
        emotion: String? = null,
        isVerse: Boolean = false,
        emotionIntensity: Float = 1.0f,
        accent: String = "standard"
    ): JSONObject {
        // Decide which engine(s) to try
        val engines = when (engineIndex) {
            ENGINE_GTTS -> listOf(ENGINE_GTTS)
            ENGINE_SYSTEM -> listOf(ENGINE_SYSTEM)
            ENGINE_SHERPA -> listOf(ENGINE_SHERPA, ENGINE_SYSTEM, ENGINE_GTTS)
            else -> listOf(ENGINE_SHERPA, ENGINE_SYSTEM, ENGINE_GTTS)  // Auto
        }

        for (engine in engines) {
            try {
                val result = when (engine) {
                    ENGINE_SHERPA -> trySherpa(text, langCode, speed, pitch, volume, isVerse)
                    ENGINE_SYSTEM -> trySystemTts(text, langCode, gender, speed, pitch)
                    ENGINE_GTTS -> tryGtts(text, langCode, gender, speed, pitch, volume, emotion, isVerse, emotionIntensity, accent)
                    else -> null
                }
                if (result != null && result.optBoolean("success", false)) {
                    Log.i(TAG, "Engine ${ENGINE_NAMES.getOrElse(engine) { "?" }} succeeded")
                    return result
                }
            } catch (e: Exception) {
                Log.w(TAG, "Engine $engine failed: ${e.message}")
            }
        }

        return JSONObject().apply {
            put("success", false)
            put("error", "All TTS engines failed")
        }
    }

    // ── Sherpa-ONNX ──────────────────────────────────────────────────────────

    @Suppress("UNUSED_PARAMETER")
    private suspend fun trySherpa(
        text: String, langCode: String, speed: Float, pitch: Float,
        volume: Float, isVerse: Boolean
    ): JSONObject? {
        if (!isSherpaModelAvailable(langCode)) {
            Log.d(TAG, "Sherpa model not available for $langCode")
            return null
        }
        // TODO: Implement Sherpa-ONNX inference once model is downloaded.
        // Will integrate com.k2fsa.sherpa:onnx AAR in a future release.
        return null
    }

    // ── System TTS ───────────────────────────────────────────────────────────

    private suspend fun trySystemTts(
        text: String, langCode: String, gender: String, speed: Float, pitch: Float
    ): JSONObject = withContext(Dispatchers.IO) {
        val engine = getSystemTts()
        if (!engine.isLanguageAvailable(langCode)) {
            return@withContext JSONObject().apply {
                put("success", false)
                put("error", "$langCode not available in System TTS")
            }
        }

        val outFile = File(context.cacheDir, "tts_system_${System.currentTimeMillis()}.wav")
        val path = engine.synthesize(
            text = text,
            langCode = langCode,
            gender = gender,
            speed = speed,
            pitch = pitch,
            outputFile = outFile
        )
        JSONObject().apply {
            put("success", true)
            put("audio_path", path)
            put("engine", "system_tts")
        }
    }

    // ── gTTS (via Python bridge) ─────────────────────────────────────────────

    private suspend fun tryGtts(
        text: String, langCode: String, gender: String, speed: Float, pitch: Float, volume: Float,
        emotion: String?, isVerse: Boolean, emotionIntensity: Float = 1.0f,
        accent: String = "standard"
    ): JSONObject = withContext(Dispatchers.IO) {
        PythonBridge.init(context)
        val kwargs = mutableMapOf<String, Any?>(
            "text" to text,
            "language" to langCode,
            "gender" to gender,
            "speed" to speed.toDouble(),
            "pitch" to pitch.toDouble(),
            "volume" to volume.toDouble(),
            "is_verse" to isVerse,
            "emotion_intensity" to emotionIntensity.toDouble(),
            "accent" to accent
        )
        if (emotion != null) kwargs["emotion"] = emotion
        val result = PythonBridge.call("tts_bridge", "generate_tts", kwargs = kwargs)
        // Normalise engine name
        if (PythonBridge.isSuccess(result) && !result.has("engine")) {
            result.put("engine", "gtts")
        }
        result
    }

    fun shutdown() {
        systemTts?.shutdown()
        systemTts = null
    }
}
