package com.marathitts.mobile.ui.bookreader

import android.app.Application
import android.graphics.BitmapFactory
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.BookPageProcessor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

data class BookReaderState(
    val isLoading: Boolean = false,
    val leftPageText: String = "",
    val rightPageText: String = "",
    val mergedText: String = "",
    val pageCount: Int = 0,
    val error: String? = null,
    val status: String = "Capture a book page to begin"
)

class BookReaderViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableLiveData(BookReaderState())
    val state: LiveData<BookReaderState> get() = _state

    /**
     * Process a photo of an open book spread (two pages).
     * Splits, OCRs, cleans, reflows, and merges text.
     */
    fun processBookSpread(imagePath: String) {
        _state.value = BookReaderState(isLoading = true, status = "Processing book spread…")
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    val bitmap = BitmapFactory.decodeFile(imagePath)
                        ?: throw IllegalArgumentException("Could not load image")
                    try {
                        BookPageProcessor.processBookSpread(bitmap)
                    } finally {
                        bitmap.recycle()
                    }
                }

                if (result.mergedText.isBlank()) {
                    _state.value = BookReaderState(status = "No text found in image")
                } else {
                    _state.value = BookReaderState(
                        leftPageText = result.leftPageText,
                        rightPageText = result.rightPageText,
                        mergedText = result.mergedText,
                        pageCount = result.pageCount,
                        status = "${result.pageCount} page(s) processed ✓"
                    )
                }
            } catch (e: Exception) {
                _state.value = BookReaderState(
                    error = e.message,
                    status = "Error: ${e.message ?: "Processing failed"}"
                )
            }
        }
    }

    /**
     * Process a single-page photo (no spine splitting).
     */
    fun processSinglePage(imagePath: String) {
        _state.value = BookReaderState(isLoading = true, status = "Processing page…")
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    val bitmap = BitmapFactory.decodeFile(imagePath)
                        ?: throw IllegalArgumentException("Could not load image")
                    try {
                        BookPageProcessor.processSinglePage(bitmap)
                    } finally {
                        bitmap.recycle()
                    }
                }

                if (result.mergedText.isBlank()) {
                    _state.value = BookReaderState(status = "No text found in image")
                } else {
                    _state.value = BookReaderState(
                        leftPageText = result.leftPageText,
                        mergedText = result.mergedText,
                        pageCount = 1,
                        status = "Page processed ✓"
                    )
                }
            } catch (e: Exception) {
                _state.value = BookReaderState(
                    error = e.message,
                    status = "Error: ${e.message ?: "Processing failed"}"
                )
            }
        }
    }
}
