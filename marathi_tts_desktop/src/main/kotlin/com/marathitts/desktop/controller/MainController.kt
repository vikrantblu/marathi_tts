package com.marathitts.desktop.controller

import com.marathitts.desktop.service.*
import javafx.application.Platform
import javafx.concurrent.Task
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import javafx.scene.layout.VBox
import javafx.stage.FileChooser
import java.net.URL
import java.util.ResourceBundle
import java.util.prefs.Preferences

/**
 * Main controller for the entire application window.
 * Wires together the tab views.
 */
class MainController : Initializable {

    @FXML lateinit var tabPane: TabPane
    @FXML lateinit var statusBar: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var projectRootField: TextField

    // Child controllers injected by JavaFX via fx:id on the <fx:include> tags.
    // Convention: fx:id="ttsView" → field name "ttsViewController"
    @FXML lateinit var ttsViewController: TtsController
    @FXML lateinit var emotionViewController: EmotionController
    @FXML lateinit var ocrViewController: OcrController
    @FXML lateinit var correctionViewController: CorrectionController
    @FXML lateinit var pdfViewController: PdfController
    @FXML lateinit var webFetchViewController: WebFetchController
    @FXML lateinit var sttViewController: SttController
    @FXML lateinit var modiViewController: ModiController

    private val prefs = Preferences.userNodeForPackage(MainController::class.java)

    /** Tab index of the TTS tab (must match order in MainView.fxml). */
    private val TTS_TAB_INDEX = 0

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        // Restore last used project root path
        projectRootField.text = prefs.get("project_root", "")
        projectRootField.textProperty().addListener { _, _, newVal ->
            prefs.put("project_root", newVal)
        }

        // Wire projectRoot lambda into every sub-controller so they all
        // pick up the current field value at call time (not at init time).
        val rootProvider: () -> String? = { resolvedProjectRoot }
        ttsViewController.projectRoot        = rootProvider
        emotionViewController.projectRoot    = rootProvider
        ocrViewController.projectRoot        = rootProvider
        correctionViewController.projectRoot = rootProvider
        pdfViewController.projectRoot        = rootProvider
        webFetchViewController.projectRoot   = rootProvider
        sttViewController.projectRoot        = rootProvider
        modiViewController.projectRoot       = rootProvider

        // Wire "Send to TTS" callbacks for every tab that has this button.
        // Each callback populates the TTS text area and switches to the TTS tab.
        val sendToTts: (String) -> Unit = { text ->
            ttsViewController.receiveText(text)
            tabPane.selectionModel.select(TTS_TAB_INDEX)
        }
        webFetchViewController.onSendToTts   = sendToTts
        ocrViewController.onSendToTts        = sendToTts
        correctionViewController.onSendToTts = sendToTts
        pdfViewController.onSendToTts        = sendToTts
        sttViewController.onSendToTts        = sendToTts
        modiViewController.onSendToTts       = sendToTts

        setStatus("Ready")
    }

    fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusBar.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }

    @FXML
    fun onBrowseProjectRoot(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val dc = javafx.stage.DirectoryChooser()
        dc.title = "Select marathi_tts project root"
        val dir = dc.showDialog(tabPane.scene.window)
        if (dir != null) projectRootField.text = dir.absolutePath
    }

    val resolvedProjectRoot: String?
        get() = projectRootField.text.takeIf { it.isNotBlank() }
}

