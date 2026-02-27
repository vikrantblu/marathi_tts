package com.marathitts.desktop.controller

import com.marathitts.desktop.service.WebFetchService
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import java.net.URL
import java.util.ResourceBundle
import java.util.concurrent.Executors

/** Controller for the Web Fetch (URL → Text) tab. */
class WebFetchController : Initializable {

    @FXML lateinit var urlField: TextField
    @FXML lateinit var fetchBtn: Button
    @FXML lateinit var textArea: TextArea
    @FXML lateinit var titleLabel: Label
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var sendToTtsBtn: Button

    var projectRoot: (() -> String?)? = null
    var onSendToTts: ((String) -> Unit)? = null

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "webfetch-worker").also { it.isDaemon = true }
    }

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        progressBar.isVisible = false
        sendToTtsBtn.isDisable = true

        // Allow fetch on Enter
        urlField.setOnAction { onFetch(it) }
    }

    @FXML
    fun onFetch(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val url = urlField.text.trim()
        if (url.isEmpty()) { setStatus("Enter a URL first."); return }

        setStatus("Fetching content…", busy = true)
        fetchBtn.isDisable = true

        val task = WebFetchService(projectRoot?.invoke()).fetchUrl(url)
        task.setOnSucceeded {
            val result = task.value
            fetchBtn.isDisable = false
            if (result["success"] == true) {
                val text = result["text"] as? String ?: ""
                val title = result["title"] as? String ?: ""
                Platform.runLater {
                    textArea.text = text
                    titleLabel.text = title
                    sendToTtsBtn.isDisable = text.isBlank()
                }
                setStatus("Content fetched ✓")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            fetchBtn.isDisable = false
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
        urlField.clear()
        textArea.clear()
        titleLabel.text = ""
        sendToTtsBtn.isDisable = true
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
