package com.marathitts.mobile.ui.modi

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

data class ModiState(
    val isLoading: Boolean = false,
    val output: String = "",
    val inputCharCount: Int = 0,
    val outputCharCount: Int = 0,
    val error: String? = null,
    val status: String = "Ready"
)

class ModiViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableLiveData(ModiState())
    val state: LiveData<ModiState> get() = _state

    companion object {
        val MODES = listOf(
            "modi_to_devanagari",
            "devanagari_to_iast",
            "iast_to_devanagari",
            "brahmi_to_devanagari"
        )
        val MODE_LABELS = listOf(
            "Modi → Devanagari",
            "Devanagari → IAST",
            "IAST → Devanagari",
            "Brahmi → Devanagari"
        )
        val MODE_HINTS = listOf(
            "Enter Modi script text to convert to Devanagari",
            "Enter Devanagari text to transliterate to IAST Roman",
            "Enter IAST Roman text to convert back to Devanagari",
            "Enter ancient Brahmi script to convert to Devanagari"
        )
    }

    init {
        PythonBridge.init(app)
    }

    fun convert(text: String, modeIndex: Int) {
        val mode = MODES[modeIndex]
        _state.value = _state.value!!.copy(isLoading = true, status = "Converting…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call(
                    "script_converter_bridge", "convert",
                    args = listOf(text, mode)
                )
            }
            if (PythonBridge.isSuccess(result)) {
                val output = result.optString("converted", "")
                _state.value = ModiState(
                    output = output,
                    inputCharCount = text.length,
                    outputCharCount = output.length,
                    status = "Conversion complete ✓"
                )
            } else {
                val err = PythonBridge.getError(result)
                _state.value = ModiState(error = err, status = "Error: $err")
            }
        }
    }

    fun clear() {
        _state.value = ModiState()
    }
}
