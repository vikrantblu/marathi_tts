package com.marathitts.mobile.util

import android.content.Context
import com.marathitts.mobile.data.AppDatabase
import com.marathitts.mobile.data.HistoryEntry
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Lightweight helper that any Fragment can call to log a history entry.
 * Performs insert + trim on IO dispatcher — fire-and-forget.
 *
 * Usage:
 *   HistoryLogger.log(context, "TTS", inputText, outputText, audioPath, engine)
 */
object HistoryLogger {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    fun log(
        context: Context,
        category: String,
        inputText: String,
        outputText: String,
        audioPath: String? = null,
        engine: String? = null
    ) {
        if (inputText.isBlank() && outputText.isBlank()) return
        scope.launch {
            try {
                val dao = AppDatabase.getInstance(context.applicationContext).historyDao()
                dao.insert(
                    HistoryEntry(
                        category = category,
                        inputText = inputText.take(2000),
                        outputText = outputText.take(2000),
                        audioPath = audioPath,
                        engine = engine
                    )
                )
                dao.trimOld()
            } catch (_: Exception) {
                // Silently ignore — history is non-critical
            }
        }
    }
}
