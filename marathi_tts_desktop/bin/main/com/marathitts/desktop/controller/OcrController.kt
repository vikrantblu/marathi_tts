package com.marathitts.desktop.controller

import com.marathitts.desktop.service.OcrService
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import javafx.scene.image.Image
import javafx.scene.image.ImageView
import javafx.stage.FileChooser
import java.io.File
import java.net.URL
import java.util.ResourceBundle
import java.util.concurrent.Executors

/** Controller for the OCR (Image → Text) tab. */
class OcrController : Initializable {

    @FXML lateinit var imageView: ImageView
    @FXML lateinit var extractedTextArea: TextArea
    @FXML lateinit var extractBtn: Button
    @FXML lateinit var browseBtn: Button
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var sendToTtsBtn: Button

    var projectRoot: (() -> String?)? = null
    var onSendToTts: ((String) -> Unit)? = null

    private var selectedImageFile: File? = null
    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "ocr-worker").also { it.isDaemon = true }
    }

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        progressBar.isVisible = false
        extractBtn.isDisable = true
        sendToTtsBtn.isDisable = true
    }

    @FXML
    fun onBrowseImage(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val fc = FileChooser()
        fc.title = "Select Image"
        fc.extensionFilters += FileChooser.ExtensionFilter("Images", "*.jpg", "*.jpeg", "*.png", "*.bmp")
        val file = fc.showOpenDialog(browseBtn.scene.window) ?: return
        selectedImageFile = file
        imageView.image = Image(file.toURI().toString())
        extractBtn.isDisable = false
        setStatus("Image loaded: ${file.name}")
    }

    @FXML
    fun onExtract(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val imgFile = selectedImageFile ?: return
        setStatus("Extracting text…", busy = true)
        extractBtn.isDisable = true

        val task = OcrService(projectRoot?.invoke()).extractFromImage(imgFile.absolutePath)
        task.setOnSucceeded {
            val result = task.value
            extractBtn.isDisable = false
            if (result["success"] == true) {
                val text = result["text"] as? String ?: ""
                Platform.runLater {
                    extractedTextArea.text = text
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
        onSendToTts?.invoke(extractedTextArea.text)
    }

    @FXML
    fun onClear(@Suppress("UNUSED_PARAMETER") e: ActionEvent) {
        imageView.image = null
        extractedTextArea.clear()
        selectedImageFile = null
        extractBtn.isDisable = true
        sendToTtsBtn.isDisable = true
        setStatus("Ready")
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
