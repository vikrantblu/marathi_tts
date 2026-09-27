package com.marathitts.mobile.service

import android.content.Context
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.io.File
import java.util.Locale
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Wraps Android's built-in [TextToSpeech] engine.
 * Works offline if the user has downloaded the language pack (Google TTS usually has Marathi/Hindi).
 */
class SystemTtsEngine(context: Context) {

    companion object {
        private const val TAG = "SystemTtsEngine"
        val SUPPORTED_LOCALES = mapOf(
            "mr" to Locale("mr", "IN"),
            "hi" to Locale("hi", "IN"),
            "sa" to Locale("sa", "IN"),
            "en" to Locale.US
        )
    }

    private var tts: TextToSpeech? = null
    private var ready = false
    private val appContext = context.applicationContext

    // Android TTS supports only ONE UtteranceProgressListener at a time.
    // Concurrent synthesize() calls overwrite each other's listeners,
    // causing continuations to never resume (30s timeout). Mutex serializes access.
    private val synthMutex = Mutex()

    /** Initialise lazily; returns true when engine is ready. */
    suspend fun init(): Boolean = suspendCancellableCoroutine { cont ->
        if (ready && tts != null) {
            cont.resume(true)
            return@suspendCancellableCoroutine
        }
        tts = TextToSpeech(appContext) { status ->
            ready = status == TextToSpeech.SUCCESS
            Log.i(TAG, "TextToSpeech init status=$status ready=$ready")
            if (cont.isActive) cont.resume(ready)
        }
    }

    /** Check if a language is available. Call after [init]. */
    fun isLanguageAvailable(langCode: String): Boolean {
        val locale = SUPPORTED_LOCALES[langCode] ?: return false
        val result = tts?.isLanguageAvailable(locale) ?: TextToSpeech.LANG_NOT_SUPPORTED
        return result >= TextToSpeech.LANG_AVAILABLE
    }

    /** Returns list of language codes that are currently available on the device. */
    fun availableLanguages(): List<String> =
        SUPPORTED_LOCALES.keys.filter { isLanguageAvailable(it) }

    /**
     * Synthesize [text] to a .wav file. Returns the file path, or throws on failure.
     *
     * @param langCode  one of "mr", "hi", "sa", "en"
     * @param gender    "female" (default) or "male" — lowers pitch for male
     * @param speed     speech rate (1.0 = normal)
     * @param pitch     pitch multiplier (1.0 = normal)
     */
    suspend fun synthesize(
        text: String,
        langCode: String = "mr",
        gender: String = "female",
        speed: Float = 1.0f,
        pitch: Float = 1.0f,
        outputFile: File
    ): String = synthMutex.withLock {
        // Mutex ensures only ONE synthesize() call uses the UtteranceProgressListener
        // at a time. Without this, concurrent streaming chunks overwrite each other's
        // listeners and continuations never resume (30s timeout → streaming hangs).
        suspendCancellableCoroutine { cont ->
            val engine = tts ?: run {
                cont.resumeWithException(IllegalStateException("TTS not initialised"))
                return@suspendCancellableCoroutine
            }

            val locale = SUPPORTED_LOCALES[langCode]
                ?: run {
                    cont.resumeWithException(IllegalArgumentException("Unsupported language: $langCode"))
                    return@suspendCancellableCoroutine
                }

            // Try to select a voice matching the requested gender via Android Voice API
            val selectedVoice = try {
                val allVoices = engine.voices?.filter { v ->
                    v.locale.language == locale.language && v.locale.country == locale.country
                } ?: emptySet()
                Log.i(TAG, "Available voices for $locale: ${allVoices.map { "${it.name} (net=${it.isNetworkConnectionRequired})" }}")

                val offlineVoices = allVoices.filter { !it.isNetworkConnectionRequired }
                val voicePool = offlineVoices.ifEmpty { allVoices }

                // Try to match gender by name pattern (Google voices often contain gender hints)
                val genderMatched = voicePool.filter { v ->
                    val name = v.name.lowercase()
                    if (gender == "male") {
                        name.contains("male") || name.contains("madhur") || name.contains("-b") || name.contains("-d")
                    } else {
                        name.contains("female") || name.contains("swara") || name.contains("-a") || name.contains("-c")
                    }
                }
                genderMatched.firstOrNull() ?: voicePool.firstOrNull()
            } catch (e: Exception) {
                Log.w(TAG, "Voice enumeration failed: ${e.message}")
                null
            }
            if (selectedVoice != null) {
                engine.voice = selectedVoice
                Log.i(TAG, "Selected voice: ${selectedVoice.name} for gender=$gender locale=$locale")
            } else {
                engine.language = locale
                Log.i(TAG, "No specific voice found, using default for locale=$locale")
            }

            // Slight pitch adjustment as additional gender differentiation
            val effectivePitch = if (gender == "male") pitch * 0.88f else pitch

            engine.setSpeechRate(speed)
            engine.setPitch(effectivePitch)

            val utteranceId = "tts_${System.currentTimeMillis()}"

            engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(id: String?) {}
                override fun onDone(id: String?) {
                    if (id == utteranceId && cont.isActive) {
                        Log.i(TAG, "Synthesis complete -> ${outputFile.absolutePath}")
                        cont.resume(outputFile.absolutePath)
                    }
                }
                @Suppress("DEPRECATION")
                override fun onError(id: String?) {
                    onError(id, TextToSpeech.ERROR)
                }
                override fun onError(id: String?, errorCode: Int) {
                    if (id == utteranceId && cont.isActive) {
                        cont.resumeWithException(RuntimeException("System TTS error code=$errorCode"))
                    }
                }
            })

            val params = Bundle().apply {
                putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, utteranceId)
            }

            val result = engine.synthesizeToFile(text, params, outputFile, utteranceId)
            if (result != TextToSpeech.SUCCESS && cont.isActive) {
                cont.resumeWithException(RuntimeException("synthesizeToFile returned error=$result"))
            }

            cont.invokeOnCancellation {
                engine.stop()
            }
        }
    }

    fun shutdown() {
        tts?.shutdown()
        tts = null
        ready = false
    }
}
