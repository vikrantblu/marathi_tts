package com.marathitts.desktop.controller

import com.marathitts.desktop.model.HistoryEntry
import com.marathitts.desktop.model.HistoryManager
import com.marathitts.desktop.util.copyToClipboard
import javafx.collections.transformation.FilteredList
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import javafx.scene.layout.HBox
import java.net.URL
import java.util.ResourceBundle

/** Controller for the Generation History tab. */
class HistoryController : Initializable {

    @FXML lateinit var historyList: ListView<HistoryEntry>
    @FXML lateinit var countLabel: Label
    @FXML lateinit var emptyLabel: Label
    @FXML lateinit var filterBox: HBox
    @FXML lateinit var filterAll:    ToggleButton
    @FXML lateinit var filterTts:    ToggleButton
    @FXML lateinit var filterStt:    ToggleButton
    @FXML lateinit var filterOcr:    ToggleButton
    @FXML lateinit var filterPdf:    ToggleButton
    @FXML lateinit var filterWeb:    ToggleButton
    @FXML lateinit var filterCorr:   ToggleButton
    @FXML lateinit var filterModi:   ToggleButton
    @FXML lateinit var filterEmot:   ToggleButton
    @FXML lateinit var filterStotra: ToggleButton

    @FXML lateinit var detailCategoryBadge: Label
    @FXML lateinit var detailTimeLabel:     Label
    @FXML lateinit var detailInputArea:     TextArea
    @FXML lateinit var detailOutputArea:    TextArea
    @FXML lateinit var detailAudioLabel:    Label
    @FXML lateinit var detailCopyBtn:       Button
    @FXML lateinit var detailSendToTtsBtn:  Button
    @FXML lateinit var detailDeleteBtn:     Button

    var onSendToTts: ((String) -> Unit)? = null

    private lateinit var filtered: FilteredList<HistoryEntry>
    private var activeCategory: String = "All"

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        filtered = FilteredList(HistoryManager.entries) { true }
        historyList.items = filtered

        // Update count label whenever list changes
        HistoryManager.entries.addListener(javafx.beans.InvalidationListener {
            updateCountLabel()
        })
        filtered.predicateProperty().addListener { _ -> updateCountLabel() }

        // Custom cell factory: category badge + snippet + time
        historyList.setCellFactory {
            object : ListCell<HistoryEntry>() {
                override fun updateItem(entry: HistoryEntry?, empty: Boolean) {
                    super.updateItem(entry, empty)
                    if (empty || entry == null) {
                        graphic = null; text = null
                        return
                    }
                    val badge = Label(entry.category).apply { styleClass.add("chip-label") }
                    val snippet = Label(entry.snippet).apply {
                        style = "-fx-text-fill: -fx-text-inner-color;"
                        maxWidth = 260.0
                        isWrapText = false
                    }
                    val time = Label(entry.timeLabel).apply { styleClass.add("status-text") }
                    val top = javafx.scene.layout.HBox(6.0, badge, time)
                    val cell = javafx.scene.layout.VBox(2.0, top, snippet)
                    cell.style = "-fx-padding: 4 0 4 0;"
                    graphic = cell
                    text = null
                }
            }
        }

        // Selection → show detail
        historyList.selectionModel.selectedItemProperty().addListener { _, _, entry ->
            showDetail(entry)
        }

        // ToggleButton group — only one active at a time
        val buttons = listOf(filterAll, filterTts, filterStt, filterOcr, filterPdf,
            filterWeb, filterCorr, filterModi, filterEmot, filterStotra)
        buttons.forEach { btn ->
            btn.selectedProperty().addListener { _, _, selected ->
                if (selected) {
                    buttons.filter { it != btn }.forEach { it.isSelected = false }
                }
            }
        }

        clearDetail()
        updateCountLabel()
    }

    // ── Filter handlers ─────────────────────────────────────────────────────

    @FXML fun onFilter(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        activeCategory = when {
            filterTts.isSelected    -> "TTS"
            filterStt.isSelected    -> "STT"
            filterOcr.isSelected    -> "OCR"
            filterPdf.isSelected    -> "PDF"
            filterWeb.isSelected    -> "WEB"
            filterCorr.isSelected   -> "CORRECTION"
            filterModi.isSelected   -> "MODI"
            filterEmot.isSelected   -> "EMOTION"
            filterStotra.isSelected -> "STOTRA"
            else                    -> { filterAll.isSelected = true; "All" }
        }
        filtered.setPredicate { entry ->
            activeCategory == "All" || entry.category == activeCategory
        }
    }

    @FXML fun onClearAll(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val dlg = Alert(Alert.AlertType.CONFIRMATION).apply {
            title = "Clear History"
            headerText = "Delete all history entries?"
            contentText = "This cannot be undone."
        }
        if (dlg.showAndWait().orElse(ButtonType.CANCEL) == ButtonType.OK) {
            HistoryManager.clear()
            clearDetail()
        }
    }

    // ── Detail pane handlers ─────────────────────────────────────────────────

    @FXML fun onDetailCopy(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = detailOutputArea.text.ifBlank { detailInputArea.text }
        copyToClipboard(text)
    }

    @FXML fun onDetailSendToTts(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = detailOutputArea.text.ifBlank { detailInputArea.text }
        if (text.isNotBlank()) onSendToTts?.invoke(text)
    }

    @FXML fun onDetailDelete(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val entry = historyList.selectionModel.selectedItem ?: return
        HistoryManager.remove(entry)
        clearDetail()
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private fun showDetail(entry: HistoryEntry?) {
        if (entry == null) { clearDetail(); return }
        detailCategoryBadge.text = entry.category
        detailTimeLabel.text = entry.timeLabel
        detailInputArea.text = entry.inputText
        detailOutputArea.text = entry.outputText
        detailAudioLabel.text = if (entry.audioPath != null) "🎵 ${entry.audioPath}" else ""
        detailCopyBtn.isDisable = false
        detailSendToTtsBtn.isDisable = false
        detailDeleteBtn.isDisable = false
    }

    private fun clearDetail() {
        detailCategoryBadge.text = ""
        detailTimeLabel.text = ""
        detailInputArea.clear()
        detailOutputArea.clear()
        detailAudioLabel.text = ""
        detailCopyBtn.isDisable = true
        detailSendToTtsBtn.isDisable = true
        detailDeleteBtn.isDisable = true
    }

    private fun updateCountLabel() {
        val total = HistoryManager.entries.size
        val shown = filtered.size
        countLabel.text = if (activeCategory == "All") "$total entries" else "$shown / $total"
        emptyLabel.isVisible = total == 0
        historyList.isVisible = total > 0
    }
}
