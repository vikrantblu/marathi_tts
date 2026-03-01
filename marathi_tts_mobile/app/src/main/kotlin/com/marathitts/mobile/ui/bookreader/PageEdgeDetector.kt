package com.marathitts.mobile.ui.bookreader

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.PointF

/**
 * Detects the page/spread bounding quad using an adaptive background-sampling
 * approach — no OpenCV required.
 *
 * **Algorithm:**
 * 1. Downsample to ~320 px thumbnail.
 * 2. Sample luminance of the 4 corner patches to estimate background colour.
 * 3. Derive an adaptive threshold between background and page centre brightness.
 * 4. Scan inward from 4 sides: a row/column is "inside the page" when ≥ 30 %
 *    of its pixels exceed the threshold.
 * 5. Apply a small border pad to exclude spine shadows.
 * 6. Return confidence so the caller can decide whether to auto-apply silently
 *    or show the manual crop editor.
 */
object PageEdgeDetector {

    private const val THUMB_SIZE          = 320
    private const val MIN_BRIGHT_FRACTION = 0.30f
    private const val CORNER_DEPTH        = 0.12f   // fraction of thumb dim
    private const val BORDER_PAD          = 0.012f  // fraction of source dim

    data class DetectedCorners(
        val tl: PointF,
        val tr: PointF,
        val br: PointF,
        val bl: PointF,
        /**
         * 0..1.  ≥ 0.55 → auto-apply silently; 0.40-0.55 → pre-fill & show
         * editor; < 0.40 → fall back to default inset corners.
         */
        val confidence: Float
    )

    fun detect(bitmap: Bitmap): DetectedCorners? {
        // ── Thumbnail ────────────────────────────────────────────
        val scale = THUMB_SIZE.toFloat() / maxOf(bitmap.width, bitmap.height)
        val tw = (bitmap.width  * scale).toInt().coerceAtLeast(1)
        val th = (bitmap.height * scale).toInt().coerceAtLeast(1)
        val thumb = Bitmap.createScaledBitmap(bitmap, tw, th, true)

        // ── Luminance map (BT.601) ───────────────────────────────
        val lum = Array(th) { y ->
            IntArray(tw) { x ->
                val p = thumb.getPixel(x, y)
                (Color.red(p) * 77 + Color.green(p) * 150 + Color.blue(p) * 29) ushr 8
            }
        }
        thumb.recycle()

        // ── Adaptive threshold ───────────────────────────────────
        val bgLum = estimateBg(lum, tw, th)
        // Centre region luminance (expected to be the bright page)
        var cSum = 0L; var cN = 0
        for (y in (th*0.35).toInt() until (th*0.65).toInt())
            for (x in (tw*0.35).toInt() until (tw*0.65).toInt()) {
                cSum += lum[y][x]; cN++
            }
        val centreLum = if (cN > 0) (cSum / cN).toInt() else 180
        // Threshold: weighted midpoint, clamped to a usable range
        val threshold = (bgLum * 0.55 + centreLum * 0.45).toInt().coerceIn(55, 220)

        // ── Edge scan ────────────────────────────────────────────
        fun rowB(y: Int) = lum[y].count   { it > threshold }.toFloat() / tw
        fun colB(x: Int) = lum.count { r -> r[x] > threshold }.toFloat() / th

        val topRow   = (0       until th      ).firstOrNull { rowB(it) > MIN_BRIGHT_FRACTION }
        val botRow   = (th - 1  downTo 0      ).firstOrNull { rowB(it) > MIN_BRIGHT_FRACTION }
        val leftCol  = (0       until tw      ).firstOrNull { colB(it) > MIN_BRIGHT_FRACTION }
        val rightCol = (tw - 1  downTo 0      ).firstOrNull { colB(it) > MIN_BRIGHT_FRACTION }

        if (topRow == null || botRow == null || leftCol == null || rightCol == null) return null
        if (botRow <= topRow || rightCol <= leftCol) return null
        val pH = botRow - topRow;  val pW = rightCol - leftCol
        if (pH < th * 0.25f || pW < tw * 0.25f) return null

        // ── Convert to source coords ─────────────────────────────
        val sx = bitmap.width.toFloat()  / tw
        val sy = bitmap.height.toFloat() / th
        val px = bitmap.width  * BORDER_PAD
        val py = bitmap.height * BORDER_PAD

        val left  = (leftCol  * sx + px).coerceIn(0f, bitmap.width.toFloat())
        val top   = (topRow   * sy + py).coerceIn(0f, bitmap.height.toFloat())
        val right = (rightCol * sx - px).coerceIn(0f, bitmap.width.toFloat())
        val bot   = (botRow   * sy - py).coerceIn(0f, bitmap.height.toFloat())
        if (right <= left || bot <= top) return null

        // ── Confidence ───────────────────────────────────────────
        val coverage  = (pH.toFloat() / th) * (pW.toFloat() / tw)
        val allEdges  = topRow < 3 && botRow > th - 4 && leftCol < 3 && rightCol > tw - 4
        val contrast  = ((threshold - bgLum).toFloat() / 60f).coerceIn(-0.3f, 0.3f)
        val conf      = (coverage * (if (allEdges) 0.45f else 1f) + contrast).coerceIn(0f, 1f)

        return DetectedCorners(
            tl = PointF(left, top), tr = PointF(right, top),
            br = PointF(right, bot), bl = PointF(left, bot),
            confidence = conf
        )
    }

    /** Average luminance of the two darkest corner patches (= background). */
    private fun estimateBg(lum: Array<IntArray>, tw: Int, th: Int): Int {
        val d = (minOf(tw, th) * CORNER_DEPTH).toInt().coerceAtLeast(3)
        fun patch(x0: Int, y0: Int): Int {
            var s = 0L; var n = 0
            for (y in y0 until (y0 + d).coerceAtMost(th))
                for (x in x0 until (x0 + d).coerceAtMost(tw)) { s += lum[y][x]; n++ }
            return if (n > 0) (s / n).toInt() else 128
        }
        val vals = listOf(patch(0, 0), patch(tw - d, 0), patch(0, th - d), patch(tw - d, th - d))
        return vals.sorted().take(2).average().toInt().coerceIn(20, 230)
    }
}
