package com.marathitts.mobile.ui.tts

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.PythonBridge
import com.marathitts.mobile.service.TtsEngineManager
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicInteger

data class TtsState(
    val isLoading: Boolean = false,
    val audioPath: String? = null,
    /** Non-empty when the last request was a streaming (chunked) generation. */
    val streamChunks: List<String> = emptyList(),
    val engine: String = "",
    val error: String? = null,
    val status: String = "Ready"
)

/** Minimum text length (chars) to trigger streaming / parallel chunk generation. */
private const val STREAMING_THRESHOLD = 250

class TtsViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableLiveData(TtsState())
    val state: LiveData<TtsState> get() = _state

    val engineManager = TtsEngineManager(app)

    /** Reference to the current streaming job so it can be cancelled. */
    private var currentJob: Job? = null

    /** Max concurrent TTS API calls during streaming (prevents rate-limiting). */
    private val streamingSemaphore = Semaphore(3)

    init {
        PythonBridge.init(app)
    }

    /** Cancel an in-progress streaming generation. */
    fun cancelGeneration() {
        currentJob?.cancel()
        currentJob = null
        _state.value = TtsState(status = "Generation cancelled")
    }

    fun generateAudio(
        text: String,
        engineIndex: Int = TtsEngineManager.ENGINE_AUTO,
        langCode: String = "mr",
        gender: String = "female",
        speed: Float = 1.0f,
        pitch: Float = 1.0f,
        volume: Float = 1.0f,
        emotion: String? = null,
        isVerse: Boolean = false,
        autoDetect: Boolean = false
    ) {
        // Route long Marathi texts to streaming
        if (langCode == "mr" && !isVerse && text.length > STREAMING_THRESHOLD) {
            generateAudioStreaming(text, engineIndex, langCode, gender,
                                   speed, pitch, volume, emotion, autoDetect)
            return
        }

        _state.value = TtsState(isLoading = true, status = "Generating audio…")
        viewModelScope.launch {
            // Step 1: optionally auto-detect emotion
            val resolvedEmotion: String? = if (autoDetect && emotion == null) {
                withContext(Dispatchers.IO) {
                    try {
                        val emoResult = PythonBridge.call(
                            "emotion_bridge", "analyze_emotion",
                            kwargs = mapOf("text" to text)
                        )
                        if (PythonBridge.isSuccess(emoResult))
                            emoResult.optString("emotion").takeIf { it.isNotEmpty() }
                        else null
                    } catch (_: Exception) { null }
                }
            } else emotion

            // Step 2: generate TTS via selected engine
            val result: JSONObject = engineManager.generate(
                text = text,
                engineIndex = engineIndex,
                langCode = langCode,
                gender = gender,
                speed = speed,
                pitch = pitch,
                volume = volume,
                emotion = resolvedEmotion,
                isVerse = isVerse
            )

            if (result.optBoolean("success", false)) {
                val engineUsed = result.optString("engine", "")
                val statusMsg = buildString {
                    append("Audio generated ✓")
                    if (engineUsed.isNotEmpty()) append("  |  Engine: $engineUsed")
                    if (autoDetect && resolvedEmotion != null) append("  |  Emotion: $resolvedEmotion")
                }
                _state.value = TtsState(
                    audioPath = result.optString("audio_path"),
                    engine = engineUsed,
                    status = statusMsg
                )
            } else {
                _state.value = TtsState(
                    error = result.optString("error", "TTS failed"),
                    status = "Error: ${result.optString("error", "TTS failed")}"
                )
            }
        }
    }

    /**
     * Streaming TTS: splits [text] into sentence-level chunks and generates all
     * chunks **in parallel** on IO threads.  The resulting [TtsState.streamChunks]
     * list is set once all chunks are ready so the Fragment can call
     * [com.marathitts.mobile.service.AudioPlayerService.playQueueAsync] immediately.
     *
     * Voice-consistency guarantee: the first chunk is generated with the
     * requested [engineIndex].  Whichever engine actually succeeds is then
     * locked-in for every remaining chunk so that the same voice is heard
     * throughout (no System-TTS / gTTS mix).
     *
     * Total latency ≈ first-chunk time + max(remaining-chunk times).
     */
    fun generateAudioStreaming(
        text: String,
        engineIndex: Int = TtsEngineManager.ENGINE_AUTO,
        langCode: String = "mr",
        gender: String = "female",
        speed: Float = 1.0f,
        pitch: Float = 1.0f,
        volume: Float = 1.0f,
        emotion: String? = null,
        autoDetect: Boolean = false
    ) {
        val sentences = splitSentences(text)
        if (sentences.size <= 1) {
            generateAudio(text, engineIndex, langCode, gender, speed, pitch, volume, emotion,
                          isVerse = false, autoDetect = autoDetect)
            return
        }

        _state.value = TtsState(isLoading = true,
            status = "Streaming: preparing ${sentences.size} chunks…")

        currentJob = viewModelScope.launch {
            // Optional emotion auto-detect on full text
            val resolvedEmotion: String? = if (autoDetect && emotion == null) {
                withContext(Dispatchers.IO) {
                    try {
                        val emoResult = PythonBridge.call(
                            "emotion_bridge", "analyze_emotion",
                            kwargs = mapOf("text" to text)
                        )
                        if (PythonBridge.isSuccess(emoResult))
                            emoResult.optString("emotion").takeIf { it.isNotEmpty() }
                        else null
                    } catch (_: Exception) { null }
                }
            } else emotion

            // ── Step 1: generate first chunk to determine the winning engine ──
            val firstResult = withContext(Dispatchers.IO) {
                engineManager.generate(
                    text = sentences.first(),
                    engineIndex = engineIndex,
                    langCode = langCode,
                    gender = gender,
                    speed = speed,
                    pitch = pitch,
                    volume = volume,
                    emotion = resolvedEmotion,
                    isVerse = false
                )
            }

            val firstPath = if (firstResult.optBoolean("success", false))
                firstResult.optString("audio_path").takeIf { it.isNotEmpty() }
            else null

            // Map the engine name that won to an engineIndex for remaining chunks.
            // This ensures EVERY chunk uses the SAME voice.
            val lockedEngine: Int = when {
                firstResult.optString("engine", "").startsWith("system") ->
                    TtsEngineManager.ENGINE_SYSTEM
                firstResult.optString("engine", "").contains("gtts") ||
                firstResult.optString("engine", "").contains("edge") ->
                    TtsEngineManager.ENGINE_GTTS
                else -> engineIndex   // keep original if we can't determine
            }

            val completedCount = AtomicInteger(1)  // first chunk already done
            _state.postValue(_state.value?.copy(
                status = "Streaming: 1 of ${sentences.size} ✓"))

            // ── Step 2: generate remaining chunks with concurrency limit ──
            // Semaphore limits to 3 concurrent API calls to avoid rate-limiting.
            val remainingDeferreds: List<Deferred<String?>> =
                sentences.drop(1).mapIndexed { _, chunk ->
                    async(Dispatchers.IO) {
                        streamingSemaphore.withPermit {
                            try {
                                val r = engineManager.generate(
                                    text = chunk,
                                    engineIndex = lockedEngine,
                                    langCode = langCode,
                                    gender = gender,
                                    speed = speed,
                                    pitch = pitch,
                                    volume = volume,
                                    emotion = resolvedEmotion,
                                    isVerse = false
                                )
                                if (r.optBoolean("success", false))
                                    r.optString("audio_path").takeIf { it.isNotEmpty() }
                                else null
                            } catch (_: Exception) { null }
                        }
                    }
                }

            // Await all remaining in ORDER (preserves sentence sequence)
            val remainingPaths = remainingDeferreds.mapIndexed { _, d ->
                d.await().also {
                    val done = completedCount.incrementAndGet()
                    _state.postValue(_state.value?.copy(
                        status = "Streaming: $done of ${sentences.size} ✓"))
                }
            }.filterNotNull()

            // Combine: first chunk path + remaining paths
            val paths = listOfNotNull(firstPath) + remainingPaths

            if (paths.isEmpty()) {
                _state.value = TtsState(
                    error = "Streaming TTS failed: no chunks generated",
                    status = "Error: streaming failed"
                )
            } else {
                val emotionLabel = if (autoDetect && resolvedEmotion != null)
                    "  |  Emotion: $resolvedEmotion" else ""
                _state.value = TtsState(
                    audioPath = paths.first(),
                    streamChunks = paths,
                    engine = "gtts_stream",
                    status = "All ${paths.size} chunks ready ✓$emotionLabel"
                )
            }
            currentJob = null
        }
    }

    /** Split Marathi text into sentence-level chunks at ।, ॥, and Latin punctuation. */
    private fun splitSentences(text: String): List<String> {
        // Split on Devanagari danda/double-danda and common sentence-end characters
        val raw = text.split(Regex("(?<=[।॥?!])\\s*|(?<=[.;])\\s+"))
            .map { it.trim() }
            .filter { it.isNotBlank() }
        if (raw.isEmpty()) return listOf(text)

        // Merge very short fragments (< 20 chars) with the next chunk to avoid tiny audio files
        val merged = mutableListOf<String>()
        val buf = StringBuilder()
        for (s in raw) {
            buf.append(if (buf.isEmpty()) s else " $s")
            if (buf.length >= 40) {
                merged.add(buf.toString())
                buf.clear()
            }
        }
        if (buf.isNotEmpty()) {
            if (merged.isNotEmpty() && buf.length < 40)
                merged[merged.lastIndex] = "${merged.last()} $buf"
            else
                merged.add(buf.toString())
        }
        return merged.ifEmpty { listOf(text) }
    }

    override fun onCleared() {
        super.onCleared()
        currentJob?.cancel()
        engineManager.shutdown()
    }
}
