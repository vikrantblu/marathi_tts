package com.marathitts.mobile.util

import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.media.MediaMetadataRetriever
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

    // ── FEAT-76: Export audio with ID3 metadata ─────────────────────
    /**
     * Save audio to the Music library with metadata (title, artist, album, language).
     * On Android Q+, uses MediaStore.Audio.Media with proper columns.
     * On older versions, copies to Music directory in external storage.
     */
    fun exportAudioWithMetadata(
        context: Context,
        audioPath: String,
        title: String = "Marathi TTS",
        artist: String = "Marathi TTS",
        album: String = "Marathi TTS Generations",
        language: String = "mr"
    ) {
        val srcFile = File(audioPath)
        if (!srcFile.exists()) {
            Toast.makeText(context, "Audio file not found", Toast.LENGTH_SHORT).show()
            return
        }

        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val ext = srcFile.extension.ifEmpty { "mp3" }
        val safeTitle = title.take(80).replace(Regex("[^\\w\\s\\-।॥]"), "").trim()
        val filename = "${safeTitle.ifEmpty { "marathi_tts" }}_$timestamp.$ext"

        // Get duration from source file
        val durationMs = try {
            MediaMetadataRetriever().use { mmr ->
                mmr.setDataSource(audioPath)
                mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
            }
        } catch (_: Exception) { 0L }

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Audio.Media.DISPLAY_NAME, filename)
                    put(MediaStore.Audio.Media.MIME_TYPE, if (ext == "wav") "audio/wav" else "audio/mpeg")
                    put(MediaStore.Audio.Media.RELATIVE_PATH, "${Environment.DIRECTORY_MUSIC}/MarathiTTS")
                    put(MediaStore.Audio.Media.TITLE, title)
                    put(MediaStore.Audio.Media.ARTIST, artist)
                    put(MediaStore.Audio.Media.ALBUM, album)
                    if (durationMs > 0) put(MediaStore.Audio.Media.DURATION, durationMs)
                    put(MediaStore.Audio.Media.IS_PENDING, 1)
                }
                val uri = context.contentResolver.insert(
                    MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                    values
                )
                uri?.let {
                    context.contentResolver.openOutputStream(it)?.use { out ->
                        FileInputStream(srcFile).use { inp -> inp.copyTo(out) }
                    }
                    // Mark as ready
                    val update = ContentValues().apply {
                        put(MediaStore.Audio.Media.IS_PENDING, 0)
                    }
                    context.contentResolver.update(it, update, null, null)
                }
                Toast.makeText(context, "Exported to Music/MarathiTTS/$filename", Toast.LENGTH_LONG).show()
            } else {
                @Suppress("DEPRECATION")
                val dir = File(
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC),
                    "MarathiTTS"
                )
                dir.mkdirs()
                srcFile.copyTo(File(dir, filename), overwrite = true)
                Toast.makeText(context, "Exported to Music/MarathiTTS/$filename", Toast.LENGTH_LONG).show()
            }
        } catch (e: Exception) {
            Toast.makeText(context, "Export failed: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    /**
     * Concatenate multiple audio chunks into a single MP3 file.
     * MP3 frames are independently decodable, so byte-level concatenation works.
     */
    fun concatenateAudioChunks(chunks: List<String>, outputPath: String): Boolean {
        return try {
            File(outputPath).outputStream().use { out ->
                for (chunk in chunks) {
                    val f = File(chunk)
                    if (f.exists()) {
                        FileInputStream(f).use { it.copyTo(out) }
                    }
                }
            }
            true
        } catch (_: Exception) { false }
    }
}
