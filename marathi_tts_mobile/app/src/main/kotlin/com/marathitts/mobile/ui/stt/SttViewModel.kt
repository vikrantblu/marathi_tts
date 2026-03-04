package com.marathitts.mobile.ui.stt

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.PythonBridge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

data class SttState(
    val isLoading: Boolean = false,
    val transcript: String = "",
    val segments: List<String> = emptyList(),
    val engine: String = "",
    val useNativeStt: Boolean = false,
    val nativeAudioPath: String? = null,
    val nativeChunks: List<String> = emptyList(),
    val error: String? = null,
    val status: String = "Ready"
)

class SttViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableLiveData(SttState())
    val state: LiveData<SttState> get() = _state

    init {
        PythonBridge.init(app)
    }

    fun transcribeFile(audioPath: String, language: String = "mr") {
        _state.value = SttState(isLoading = true, status = "Preparing audio\u2026")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call(
                    "stt_bridge", "transcribe_long_audio",
                    args = listOf(audioPath, language)
                )
            }
            parseResult(result)
        }
    }

    fun recordAndTranscribe(durationSeconds: Int = 10, language: String = "mr") {
        _state.value = SttState(isLoading = true, status = "Recording for ${durationSeconds}s…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call(
                    "stt_bridge", "record_and_transcribe",
                    kwargs = mapOf(
                        "duration_seconds" to durationSeconds,
                        "language" to language
                    )
                )
            }
            parseResult(result)
        }
    }

    private fun parseResult(result: JSONObject) {
        if (PythonBridge.isSuccess(result)) {
            // Check if native Android STT should be used instead
            if (result.optBoolean("use_native_stt", false)) {
                val audioPath = result.optString("audio_path", "").takeIf { it.isNotEmpty() }
                val chunksJson = result.optJSONArray("chunks")
                val chunks = mutableListOf<String>()
                if (chunksJson != null) {
                    for (i in 0 until chunksJson.length()) chunks.add(chunksJson.optString(i))
                }
                if (chunks.isEmpty() && audioPath != null) chunks.add(audioPath)
                _state.value = SttState(
                    useNativeStt = true,
                    nativeAudioPath = chunks.firstOrNull() ?: audioPath,
                    nativeChunks = chunks,
                    status = if (chunks.size > 1)
                        "Using Android recognizer (${chunks.size} chunks)"
                    else
                        "Using Android speech recognizer"
                )
                return
            }
            val segList = mutableListOf<String>()
            val segsJson: JSONArray? = result.optJSONArray("segments")
            if (segsJson != null) {
                for (i in 0 until segsJson.length()) {
                    val seg = segsJson.optJSONObject(i)
                    if (seg != null) {
                        val start = "%.1f".format(seg.optDouble("start", 0.0))
                        val end = "%.1f".format(seg.optDouble("end", 0.0))
                        val text = seg.optString("text", "")
                        segList.add("[${start}s – ${end}s]  $text")
                    }
                }
            }
            _state.value = SttState(
                transcript = result.optString("text", ""),
                segments = segList,
                engine = result.optString("engine", ""),
                status = "Transcription complete ✓"
            )
        } else {
            val err = PythonBridge.getError(result)
            _state.value = SttState(error = err, status = "Error: $err")
        }
    }

    fun clear() {
        _state.value = SttState()
    }

    fun clearNativeSttFlag() {
        _state.value = _state.value?.copy(
            useNativeStt = false,
            nativeAudioPath = null,
            nativeChunks = emptyList()
        )
    }
}
