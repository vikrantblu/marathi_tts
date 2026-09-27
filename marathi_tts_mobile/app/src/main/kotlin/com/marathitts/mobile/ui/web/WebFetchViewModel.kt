package com.marathitts.mobile.ui.web

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.NativeImageOcr
import com.marathitts.mobile.service.PythonBridge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.URL

data class WebFetchState(
    val isLoading: Boolean = false,
    val text: String? = null,
    val title: String? = null,
    val error: String? = null,
    val status: String = "Enter a URL and tap Fetch"
)

class WebFetchViewModel(app: Application) : AndroidViewModel(app) {
    private val _state = MutableLiveData(WebFetchState())
    val state: LiveData<WebFetchState> get() = _state

    init { PythonBridge.init(app) }

    /** Minimum text chars (excluding title) to consider extraction successful. */
    private val MIN_TEXT_FOR_OCR = 100

    fun fetchUrl(url: String) {
        _state.value = WebFetchState(isLoading = true, status = "Fetching content…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call("web_bridge", "fetch_url", kwargs = mapOf("url" to url))
            }
            if (PythonBridge.isSuccess(result)) {
                val text = result.optString("text")
                val title = result.optString("title")
                val imageUrlsArr = result.optJSONArray("image_urls")
                val imageUrls = mutableListOf<String>()
                if (imageUrlsArr != null) {
                    for (i in 0 until imageUrlsArr.length()) {
                        imageUrls.add(imageUrlsArr.getString(i))
                    }
                }

                // If text is minimal and images are available, run OCR on images
                val textLen = text.length - (title.length + 2).coerceAtMost(text.length)
                if (textLen < MIN_TEXT_FOR_OCR && imageUrls.isNotEmpty()) {
                    _state.value = WebFetchState(
                        isLoading = true, text = text, title = title,
                        status = "Text minimal — OCR scanning ${imageUrls.size} images…"
                    )
                    val ocrText = ocrImageUrls(imageUrls)
                    val combined = if (ocrText.isNotBlank()) {
                        if (text.isNotBlank()) "$text\n\n$ocrText" else ocrText
                    } else text
                    _state.value = WebFetchState(
                        text = combined, title = title,
                        status = if (ocrText.isNotBlank()) "Content + image OCR fetched ✓"
                                 else "Content fetched ✓ (image OCR found no text)"
                    )
                } else {
                    _state.value = WebFetchState(
                        text = text, title = title, status = "Content fetched ✓"
                    )
                }
            } else {
                _state.value = WebFetchState(error = PythonBridge.getError(result),
                    status = "Error: ${PythonBridge.getError(result)}")
            }
        }
    }

    /**
     * Download images from URLs and run ML Kit Devanagari OCR on each.
     * Returns combined OCR text or empty string.
     */
    private suspend fun ocrImageUrls(urls: List<String>): String = withContext(Dispatchers.IO) {
        val cacheDir = getApplication<Application>().cacheDir
        val results = mutableListOf<String>()
        val limit = urls.take(5)  // cap at 5 images to avoid OOM

        for ((idx, imgUrl) in limit.withIndex()) {
            try {
                withContext(Dispatchers.Main) {
                    _state.value = _state.value?.copy(
                        status = "OCR scanning image ${idx + 1} of ${limit.size}…"
                    )
                }
                val tmpFile = File(cacheDir, "web_ocr_${idx}.jpg")
                URL(imgUrl).openStream().use { input ->
                    tmpFile.outputStream().use { output -> input.copyTo(output) }
                }
                if (tmpFile.length() < 1024) { // skip tiny files (icons)
                    tmpFile.delete()
                    continue
                }
                val text = NativeImageOcr.extract(tmpFile)
                if (text.isNotBlank() && text.length > 10) {
                    results.add(text)
                }
                tmpFile.delete()
            } catch (_: Exception) {
                // Skip failed images silently
            }
        }
        results.joinToString("\n\n")
    }
}
