package com.marathitts.desktop.controller

import com.marathitts.desktop.service.PdfService
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

/** Controller for PDF text extraction tab. */
class PdfController : Initializable {

    @FXML lateinit var browseBtn: Button
    @FXML lateinit var extractBtn: Button
    @FXML lateinit var fileLabel: Label
    @FXML lateinit var textArea: TextArea
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var sendToTtsBtn: Button
    @FXML lateinit var methodLabel: Label

    var projectRoot: (() -> String?)? = null
    var onSendToTts: ((String) -> Unit)? = null

    private var selectedPdf: File? = null
    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "pdf-worker").also { it.isDaemon = true }
    }

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        progressBar.isVisible = false
        extractBtn.isDisable = true
        sendToTtsBtn.isDisable = true
    }

    @FXML
    fun onBrowse(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val fc = FileChooser()
        fc.title = "Select PDF"
        fc.extensionFilters += FileChooser.ExtensionFilter("PDF Files", "*.pdf")
        val file = fc.showOpenDialog(browseBtn.scene.window) ?: return
        selectedPdf = file
        fileLabel.text = file.name
        extractBtn.isDisable = false
        setStatus("PDF selected: ${file.name}")
    }

    @FXML
    fun onExtract(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val pdf = selectedPdf ?: return
        setStatus("Extracting text from PDF…", busy = true)
        extractBtn.isDisable = true

        val task = PdfService(projectRoot?.invoke()).extractFromPdf(pdf.absolutePath)
        task.setOnSucceeded {
            val result = task.value
            extractBtn.isDisable = false
            if (result["success"] == true) {
                val text = result["text"] as? String ?: ""
                val method = result["method"] as? String ?: ""
                Platform.runLater {
                    textArea.text = text
                    methodLabel.text = "Method: $method"
                    sendToTtsBtn.isDisable = text.isBlank()
                }
                setStatus("Extraction complete ✓")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            extractBtn.isDisable = false
            setStatus("Failed: ${task.exception?.message}")
        }
        executor.submit(task)
    }

    @FXML
    fun onSendToTts(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        onSendToTts?.invoke(textArea.text)
    }

    @FXML
    fun onClear(@Suppress("UNUSED_PARAMETER") e: ActionEvent) {
        selectedPdf = null
        fileLabel.text = "No file selected"
        textArea.clear()
        methodLabel.text = ""
        extractBtn.isDisable = true
        sendToTtsBtn.isDisable = true
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
