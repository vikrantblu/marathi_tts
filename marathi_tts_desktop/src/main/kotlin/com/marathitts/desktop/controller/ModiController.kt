package com.marathitts.desktop.controller

import com.marathitts.desktop.service.ScriptConverterService
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import java.net.URL
import java.util.ResourceBundle
import java.util.concurrent.Executors

/**
 * Controller for the Script Converter tab.
 *
 * Supported conversions:
 *  - Modi script → Devanagari
 *  - Devanagari → IAST (transliteration)
 *  - IAST → Devanagari
 *  - Brahmi → Devanagari
 *
 * Send result to TTS tab for audio generation.
 */
class ModiController : Initializable {

    @FXML lateinit var inputArea: TextArea
    @FXML lateinit var outputArea: TextArea
    @FXML lateinit var modeCombo: ComboBox<String>
    @FXML lateinit var convertBtn: Button
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var sendToTtsBtn: Button
    @FXML lateinit var charCountLabel: Label
    @FXML lateinit var modeDescLabel: Label

    var projectRoot: (() -> String?)? = null
    var onSendToTts: ((String) -> Unit)? = null

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "modi-worker").also { it.isDaemon = true }
    }

    companion object {
        val MODES = listOf(
            "modi_to_devanagari",
            "devanagari_to_iast",
            "iast_to_devanagari",
            "brahmi_to_devanagari"
        )
        val MODE_LABELS = mapOf(
            "modi_to_devanagari"    to "𑘦𑘻𑘛𑘲 Modi → देवनागरी Devanagari",
            "devanagari_to_iast"    to "देवनागरी Devanagari → IAST (romanization)",
            "iast_to_devanagari"    to "IAST (romanization) → देवनागरी Devanagari",
            "brahmi_to_devanagari"  to "𑀩𑁆𑀭𑀸𑀳𑁆𑀫𑀻 Brahmi → देवनागरी Devanagari"
        )
        val MODE_HINTS = mapOf(
            "modi_to_devanagari"    to "Paste Modi script (Unicode block U+11600–U+1165F) here.",
            "devanagari_to_iast"    to "Paste modern Devanagari text to get IAST romanization.",
            "iast_to_devanagari"    to "Paste IAST romanized text (e.g. mārata) to get Devanagari.",
            "brahmi_to_devanagari"  to "Paste Brahmi script (Unicode block U+11000–U+1107F) here."
        )
    }

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        modeCombo.items.addAll(MODES)
        modeCombo.selectionModel.selectFirst()

        modeCombo.selectionModel.selectedItemProperty().addListener { _, _, newMode ->
            updateModeDescription(newMode)
        }
        updateModeDescription(MODES[0])

        inputArea.textProperty().addListener { _, _, text ->
            charCountLabel.text = "${text.length} chars"
        }

        progressBar.isVisible = false
        sendToTtsBtn.isDisable = true
    }

    private fun updateModeDescription(mode: String) {
        modeDescLabel.text = MODE_HINTS[mode] ?: ""
        inputArea.promptText = MODE_HINTS[mode] ?: "Enter input text…"
    }

    @FXML
    fun onConvert(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = inputArea.text.trim()
        if (text.isEmpty()) { setStatus("Please enter input text."); return }

        val mode = modeCombo.value ?: MODES[0]
        setStatus("Converting…", busy = true)
        convertBtn.isDisable = true

        val task = ScriptConverterService(projectRoot?.invoke()).convert(text, mode)
        task.setOnSucceeded {
            val result = task.value
            convertBtn.isDisable = false
            if (result["success"] == true) {
                val converted = result["converted_text"] as? String ?: ""
                Platform.runLater {
                    outputArea.text = converted
                    sendToTtsBtn.isDisable = converted.isBlank()
                }
                val note = if (result["note"] != null) " (${result["note"]})" else ""
                setStatus("Conversion complete ✓$note")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            convertBtn.isDisable = false
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
        inputArea.clear()
        outputArea.clear()
        sendToTtsBtn.isDisable = true
        setStatus("Ready")
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
