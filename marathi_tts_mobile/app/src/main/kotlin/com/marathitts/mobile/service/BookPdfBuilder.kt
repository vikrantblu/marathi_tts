package com.marathitts.mobile.service

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.pdf.PdfDocument
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import java.io.File
import java.io.FileOutputStream

/**
 * Build a multi-page PDF from a list of bitmap-on-disk pages and write it to
 * the user's `Downloads/MarathiTTS` directory.
 *
 * Uses the platform's [android.graphics.pdf.PdfDocument] — no third-party
 * dependency.  Each page is rendered at A4 size (595 × 842 points at 72 DPI)
 * with the bitmap centred and scaled to preserve aspect ratio.
 *
 * On Android Q+ the file is created via MediaStore so the user can find it
 * in any file picker.  On pre-Q devices it falls back to the public
 * `Downloads` directory (requires WRITE_EXTERNAL_STORAGE which is granted at
 * install time on those API levels).
 */
object BookPdfBuilder {

    private const val TAG = "BookPdfBuilder"
    private const val A4_WIDTH_PT  = 595
    private const val A4_HEIGHT_PT = 842
    private const val MARGIN_PT    = 24

    /**
     * Result returned to the caller.
     *
     * @param uri        Content URI when MediaStore was used (Q+); else null.
     * @param filePath   Absolute path on legacy storage (pre-Q); else null.
     * @param displayName Final file name as visible to the user.
     */
    data class Result(
        val uri: Uri?,
        val filePath: String?,
        val displayName: String
    )

    /**
     * Build a PDF from the supplied page image paths.
     *
     * @param context      Any context.
     * @param imagePaths   Absolute paths to JPEG/PNG page images.
     * @param baseFileName Base name **without** extension (timestamp appended).
     * @return [Result] on success, throws on I/O failure.
     */
    fun build(
        context: Context,
        imagePaths: List<String>,
        baseFileName: String = "MarathiTTS_Book"
    ): Result {
        require(imagePaths.isNotEmpty()) { "No pages supplied" }

        val timestamp = System.currentTimeMillis()
        val displayName = "${baseFileName}_$timestamp.pdf"

        val pdf = PdfDocument()
        try {
            for ((index, path) in imagePaths.withIndex()) {
                val bmp = BitmapFactory.decodeFile(path)
                if (bmp == null) {
                    Log.w(TAG, "Could not decode page $index ($path) — skipping")
                    continue
                }
                val pageInfo = PdfDocument.PageInfo.Builder(
                    A4_WIDTH_PT, A4_HEIGHT_PT, index + 1
                ).create()
                val page = pdf.startPage(pageInfo)
                drawCentered(page.canvas, bmp)
                pdf.finishPage(page)
                bmp.recycle()
            }

            return when {
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q ->
                    writeViaMediaStore(context, pdf, displayName)
                else ->
                    writeToLegacyDownloads(pdf, displayName)
            }
        } finally {
            pdf.close()
        }
    }

    private fun drawCentered(canvas: Canvas, bmp: Bitmap) {
        val maxW = A4_WIDTH_PT  - MARGIN_PT * 2
        val maxH = A4_HEIGHT_PT - MARGIN_PT * 2
        val srcRatio = bmp.width.toFloat() / bmp.height
        val dstRatio = maxW.toFloat() / maxH
        val drawW: Int; val drawH: Int
        if (srcRatio > dstRatio) {
            drawW = maxW
            drawH = (maxW / srcRatio).toInt()
        } else {
            drawH = maxH
            drawW = (maxH * srcRatio).toInt()
        }
        val left = MARGIN_PT + (maxW - drawW) / 2
        val top  = MARGIN_PT + (maxH - drawH) / 2
        val rect = Rect(left, top, left + drawW, top + drawH)
        val paint = Paint(Paint.FILTER_BITMAP_FLAG)
        canvas.drawBitmap(bmp, null, rect, paint)
    }

    private fun writeViaMediaStore(
        context: Context, pdf: PdfDocument, displayName: String
    ): Result {
        val resolver = context.contentResolver
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, displayName)
            put(MediaStore.Downloads.MIME_TYPE, "application/pdf")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Downloads.RELATIVE_PATH,
                    Environment.DIRECTORY_DOWNLOADS + "/MarathiTTS")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
        }
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: throw java.io.IOException("MediaStore insert failed")
        try {
            resolver.openOutputStream(uri)?.use { pdf.writeTo(it) }
                ?: throw java.io.IOException("MediaStore openOutputStream null")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                values.clear()
                values.put(MediaStore.Downloads.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            }
            return Result(uri = uri, filePath = null, displayName = displayName)
        } catch (e: Exception) {
            resolver.delete(uri, null, null)
            throw e
        }
    }

    private fun writeToLegacyDownloads(pdf: PdfDocument, displayName: String): Result {
        val downloads = Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOWNLOADS
        )
        val dir = File(downloads, "MarathiTTS").apply { if (!exists()) mkdirs() }
        val file = File(dir, displayName)
        FileOutputStream(file).use { pdf.writeTo(it) }
        return Result(uri = Uri.fromFile(file), filePath = file.absolutePath, displayName = displayName)
    }
}
