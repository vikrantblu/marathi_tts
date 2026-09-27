package com.marathitts.mobile.ui.bookreader

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.PointF
import kotlin.math.sqrt

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
 * 6. **Sobel refinement** (optional): snap each edge to the nearest gradient
 *    peak within ±5 % of the source dimension.  Improves accuracy on
 *    low-contrast cream / yellowed pages where pure brightness scanning
 *    settles a few pixels in from the true edge.  See [refineWithSobel].
 * 7. Return confidence so the caller can decide whether to auto-apply silently
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

        // ── Sobel-based refinement on the thumbnail ──────────────
        // Snap each rough edge index to the nearest gradient ridge within a
        // ±5 % window.  Improves accuracy on low-contrast pages.
        val refined = refineWithSobel(lum, tw, th, topRow, botRow, leftCol, rightCol)

        // ── Convert to source coords ─────────────────────────────
        val sx = bitmap.width.toFloat()  / tw
        val sy = bitmap.height.toFloat() / th
        val px = bitmap.width  * BORDER_PAD
        val py = bitmap.height * BORDER_PAD

        val left  = (refined.left  * sx + px).coerceIn(0f, bitmap.width.toFloat())
        val top   = (refined.top   * sy + py).coerceIn(0f, bitmap.height.toFloat())
        val right = (refined.right * sx - px).coerceIn(0f, bitmap.width.toFloat())
        val bot   = (refined.bot   * sy - py).coerceIn(0f, bitmap.height.toFloat())
        if (right <= left || bot <= top) return null

        // ── Confidence ───────────────────────────────────────────
        val coverage  = (pH.toFloat() / th) * (pW.toFloat() / tw)
        val allEdges  = topRow < 3 && botRow > th - 4 && leftCol < 3 && rightCol > tw - 4
        val contrast  = ((threshold - bgLum).toFloat() / 60f).coerceIn(-0.3f, 0.3f)
        // Sobel-confirmed edges add a small confidence bonus.
        val sobelBonus = if (refined.snapped) 0.10f else 0f
        val conf      = (coverage * (if (allEdges) 0.45f else 1f) + contrast + sobelBonus)
            .coerceIn(0f, 1f)

        return DetectedCorners(
            tl = PointF(left, top), tr = PointF(right, top),
            br = PointF(right, bot), bl = PointF(left, bot),
            confidence = conf
        )
    }

    /** Result of [refineWithSobel]: refined thumbnail edge indices + flag. */
    private data class RefinedEdges(
        val top: Int, val bot: Int, val left: Int, val right: Int,
        /** True when at least one edge was snapped to a Sobel gradient peak. */
        val snapped: Boolean
    )

    /**
     * Computes a 3×3 Sobel gradient magnitude on the thumbnail and snaps each
     * brightness-derived edge to the strongest gradient ridge within a ±5 %
     * window of the source dimension.
     *
     * Sobel kernels:
     *   Gx = [[-1,0,1],[-2,0,2],[-1,0,1]]
     *   Gy = [[-1,-2,-1],[0,0,0],[1,2,1]]
     *   |G| = √(Gx² + Gy²)
     *
     * For each edge we scan a perpendicular slice and pick the row/column with
     * the highest summed gradient magnitude (across the page span).  Ties or
     * weak peaks fall back to the original brightness index.
     */
    private fun refineWithSobel(
        lum: Array<IntArray>, tw: Int, th: Int,
        topRow0: Int, botRow0: Int, leftCol0: Int, rightCol0: Int
    ): RefinedEdges {
        if (tw < 5 || th < 5) {
            return RefinedEdges(topRow0, botRow0, leftCol0, rightCol0, snapped = false)
        }

        // Full Sobel magnitude grid (interior only; borders left at 0).
        val mag = Array(th) { IntArray(tw) }
        for (y in 1 until th - 1) {
            for (x in 1 until tw - 1) {
                val gx = -lum[y - 1][x - 1] + lum[y - 1][x + 1] +
                         -2 * lum[y][x - 1] + 2 * lum[y][x + 1] +
                         -lum[y + 1][x - 1] + lum[y + 1][x + 1]
                val gy = -lum[y - 1][x - 1] - 2 * lum[y - 1][x] - lum[y - 1][x + 1] +
                          lum[y + 1][x - 1] + 2 * lum[y + 1][x] + lum[y + 1][x + 1]
                mag[y][x] = sqrt((gx * gx + gy * gy).toDouble()).toInt()
            }
        }

        val winV = (th * 0.05f).toInt().coerceAtLeast(2)
        val winH = (tw * 0.05f).toInt().coerceAtLeast(2)

        fun strongestRow(centre: Int, col0: Int, col1: Int): Pair<Int, Int> {
            val lo = (centre - winV).coerceAtLeast(1)
            val hi = (centre + winV).coerceAtMost(th - 2)
            var best = centre; var bestSum = -1
            for (y in lo..hi) {
                var s = 0
                for (x in col0..col1) s += mag[y][x]
                if (s > bestSum) { bestSum = s; best = y }
            }
            return best to bestSum
        }

        fun strongestCol(centre: Int, row0: Int, row1: Int): Pair<Int, Int> {
            val lo = (centre - winH).coerceAtLeast(1)
            val hi = (centre + winH).coerceAtMost(tw - 2)
            var best = centre; var bestSum = -1
            for (x in lo..hi) {
                var s = 0
                for (y in row0..row1) s += mag[y][x]
                if (s > bestSum) { bestSum = s; best = x }
            }
            return best to bestSum
        }

        val rowSpanLo = (leftCol0 + (rightCol0 - leftCol0) / 4).coerceAtLeast(1)
        val rowSpanHi = (rightCol0 - (rightCol0 - leftCol0) / 4).coerceAtMost(tw - 2)
        val colSpanLo = (topRow0  + (botRow0  - topRow0 ) / 4).coerceAtLeast(1)
        val colSpanHi = (botRow0  - (botRow0  - topRow0 ) / 4).coerceAtMost(th - 2)

        val (topR, topS)   = strongestRow(topRow0,   rowSpanLo, rowSpanHi)
        val (botR, botS)   = strongestRow(botRow0,   rowSpanLo, rowSpanHi)
        val (leftC, leftS) = strongestCol(leftCol0,  colSpanLo, colSpanHi)
        val (rightC, rgtS) = strongestCol(rightCol0, colSpanLo, colSpanHi)

        // Require the snapped peak to be reasonably strong relative to the
        // span length, otherwise keep the brightness-derived index.
        val minRowStrength = (rowSpanHi - rowSpanLo + 1) * 30
        val minColStrength = (colSpanHi - colSpanLo + 1) * 30
        val finalTop   = if (topS  >= minRowStrength) topR   else topRow0
        val finalBot   = if (botS  >= minRowStrength) botR   else botRow0
        val finalLeft  = if (leftS >= minColStrength) leftC  else leftCol0
        val finalRight = if (rgtS  >= minColStrength) rightC else rightCol0
        val snapped = (finalTop != topRow0) || (finalBot != botRow0) ||
                      (finalLeft != leftCol0) || (finalRight != rightCol0)

        // Sanity: keep ordering & non-degenerate rect; otherwise fall back.
        if (finalBot <= finalTop || finalRight <= finalLeft) {
            return RefinedEdges(topRow0, botRow0, leftCol0, rightCol0, snapped = false)
        }
        return RefinedEdges(finalTop, finalBot, finalLeft, finalRight, snapped)
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
