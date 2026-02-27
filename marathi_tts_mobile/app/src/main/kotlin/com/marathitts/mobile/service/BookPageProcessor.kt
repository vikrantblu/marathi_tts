package com.marathitts.mobile.service

import android.graphics.Bitmap
import android.graphics.Color
import android.util.Log
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Processes an open-book photograph: splits into two pages,
 * OCRs each page, cleans header/footer/page numbers, and
 * returns merged readable text.
 *
 * Designed for elderly users — capture → clean → read aloud.
 */
object BookPageProcessor {

    private const val TAG = "BookPageProcessor"

    private val recognizer by lazy {
        TextRecognition.getClient(DevanagariTextRecognizerOptions.Builder().build())
    }

    // ── Regex patterns for header/footer/page number removal ────────────

    /** Devanagari digits only (page numbers like ५४, ५५) */
    private val PAGE_NUMBER_RE = Regex("""^\s*[०-९\d]{1,4}\s*$""")

    /** Double-danda wrapped book title: ॥ श्रीवामनराज ॥ */
    private val DOUBLE_DANDA_TITLE_RE = Regex("""॥\s*[^\n॥]+?\s*॥""")

    /** Date / chapter stamps like "कार्तिक, श्रीशके १९४७" */
    private val DATE_STAMP_RE = Regex("""(श्रीशके|शके|संवत्?|सन|इ\.स\.)\s*[०-९\d]{3,4}""")

    /** Decorative glyphs that appear in headers/footers */
    private val DECORATIVE_RE = Regex("""^\s*[◆❖•✦✧★☆◇◈▪▫♦]+\s*$""")

    /** Very short lines (≤5 chars) that are likely artifacts */
    private val SHORT_ARTIFACT_RE = Regex("""^\s*.{0,3}\s*$""")

    /** Combined header/footer line: "५४ ◆ ॥ श्रीवामनराज ॥   कार्तिक, श्रीशके…" */
    private val HEADER_FOOTER_COMBINED_RE = Regex(
        """^\s*[०-९\d]*\s*[◆❖•♦]?\s*॥.*?॥.*?(श्रीशके|शके|कार्तिक|संवत).*$""",
        RegexOption.IGNORE_CASE
    )

    // ── Public API ──────────────────────────────────────────────────────

    data class BookReadResult(
        val leftPageText: String,
        val rightPageText: String,
        val mergedText: String,
        val pageCount: Int
    )

    /**
     * Process a full book-spread image:
     * 1. Split into left/right pages
     * 2. OCR each page via ML Kit Devanagari
     * 3. Clean headers, footers, page numbers
     * 4. Merge in reading order
     */
    suspend fun processBookSpread(bitmap: Bitmap): BookReadResult {
        Log.i(TAG, "Processing book spread: ${bitmap.width}x${bitmap.height}")

        // Step 1: Detect spine and split
        val spineX = detectSpine(bitmap)
        Log.i(TAG, "Spine detected at x=$spineX (image width=${bitmap.width})")

        val leftPage = Bitmap.createBitmap(bitmap, 0, 0, spineX, bitmap.height)
        val rightPage = Bitmap.createBitmap(bitmap, spineX, 0,
            bitmap.width - spineX, bitmap.height)

        // Step 2: OCR each page
        val leftRaw = ocrPage(leftPage)
        val rightRaw = ocrPage(rightPage)
        Log.i(TAG, "OCR done: left=${leftRaw.length} chars, right=${rightRaw.length} chars")

        // Recycle split bitmaps (not the original — caller owns that)
        leftPage.recycle()
        rightPage.recycle()

        // Step 3: Clean each page
        val leftClean = cleanPageText(leftRaw)
        val rightClean = cleanPageText(rightRaw)
        Log.i(TAG, "Cleaned: left=${leftClean.length} chars, right=${rightClean.length} chars")

        // Step 4: Merge
        val merged = buildString {
            if (leftClean.isNotBlank()) append(leftClean)
            if (leftClean.isNotBlank() && rightClean.isNotBlank()) append("\n\n")
            if (rightClean.isNotBlank()) append(rightClean)
        }.trim()

        return BookReadResult(
            leftPageText = leftClean,
            rightPageText = rightClean,
            mergedText = merged,
            pageCount = listOf(leftClean, rightClean).count { it.isNotBlank() }
        )
    }

    /**
     * Process a single page image (no splitting needed).
     */
    suspend fun processSinglePage(bitmap: Bitmap): BookReadResult {
        val raw = ocrPage(bitmap)
        val clean = cleanPageText(raw)
        return BookReadResult(
            leftPageText = clean,
            rightPageText = "",
            mergedText = clean,
            pageCount = 1
        )
    }

    // ── Spine detection ─────────────────────────────────────────────────

    /**
     * Detect the book spine (center fold) by finding the darkest
     * vertical strip in the middle ~40% of the image.
     *
     * The spine/gutter is typically a dark vertical line/shadow
     * near the center of the spread photo.
     */
    private fun detectSpine(bitmap: Bitmap): Int {
        val w = bitmap.width
        val h = bitmap.height

        // Search in the middle 40% of image width
        val searchStart = (w * 0.30).toInt()
        val searchEnd = (w * 0.70).toInt()

        // Sample every 4th row for performance
        val sampleStep = maxOf(h / 100, 4)
        val columnBrightness = IntArray(searchEnd - searchStart)

        for (x in searchStart until searchEnd) {
            var totalBrightness = 0L
            var sampleCount = 0
            var y = 0
            while (y < h) {
                val pixel = bitmap.getPixel(x, y)
                // Luma = 0.299R + 0.587G + 0.114B
                totalBrightness += (0.299 * Color.red(pixel) +
                        0.587 * Color.green(pixel) +
                        0.114 * Color.blue(pixel)).toLong()
                sampleCount++
                y += sampleStep
            }
            columnBrightness[x - searchStart] =
                if (sampleCount > 0) (totalBrightness / sampleCount).toInt() else 255
        }

        // Find the darkest column (lowest brightness = spine shadow)
        var minBrightness = 256
        var spineOffset = columnBrightness.size / 2  // default: exact center

        // Use a sliding window of 5 columns to find the darkest region
        val windowSize = 5
        for (i in 0 until columnBrightness.size - windowSize) {
            val windowAvg = columnBrightness.slice(i until i + windowSize).average().toInt()
            if (windowAvg < minBrightness) {
                minBrightness = windowAvg
                spineOffset = i + windowSize / 2
            }
        }

        val spineX = searchStart + spineOffset

        // Sanity check: if contrast is very low (no clear spine),
        // fall back to geometric center
        val overallAvg = columnBrightness.average().toInt()
        return if (overallAvg - minBrightness < 10) {
            Log.w(TAG, "No clear spine detected, using geometric center")
            w / 2
        } else {
            spineX
        }
    }

    // ── ML Kit OCR ──────────────────────────────────────────────────────

    private suspend fun ocrPage(pageBitmap: Bitmap): String {
        val inputImage = InputImage.fromBitmap(pageBitmap, 0)
        return suspendCancellableCoroutine { cont ->
            recognizer.process(inputImage)
                .addOnSuccessListener { visionText ->
                    cont.resume(visionText.text)
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "OCR failed: ${e.message}")
                    cont.resumeWithException(e)
                }
        }
    }

    // ── Text cleaning ───────────────────────────────────────────────────

    /**
     * Remove headers, footers, page numbers, decorative symbols,
     * and other non-content text from an OCR'd book page.
     *
     * Strategy:
     * - First few lines and last few lines are likely header/footer
     * - Lines matching known patterns are removed
     * - Interior lines are kept as-is
     */
    fun cleanPageText(rawText: String): String {
        if (rawText.isBlank()) return ""

        val lines = rawText.lines()
        if (lines.isEmpty()) return ""

        // How many lines from top/bottom to inspect for header/footer
        val edgeLines = minOf(4, lines.size / 3 + 1)

        val cleaned = lines.mapIndexedNotNull { idx, line ->
            val trimmed = line.trim()
            if (trimmed.isEmpty()) return@mapIndexedNotNull null

            // Always filter these patterns (anywhere on page)
            if (isPageNumber(trimmed)) return@mapIndexedNotNull null
            if (DECORATIVE_RE.matches(trimmed)) return@mapIndexedNotNull null
            if (HEADER_FOOTER_COMBINED_RE.matches(trimmed)) return@mapIndexedNotNull null

            // For edge lines (first/last N), apply stricter filtering
            val isEdge = idx < edgeLines || idx >= lines.size - edgeLines
            if (isEdge) {
                if (isHeaderFooterLine(trimmed)) return@mapIndexedNotNull null
                if (SHORT_ARTIFACT_RE.matches(trimmed)) return@mapIndexedNotNull null
            }

            trimmed
        }

        // Join lines, then reflow prose so TTS doesn't pause at visual line breaks
        val joined = cleaned.joinToString("\n")
            .replace(Regex("""\n{3,}"""), "\n\n")
            .trim()
        return TextReflow.reflow(joined)
    }

    /**
     * Check if a line is a header/footer element.
     */
    private fun isHeaderFooterLine(line: String): Boolean {
        // Contains double-danda title pattern
        if (DOUBLE_DANDA_TITLE_RE.containsMatchIn(line)) return true

        // Contains date/era stamp
        if (DATE_STAMP_RE.containsMatchIn(line)) return true

        // Just a page number with optional decorations
        val stripped = line.replace(Regex("""[◆❖•♦\s]"""), "")
        if (PAGE_NUMBER_RE.matches(stripped)) return true

        // Line is primarily decorative + numbers + dandas (e.g., "५४ ◆ ॥ श्रीवामनराज ॥")
        val devanagariLetterCount = line.count { it in '\u0904'..'\u0963' }
        val totalCount = line.count { !it.isWhitespace() }
        if (totalCount > 0 && devanagariLetterCount <= 5 && line.contains("॥")) return true

        return false
    }

    private fun isPageNumber(line: String): Boolean {
        return PAGE_NUMBER_RE.matches(line)
    }
}
