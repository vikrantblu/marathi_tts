package com.marathitts.desktop.model

/**
 * A single entry in the generation history.
 *
 * @param id        Monotonically increasing ID.
 * @param category  One of: TTS, STT, OCR, PDF, WEB, CORRECTION, MODI, EMOTION, STOTRA
 * @param inputText The text/URL/path that was processed.
 * @param outputText The text result (transcript, extracted text, emotion summary, etc.)
 * @param audioPath Optional path to a generated audio file (TTS only).
 * @param timestamp Epoch-millis when the entry was created.
 */
data class HistoryEntry(
    val id: Int,
    val category: String,
    val inputText: String,
    val outputText: String,
    val audioPath: String? = null,
    val timestamp: Long = System.currentTimeMillis()
) {
    /** A short display label: first 80 non-whitespace chars of outputText (or inputText if output empty). */
    val snippet: String get() {
        val src = outputText.ifBlank { inputText }
        return src.replace('\n', ' ').replace('\r', ' ').trim().take(80).let {
            if ((outputText.ifBlank { inputText }).length > 80) "$it…" else it
        }
    }

    /** Human-readable timestamp e.g. "14:35" (today) or "Mar 4" (other days). */
    val timeLabel: String get() {
        val cal = java.util.Calendar.getInstance().apply { timeInMillis = timestamp }
        val now = java.util.Calendar.getInstance()
        return if (cal.get(java.util.Calendar.DAY_OF_YEAR) == now.get(java.util.Calendar.DAY_OF_YEAR) &&
            cal.get(java.util.Calendar.YEAR) == now.get(java.util.Calendar.YEAR)) {
            "%02d:%02d".format(cal.get(java.util.Calendar.HOUR_OF_DAY), cal.get(java.util.Calendar.MINUTE))
        } else {
            val months = arrayOf("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")
            "${months[cal.get(java.util.Calendar.MONTH)]} ${cal.get(java.util.Calendar.DAY_OF_MONTH)}"
        }
    }
}
