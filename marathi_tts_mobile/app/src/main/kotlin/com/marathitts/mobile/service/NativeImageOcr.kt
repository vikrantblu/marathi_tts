package com.marathitts.mobile.service

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Paint
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.File
import java.util.logging.Logger
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Native on-device Devanagari OCR using ML Kit.
 *
 * Includes image preprocessing (downscale + grayscale + contrast enhance)
 * and post-OCR cleanup of misrecognized Unicode characters.
 *
 * Works entirely offline once the ML Kit model is downloaded.
 */
object NativeImageOcr {

    private val log = Logger.getLogger(NativeImageOcr::class.java.name)
    private const val MAX_OCR_DIM = 2400

    private val recognizer by lazy {
        TextRecognition.getClient(DevanagariTextRecognizerOptions.Builder().build())
    }

    /** Unicode noise that ML Kit commonly introduces from book/document scans. */
    private val OCR_NOISE_RE = Regex(
        """[\u25CC\u02D0\u02D1\u0300-\u036F\u200B-\u200F\u2028\u2029\uFEFF\u00B7\u02BC\u02BB]"""
    )

    /**
     * Extract Devanagari text from an image file.
     * Preprocesses the image (grayscale + contrast) before OCR for better accuracy.
     *
     * @param imageFile JPEG/PNG file on device storage
     * @return Extracted and cleaned text, or empty string
     */
    suspend fun extract(imageFile: File): String {
        log.info("NativeImageOcr: opening ${imageFile.name} (${imageFile.length()} bytes)")

        val rawBitmap = BitmapFactory.decodeFile(imageFile.absolutePath)
            ?: throw IllegalArgumentException("Cannot decode image: ${imageFile.name}")

        // Preprocess: downscale → grayscale → contrast enhance
        val preprocessed = preprocessForOcr(rawBitmap)
        if (preprocessed !== rawBitmap) rawBitmap.recycle()

        val inputImage = InputImage.fromBitmap(preprocessed, 0)

        val rawText: String = suspendCancellableCoroutine { cont ->
            recognizer.process(inputImage)
                .addOnSuccessListener { visionText ->
                    // Use block-based extraction for better reading order
                    val text = extractSortedText(visionText)
                    log.info("NativeImageOcr: extracted ${text.length} chars")
                    preprocessed.recycle()
                    cont.resume(text)
                }
                .addOnFailureListener { e ->
                    log.warning("NativeImageOcr: recognition failed: ${e.message}")
                    preprocessed.recycle()
                    cont.resumeWithException(e)
                }
        }

        // Post-OCR cleanup
        return cleanOcrText(rawText)
    }

    /** Sort text blocks by vertical position; drop hallucinated non-Devanagari blocks. */
    private fun extractSortedText(visionText: com.google.mlkit.vision.text.Text): String {
        if (visionText.textBlocks.isEmpty()) return visionText.text

        val sorted = visionText.textBlocks.sortedBy { it.boundingBox?.top ?: 0 }
        return buildString {
            for ((idx, block) in sorted.withIndex()) {
                // Hallucination filter: skip blocks that are mostly non-Devanagari
                val letters = block.text.count { it.isLetter() }
                val devLetters = block.text.count { it in '\u0900'..'\u097F' }
                if (letters > 6 && devLetters.toFloat() / letters < 0.25f) continue

                var addedAny = false
                for ((lineIdx, line) in block.lines.withIndex()) {
                    val ll = line.text.count { it.isLetter() }
                    val ld = line.text.count { it in '\u0900'..'\u097F' }
                    if (ll > 4 && ld.toFloat() / ll < 0.20f) continue
                    append(line.text)
                    if (lineIdx < block.lines.lastIndex) append('\n')
                    addedAny = true
                }
                if (addedAny && idx < sorted.lastIndex) append("\n\n")
            }
        }
    }

    /** Remove misrecognized Unicode noise characters from OCR output. */
    private fun cleanOcrText(text: String): String {
        var result = OCR_NOISE_RE.replace(text, "")
        result = result.replace("\u034F", "")  // Combining Grapheme Joiner
        result = result.replace("\u200C", "")  // ZWNJ (stray)
        result = result.replace("\u200D", "")  // ZWJ (stray)
        result = result.replace(Regex(""" {2,}"""), " ")  // collapse multi-spaces
        return result
    }

    // ── Image Preprocessing ──────────────────────────────────────

    // Downscale only — grayscale/contrast hurts ML Kit Devanagari accuracy.
    private fun preprocessForOcr(bitmap: Bitmap): Bitmap {
        return downscaleIfNeeded(bitmap)
    }

    private fun downscaleIfNeeded(bitmap: Bitmap): Bitmap {
        val maxDim = maxOf(bitmap.width, bitmap.height)
        if (maxDim <= MAX_OCR_DIM) return bitmap
        val scale = MAX_OCR_DIM.toFloat() / maxDim
        return Bitmap.createScaledBitmap(
            bitmap,
            (bitmap.width * scale).toInt(),
            (bitmap.height * scale).toInt(),
            true
        )
    }

    private fun toGrayscale(bitmap: Bitmap): Bitmap {
        val result = Bitmap.createBitmap(bitmap.width, bitmap.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(result)
        canvas.drawBitmap(bitmap, 0f, 0f, Paint().apply {
            colorFilter = ColorMatrixColorFilter(ColorMatrix().apply { setSaturation(0f) })
        })
        return result
    }

    private fun enhanceContrast(bitmap: Bitmap, factor: Float): Bitmap {
        val translate = 128f * (1f - factor)
        val cm = ColorMatrix(floatArrayOf(
            factor, 0f, 0f, 0f, translate,
            0f, factor, 0f, 0f, translate,
            0f, 0f, factor, 0f, translate,
            0f, 0f, 0f, 1f, 0f
        ))
        val result = Bitmap.createBitmap(bitmap.width, bitmap.height, Bitmap.Config.ARGB_8888)
        Canvas(result).drawBitmap(bitmap, 0f, 0f, Paint().apply {
            colorFilter = ColorMatrixColorFilter(cm)
        })
        return result
    }
}
