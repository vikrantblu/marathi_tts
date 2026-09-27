package com.marathitts.mobile.ui.output

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.PythonBridge
import com.marathitts.mobile.service.TtsEngineManager
import com.marathitts.mobile.util.AppPreferences
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import java.io.File
import java.util.concurrent.atomic.AtomicInteger

data class OutputState(
    val isLoading: Boolean = false,
    val inputText: String = "",
    val sentences: List<String> = emptyList(),
    val audioPath: String? = null,
    val streamChunks: List<String> = emptyList(),
    val chunkSentenceMap: List<Int> = emptyList(),
    val engine: String = "",
    val error: String? = null,
    val status: String = "",
    val activePlayingIndex: Int = -1,
    val gender: String = "female",
    val autoPlayPending: Boolean = false
)

private const val STREAMING_THRESHOLD = 250

/**
 * Activity-scoped ViewModel for TTS generation.
 * Manages audio generation (single + streaming) and tracks state
 * for the Output tab's sentence-level playback highlighting.
 */
class OutputViewModel(app: Application) : AndroidViewModel(app) {

    companion object {
        private const val TAG = "OutputViewModel"
    }

    private val _state = MutableLiveData(OutputState())
    val state: LiveData<OutputState> get() = _state

    val engineManager = TtsEngineManager(app)
    private var currentJob: Job? = null
    private val streamingSemaphore = Semaphore(3)

    init {
        PythonBridge.init(app)
    }

    // ── Engine selection ───────────────────────────────────────────────

    private fun resolveEngineIndex(): Int {
        val ctx = getApplication<Application>()
        val userChoice = AppPreferences.getDefaultEngine(ctx)
        if (userChoice != "auto") {
            return when (userChoice) {
                "edge-tts" -> TtsEngineManager.ENGINE_GTTS
                "gtts" -> TtsEngineManager.ENGINE_GTTS
                "native" -> TtsEngineManager.ENGINE_SYSTEM
                else -> TtsEngineManager.ENGINE_AUTO
            }
        }
        val learned = AppPreferences.getLearnedPreferredEngine(ctx)
        return when (learned) {
            "system_tts" -> TtsEngineManager.ENGINE_SYSTEM
            "sherpa" -> TtsEngineManager.ENGINE_SHERPA
            else -> TtsEngineManager.ENGINE_AUTO
        }
    }

    private fun recordSuccess(engineName: String) {
        AppPreferences.recordEngineSuccess(getApplication(), engineName)
    }

    // ── Public API ─────────────────────────────────────────────────────

    /**
     * Called by InputFragment when user taps Generate.
     * Cancels any in-progress generation and starts fresh.
     */
    fun requestGeneration(text: String, langCode: String, isVerse: Boolean, gender: String) {
        // Cancel any previous generation
        currentJob?.cancel()
        currentJob = null

        val sentences = splitSentences(text)
        Log.i(TAG, "requestGeneration: len=${text.length} lang=$langCode verse=$isVerse " +
                "sentences=${sentences.size}")

        _state.value = OutputState(
            isLoading = true,
            inputText = text,
            sentences = sentences,
            gender = gender,
            status = "Generating audio\u2026"
        )

        if (langCode == "mr" && !isVerse && text.length > STREAMING_THRESHOLD) {
            generateStreaming(text, langCode, gender)
        } else {
            generateSingle(text, langCode, isVerse, gender)
        }
    }

    fun cancelGeneration() {
        currentJob?.cancel()
        currentJob = null
        _state.value = _state.value?.copy(isLoading = false, status = "Cancelled")
    }

    fun setActivePlayingIndex(index: Int) {
        _state.value = _state.value?.copy(activePlayingIndex = index)
    }

    fun consumeAutoPlay() {
        _state.value = _state.value?.copy(autoPlayPending = false)
    }

    // ── Single generation ──────────────────────────────────────────────

    private fun generateSingle(text: String, langCode: String, isVerse: Boolean, gender: String) {
        currentJob = viewModelScope.launch {
            try {
                val emotion = detectEmotion(text)
                val result = engineManager.generate(
                    text = text,
                    engineIndex = resolveEngineIndex(),
                    langCode = langCode,
                    gender = gender,
                    isVerse = isVerse,
                    emotion = emotion
                )

                if (result.optBoolean("success", false)) {
                    val engineUsed = result.optString("engine", "")
                    val audioPath = result.optString("audio_path")
                    Log.i(TAG, "generateSingle SUCCESS: engine=$engineUsed")
                    recordSuccess(engineUsed)
                    _state.value = (_state.value ?: OutputState()).copy(
                        isLoading = false,
                        audioPath = audioPath,
                        engine = engineUsed,
                        status = "Ready \u2713",
                        error = null,
                        autoPlayPending = true
                    )
                } else {
                    val errMsg = result.optString("error", "TTS failed")
                    Log.e(TAG, "generateSingle FAILED: $errMsg")
                    _state.value = (_state.value ?: OutputState()).copy(
                        isLoading = false,
                        error = errMsg,
                        status = "Error"
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "generateSingle exception", e)
                _state.value = (_state.value ?: OutputState()).copy(
                    isLoading = false,
                    error = "Generation failed: ${e.message}",
                    status = "Error"
                )
            } finally {
                currentJob = null
            }
        }
    }

    // ── Streaming generation ───────────────────────────────────────────

    private fun generateStreaming(text: String, langCode: String, gender: String) {
        val sentences = _state.value?.sentences ?: splitSentences(text)
        if (sentences.size <= 1) {
            generateSingle(text, langCode, isVerse = false, gender = gender)
            return
        }

        currentJob = viewModelScope.launch {
            try {
                val emotion = detectEmotion(text)
                val chunkTimeoutMs = 30_000L

                // First chunk — determines engine
                val firstResult = withContext(Dispatchers.IO) {
                    withTimeoutOrNull(chunkTimeoutMs) {
                        engineManager.generate(
                            text = sentences.first(),
                            engineIndex = resolveEngineIndex(),
                            langCode = langCode,
                            gender = gender,
                            emotion = emotion,
                            isStreamingChunk = true
                        )
                    }
                }

                val firstPath = firstResult
                    ?.takeIf { it.optBoolean("success", false) }
                    ?.optString("audio_path")
                    ?.takeIf { it.isNotEmpty() && File(it).exists() }

                if (firstPath == null) {
                    Log.e(TAG, "Streaming: first chunk failed")
                    _state.value = (_state.value ?: OutputState()).copy(
                        isLoading = false,
                        error = "First chunk failed — try again",
                        status = "Error"
                    )
                    return@launch
                }

                val lockedEngine = when {
                    firstResult!!.optString("engine", "").startsWith("system") ->
                        TtsEngineManager.ENGINE_SYSTEM
                    firstResult.optString("engine", "").let {
                        it.contains("gtts") || it.contains("edge")
                    } -> TtsEngineManager.ENGINE_GTTS
                    else -> TtsEngineManager.ENGINE_AUTO
                }
                val firstEngine = firstResult.optString("engine", "")
                if (firstEngine.isNotEmpty()) recordSuccess(firstEngine)

                val allPaths = mutableListOf(firstPath)
                val sentenceMap = mutableListOf(0) // chunk 0 → sentence 0

                // ★ Start playback immediately — don't wait for all chunks
                _state.value = (_state.value ?: OutputState()).copy(
                    isLoading = true,
                    streamChunks = allPaths.toList(),
                    chunkSentenceMap = sentenceMap.toList(),
                    status = "Streaming: 1 of ${sentences.size} \u2713",
                    error = null,
                    autoPlayPending = true
                )

                // Remaining chunks — parallel with semaphore
                val completedCount = AtomicInteger(1)

                val deferreds: List<Deferred<Pair<Int, String?>>> =
                    sentences.drop(1).mapIndexed { idx, chunk ->
                        val sentenceIdx = idx + 1
                        async(Dispatchers.IO) {
                            streamingSemaphore.withPermit {
                                try {
                                    val path = withTimeoutOrNull(chunkTimeoutMs) {
                                        val r = engineManager.generate(
                                            text = chunk,
                                            engineIndex = lockedEngine,
                                            langCode = langCode,
                                            gender = gender,
                                            emotion = emotion,
                                            isStreamingChunk = true
                                        )
                                        if (r.optBoolean("success", false))
                                            r.optString("audio_path")
                                                .takeIf { it.isNotEmpty() && File(it).exists() }
                                        else null
                                    }
                                    sentenceIdx to path
                                } catch (e: Exception) {
                                    Log.w(TAG, "Chunk $sentenceIdx exception: ${e.message}")
                                    sentenceIdx to null
                                }
                            }
                        }
                    }

                for (d in deferreds) {
                    val (sentenceIdx, path) = d.await()
                    val done = completedCount.incrementAndGet()
                    if (path != null) {
                        allPaths.add(path)
                        sentenceMap.add(sentenceIdx)
                    }
                    _state.value = _state.value?.copy(
                        streamChunks = allPaths.toList(),
                        chunkSentenceMap = sentenceMap.toList(),
                        status = "Streaming: $done of ${sentences.size} \u2713"
                    )
                }

                Log.i(TAG, "Streaming DONE: ${allPaths.size}/${sentences.size} chunks")

                _state.value = (_state.value ?: OutputState()).copy(
                    isLoading = false,
                    audioPath = allPaths.firstOrNull(),
                    streamChunks = allPaths.toList(),
                    chunkSentenceMap = sentenceMap.toList(),
                    engine = "stream ($firstEngine)",
                    status = "All ${allPaths.size} chunks ready \u2713",
                    error = null
                )
            } catch (e: Exception) {
                Log.e(TAG, "generateStreaming exception", e)
                _state.value = (_state.value ?: OutputState()).copy(
                    isLoading = false,
                    error = "Streaming failed: ${e.message}",
                    status = "Error"
                )
            } finally {
                currentJob = null
            }
        }
    }

    // ── Helpers ─────────────────────────────────────────────────────────

    private suspend fun detectEmotion(text: String): String? {
        return withContext(Dispatchers.IO) {
            try {
                val result = PythonBridge.call(
                    "emotion_bridge", "analyze_emotion",
                    kwargs = mapOf("text" to text)
                )
                if (PythonBridge.isSuccess(result))
                    result.optString("emotion").takeIf { it.isNotEmpty() }
                else null
            } catch (_: Exception) { null }
        }
    }

    fun splitSentences(text: String): List<String> {
        val raw = text.split(Regex("(?<=[।॥?!.;])\\s*"))
            .map { it.trim() }
            .filter { it.isNotBlank() }
        if (raw.isEmpty()) return listOf(text)

        val parts = if (raw.size == 1 && text.length > STREAMING_THRESHOLD) {
            text.split(Regex("[,，]\\ *|\\n+"))
                .map { it.trim() }
                .filter { it.isNotBlank() }
                .ifEmpty { raw }
        } else {
            raw
        }

        val merged = mutableListOf<String>()
        val buf = StringBuilder()
        for (s in parts) {
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
