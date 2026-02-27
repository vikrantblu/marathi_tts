package com.marathitts.desktop.controller

import com.marathitts.desktop.service.SttService
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import javafx.stage.FileChooser
import java.io.File
import java.net.URL
import java.util.ResourceBundle
import java.util.concurrent.Executors

/**
 * Controller for the Speech-to-Text tab.
 *
 * Features:
 *  - Upload an audio file (WAV/MP3/M4A/OGG) and transcribe it
 *  - Record from microphone with configurable duration
 *  - Displays full transcript + per-segment timings
 *  - Send result to TTS tab
 */
class SttController : Initializable {

    @FXML lateinit var audioFileLabel: Label
    @FXML lateinit var languageCombo: ComboBox<String>
    @FXML lateinit var transcribeBtn: Button
    @FXML lateinit var recordDurationSlider: Slider
    @FXML lateinit var durationLabel: Label
    @FXML lateinit var recordBtn: Button
    @FXML lateinit var outputArea: TextArea
    @FXML lateinit var segmentsArea: TextArea
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var sendToTtsBtn: Button
    @FXML lateinit var engineLabel: Label

    var projectRoot: (() -> String?)? = null
    var onSendToTts: ((String) -> Unit)? = null

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "stt-worker").also { it.isDaemon = true }
    }
    private var selectedAudioFile: File? = null

    companion object {
        val LANGUAGES = listOf("mr (Marathi)", "hi (Hindi)", "sa (Sanskrit)", "en (English)")
        val LANGUAGE_CODES = mapOf(
            "mr (Marathi)" to "mr",
            "hi (Hindi)" to "hi",
            "sa (Sanskrit)" to "sa",
            "en (English)" to "en"
        )
    }

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        languageCombo.items.addAll(LANGUAGES)
        languageCombo.selectionModel.selectFirst()

        recordDurationSlider.valueProperty().addListener { _, _, v ->
            durationLabel.text = "${v.toInt()}s"
        }

        progressBar.isVisible = false
        transcribeBtn.isDisable = true
        sendToTtsBtn.isDisable = true
    }

    @FXML
    fun onBrowseAudio(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val fc = FileChooser().apply {
            title = "Select Audio File"
            extensionFilters += FileChooser.ExtensionFilter(
                "Audio Files", "*.wav", "*.mp3", "*.m4a", "*.ogg", "*.flac"
            )
        }
        val file = fc.showOpenDialog(outputArea.scene.window) ?: return
        selectedAudioFile = file
        audioFileLabel.text = file.name
        transcribeBtn.isDisable = false
        setStatus("File selected: ${file.name}")
    }

    @FXML
    fun onTranscribe(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val file = selectedAudioFile ?: return
        val langDisplay = languageCombo.value ?: "mr (Marathi)"
        val lang = LANGUAGE_CODES[langDisplay] ?: "mr"

        setStatus("Transcribing audio…", busy = true)
        transcribeBtn.isDisable = true

        val task = SttService(projectRoot?.invoke()).transcribe(file.absolutePath, lang)
        task.setOnSucceeded {
            val result = task.value
            transcribeBtn.isDisable = false
            if (result["success"] == true) {
                val text = result["text"] as? String ?: ""
                val duration = result["duration_seconds"]
                val model = result["model"] as? String ?: "whisper"

                @Suppress("UNCHECKED_CAST")
                val segs = result["segments"] as? List<Map<String, Any?>> ?: emptyList()
                val segText = segs.joinToString("\n") { seg ->
                    "[%.1fs–%.1fs] ${seg["text"]}".format(
                        (seg["start"] as? Number)?.toDouble() ?: 0.0,
                        (seg["end"] as? Number)?.toDouble() ?: 0.0
                    )
                }

                Platform.runLater {
                    outputArea.text = text
                    segmentsArea.text = segText
                    engineLabel.text = "Engine: $model  |  Duration: ${duration ?: "?"}s"
                    sendToTtsBtn.isDisable = text.isBlank()
                }
                setStatus("Transcription complete ✓")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            transcribeBtn.isDisable = false
            setStatus("Failed: ${task.exception?.message}")
        }
        executor.submit(task)
    }

    @FXML
    fun onRecord(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val duration = recordDurationSlider.value.toInt()
        val langDisplay = languageCombo.value ?: "mr (Marathi)"
        val lang = LANGUAGE_CODES[langDisplay] ?: "mr"

        setStatus("Recording for ${duration}s…", busy = true)
        recordBtn.isDisable = true

        val task = SttService(projectRoot?.invoke()).recordAndTranscribe(duration, lang)
        task.setOnSucceeded {
            val result = task.value
            recordBtn.isDisable = false
            if (result["success"] == true) {
                val text = result["text"] as? String ?: ""
                Platform.runLater {
                    outputArea.text = text
                    audioFileLabel.text = result["audio_path"] as? String ?: "recorded.wav"
                    sendToTtsBtn.isDisable = text.isBlank()
                }
                setStatus("Recording & transcription complete ✓")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            recordBtn.isDisable = false
            setStatus("Failed: ${task.exception?.message}")
        }
        executor.submit(task)
    }

    @FXML
    fun onSendToTts(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        onSendToTts?.invoke(outputArea.text)
    }

    @FXML
    fun onClear(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        outputArea.clear()
        segmentsArea.clear()
        audioFileLabel.text = "No file selected"
        engineLabel.text = ""
        selectedAudioFile = null
        transcribeBtn.isDisable = true
        sendToTtsBtn.isDisable = true
        setStatus("Ready")
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
