package com.marathitts.mobile.ui.tts

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.PythonBridge
import com.marathitts.mobile.service.TtsEngineManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class TtsState(
    val isLoading: Boolean = false,
    val audioPath: String? = null,
    val engine: String = "",
    val error: String? = null,
    val status: String = "Ready"
)

class TtsViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableLiveData(TtsState())
    val state: LiveData<TtsState> get() = _state

    val engineManager = TtsEngineManager(app)

    init {
        PythonBridge.init(app)
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

    override fun onCleared() {
        super.onCleared()
        engineManager.shutdown()
    }
}
