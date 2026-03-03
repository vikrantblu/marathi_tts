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
    val statusMessage: String? = null
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
            isGenerating = false
        )
    }

    fun clearSelection() {
        _state.value = _state.value?.copy(
            selectedStotra = null,
            stotraText = null,
            audioPath = null,
            statusMessage = null,
            isGenerating = false
        )
    }

    /**
     * Generate TTS audio for the selected stotra using verse mode.
     */
    fun playWithTts() {
        val s = _state.value ?: return
        val stotra = s.selectedStotra ?: return
        val text = s.stotraText ?: return

        _state.value = s.copy(isGenerating = true, statusMessage = "Generating verse audio…", audioPath = null)

        viewModelScope.launch {
            Log.i(TAG, "playWithTts: '${stotra.titleEn}' lang=${stotra.language} chars=${text.length}")
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
                Log.i(TAG, "playWithTts success: engine=$engine path=$path")
                _state.value = _state.value?.copy(
                    isGenerating = false,
                    audioPath = path,
                    statusMessage = "Ready — generated with $engine"
                )
            } else {
                val err = result.optString("error", "Unknown error")
                Log.e(TAG, "playWithTts failed: $err")
                _state.value = _state.value?.copy(
                    isGenerating = false,
                    statusMessage = "Failed: $err"
                )
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        engineManager.shutdown()
    }
}
