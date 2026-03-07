package com.marathitts.mobile.util

import android.content.Context
import com.marathitts.mobile.data.AppDatabase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

/**
 * Syncs user phonetic corrections from Room DB to a JSON file that the
 * Python TTS bridge reads at generation time. The JSON is a simple
 * object mapping word → correctedForm.
 */
object PhoneticCorrectionSync {

    private const val FILENAME = "user_corrections.json"

    /** Write all corrections from Room to the JSON file. Call after every insert/delete. */
    suspend fun sync(context: Context) = withContext(Dispatchers.IO) {
        val dao = AppDatabase.getInstance(context).phoneticCorrectionDao()
        val corrections = dao.getAll()
        val json = JSONObject()
        for (c in corrections) {
            json.put(c.word, c.correctedForm)
        }
        val file = File(context.filesDir, FILENAME)
        file.writeText(json.toString(2))
    }

    /** Return the path to the corrections JSON file. */
    fun getFilePath(context: Context): String =
        File(context.filesDir, FILENAME).absolutePath
}
