package com.marathitts.mobile.service

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Paint
import android.util.Log
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.math.abs
import kotlin.math.min

/**
 * Processes an open-book photograph: preprocesses the image,
 * splits into two pages, OCRs each page via ML Kit Devanagari,
 * cleans and reflows the text for TTS.
 *
 * Image pipeline:
 *   Camera photo → downscale → grayscale → contrast enhance →
 *   spine detect → split → margin crop → OCR → clean → reflow
 */
object BookPageProcessor {

    private const val TAG = "BookPageProcessor"

    /** Maximum dimension for OCR — larger images are downscaled. */
    // Larger limit so each *half* of a split spread keeps enough width for
    // dense Devanagari text.  A 4800 px tall half-page at 1:2 ratio is ~2400
    // px wide — well within ML Kit's ideal range and memory budget.
    private const val MAX_OCR_DIM = 4800

    /** Inner margin to trim after splitting (% of page width). Removes spine shadow. */
    private const val INNER_MARGIN_PERCENT = 0.04f

    /** Outer margin to trim (% of page width). Removes edge noise. */
    private const val OUTER_MARGIN_PERCENT = 0.02f

    /** Top/bottom margin to trim (% of page height). Removes header/footer lines. */
    private const val VERTICAL_MARGIN_PERCENT = 0.03f

    private val recognizer by lazy {
        TextRecognition.getClient(DevanagariTextRecognizerOptions.Builder().build())
    }

    // ── Regex patterns for header/footer/page number removal ────────────

    private val PAGE_NUMBER_RE = Regex("""^\s*[◆❖•♦\s]*[०-९\d]{1,4}[◆❖•♦\s]*$""")
    private val DOUBLE_DANDA_TITLE_RE = Regex("""॥\s*[^\n॥]+?\s*॥""")
    private val DATE_STAMP_RE = Regex("""(श्रीशके|शके|संवत्?|सन|इ\.स\.)\s*[०-९\d]{3,4}""")
    private val DECORATIVE_RE = Regex("""^\s*[◆❖•✦✧★☆◇◈▪▫♦\-–—=_]+\s*$""")
    private val SHORT_ARTIFACT_RE = Regex("""^\s*.{0,3}\s*$""")
    private val HEADER_FOOTER_COMBINED_RE = Regex(
        """^\s*[०-९\d]*\s*[◆❖•♦]?\s*॥.*?॥.*?(श्रीशके|शके|कार्तिक|संवत).*$""",
        RegexOption.IGNORE_CASE
    )

    /** Unicode characters that ML Kit commonly misrecognizes from book scans.
     *  These are combining marks, modifier letters, and symbols that
     *  don't belong in running Marathi prose. */
    private val OCR_NOISE_RE = Regex(
        """[\u25CC\u02D0\u02D1\u0300-\u036F\u200B-\u200F\u2028\u2029\uFEFF\u00B7\u02BC\u02BB\u0358\u0359]"""
    )

    /** Dangling single combining marks (virama, anusvara, etc.) not attached to a base. */
    private val DANGLING_DIACRITIC_RE = Regex("""(?<=\s|^)[\u0900-\u0903\u093A-\u094F\u0951-\u0957]+(?=\s|$)""")

    // ── Public API ──────────────────────────────────────────────────────

    data class BookReadResult(
        val leftPageText: String,
        val rightPageText: String,
        val mergedText: String,
        val pageCount: Int
    )

    /**
     * Process a full book-spread image. Full pipeline:
     * preprocess → spine detect → split → margin crop → OCR → clean → reflow → merge.
     */
    suspend fun processBookSpread(bitmap: Bitmap): BookReadResult {
        Log.i(TAG, "Input: ${bitmap.width}x${bitmap.height}")

        // Step 1: Preprocess full image (downscale + grayscale + contrast)
        val preprocessed = preprocessForOcr(bitmap)
        Log.i(TAG, "Preprocessed: ${preprocessed.width}x${preprocessed.height}")

        // Step 2: Detect spine
        val spineX = detectSpine(preprocessed)
        Log.i(TAG, "Spine at x=$spineX / ${preprocessed.width}")

        // Step 3: Split into left/right pages
        val leftFull = Bitmap.createBitmap(preprocessed, 0, 0, spineX, preprocessed.height)
        val rightFull = Bitmap.createBitmap(
            preprocessed, spineX, 0,
            preprocessed.width - spineX, preprocessed.height
        )
        if (preprocessed !== bitmap) preprocessed.recycle()

        // Step 4: Crop margins (remove spine shadow + edge noise)
        val leftCropped = cropPageMargins(leftFull, isLeftPage = true)
        val rightCropped = cropPageMargins(rightFull, isLeftPage = false)
        leftFull.recycle()
        rightFull.recycle()

        // Step 5: OCR each page using block-based extraction
        val leftRaw = ocrPageStructured(leftCropped)
        val rightRaw = ocrPageStructured(rightCropped)
        leftCropped.recycle()
        rightCropped.recycle()
        Log.i(TAG, "OCR: left=${leftRaw.length}c, right=${rightRaw.length}c")

        // Step 6: Clean and reflow
        val leftClean = cleanPageText(leftRaw)
        val rightClean = cleanPageText(rightRaw)
        Log.i(TAG, "Cleaned: left=${leftClean.length}c, right=${rightClean.length}c")

        // Step 7: Merge
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
     * Process a single page image (no splitting, but still preprocesses).
     */
    suspend fun processSinglePage(bitmap: Bitmap): BookReadResult {
        val preprocessed = preprocessForOcr(bitmap)
        val raw = ocrPageStructured(preprocessed)
        if (preprocessed !== bitmap) preprocessed.recycle()
        val clean = cleanPageText(raw)
        return BookReadResult(
            leftPageText = clean, rightPageText = "",
            mergedText = clean, pageCount = 1
        )
    }

    // ══════════════════════════════════════════════════════════════════════
    //  IMAGE PREPROCESSING PIPELINE
    // ══════════════════════════════════════════════════════════════════════

    /**
     * Preprocessing for OCR:
     * Downscale only — ML Kit's Devanagari model performs better on the
     * original colour image; grayscale + contrast conversion degrades
     * recognition of complex ligatures.
     *
     * Returns a NEW bitmap only when downscaling was needed (caller must
     * recycle if != input), otherwise returns the same instance.
     */
    private fun preprocessForOcr(bitmap: Bitmap): Bitmap {
        return downscaleIfNeeded(bitmap)
    }

    /** Downscale so longest side ≤ MAX_OCR_DIM. Preserves aspect ratio. */
    private fun downscaleIfNeeded(bitmap: Bitmap): Bitmap {
        val maxDim = maxOf(bitmap.width, bitmap.height)
        if (maxDim <= MAX_OCR_DIM) return bitmap
        val scale = MAX_OCR_DIM.toFloat() / maxDim
        val newW = (bitmap.width * scale).toInt()
        val newH = (bitmap.height * scale).toInt()
        Log.d(TAG, "Downscaling ${bitmap.width}x${bitmap.height} → ${newW}x${newH}")
        return Bitmap.createScaledBitmap(bitmap, newW, newH, true)
    }

    /** Convert to grayscale using ColorMatrix. Returns new bitmap. */
    private fun toGrayscale(bitmap: Bitmap): Bitmap {
        val result = Bitmap.createBitmap(bitmap.width, bitmap.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(result)
        val paint = Paint().apply {
            colorFilter = ColorMatrixColorFilter(ColorMatrix().apply { setSaturation(0f) })
        }
        canvas.drawBitmap(bitmap, 0f, 0f, paint)
        return result
    }

    /**
     * Enhance contrast by applying a linear stretch around the midpoint.
     * Factor > 1.0 increases contrast.
     */
    private fun enhanceContrast(bitmap: Bitmap, factor: Float): Bitmap {
        val translate = 128f * (1f - factor)
        val cm = ColorMatrix(floatArrayOf(
            factor, 0f, 0f, 0f, translate,
            0f, factor, 0f, 0f, translate,
            0f, 0f, factor, 0f, translate,
            0f, 0f, 0f, 1f, 0f
        ))
        val result = Bitmap.createBitmap(bitmap.width, bitmap.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(result)
        canvas.drawBitmap(bitmap, 0f, 0f, Paint().apply {
            colorFilter = ColorMatrixColorFilter(cm)
        })
        return result
    }

    // ══════════════════════════════════════════════════════════════════════
    //  MARGIN CROPPING
    // ══════════════════════════════════════════════════════════════════════

    /**
     * Crop a split page to remove:
     * - Inner edge (spine shadow)
     * - Outer edge (dark edge / finger)
     * - Top/bottom (header/footer visual area)
     */
    private fun cropPageMargins(page: Bitmap, isLeftPage: Boolean): Bitmap {
        val w = page.width
        val h = page.height
        val innerCrop = (w * INNER_MARGIN_PERCENT).toInt().coerceAtLeast(4)
        val outerCrop = (w * OUTER_MARGIN_PERCENT).toInt().coerceAtLeast(2)
        val topCrop = (h * VERTICAL_MARGIN_PERCENT).toInt().coerceAtLeast(2)
        val bottomCrop = (h * VERTICAL_MARGIN_PERCENT).toInt().coerceAtLeast(2)

        val x = if (isLeftPage) outerCrop else innerCrop
        val cropW = w - innerCrop - outerCrop
        val cropH = h - topCrop - bottomCrop

        if (cropW < 50 || cropH < 50) {
            Log.w(TAG, "Page too small after cropping, returning original")
            return page
        }

        return Bitmap.createBitmap(page, x, topCrop, cropW, cropH)
    }

    // ══════════════════════════════════════════════════════════════════════
    //  SPINE DETECTION
    // ══════════════════════════════════════════════════════════════════════

    /**
     * Detect the book spine by combining two heuristics:
     * 1. Darkest vertical strip in center 40% (shadow in gutter)
     * 2. Maximum brightness gradient (sharp brightness change at spine edge)
     *
     * Returns x-coordinate of the spine.
     */
    private fun detectSpine(bitmap: Bitmap): Int {
        val w = bitmap.width
        val h = bitmap.height

        val searchStart = (w * 0.30).toInt()
        val searchEnd = (w * 0.70).toInt()
        val range = searchEnd - searchStart

        // Sample rows evenly
        val sampleStep = maxOf(h / 80, 4)
        val colBrightness = FloatArray(range)

        for (x in searchStart until searchEnd) {
            var totalBrightness = 0L
            var sampleCount = 0
            var y = 0
            while (y < h) {
                val pixel = bitmap.getPixel(x, y)
                totalBrightness += (0.299 * Color.red(pixel) +
                        0.587 * Color.green(pixel) +
                        0.114 * Color.blue(pixel)).toLong()
                sampleCount++
                y += sampleStep
            }
            colBrightness[x - searchStart] =
                if (sampleCount > 0) totalBrightness.toFloat() / sampleCount else 255f
        }

        // ── Heuristic 1: Darkest region (sliding window of 9 px) ────
        val windowSize = 9
        var minBrightness = Float.MAX_VALUE
        var darkestOffset = range / 2

        for (i in 0 until range - windowSize) {
            var sum = 0f
            for (j in 0 until windowSize) sum += colBrightness[i + j]
            val avg = sum / windowSize
            if (avg < minBrightness) {
                minBrightness = avg
                darkestOffset = i + windowSize / 2
            }
        }

        // ── Heuristic 2: Maximum gradient (steepest brightness drop) ────
        val gradientWindow = 7
        var maxGradient = 0f
        var gradientOffset = range / 2

        for (i in gradientWindow until range - gradientWindow) {
            var leftAvg = 0f
            var rightAvg = 0f
            for (j in 1..gradientWindow) {
                leftAvg += colBrightness[i - j]
                rightAvg += colBrightness[i + j]
            }
            leftAvg /= gradientWindow
            rightAvg /= gradientWindow
            // Spine = where both sides are brighter than center
            val gradient = ((leftAvg + rightAvg) / 2f) - colBrightness[i]
            if (gradient > maxGradient) {
                maxGradient = gradient
                gradientOffset = i
            }
        }

        // Combine: prefer gradient if it's strong, otherwise use darkest
        val overallAvg = colBrightness.average().toFloat()
        val darknessContrast = overallAvg - minBrightness

        val spineOffset = when {
            // Strong gradient AND the two methods roughly agree → use gradient
            maxGradient > 15f && abs(gradientOffset - darkestOffset) < range / 6 ->
                (gradientOffset + darkestOffset) / 2
            // Strong darkness contrast → use darkest
            darknessContrast > 12f -> darkestOffset
            // Strong gradient → use gradient
            maxGradient > 20f -> gradientOffset
            // Fallback: geometric center
            else -> {
                Log.w(TAG, "No clear spine (contrast=$darknessContrast, gradient=$maxGradient), using center")
                range / 2
            }
        }

        return searchStart + spineOffset
    }

    // ══════════════════════════════════════════════════════════════════════
    //  OCR (Block-based extraction for proper reading order)
    // ══════════════════════════════════════════════════════════════════════

    /**
     * OCR using ML Kit's structured Text output.
     * Sorts TextBlocks by their vertical position (top Y) so text
     * is returned in reading order (top to bottom).
     * Within each block, lines are already in order.
     *
     * Hallucination filter: blocks with < 25 % Devanagari letters are dropped.
     * ML Kit sometimes reads background noise / decorative elements as Latin
     * characters or garbled sequences; real Marathi prose is ≥ 60 % Devanagari.
     */
    private suspend fun ocrPageStructured(pageBitmap: Bitmap): String {
        val inputImage = InputImage.fromBitmap(pageBitmap, 0)
        val visionText: Text = suspendCancellableCoroutine { cont ->
            recognizer.process(inputImage)
                .addOnSuccessListener { result -> cont.resume(result) }
                .addOnFailureListener { e ->
                    Log.e(TAG, "OCR failed: ${e.message}")
                    cont.resumeWithException(e)
                }
        }

        if (visionText.textBlocks.isEmpty()) return ""

        val sortedBlocks = visionText.textBlocks.sortedBy { it.boundingBox?.top ?: 0 }

        return buildString {
            for ((blockIdx, block) in sortedBlocks.withIndex()) {
                // ── Hallucination filter ────────────────────────────
                // Count only letter characters to avoid skewing ratio with spaces or dandas
                val blockText    = block.text
                val letterCount  = blockText.count { it.isLetter() }
                val devCount     = blockText.count { it in '\u0900'..'\u097F' }
                // If the block has letters but almost none are Devanagari, skip it
                if (letterCount > 6 && devCount.toFloat() / letterCount < 0.25f) {
                    Log.d(TAG, "Skipping non-Devanagari block (dev=${devCount}/${letterCount}): ${blockText.take(40)}")
                    continue
                }

                var addedAny = false
                for ((lineIdx, line) in block.lines.withIndex()) {
                    // Per-line hallucination filter (catches mixed blocks)
                    val lLetters = line.text.count { it.isLetter() }
                    val lDev     = line.text.count { it in '\u0900'..'\u097F' }
                    if (lLetters > 4 && lDev.toFloat() / lLetters < 0.20f) continue

                    append(line.text)
                    if (lineIdx < block.lines.lastIndex) append('\n')
                    addedAny = true
                }
                if (addedAny && blockIdx < sortedBlocks.lastIndex) append("\n\n")
            }
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    //  TEXT CLEANING & POST-OCR CORRECTION
    // ══════════════════════════════════════════════════════════════════════

    /**
     * Full text cleaning pipeline:
     * 1. Remove OCR noise characters (misrecognized combining marks, ZWJ, etc.)
     * 2. Remove dangling diacritics
     * 3. Fix common OCR substitutions
     * 4. Remove headers/footers/page numbers
     * 5. Reflow prose lines for natural TTS reading
     */
    fun cleanPageText(rawText: String): String {
        if (rawText.isBlank()) return ""

        // Step 1: Remove Unicode noise
        var text = OCR_NOISE_RE.replace(rawText, "")

        // Step 2: Remove dangling diacritics that aren't attached to a base character
        text = DANGLING_DIACRITIC_RE.replace(text, "")

        // Step 3: Fix common OCR substitutions in Devanagari
        text = fixOcrSubstitutions(text)

        // Step 4: Remove headers, footers, page numbers
        val lines = text.lines()
        if (lines.isEmpty()) return ""

        val edgeLines = min(4, lines.size / 3 + 1)
        val cleaned = lines.mapIndexedNotNull { idx, line ->
            val trimmed = line.trim()
            if (trimmed.isEmpty()) return@mapIndexedNotNull null

            // Always filter
            if (isPageNumber(trimmed)) return@mapIndexedNotNull null
            if (DECORATIVE_RE.matches(trimmed)) return@mapIndexedNotNull null
            if (HEADER_FOOTER_COMBINED_RE.matches(trimmed)) return@mapIndexedNotNull null

            // Edge lines: stricter
            val isEdge = idx < edgeLines || idx >= lines.size - edgeLines
            if (isEdge) {
                if (isHeaderFooterLine(trimmed)) return@mapIndexedNotNull null
                if (SHORT_ARTIFACT_RE.matches(trimmed)) return@mapIndexedNotNull null
            }

            trimmed
        }

        // Step 5: Join + reflow
        val joined = cleaned.joinToString("\n")
            .replace(Regex("""\n{3,}"""), "\n\n")
            .trim()
        return TextReflow.reflow(joined)
    }

    /**
     * Fix common ML Kit Devanagari OCR character confusions.
     */
    private fun fixOcrSubstitutions(text: String): String {
        var result = text

        // Multiple spaces → single space (ML Kit sometimes adds extra)
        result = result.replace(Regex(""" {2,}"""), " ")

        // Misrecognized Latin characters that should be Devanagari
        // "." inside Devanagari text → "।" (danda) — only between Devanagari chars
        result = result.replace(
            Regex("""(?<=[\u0900-\u097F])\s*\.\s*(?=[\u0900-\u097F]|\s*${'$'})"""),
            "। "
        )

        // Remove stray combining grapheme joiner / non-joiner
        result = result.replace("\u034F", "")  // Combining Grapheme Joiner
        result = result.replace("\u200C", "")  // ZWNJ (stray — legitimate usage is rare in OCR output)
        result = result.replace("\u200D", "")  // ZWJ (stray)

        // Common confusions: ˑ (modifier letter half triangular colon) → nothing
        result = result.replace("\u02D1", "")
        result = result.replace("\u02D0", "")

        // Dotted circle placeholder → remove
        result = result.replace("\u25CC", "")

        // Clean up resulting double spaces
        result = result.replace(Regex(""" {2,}"""), " ")

        return result
    }

    private fun isHeaderFooterLine(line: String): Boolean {
        if (DOUBLE_DANDA_TITLE_RE.containsMatchIn(line)) return true
        if (DATE_STAMP_RE.containsMatchIn(line)) return true

        val stripped = line.replace(Regex("""[◆❖•♦\s]"""), "")
        if (PAGE_NUMBER_RE.matches(stripped)) return true

        // Line is mostly decorative + numbers + dandas
        val devanagariLetterCount = line.count { it in '\u0904'..'\u0963' }
        val totalCount = line.count { !it.isWhitespace() }
        if (totalCount > 0 && devanagariLetterCount <= 5 && line.contains("॥")) return true

        return false
    }

    private fun isPageNumber(line: String): Boolean = PAGE_NUMBER_RE.matches(line)
}
