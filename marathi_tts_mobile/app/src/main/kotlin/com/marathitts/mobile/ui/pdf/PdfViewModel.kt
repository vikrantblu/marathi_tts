package com.marathitts.mobile.ui.pdf

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.NativePdfExtractor
import com.marathitts.mobile.service.PythonBridge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

data class PdfState(
    val isLoading: Boolean = false,
    val text: String? = null,
    val method: String? = null,
    val error: String? = null,
    val status: String = "Select a PDF to begin"
)

class PdfViewModel(app: Application) : AndroidViewModel(app) {
    private val _state = MutableLiveData(PdfState())
    val state: LiveData<PdfState> get() = _state

    init { PythonBridge.init(app) }

    fun extractFromPdf(pdfPath: String) {
        _state.value = PdfState(isLoading = true, status = "Extracting text from PDF…")
        viewModelScope.launch {
            try {
                // Stage 1: PyPDF2 via Python bridge (fast, works for text-based PDFs)
                _state.value = _state.value!!.copy(status = "Trying text extraction (PyPDF2)…")
                val result: JSONObject = withContext(Dispatchers.IO) {
                    PythonBridge.call("pdf_bridge", "extract_pdf", kwargs = mapOf("pdf_path" to pdfPath))
                }

                val pyText = if (PythonBridge.isSuccess(result)) result.optString("text") else ""
                val pyMethod = result.optString("method", "")

                // If PyPDF2 extracted meaningful Devanagari text, use it
                if (pyText.isNotBlank() && devanagariRatio(pyText) >= 0.1) {
                    _state.value = PdfState(
                        text = pyText,
                        method = pyMethod.ifBlank { "PyPDF2" },
                        status = "Extraction complete ✓"
                    )
                    return@launch
                }

                // Stage 2: Image-based PDF → Android PdfRenderer + ML Kit Devanagari OCR
                _state.value = _state.value!!.copy(
                    status = "Image-based PDF detected — running Devanagari OCR…"
                )
                val nativeText: String = withContext(Dispatchers.IO) {
                    NativePdfExtractor.extract(File(pdfPath))
                }

                if (nativeText.isNotBlank()) {
                    _state.value = PdfState(
                        text = nativeText,
                        method = "ML Kit Devanagari OCR",
                        status = "Extraction complete ✓ (OCR)"
                    )
                } else {
                    _state.value = PdfState(
                        error = "No text could be extracted from this PDF",
                        status = "Extraction failed — PDF may be encrypted or unsupported"
                    )
                }
            } catch (e: Exception) {
                _state.value = PdfState(
                    error = e.message,
                    status = "Error: ${e.message}"
                )
            }
        }
    }

    /** Fraction of Devanagari codepoints (U+0900–U+097F) in text */
    private fun devanagariRatio(text: String): Double {
        if (text.isEmpty()) return 0.0
        val deva = text.count { it.code in 0x0900..0x097F }
        return deva.toDouble() / text.length
    }
}

