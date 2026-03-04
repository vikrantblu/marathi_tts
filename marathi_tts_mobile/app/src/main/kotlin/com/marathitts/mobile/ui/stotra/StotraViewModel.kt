package com.marathitts.mobile.ui.stotra

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.StotraRepository
import com.marathitts.mobile.service.TtsEngineManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class StotraListState(
    val stotras: List<StotraRepository.Stotra> = emptyList(),
    val filteredStotras: List<StotraRepository.Stotra> = emptyList(),
    val selectedStotra: StotraRepository.Stotra? = null,
    val stotraText: String? = null,
    val isGenerating: Boolean = false,
    val audioPath: String? = null,
    val statusMessage: String? = null,
    val hasPreRecordedAudio: Boolean = false
)

class StotraViewModel(app: Application) : AndroidViewModel(app) {

    companion object { private const val TAG = "StotraViewModel" }

    private val repo = StotraRepository(app)
    val engineManager = TtsEngineManager(app)

    private val _state = MutableLiveData(StotraListState())
    val state: LiveData<StotraListState> get() = _state

    private var currentFilter: String? = null  // deity filter
    private var currentQuery: String = ""

    init {
        loadCatalog()
    }

    private fun loadCatalog() {
        val all = repo.getAll()
        _state.value = StotraListState(stotras = all, filteredStotras = all)
    }

    fun filterByDeity(deity: String?) {
        currentFilter = deity
        applyFilters()
    }

    fun search(query: String) {
        currentQuery = query
        applyFilters()
    }

    private fun applyFilters() {
        val s = _state.value ?: return
        var list = s.stotras
        if (!currentFilter.isNullOrEmpty()) {
            list = list.filter { it.deity == currentFilter }
        }
        if (currentQuery.isNotBlank()) {
            val q = currentQuery.lowercase()
            list = list.filter {
                it.title.lowercase().contains(q) ||
                it.titleEn.lowercase().contains(q) ||
                it.deity.lowercase().contains(q)
            }
        }
        _state.value = s.copy(filteredStotras = list)
    }

    fun selectStotra(stotra: StotraRepository.Stotra) {
        val text = repo.loadText(stotra)
        _state.value = _state.value?.copy(
            selectedStotra = stotra,
            stotraText = text,
            audioPath = null,
            statusMessage = null,
            isGenerating = false,
            hasPreRecordedAudio = stotra.audioFile != null
        )
    }

    fun clearSelection() {
        _state.value = _state.value?.copy(
            selectedStotra = null,
            stotraText = null,
            audioPath = null,
            statusMessage = null,
            isGenerating = false,
            hasPreRecordedAudio = false
        )
    }

    /**
     * Play the selected stotra.
     * Stage 0: serve pre-recorded audio from assets if [audioFile] is set in the catalog.
     * Stage 1: fall back to TTS generation (verse mode).
     */
    fun playWithTts() {
        val s = _state.value ?: return
        val stotra = s.selectedStotra ?: return
        val text = s.stotraText ?: return

        // ── Stage 0: pre-recorded audio from assets ──────────────────────────
        if (stotra.audioFile != null) {
            _state.value = s.copy(isGenerating = true,
                                  statusMessage = "Loading pre-recorded audio…",
                                  audioPath = null)
            viewModelScope.launch {
                val path = withContext(Dispatchers.IO) { repo.extractAudioToCache(stotra) }
                if (path != null) {
                    Log.i(TAG, "Stage 0 hit: pre-recorded audio for '${stotra.titleEn}' -> $path")
                    _state.value = _state.value?.copy(
                        isGenerating = false,
                        audioPath = path,
                        statusMessage = "Pre-recorded audio"
                    )
                    return@launch
                }
                Log.w(TAG, "Stage 0 miss: audio asset not found for '${stotra.id}', falling back to TTS")
                // Fall through to TTS generation below
                generateTts(stotra, text)
            }
            return
        }

        // ── Stage 1: TTS generation ───────────────────────────────────────────
        _state.value = s.copy(isGenerating = true, statusMessage = "Generating verse audio…", audioPath = null)
        viewModelScope.launch { generateTts(stotra, text) }
    }

    private suspend fun generateTts(stotra: StotraRepository.Stotra, text: String) {
        Log.i(TAG, "generateTts: '${stotra.titleEn}' lang=${stotra.language} chars=${text.length}")
        val langCode = stotra.language
        val result = engineManager.generate(
            text = text,
            engineIndex = TtsEngineManager.ENGINE_AUTO,
            langCode = langCode,
            speed = 0.9f,    // slightly slower for devotional pace
            pitch = 1.0f,
            isVerse = true
        )

        if (result.optBoolean("success", false)) {
            val path = result.optString("audio_path", "")
            val engine = result.optString("engine", "")
            Log.i(TAG, "generateTts success: engine=$engine path=$path")
            _state.value = _state.value?.copy(
                isGenerating = false,
                audioPath = path,
                statusMessage = "Ready — generated with $engine"
            )
        } else {
            val err = result.optString("error", "Unknown error")
            Log.e(TAG, "generateTts failed: $err")
            _state.value = _state.value?.copy(
                isGenerating = false,
                statusMessage = "Failed: $err"
            )
        }
    }

    override fun onCleared() {
        super.onCleared()
        engineManager.shutdown()
    }
}
