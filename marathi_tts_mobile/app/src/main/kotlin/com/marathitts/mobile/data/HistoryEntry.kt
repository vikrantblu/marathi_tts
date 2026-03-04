package com.marathitts.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * A single history entry — any output from any screen.
 * category values: TTS, STT, OCR, PDF, WEB, CORRECTION, MODI, EMOTION, STOTRA, BOOK_READER
 */
@Entity(tableName = "history")
data class HistoryEntry(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val category: String,          // e.g. "TTS", "OCR", "STT"
    val inputText: String,         // user input / source
    val outputText: String,        // result text
    val audioPath: String? = null, // generated audio file (TTS/Stotra)
    val engine: String? = null,    // engine used
    val timestamp: Long = System.currentTimeMillis()
)
