package com.marathitts.desktop.controller

import com.marathitts.desktop.service.CorrectionService
import com.marathitts.desktop.service.FormatService
import com.marathitts.desktop.service.SuggestCorrectionService
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import java.net.URL
import java.util.ResourceBundle
import java.util.concurrent.Executors

/** Controller for the AI Text Correction tab. */
class CorrectionController : Initializable {

    @FXML lateinit var inputArea: TextArea
    @FXML lateinit var outputArea: TextArea
    @FXML lateinit var correctBtn: Button
    @FXML lateinit var formatBtn: Button
    @FXML lateinit var suggestBtn: Button
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var sendToTtsBtn: Button
    @FXML lateinit var methodLabel: Label

    var projectRoot: (() -> String?)? = null
    var onSendToTts: ((String) -> Unit)? = null

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "correction-worker").also { it.isDaemon = true }
    }

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        progressBar.isVisible = false
        sendToTtsBtn.isDisable = true
    }

    @FXML
    fun onCorrect(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = inputArea.text.trim()
        if (text.isEmpty()) { setStatus("Please enter text."); return }

        setStatus("Correcting text…", busy = true)
        correctBtn.isDisable = true

        val task = CorrectionService(projectRoot?.invoke()).correct(text)
        task.setOnSucceeded {
            val result = task.value
            correctBtn.isDisable = false
            if (result["success"] == true) {
                val corrected = result["corrected_text"] as? String ?: text
                val method = result["method"] as? String ?: ""
                Platform.runLater {
                    outputArea.text = corrected
                    methodLabel.text = "Method: $method"
                    sendToTtsBtn.isDisable = corrected.isBlank()
                }
                setStatus("Correction applied ✓")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            correctBtn.isDisable = false
            setStatus("Failed: ${task.exception?.message}")
        }
        executor.submit(task)
    }

    @FXML
    fun onFormat(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = inputArea.text.trim()
        if (text.isEmpty()) { setStatus("Please enter text to format."); return }

        setStatus("Formatting text…", busy = true)
        formatBtn.isDisable = true

        val task = FormatService(projectRoot?.invoke()).format(text)
        task.setOnSucceeded {
            val result = task.value
            formatBtn.isDisable = false
            if (result["success"] == true) {
                val formatted = result["formatted_text"] as? String ?: text
                Platform.runLater {
                    outputArea.text = formatted
                    methodLabel.text = "Method: text_formatter"
                    sendToTtsBtn.isDisable = formatted.isBlank()
                }
                setStatus("Text formatted ✓")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            formatBtn.isDisable = false
            setStatus("Failed: ${task.exception?.message}")
        }
        executor.submit(task)
    }

    @FXML
    fun onSuggestCorrection(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val incorrect = inputArea.text.trim()
        val correct = outputArea.text.trim()
        if (incorrect.isEmpty() || correct.isEmpty()) {
            setStatus("Enter original text in the top box and corrected text in the output box.")
            return
        }

        // Show a simple dialog to confirm the pair
        val dialog = Dialog<ButtonType>().apply {
            title = "Submit Correction Suggestion"
            headerText = "Submit this correction for model retraining?"
            dialogPane.content = javafx.scene.control.TextArea(
                "Incorrect:\n$incorrect\n\nCorrect:\n$correct"
            ).also { it.isEditable = false; it.prefRowCount = 6 }
            dialogPane.buttonTypes.addAll(ButtonType.OK, ButtonType.CANCEL)
        }
        val result = dialog.showAndWait()
        if (result.orElse(ButtonType.CANCEL) != ButtonType.OK) return

        setStatus("Submitting suggestion…", busy = true)
        val task = SuggestCorrectionService(projectRoot?.invoke()).suggest(incorrect, correct)
        task.setOnSucceeded {
            val r = task.value
            if (r["success"] == true) setStatus("Suggestion submitted ✓")
            else setStatus("Error: ${r["error"]}")
        }
        task.setOnFailed { setStatus("Failed: ${task.exception?.message}") }
        executor.submit(task)
    }

    @FXML
    fun onSendToTts(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        onSendToTts?.invoke(outputArea.text)
    }

    @FXML
    fun onClear(@Suppress("UNUSED_PARAMETER") e: ActionEvent) {
        inputArea.clear(); outputArea.clear()
        methodLabel.text = ""
        sendToTtsBtn.isDisable = true
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
