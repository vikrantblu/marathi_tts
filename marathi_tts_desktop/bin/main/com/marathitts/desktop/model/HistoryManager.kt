package com.marathitts.desktop.model

import javafx.collections.FXCollections
import javafx.collections.ObservableList
import java.util.concurrent.atomic.AtomicInteger

/**
 * In-memory history store. Survives tab switches for the lifetime of the JVM.
 *
 * Thread-safe: add() can be called from any thread; the ObservableList is
 * always mutated on the JavaFX Application Thread via Platform.runLater.
 */
object HistoryManager {

    private val counter = AtomicInteger(0)

    /** The backing observable list — bind a ListView directly to this. */
    val entries: ObservableList<HistoryEntry> = FXCollections.observableArrayList()

    private const val MAX_ENTRIES = 200

    /**
     * Adds a new entry to the front of the list.
     * Trims text fields to 2000 chars to avoid huge memory use.
     *
     * @param category  One of: TTS, STT, OCR, PDF, WEB, CORRECTION, MODI, EMOTION, STOTRA
     * @param inputText The source text / URL / filename.
     * @param outputText The result text.
     * @param audioPath Optional audio file path (TTS only).
     */
    fun add(
        category: String,
        inputText: String,
        outputText: String,
        audioPath: String? = null
    ) {
        val entry = HistoryEntry(
            id        = counter.incrementAndGet(),
            category  = category,
            inputText = inputText.take(2000),
            outputText= outputText.take(2000),
            audioPath = audioPath,
        )
        javafx.application.Platform.runLater {
            entries.add(0, entry)
            while (entries.size > MAX_ENTRIES) entries.removeAt(entries.size - 1)
        }
    }

    /** Remove a single entry. */
    fun remove(entry: HistoryEntry) = javafx.application.Platform.runLater { entries.remove(entry) }

    /** Remove all entries. */
    fun clear() = javafx.application.Platform.runLater { entries.clear() }
}
