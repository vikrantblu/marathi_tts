package com.marathitts.mobile.ui.bookreader

import android.graphics.PointF
import android.graphics.RectF
import androidx.camera.core.ImageProxy

/**
 * Fast per-frame page-edge detector for the live camera preview.
 *
 * Designed for [androidx.camera.core.ImageAnalysis] callbacks where every
 * millisecond counts.  Operates **only** on the Y (luminance) plane of a
 * YUV_420_888 [ImageProxy], avoiding any RGB conversion.
 *
 * Algorithm (a stripped-down sibling of [PageEdgeDetector]):
 *  1. Down-sample the Y plane to a small thumbnail (~160 px on the long edge).
 *  2. Estimate background luminance from the four corner patches.
 *  3. Estimate page luminance from the centre patch.
 *  4. Threshold and scan inward from each edge to find the page rectangle.
 *  5. Return the rectangle in **image-source pixels** plus a confidence score.
 *
 * Inspired by the OSS-DocumentScanner / OpenScan live-detection loop, but with
 * pure Kotlin / no OpenCV dependency.
 *
 * The detector is stateless and thread-safe — feel free to call it from the
 * ImageAnalysis executor without synchronization.
 */
object LiveEdgeDetector {

    private const val THUMB_SIZE          = 160
    private const val MIN_BRIGHT_FRACTION = 0.30f
    private const val CORNER_DEPTH        = 0.12f

    data class LiveQuad(
        val tl: PointF,
        val tr: PointF,
        val br: PointF,
        val bl: PointF,
        /** 0..1 — caller decides what counts as "good enough". */
        val confidence: Float,
        /** Source frame size at the time of detection (pre-rotation). */
        val frameWidth: Int,
        val frameHeight: Int
    ) {
        /** Returns the bounding rect of the quad in source pixels. */
        fun bounds(): RectF = RectF(
            minOf(tl.x, bl.x), minOf(tl.y, tr.y),
            maxOf(tr.x, br.x), maxOf(bl.y, br.y)
        )
    }

    /**
     * Detects the page quad in [proxy].  Returns null when no usable rectangle
     * is found.  Caller is responsible for `proxy.close()` after consuming.
     *
     * The returned coordinates are in the YUV image's native orientation (no
     * rotation applied).  Apply [proxy.imageInfo.rotationDegrees] if you need
     * display orientation.
     */
    fun detect(proxy: ImageProxy): LiveQuad? {
        val yPlane = proxy.planes.getOrNull(0) ?: return null
        val w = proxy.width
        val h = proxy.height
        if (w <= 0 || h <= 0) return null

        // ── Down-sample Y plane into a small luminance grid ──────
        val scale = THUMB_SIZE.toFloat() / maxOf(w, h)
        val tw = (w * scale).toInt().coerceAtLeast(8)
        val th = (h * scale).toInt().coerceAtLeast(8)

        val rowStride = yPlane.rowStride
        val pixelStride = yPlane.pixelStride
        val buf = yPlane.buffer
        val bytes = ByteArray(buf.remaining())
        buf.get(bytes)

        val lum = Array(th) { IntArray(tw) }
        val sx = w.toFloat() / tw
        val sy = h.toFloat() / th
        for (y in 0 until th) {
            val srcY = (y * sy).toInt().coerceAtMost(h - 1)
            val rowOff = srcY * rowStride
            for (x in 0 until tw) {
                val srcX = (x * sx).toInt().coerceAtMost(w - 1)
                val idx = rowOff + srcX * pixelStride
                lum[y][x] = if (idx in bytes.indices) bytes[idx].toInt() and 0xFF else 0
            }
        }

        // ── Background + centre luminance estimate ───────────────
        val bgLum = estimateBg(lum, tw, th)
        var cSum = 0L; var cN = 0
        val cy0 = (th * 0.35).toInt(); val cy1 = (th * 0.65).toInt()
        val cx0 = (tw * 0.35).toInt(); val cx1 = (tw * 0.65).toInt()
        for (y in cy0 until cy1) for (x in cx0 until cx1) { cSum += lum[y][x]; cN++ }
        val centreLum = if (cN > 0) (cSum / cN).toInt() else 180
        val threshold = (bgLum * 0.55 + centreLum * 0.45).toInt().coerceIn(55, 220)

        // ── Edge scan ────────────────────────────────────────────
        fun rowB(y: Int): Float {
            var n = 0
            for (x in 0 until tw) if (lum[y][x] > threshold) n++
            return n.toFloat() / tw
        }
        fun colB(x: Int): Float {
            var n = 0
            for (y in 0 until th) if (lum[y][x] > threshold) n++
            return n.toFloat() / th
        }

        var topRow   = -1
        var botRow   = -1
        var leftCol  = -1
        var rightCol = -1
        for (y in 0 until th) if (rowB(y) > MIN_BRIGHT_FRACTION) { topRow = y; break }
        for (y in th - 1 downTo 0) if (rowB(y) > MIN_BRIGHT_FRACTION) { botRow = y; break }
        for (x in 0 until tw) if (colB(x) > MIN_BRIGHT_FRACTION) { leftCol = x; break }
        for (x in tw - 1 downTo 0) if (colB(x) > MIN_BRIGHT_FRACTION) { rightCol = x; break }

        if (topRow < 0 || botRow < 0 || leftCol < 0 || rightCol < 0) return null
        if (botRow <= topRow || rightCol <= leftCol) return null
        val pH = botRow - topRow; val pW = rightCol - leftCol
        if (pH < th * 0.25f || pW < tw * 0.25f) return null

        // ── Project back to source pixels ────────────────────────
        val left  = (leftCol  * sx).coerceIn(0f, w.toFloat())
        val top   = (topRow   * sy).coerceIn(0f, h.toFloat())
        val right = (rightCol * sx).coerceIn(0f, w.toFloat())
        val bot   = (botRow   * sy).coerceIn(0f, h.toFloat())

        // ── Confidence ───────────────────────────────────────────
        val coverage = (pH.toFloat() / th) * (pW.toFloat() / tw)
        val touchesAllEdges =
            topRow < 3 && botRow > th - 4 && leftCol < 3 && rightCol > tw - 4
        val contrast = ((threshold - bgLum).toFloat() / 60f).coerceIn(-0.3f, 0.3f)
        val conf = (coverage * (if (touchesAllEdges) 0.45f else 1f) + contrast)
            .coerceIn(0f, 1f)

        return LiveQuad(
            tl = PointF(left, top),
            tr = PointF(right, top),
            br = PointF(right, bot),
            bl = PointF(left, bot),
            confidence = conf,
            frameWidth = w,
            frameHeight = h
        )
    }

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
