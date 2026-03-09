package com.marathitts.mobile.ui.output

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.data.AppDatabase
import com.marathitts.mobile.data.PhoneticCorrection
import com.marathitts.mobile.service.PythonBridge
import com.marathitts.mobile.service.TtsEngineManager
import com.marathitts.mobile.util.AppPreferences
import com.marathitts.mobile.util.PhoneticCorrectionSync
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

data class OutputState(
    val isLoading: Boolean = false,
    val audioPath: String? = null,
    val streamChunks: List<String> = emptyList(),
    val engine: String = "",
    val error: String? = null,
    val status: String = "",
    val emotionLabel: String? = null,
    val emotionScore: Float = 0f,
    val emotionIntensity: Float = 0.5f,
    val accent: String = "standard",
    val gender: String = "female",
    val prosodySegments: List<ProsodySegment> = emptyList(),
    val isVerseDetected: Boolean = false,
    val detectedMetre: String = "",
    val regeneratingIndex: Int = -1,
    val activePlayingIndex: Int = -1
)

private const val STREAMING_THRESHOLD = 250

class OutputViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableLiveData(OutputState())
    val state: LiveData<OutputState> get() = _state

    val engineManager = TtsEngineManager(app)
    private var currentJob: Job? = null
    private val streamingSemaphore = Semaphore(3)
    private var hasStartedGeneration = false

    init {
        PythonBridge.init(app)
    }

    /**
     * Resolve which engine index to use based on user setting + learned preference.
     * If user chose "auto" and we've learned a preferred engine, use that.
     */
    private fun resolveEngineIndex(): Int {
        val ctx = getApplication<Application>()
        val userChoice = AppPreferences.getDefaultEngine(ctx)
        if (userChoice != "auto") {
            return when (userChoice) {
                "edge-tts" -> TtsEngineManager.ENGINE_GTTS  // gTTS bridge handles edge-tts
                "gtts" -> TtsEngineManager.ENGINE_GTTS
                "native" -> TtsEngineManager.ENGINE_SYSTEM
                else -> TtsEngineManager.ENGINE_AUTO
            }
        }
        // Auto mode — check learned preference
        val learned = AppPreferences.getLearnedPreferredEngine(ctx)
        return when (learned) {
            "system_tts" -> TtsEngineManager.ENGINE_SYSTEM
            "sherpa" -> TtsEngineManager.ENGINE_SHERPA
            else -> TtsEngineManager.ENGINE_AUTO  // gtts/edge → let Auto handle
        }
    }

    private fun recordSuccess(engineName: String) {
        AppPreferences.recordEngineSuccess(getApplication(), engineName)
    }

    fun cancelGeneration() {
        currentJob?.cancel()
        currentJob = null
        hasStartedGeneration = false
        _state.value = _state.value?.copy(isLoading = false, status = "Cancelled")
    }

    /** FEAT-54: Update emotion intensity from the UI slider. */
    fun setEmotionIntensity(intensity: Float) {
        _state.value = _state.value?.copy(emotionIntensity = intensity.coerceIn(0f, 1f))
    }

    /** FEAT-57: Update accent profile. */
    fun setAccent(accent: String) {
        _state.value = _state.value?.copy(accent = accent)
    }

    /** FEAT-74: Update voice gender. */
    fun setGender(gender: String) {
        _state.value = _state.value?.copy(gender = gender)
    }

    /** FEAT-75: Update the currently playing segment index for playback highlighting. */
    fun setActivePlayingIndex(index: Int) {
        _state.value = _state.value?.copy(activePlayingIndex = index)
    }

    /**
     * Entry point — called by OutputFragment when it receives arguments.
     * Auto-routes to streaming for long Marathi prose.
     */
    fun generate(text: String, langCode: String, isVerse: Boolean) {
        if (hasStartedGeneration) return
        hasStartedGeneration = true

        // FEAT-51: launch prosody analysis concurrently (fast, no network)
        val emotion = null // will be detected below; prosody starts with neutral
        analyzeProsody(text, langCode, isVerse, emotion)

        if (langCode == "mr" && !isVerse && text.length > STREAMING_THRESHOLD) {
            generateStreaming(text, langCode)
        } else {
            generateSingle(text, langCode, isVerse)
        }
    }

    private fun generateSingle(text: String, langCode: String, isVerse: Boolean) {
        _state.value = OutputState(isLoading = true, status = "Generating audio…")

        currentJob = viewModelScope.launch {
            try {
                // Auto-detect emotion
                val emotion = detectEmotion(text)
                val intensity = _state.value?.emotionIntensity ?: 0.5f
                val accent = _state.value?.accent ?: "standard"

                val gender = _state.value?.gender ?: "female"
                val result = engineManager.generate(
                    text = text,
                    engineIndex = resolveEngineIndex(),
                    langCode = langCode,
                    gender = gender,
                    isVerse = isVerse,
                    emotion = emotion,
                    emotionIntensity = intensity,
                    accent = accent
                )

                if (result.optBoolean("success", false)) {
                    val engineUsed = result.optString("engine", "")
                    recordSuccess(engineUsed)
                    _state.value = OutputState(
                        audioPath = result.optString("audio_path"),
                        engine = engineUsed,
                        status = "Audio ready ✓",
                        emotionLabel = emotion,
                        emotionScore = 0f
                    )
                } else {
                    _state.value = OutputState(
                        error = result.optString("error", "TTS failed"),
                        status = "Error: ${result.optString("error", "TTS failed")}"
                    )
                }
            } finally {
                hasStartedGeneration = false
                currentJob = null
            }
        }
    }

    private fun generateStreaming(text: String, langCode: String) {
        val sentences = splitSentences(text)
        if (sentences.size <= 1) {
            generateSingle(text, langCode, isVerse = false)
            return
        }

        _state.value = OutputState(
            isLoading = true,
            status = "Streaming: preparing ${sentences.size} chunks…"
        )

        currentJob = viewModelScope.launch {
            try {
                val emotion = detectEmotion(text)
                val intensity = _state.value?.emotionIntensity ?: 0.5f
                val accent = _state.value?.accent ?: "standard"

                val gender = _state.value?.gender ?: "female"
                // First chunk — determines which engine to lock
                val firstResult = withContext(Dispatchers.IO) {
                    engineManager.generate(
                    text = sentences.first(),
                    engineIndex = resolveEngineIndex(),
                    langCode = langCode,
                    gender = gender,
                    emotion = emotion,
                    emotionIntensity = intensity,
                    accent = accent
                )
            }

            val firstPath = if (firstResult.optBoolean("success", false))
                firstResult.optString("audio_path").takeIf { it.isNotEmpty() }
            else null

            val lockedEngine = when {
                firstResult.optString("engine", "").startsWith("system") ->
                    TtsEngineManager.ENGINE_SYSTEM
                firstResult.optString("engine", "").contains("gtts") ||
                firstResult.optString("engine", "").contains("edge") ->
                    TtsEngineManager.ENGINE_GTTS
                else -> TtsEngineManager.ENGINE_AUTO
            }

            val completedCount = AtomicInteger(1)
            _state.postValue(_state.value?.copy(
                status = "Streaming: 1 of ${sentences.size} ✓"
            ))

            val remainingDeferreds: List<Deferred<String?>> =
                sentences.drop(1).map { chunk ->
                    async(Dispatchers.IO) {
                        streamingSemaphore.withPermit {
                            try {
                                val r = engineManager.generate(
                                    text = chunk,
                                    engineIndex = lockedEngine,
                                    langCode = langCode,
                                    gender = gender,
                                    emotion = emotion,
                                    emotionIntensity = intensity,
                                    accent = accent
                                )
                                if (r.optBoolean("success", false))
                                    r.optString("audio_path").takeIf { it.isNotEmpty() }
                                else null
                            } catch (_: Exception) { null }
                        }
                    }
                }

            val remainingPaths = remainingDeferreds.map { d ->
                d.await().also {
                    val done = completedCount.incrementAndGet()
                    _state.postValue(_state.value?.copy(
                        status = "Streaming: $done of ${sentences.size} ✓"
                    ))
                }
            }.filterNotNull()

            val paths = listOfNotNull(firstPath) + remainingPaths

            if (paths.isEmpty()) {
                _state.value = OutputState(
                    error = "Streaming TTS failed",
                    status = "Error: streaming failed"
                )
            } else {
                // Record the engine that worked for the first chunk
                val firstEngine = firstResult.optString("engine", "")
                if (firstEngine.isNotEmpty()) recordSuccess(firstEngine)
                _state.value = OutputState(
                    audioPath = paths.first(),
                    streamChunks = paths,
                    engine = "stream",
                    status = "All ${paths.size} chunks ready ✓",
                    emotionLabel = emotion
                )
            }
            } finally {
                hasStartedGeneration = false
                currentJob = null
            }
        }
    }

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

    private fun splitSentences(text: String): List<String> {
        // Split on Devanagari punctuation (danda, double-danda) and ASCII
        // sentence-ending marks. Allow zero or more trailing whitespace.
        val raw = text.split(Regex("(?<=[।॥?!.;])\\s*"))
            .map { it.trim() }
            .filter { it.isNotBlank() }
        if (raw.isEmpty()) return listOf(text)

        // If no splits found (e.g. long prose without punctuation), force-split
        // by comma or newline boundaries as a fallback
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

    // -----------------------------------------------------------------
    // FEAT-51: Prosody analysis (runs before/during generation)
    // -----------------------------------------------------------------

    /**
     * Analyze prosody segments for the given text.
     * Called automatically at the start of generate(); results are fast
     * (pure text analysis, no network) so they appear before audio is ready.
     */
    fun analyzeProsody(text: String, language: String, isVerse: Boolean, emotion: String?) {
        viewModelScope.launch {
            val intensity = _state.value?.emotionIntensity ?: 0.5f
            val segments = withContext(Dispatchers.IO) {
                try {
                    val result = PythonBridge.call(
                        "tts_bridge", "analyze_prosody",
                        kwargs = mapOf(
                            "text" to text,
                            "language" to language,
                            "is_verse" to isVerse,
                            "emotion" to emotion,
                            "emotion_intensity" to intensity.toDouble()
                        )
                    )
                    if (PythonBridge.isSuccess(result)) {
                        parseProsodySegments(result)
                    } else null
                } catch (_: Exception) { null }
            } ?: return@launch

            _state.value = _state.value?.copy(
                prosodySegments = segments.first,
                isVerseDetected = segments.second,
                detectedMetre = segments.third
            )
        }
    }

    private fun parseProsodySegments(json: JSONObject): Triple<List<ProsodySegment>, Boolean, String> {
        val arr = json.optJSONArray("segments") ?: return Triple(emptyList(), false, "")
        val segments = mutableListOf<ProsodySegment>()
        for (i in 0 until arr.length()) {
            val s = arr.getJSONObject(i)
            segments.add(ProsodySegment(
                index = s.optInt("index", i),
                text = s.optString("text", ""),
                pauseAfterMs = s.optInt("pause_after_ms", 0),
                emotion = s.optString("emotion", "neutral"),
                emphasis = s.optDouble("emphasis", 1.0).toFloat(),
                pitchShift = s.optDouble("pitch_shift", 0.0).toFloat(),
                isVerse = s.optBoolean("is_verse", false),
                metreName = s.optString("metre_name", ""),
                ttsRate = s.optDouble("tts_rate", 1.0).toFloat(),
            ))
        }
        val isVerse = json.optBoolean("is_verse_detected", false)
        val metre = json.optString("metre", "")
        return Triple(segments, isVerse, metre)
    }

    // -----------------------------------------------------------------
    // FEAT-52: Per-sentence regeneration
    // -----------------------------------------------------------------

    /**
     * Regenerate a single segment at [segmentIndex] using the given params.
     * Replaces the corresponding streamChunk audio path in-place.
     */
    fun regenerateSegment(
        segmentIndex: Int,
        text: String,
        speed: Float = 1.0f,
        pitch: Float = 1.0f,
        volume: Float = 1.0f,
        language: String = "mr",
        isVerse: Boolean = false
    ) {
        _state.value = _state.value?.copy(regeneratingIndex = segmentIndex)

        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                try {
                    PythonBridge.call(
                        "tts_bridge", "regenerate_segment",
                        kwargs = mapOf(
                            "text" to text,
                            "speed" to speed.toDouble(),
                            "pitch" to pitch.toDouble(),
                            "volume" to volume.toDouble(),
                            "language" to language,
                            "is_verse" to isVerse
                        )
                    )
                } catch (e: Exception) {
                    JSONObject().put("success", false).put("error", e.message)
                }
            }

            val current = _state.value ?: return@launch
            if (PythonBridge.isSuccess(result)) {
                val newPath = result.optString("audio_path")
                if (newPath.isNotEmpty()) {
                    // Update the stream chunk at this index
                    val updatedChunks = current.streamChunks.toMutableList()
                    if (segmentIndex in updatedChunks.indices) {
                        updatedChunks[segmentIndex] = newPath
                    }
                    // Also update the prosody segment's audio path
                    val updatedSegments = current.prosodySegments.toMutableList()
                    if (segmentIndex in updatedSegments.indices) {
                        updatedSegments[segmentIndex] = updatedSegments[segmentIndex].copy(
                            audioPath = newPath
                        )
                    }
                    _state.value = current.copy(
                        streamChunks = updatedChunks,
                        prosodySegments = updatedSegments,
                        regeneratingIndex = -1,
                        status = "Segment ${segmentIndex + 1} regenerated ✓"
                    )
                }
            } else {
                _state.value = current.copy(
                    regeneratingIndex = -1,
                    status = "Regen failed: ${result.optString("error", "Unknown")}"
                )
            }
        }
    }

    // -----------------------------------------------------------------
    // FEAT-55: Phonetic Explainer
    // -----------------------------------------------------------------

    private val _phoneticExplanation = MutableLiveData<PhoneticExplanation?>()
    val phoneticExplanation: LiveData<PhoneticExplanation?> get() = _phoneticExplanation

    data class PhoneticRule(
        val stage: String,
        val rule: String,
        val before: String,
        val after: String,
        val description: String
    )

    data class PhoneticExplanation(
        val original: String,
        val final: String,
        val rules: List<PhoneticRule>
    )

    fun explainPhonetics(word: String, language: String) {
        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                try {
                    PythonBridge.call(
                        "tts_bridge", "explain_phonetics",
                        kwargs = mapOf("word" to word, "language" to language)
                    )
                } catch (_: Exception) { null }
            }
            if (result != null && result.optBoolean("success", false)) {
                val rulesArr = result.optJSONArray("rules")
                val rules = mutableListOf<PhoneticRule>()
                if (rulesArr != null) {
                    for (i in 0 until rulesArr.length()) {
                        val r = rulesArr.getJSONObject(i)
                        rules.add(PhoneticRule(
                            stage = r.optString("stage", ""),
                            rule = r.optString("rule", ""),
                            before = r.optString("before", ""),
                            after = r.optString("after", ""),
                            description = r.optString("description", "")
                        ))
                    }
                }
                _phoneticExplanation.value = PhoneticExplanation(
                    original = result.optString("original", word),
                    final = result.optString("final", word),
                    rules = rules
                )
            }
        }
    }

    fun clearPhoneticExplanation() {
        _phoneticExplanation.value = null
    }

    // -----------------------------------------------------------------
    // FEAT-59: Community Phonetic Corrections
    // -----------------------------------------------------------------

    private val _correctionSaved = MutableLiveData<Boolean?>()
    val correctionSaved: LiveData<Boolean?> get() = _correctionSaved

    fun submitCorrection(word: String, correctedForm: String) {
        viewModelScope.launch {
            withContext(Dispatchers.IO) {
                val ctx = getApplication<Application>()
                val dao = AppDatabase.getInstance(ctx).phoneticCorrectionDao()
                dao.insert(PhoneticCorrection(word = word, correctedForm = correctedForm))
                PhoneticCorrectionSync.sync(ctx)
            }
            _correctionSaved.value = true
        }
    }

    fun clearCorrectionSaved() {
        _correctionSaved.value = null
    }
}
