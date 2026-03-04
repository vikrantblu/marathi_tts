package com.marathitts.mobile.util

import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileInputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Shared utility for Copy / Share / Save actions across all screens.
 */
object OutputActions {

    // ── Copy text to clipboard ──────────────────────────────────────
    fun copyText(context: Context, text: String, label: String = "Marathi Text") {
        if (text.isBlank()) {
            Toast.makeText(context, "Nothing to copy", Toast.LENGTH_SHORT).show()
            return
        }
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(context, "Copied to clipboard", Toast.LENGTH_SHORT).show()
    }

    // ── Share text via Android share sheet ───────────────────────────
    fun shareText(context: Context, text: String, subject: String = "Marathi TTS") {
        if (text.isBlank()) {
            Toast.makeText(context, "Nothing to share", Toast.LENGTH_SHORT).show()
            return
        }
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
            putExtra(Intent.EXTRA_SUBJECT, subject)
        }
        context.startActivity(Intent.createChooser(intent, "Share text via"))
    }

    // ── Share audio file via Android share sheet ─────────────────────
    fun shareAudio(context: Context, audioPath: String) {
        val file = File(audioPath)
        if (!file.exists()) {
            Toast.makeText(context, "Audio file not found", Toast.LENGTH_SHORT).show()
            return
        }
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "audio/mpeg"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, "Share audio via"))
    }

    // ── Save text to Downloads ──────────────────────────────────────
    fun saveTextToDownloads(context: Context, text: String, filenamePrefix: String = "marathi_tts") {
        if (text.isBlank()) {
            Toast.makeText(context, "Nothing to save", Toast.LENGTH_SHORT).show()
            return
        }
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val filename = "${filenamePrefix}_$timestamp.txt"

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                // Use MediaStore for Android 10+
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, filename)
                    put(MediaStore.Downloads.MIME_TYPE, "text/plain")
                    put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                }
                val uri = context.contentResolver.insert(
                    MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                    values
                )
                uri?.let {
                    context.contentResolver.openOutputStream(it)?.use { out ->
                        out.write(text.toByteArray(Charsets.UTF_8))
                    }
                }
            } else {
                @Suppress("DEPRECATION")
                val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                dir.mkdirs()
                File(dir, filename).writeText(text, Charsets.UTF_8)
            }
            Toast.makeText(context, "Saved to Downloads/$filename", Toast.LENGTH_LONG).show()
        } catch (e: Exception) {
            Toast.makeText(context, "Save failed: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    // ── Save audio to Downloads ─────────────────────────────────────
    fun saveAudioToDownloads(context: Context, audioPath: String, filenamePrefix: String = "marathi_tts") {
        val srcFile = File(audioPath)
        if (!srcFile.exists()) {
            Toast.makeText(context, "Audio file not found", Toast.LENGTH_SHORT).show()
            return
        }
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val ext = srcFile.extension.ifEmpty { "mp3" }
        val filename = "${filenamePrefix}_$timestamp.$ext"

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, filename)
                    put(MediaStore.Downloads.MIME_TYPE, "audio/mpeg")
                    put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                }
                val uri = context.contentResolver.insert(
                    MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                    values
                )
                uri?.let {
                    context.contentResolver.openOutputStream(it)?.use { out ->
                        FileInputStream(srcFile).use { inp -> inp.copyTo(out) }
                    }
                }
            } else {
                @Suppress("DEPRECATION")
                val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                dir.mkdirs()
                srcFile.copyTo(File(dir, filename), overwrite = true)
            }
            Toast.makeText(context, "Saved to Downloads/$filename", Toast.LENGTH_LONG).show()
        } catch (e: Exception) {
            Toast.makeText(context, "Save failed: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
}
