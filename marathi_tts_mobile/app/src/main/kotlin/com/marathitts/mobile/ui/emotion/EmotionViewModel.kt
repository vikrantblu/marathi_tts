package com.marathitts.mobile.ui.emotion

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.PythonBridge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class EmotionState(
    val isLoading: Boolean = false,
    val emotion: String? = null,
    val scores: Map<String, Float>? = null,
    val error: String? = null,
    val status: String = "Ready"
)

class EmotionViewModel(app: Application) : AndroidViewModel(app) {
    private val _state = MutableLiveData(EmotionState())
    val state: LiveData<EmotionState> get() = _state

    init { PythonBridge.init(app) }

    fun analyzeEmotion(text: String) {
        _state.value = EmotionState(isLoading = true, status = "Analysing emotion…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call("emotion_bridge", "analyze_emotion",
                    kwargs = mapOf("text" to text))
            }
            if (PythonBridge.isSuccess(result)) {
                val emotion = result.optString("emotion", "neutral")
                val scoresJson = result.optJSONObject("scores")
                val scores = scoresJson?.let { obj ->
                    obj.keys().asSequence().associate { k -> k to obj.optDouble(k, 0.0).toFloat() }
                }
                _state.value = EmotionState(emotion = emotion, scores = scores, status = "Analysis complete ✓")
            } else {
                _state.value = EmotionState(error = PythonBridge.getError(result),
                    status = "Error: ${PythonBridge.getError(result)}")
            }
        }
    }
}
