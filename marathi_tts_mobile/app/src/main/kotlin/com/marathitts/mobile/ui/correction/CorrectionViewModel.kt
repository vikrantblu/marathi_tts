package com.marathitts.mobile.ui.correction

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

data class CorrectionState(
    val isLoading: Boolean = false,
    val correctedText: String? = null,
    val method: String? = null,
    val error: String? = null,
    val status: String = "Ready"
)

class CorrectionViewModel(app: Application) : AndroidViewModel(app) {
    private val _state = MutableLiveData(CorrectionState())
    val state: LiveData<CorrectionState> get() = _state

    init { PythonBridge.init(app) }

    fun correctText(text: String) {
        _state.value = CorrectionState(isLoading = true, status = "Correcting text…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call("correction_bridge", "correct_text", kwargs = mapOf("text" to text))
            }
            if (PythonBridge.isSuccess(result)) {
                _state.value = CorrectionState(
                    correctedText = result.optString("corrected_text"),
                    method = result.optString("method"),
                    status = "Correction applied ✓"
                )
            } else {
                _state.value = CorrectionState(error = PythonBridge.getError(result),
                    status = "Error: ${PythonBridge.getError(result)}")
            }
        }
    }

    fun formatText(text: String) {
        _state.value = _state.value!!.copy(isLoading = true, status = "Formatting text…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call("correction_bridge", "format_text", kwargs = mapOf("text" to text))
            }
            if (PythonBridge.isSuccess(result)) {
                _state.value = CorrectionState(
                    correctedText = result.optString("formatted_text"),
                    method = "format",
                    status = "Text formatted ✓"
                )
            } else {
                _state.value = _state.value!!.copy(
                    isLoading = false, status = "Format error: ${PythonBridge.getError(result)}"
                )
            }
        }
    }

    fun suggestCorrection(incorrect: String, correct: String, category: String = "general") {
        _state.value = _state.value!!.copy(isLoading = true, status = "Submitting suggestion…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call(
                    "correction_bridge", "suggest_correction",
                    kwargs = mapOf("incorrect" to incorrect, "correct" to correct, "category" to category)
                )
            }
            _state.value = _state.value!!.copy(
                isLoading = false,
                status = if (PythonBridge.isSuccess(result)) "Suggestion saved ✓"
                        else "Save error: ${PythonBridge.getError(result)}"
            )
        }
    }
}
