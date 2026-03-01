package com.marathitts.mobile.ui.bookreader

import android.app.Application
import android.graphics.BitmapFactory
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.AudioPlayerService
import com.marathitts.mobile.service.BookPageProcessor
import com.marathitts.mobile.service.PythonBridge
import com.marathitts.mobile.service.TtsEngineManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

/** Range of a single sentence inside the full merged text. */
data class SentenceRange(val start: Int, val end: Int, val text: String)

data class BookReaderState(
    // OCR processing
    val isProcessing: Boolean = false,
    val mergedText: String = "",
    val pageCount: Int = 0,
    val error: String? = null,
    val status: String = "Capture a book page to begin",
    // Last captured / used image path (for photo-review feature)
    val lastCapturedImagePath: String? = null,
    // Sentence-by-sentence reading
    val sentences: List<SentenceRange> = emptyList(),
    val currentSentenceIndex: Int = -1,
    val isGeneratingAudio: Boolean = false,
    val currentAudioPath: String? = null,
    val audioGeneration: Int = 0,
    val isReading: Boolean = false,
    val isPaused: Boolean = false,
    // UI
    val fontSize: Float = 18f,
    val imageExpanded: Boolean = true,
    // TTS settings
    val ttsEngine: Int = TtsEngineManager.ENGINE_AUTO,
    val ttsSpeed: Float = 1.0f,
    val ttsPitch: Float = 1.0f,
    val ttsSettingsExpanded: Boolean = false,
)

class BookReaderViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableLiveData(BookReaderState())
    val state: LiveData<BookReaderState> get() = _state

    val engineManager = TtsEngineManager(app)

    /** MediaPlayer wrapper — lives in ViewModel so playback survives screen-off. */
    private val audioPlayer = AudioPlayerService()

    init { PythonBridge.init(app) }

    // ── OCR Processing ──────────────────────────────────────────

    fun processBookSpread(imagePath: String, append: Boolean = false) {
        val current = _state.value ?: BookReaderState()
        _state.value = current.copy(isProcessing = true, error = null,
            lastCapturedImagePath = imagePath,
            status = "Processing book spread…")
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    val bitmap = BitmapFactory.decodeFile(imagePath)
                        ?: throw IllegalArgumentException("Could not load image")
                    try { BookPageProcessor.processBookSpread(bitmap) }
                    finally { bitmap.recycle() }
                }
                applyOcrResult(result, append)
            } catch (e: Exception) {
                val cur = _state.value ?: BookReaderState()
                _state.value = cur.copy(
                    isProcessing = false,
                    error = e.message,
                    status = "Error: ${e.message ?: "Processing failed"}"
                )
            }
        }
    }

    fun processSinglePage(imagePath: String, append: Boolean = false) {
        val current = _state.value ?: BookReaderState()
        _state.value = current.copy(isProcessing = true, error = null,
            lastCapturedImagePath = imagePath,
            status = "Processing page…")
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    val bitmap = BitmapFactory.decodeFile(imagePath)
                        ?: throw IllegalArgumentException("Could not load image")
                    try { BookPageProcessor.processSinglePage(bitmap) }
                    finally { bitmap.recycle() }
                }
                applyOcrResult(result, append)
            } catch (e: Exception) {
                val cur = _state.value ?: BookReaderState()
                _state.value = cur.copy(
                    isProcessing = false,
                    error = e.message,
                    status = "Error: ${e.message ?: "Processing failed"}"
                )
            }
        }
    }

    /** Re-run OCR on the last captured image with current settings. */
    fun reprocessLastImage(singlePage: Boolean = false) {
        val path = _state.value?.lastCapturedImagePath ?: return
        if (singlePage) processSinglePage(path, append = false)
        else processBookSpread(path, append = false)
    }

    private fun applyOcrResult(result: BookPageProcessor.BookReadResult, append: Boolean) {
        val current = _state.value ?: BookReaderState()
        if (result.mergedText.isBlank()) {
            _state.value = current.copy(isProcessing = false,
                status = "No text found in image")
            return
        }
        val newText = if (append && current.mergedText.isNotBlank()) {
            current.mergedText + "\n\n" + result.mergedText
        } else {
            result.mergedText
        }
        val newPageCount = if (append) current.pageCount + result.pageCount
            else result.pageCount

        _state.value = current.copy(
            isProcessing = false,
            mergedText = newText,
            pageCount = newPageCount,
            imageExpanded = false, // auto-collapse after extraction
            status = "$newPageCount page(s) • ${newText.length} chars"
        )
    }

    // ── Sentence Splitting ──────────────────────────────────────

    private val sentenceEnders = setOf('।', '॥', '.', '!', '?')

    /**
     * Split full text into sentence ranges, tracking start/end positions
     * for highlighting. Splits on sentence-ending punctuation and newlines.
     */
    private fun computeSentenceRanges(fullText: String): List<SentenceRange> {
        val ranges = mutableListOf<SentenceRange>()
        var segStart = 0
        var i = 0

        while (i < fullText.length) {
            val ch = fullText[i]
            if (ch in sentenceEnders) {
                val end = i + 1
                val sentence = fullText.substring(segStart, end).trim()
                if (sentence.isNotBlank()) {
                    val actualStart = indexOfNonWhitespace(fullText, segStart)
                    ranges.add(SentenceRange(
                        start = if (actualStart >= 0) actualStart else segStart,
                        end = end,
                        text = sentence
                    ))
                }
                segStart = end
                // skip whitespace (but stop at newlines — those are separate breaks)
                while (segStart < fullText.length && fullText[segStart] == ' ') segStart++
                i = segStart
            } else if (ch == '\n') {
                val sentence = fullText.substring(segStart, i).trim()
                if (sentence.isNotBlank()) {
                    val actualStart = indexOfNonWhitespace(fullText, segStart)
                    ranges.add(SentenceRange(
                        start = if (actualStart >= 0) actualStart else segStart,
                        end = i,
                        text = sentence
                    ))
                }
                segStart = i + 1
                while (segStart < fullText.length && fullText[segStart].isWhitespace()) segStart++
                i = segStart
            } else {
                i++
            }
        }

        // Remaining text without trailing punctuation
        if (segStart < fullText.length) {
            val remaining = fullText.substring(segStart).trim()
            if (remaining.isNotBlank()) {
                val actualStart = indexOfNonWhitespace(fullText, segStart)
                ranges.add(SentenceRange(
                    start = if (actualStart >= 0) actualStart else segStart,
                    end = fullText.length,
                    text = remaining
                ))
            }
        }

        return ranges
    }

    private fun indexOfNonWhitespace(text: String, from: Int): Int {
        for (idx in from until text.length) {
            if (!text[idx].isWhitespace()) return idx
        }
        return -1
    }

    // ── Reading Session ─────────────────────────────────────────

    /** Begin sentence-by-sentence reading from the start. */
    fun startReading() {
        val current = _state.value ?: return
        if (current.mergedText.isBlank()) return

        val sentences = computeSentenceRanges(current.mergedText)
        if (sentences.isEmpty()) return

        _state.value = current.copy(
            sentences = sentences,
            currentSentenceIndex = 0,
            isReading = true,
            isPaused = false,
            status = "Reading… 1/${sentences.size}"
        )
        generateCurrentSentenceAudio()
    }

    fun pauseReading() {
        val current = _state.value ?: return
        if (!current.isReading) return
        audioPlayer.pause()
        _state.value = current.copy(isPaused = true, status = "Paused")
    }

    fun resumeReading() {
        val current = _state.value ?: return
        if (!current.isReading || !current.isPaused) return
        audioPlayer.resume()
        _state.value = current.copy(
            isPaused = false,
            status = "Reading… ${current.currentSentenceIndex + 1}/${current.sentences.size}"
        )
    }

    fun stopReading() {
        audioPlayer.stop()
        val current = _state.value ?: return
        _state.value = current.copy(
            currentSentenceIndex = -1,
            isReading = false,
            isPaused = false,
            currentAudioPath = null,
            isGeneratingAudio = false,
            status = "${current.pageCount} page(s) • ${current.mergedText.length} chars"
        )
    }

    fun nextSentence() {
        val current = _state.value ?: return
        if (!current.isReading) return
        val nextIdx = current.currentSentenceIndex + 1
        if (nextIdx >= current.sentences.size) {
            stopReading()
            return
        }
        _state.value = current.copy(
            currentSentenceIndex = nextIdx,
            isPaused = false,
            status = "Reading… ${nextIdx + 1}/${current.sentences.size}"
        )
        generateCurrentSentenceAudio()
    }

    fun prevSentence() {
        val current = _state.value ?: return
        if (!current.isReading) return
        val prevIdx = (current.currentSentenceIndex - 1).coerceAtLeast(0)
        _state.value = current.copy(
            currentSentenceIndex = prevIdx,
            isPaused = false,
            status = "Reading… ${prevIdx + 1}/${current.sentences.size}"
        )
        generateCurrentSentenceAudio()
    }

    /** Called internally (and by Fragment as fallback) when sentence audio finishes. */
    fun onPlaybackComplete() {
        val current = _state.value ?: return
        if (!current.isReading || current.isPaused) return
        nextSentence()
    }

    private fun generateCurrentSentenceAudio() {
        val current = _state.value ?: return
        val idx = current.currentSentenceIndex
        if (idx < 0 || idx >= current.sentences.size) return

        val sentence = current.sentences[idx]
        _state.value = current.copy(isGeneratingAudio = true)

        viewModelScope.launch {
            try {
                val result: JSONObject = engineManager.generate(
                    text = sentence.text,
                    engineIndex = current.ttsEngine,
                    langCode = "mr",
                    gender = "female",
                    speed = current.ttsSpeed,
                    pitch = current.ttsPitch
                )
                val cur = _state.value ?: return@launch
                if (result.optBoolean("success", false)) {
                    val audioPath = result.optString("audio_path")
                    _state.postValue(cur.copy(
                        isGeneratingAudio = false,
                        currentAudioPath = audioPath,
                        audioGeneration = cur.audioGeneration + 1
                    ))
                    // Play directly from ViewModel — works even when screen is off
                    audioPlayer.play(audioPath) { onPlaybackComplete() }
                } else {
                    _state.value = cur.copy(
                        isGeneratingAudio = false,
                        error = result.optString("error", "TTS failed"),
                        status = "Audio error — tap Next to skip"
                    )
                }
            } catch (e: Exception) {
                val cur = _state.value ?: return@launch
                _state.value = cur.copy(
                    isGeneratingAudio = false,
                    error = "Audio: ${e.message}",
                    status = "Audio error — tap Next to skip"
                )
            }
        }
    }

    // ── UI Helpers ──────────────────────────────────────────────

    fun setFontSize(size: Float) {
        val current = _state.value ?: return
        _state.value = current.copy(fontSize = size.coerceIn(12f, 32f))
    }

    fun toggleImage() {
        val current = _state.value ?: return
        _state.value = current.copy(imageExpanded = !current.imageExpanded)
    }

    fun toggleTtsSettings() {
        val current = _state.value ?: return
        _state.value = current.copy(ttsSettingsExpanded = !current.ttsSettingsExpanded)
    }

    fun setTtsEngine(engineIndex: Int) {
        val current = _state.value ?: return
        _state.value = current.copy(ttsEngine = engineIndex)
    }

    fun setTtsSpeed(speed: Float) {
        val current = _state.value ?: return
        _state.value = current.copy(ttsSpeed = speed.coerceIn(0.5f, 2.0f))
    }

    fun setTtsPitch(pitch: Float) {
        val current = _state.value ?: return
        _state.value = current.copy(ttsPitch = pitch.coerceIn(0.5f, 2.0f))
    }

    fun clearAll() {
        stopReading()
        _state.value = BookReaderState()
    }

    override fun onCleared() {
        audioPlayer.stop()
        engineManager.shutdown()
        super.onCleared()
    }
}
