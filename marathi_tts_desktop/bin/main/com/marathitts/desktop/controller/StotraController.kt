package com.marathitts.desktop.controller

import com.marathitts.desktop.service.TtsService
import com.marathitts.desktop.util.AudioPlayerUtil
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import javafx.application.Platform
import javafx.collections.FXCollections
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import javafx.scene.layout.HBox
import java.io.File
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.ResourceBundle
import java.util.concurrent.Executors

/**
 * Controller for the Stotra Library tab.
 *
 * Features:
 *  - Browse stotra catalog (loaded from stotra_catalog.json)
 *  - Search by name
 *  - Filter by deity
 *  - View full stotra text
 *  - Send stotra text to TTS tab (verse mode)
 *  - Play stotra via TTS directly
 */
class StotraController : Initializable {

    @FXML lateinit var searchField: TextField
    @FXML lateinit var deityFilterBox: HBox
    @FXML lateinit var filterAll: ToggleButton
    @FXML lateinit var stotraListView: ListView<String>
    @FXML lateinit var countLabel: Label
    @FXML lateinit var stotraTitle: Label
    @FXML lateinit var deityLabel: Label
    @FXML lateinit var languageLabel: Label
    @FXML lateinit var meterLabel: Label
    @FXML lateinit var sourceLabel: Label
    @FXML lateinit var stotraTextArea: TextArea
    @FXML lateinit var sendToTtsBtn: Button
    @FXML lateinit var playBtn: Button
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar

    var projectRoot: (() -> String?)? = null
    var onSendToTts: ((String) -> Unit)? = null

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "stotra-worker").also { it.isDaemon = true }
    }
    private val player = AudioPlayerUtil()
    private var catalog = mutableListOf<StotraEntry>()
    private var filteredList = mutableListOf<StotraEntry>()
    private var selectedStotra: StotraEntry? = null
    private var activeFilter: String = "All"

    data class StotraEntry(
        val id: Int,
        val name: String,
        val audioFile: String,
        val textFile: String?,
        val language: String,
        val meter: String,
        val deity: String,
        val source: String,
        val text: String? = null // loaded lazily
    )

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        // Deity filter chip clicks
        deityFilterBox.children.filterIsInstance<ToggleButton>().forEach { chip ->
            chip.setOnAction {
                activeFilter = chip.text
                // Deselect others
                deityFilterBox.children.filterIsInstance<ToggleButton>().forEach { c ->
                    c.isSelected = c == chip
                }
                applyFilters()
            }
        }

        // Search debounce
        searchField.textProperty().addListener { _, _, _ -> applyFilters() }

        // List selection
        stotraListView.selectionModel.selectedIndexProperty().addListener { _, _, idx ->
            val i = idx.toInt()
            if (i in filteredList.indices) {
                showStotraDetail(filteredList[i])
            }
        }

        // Load catalog after a short delay to let projectRoot be set
        Platform.runLater { loadCatalog() }
    }

    private fun loadCatalog() {
        catalog.clear()
        val stotrasDir = findStotrasDir() ?: run {
            setStatus("Stotra catalog not found")
            return
        }
        val catalogFile = File(stotrasDir, "stotra_catalog.json")
        if (!catalogFile.exists()) {
            setStatus("stotra_catalog.json not found in $stotrasDir")
            return
        }

        try {
            val mapper = ObjectMapper()
            val tree = mapper.readTree(catalogFile)
            val arr = tree["stotras"] ?: return
            var idx = 0
            for (obj in arr) {
                val audioFile = obj["audio_file"]?.let {
                    if (it.isNull) null else it.asText().ifEmpty { null }
                }
                val textFileName = obj["text_file"]?.asText()
                    ?: audioFile?.replace(".mp3", ".txt")
                catalog.add(StotraEntry(
                    id = idx,
                    name = obj["name"]?.asText() ?: "Stotra $idx",
                    audioFile = audioFile ?: "",
                    textFile = textFileName,
                    language = obj["language"]?.asText() ?: "sa",
                    meter = obj["meter"]?.asText() ?: "",
                    deity = obj["deity"]?.asText() ?: "",
                    source = obj["source"]?.asText() ?: ""
                ))
                idx++
            }
            applyFilters()
            setStatus("${catalog.size} stotras loaded")
        } catch (e: Exception) {
            setStatus("Error loading catalog: ${e.message}")
        }
    }

    private fun findStotrasDir(): File? {
        val candidates = listOfNotNull(
            projectRoot?.invoke()?.let { File(it, "marathi_tts_desktop/stotras") },
            projectRoot?.invoke()?.let { File(it, "stotras") },
            File("stotras"),
            File("marathi_tts_desktop/stotras")
        )
        return candidates.firstOrNull { it.isDirectory && File(it, "stotra_catalog.json").exists() }
    }

    private fun applyFilters() {
        val query = searchField.text?.trim()?.lowercase() ?: ""
        filteredList = catalog.filter { entry ->
            val matchDeity = activeFilter == "All" || entry.deity.contains(activeFilter)
            val matchSearch = query.isEmpty() || entry.name.lowercase().contains(query) ||
                    entry.deity.lowercase().contains(query)
            matchDeity && matchSearch
        }.toMutableList()

        stotraListView.items = FXCollections.observableArrayList(
            filteredList.map { "${it.name}  (${it.deity})" }
        )
        countLabel.text = "${filteredList.size} stotras"
    }

    private fun showStotraDetail(entry: StotraEntry) {
        selectedStotra = entry
        stotraTitle.text = entry.name
        deityLabel.text = entry.deity
        languageLabel.text = when (entry.language) {
            "mr" -> "मराठी"
            "hi" -> "हिंदी"
            "sa" -> "संस्कृत"
            "en" -> "English"
            else -> entry.language
        }
        meterLabel.text = entry.meter
        sourceLabel.text = "— ${entry.source}"
        sendToTtsBtn.isDisable = false
        playBtn.isDisable = false

        // Load text from .txt file
        val stotrasDir = findStotrasDir()
        if (stotrasDir != null && !entry.textFile.isNullOrEmpty()) {
            val textFile = File(stotrasDir, entry.textFile)
            if (textFile.exists()) {
                stotraTextArea.text = textFile.readText(StandardCharsets.UTF_8)
                return
            }
        }
        stotraTextArea.text = "(Stotra text not available — add ${entry.textFile ?: "text file"} to stotras/ directory)"
    }

    @FXML
    fun onSendToTts(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = stotraTextArea.text?.trim()
        if (text.isNullOrEmpty()) {
            setStatus("No text to send")
            return
        }
        onSendToTts?.invoke(text)
        setStatus("Sent to TTS (verse mode)")
    }

    @FXML
    fun onPlayStotra(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = stotraTextArea.text?.trim()
        if (text.isNullOrEmpty()) {
            setStatus("No text to play")
            return
        }
        setStatus("Generating stotra audio…", busy = true)
        playBtn.isDisable = true

        val task = TtsService(projectRoot?.invoke()).generateAudio(
            text = text,
            speed = 0.9,
            pitch = 1.0,
            volume = 1.0,
            isVerse = true,
            language = selectedStotra?.language ?: "sa"
        )
        task.setOnSucceeded {
            val result = task.value
            if (result["success"] == true) {
                val audioPath = result["audio_path"] as? String
                if (audioPath != null) {
                    player.play(audioPath)
                    setStatus("Playing: ${selectedStotra?.name ?: "stotra"}")
                }
            } else {
                setStatus("Error: ${result["error"]}")
            }
            Platform.runLater { playBtn.isDisable = false }
        }
        task.setOnFailed {
            setStatus("Failed: ${task.exception?.message}")
            Platform.runLater { playBtn.isDisable = false }
        }
        executor.submit(task)
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
