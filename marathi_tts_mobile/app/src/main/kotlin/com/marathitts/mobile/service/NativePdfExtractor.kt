package com.marathitts.mobile.service

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.File
import java.util.logging.Logger
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Native Android PDF text extractor.
 *
 * Processing pipeline:
 *   1. Android PdfRenderer  → renders each page as a Bitmap at 2x display density
 *   2. ML Kit Devanagari Text Recognition → OCR on each page bitmap
 *   3. Concatenate per-page results → return combined text
 *
 * Used as fallback when pdf_bridge.py (PyPDF2) returns empty text, i.e. when
 * the PDF is image-based rather than text-based.
 */
object NativePdfExtractor {

    private val log = Logger.getLogger(NativePdfExtractor::class.java.name)

    // ML Kit recognizer reused across calls
    private val recognizer by lazy {
        TextRecognition.getClient(DevanagariTextRecognizerOptions.Builder().build())
    }

    /**
     * Extract text from a PDF file using PdfRenderer + ML Kit Devanagari OCR.
     *
     * @param context Android context
     * @param pdfFile PDF file on device storage
     * @param renderDpi  Dots-per-inch for page rendering (higher = better OCR, slower)
     * @return Extracted text or empty string
     */
    suspend fun extract(pdfFile: File, renderDpi: Int = 300): String {
        log.info("NativePdfExtractor: opening ${pdfFile.name} (${pdfFile.length()} bytes)")
        val pfd = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
        return pfd.use {
            val renderer = PdfRenderer(pfd)
            renderer.use {
                val pageTexts = mutableListOf<String>()
                val pageCount = renderer.pageCount
                log.info("NativePdfExtractor: $pageCount pages to render at ${renderDpi}dpi")

                for (i in 0 until pageCount) {
                    val page = renderer.openPage(i)
                    val bitmap = renderPage(page, renderDpi)
                    page.close()

                    val text = recognizeBitmap(bitmap)
                    bitmap.recycle()
                    log.info("NativePdfExtractor: page ${i + 1}/$pageCount → ${text.length} chars")
                    if (text.isNotBlank()) pageTexts.add(text.trim())
                }
                pageTexts.joinToString("\n\n")
            }
        }
    }

    /**
     * Render one PDF page to a Bitmap at the requested DPI.
     * PDF "points" are 1/72 inch — scale to pixels accordingly.
     */
    private fun renderPage(page: PdfRenderer.Page, dpi: Int): Bitmap {
        val scale = dpi / 72f
        val widthPx = (page.width * scale).toInt().coerceAtLeast(1)
        val heightPx = (page.height * scale).toInt().coerceAtLeast(1)
        val bitmap = Bitmap.createBitmap(widthPx, heightPx, Bitmap.Config.ARGB_8888)
        // Fill with white before rendering (PDF background may be transparent)
        bitmap.eraseColor(Color.WHITE)
        page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
        return bitmap
    }

    /**
     * Run ML Kit Devanagari text recognition on a Bitmap.
     * Uses suspendCancellableCoroutine to bridge the Task callback API.
     */
    private suspend fun recognizeBitmap(bitmap: Bitmap): String =
        suspendCancellableCoroutine { cont ->
            val image = InputImage.fromBitmap(bitmap, 0)
            recognizer.process(image)
                .addOnSuccessListener { visionText ->
                    cont.resume(visionText.text)
                }
                .addOnFailureListener { e ->
                    log.warning("NativePdfExtractor: ML Kit failed on page: ${e.message}")
                    cont.resume("")   // soft failure — skip page, don't abort
                }
        }
}
