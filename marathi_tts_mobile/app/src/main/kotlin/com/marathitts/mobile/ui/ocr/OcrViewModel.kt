package com.marathitts.mobile.ui.ocr

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.NativeImageOcr
import com.marathitts.mobile.service.TextReflow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

data class OcrState(
    val isLoading: Boolean = false,
    val text: String? = null,
    val error: String? = null,
    val status: String = "Select an image to begin"
)

class OcrViewModel(app: Application) : AndroidViewModel(app) {
    private val _state = MutableLiveData(OcrState())
    val state: LiveData<OcrState> get() = _state

    fun extractFromImage(imagePath: String) {
        _state.value = OcrState(isLoading = true, status = "Extracting text…")
        viewModelScope.launch {
            try {
                val rawText = withContext(Dispatchers.IO) {
                    NativeImageOcr.extract(File(imagePath))
                }
                if (rawText.isBlank()) {
                    _state.value = OcrState(status = "No text found in image")
                } else {
                    // Reflow: join word-wrapped lines so TTS doesn't pause at visual line breaks
                    val text = TextReflow.reflow(rawText)
                    _state.value = OcrState(text = text, status = "Extraction complete ✓")
                }
            } catch (e: Exception) {
                _state.value = OcrState(
                    error = e.message,
                    status = "Error: ${e.message ?: "OCR failed"}"
                )
            }
        }
    }
}
