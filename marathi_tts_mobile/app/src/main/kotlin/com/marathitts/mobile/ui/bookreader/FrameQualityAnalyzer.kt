package com.marathitts.mobile.ui.bookreader

import androidx.camera.core.ImageProxy
import kotlin.math.abs

/**
 * Frame-level quality checks used to suppress auto-capture when the image is
 * unlikely to OCR well.
 *
 *  • **Blur** — Laplacian-variance score on the down-sampled Y plane.
 *    Sharp images score high (lots of high-frequency detail); blurry frames
 *    score low.  Threshold tuned empirically.
 *
 *  • **Glare** — Average luminance of the brightest 1 % of pixels.  When a
 *    glossy book page reflects a lamp, a small patch saturates to 255; this
 *    drives the score above the threshold even when the rest of the page is
 *    well-exposed.
 *
 * Inspired by the OSS-DocumentScanner / MakeACopy pre-capture quality gates,
 * but implemented with no OpenCV / no NDK so it runs anywhere.
 */
object FrameQualityAnalyzer {

    private const val THUMB_SIZE      = 120
    private const val BLUR_THRESHOLD  = 60.0     // variance below ⇒ blurry
    private const val GLARE_THRESHOLD = 245      // top-1% mean above ⇒ glare

    data class FrameQuality(
        val blurVariance: Double,
        val glareLuminance: Int,
        val isBlurry: Boolean,
        val hasGlare: Boolean
    ) {
        val isAcceptable: Boolean get() = !isBlurry && !hasGlare
    }

    /** Lightweight Y-plane analysis.  Caller is responsible for proxy lifecycle. */
    fun analyze(proxy: ImageProxy): FrameQuality {
        val yPlane = proxy.planes.getOrNull(0)
            ?: return FrameQuality(0.0, 0, isBlurry = true, hasGlare = false)

        val w = proxy.width; val h = proxy.height
        if (w <= 0 || h <= 0) {
            return FrameQuality(0.0, 0, isBlurry = true, hasGlare = false)
        }

        val rowStride = yPlane.rowStride
        val pixelStride = yPlane.pixelStride
        val buf = yPlane.buffer
        val bytes = ByteArray(buf.remaining())
        buf.get(bytes)

        // Down-sample into a small luminance grid we can pass twice cheaply.
        val scale = THUMB_SIZE.toFloat() / maxOf(w, h)
        val tw = (w * scale).toInt().coerceAtLeast(8)
        val th = (h * scale).toInt().coerceAtLeast(8)
        val sx = w.toFloat() / tw
        val sy = h.toFloat() / th
        val lum = IntArray(tw * th)
        for (y in 0 until th) {
            val srcY = (y * sy).toInt().coerceAtMost(h - 1)
            val rowOff = srcY * rowStride
            for (x in 0 until tw) {
                val srcX = (x * sx).toInt().coerceAtMost(w - 1)
                val idx = rowOff + srcX * pixelStride
                lum[y * tw + x] = if (idx in bytes.indices) bytes[idx].toInt() and 0xFF else 0
            }
        }

        val variance = laplacianVariance(lum, tw, th)
        val glare = topOnePercentMean(lum)

        return FrameQuality(
            blurVariance = variance,
            glareLuminance = glare,
            isBlurry = variance < BLUR_THRESHOLD,
            hasGlare = glare > GLARE_THRESHOLD
        )
    }

    /**
     * 4-neighbour discrete Laplacian:
     *   L(x,y) = |4·p(x,y) − p(x±1,y) − p(x,y±1)|
     * Variance of L over the interior pixels approximates focus quality.
     */
    private fun laplacianVariance(lum: IntArray, w: Int, h: Int): Double {
        if (w < 3 || h < 3) return 0.0
        var sum = 0.0; var sqSum = 0.0; var n = 0
        for (y in 1 until h - 1) {
            val rowOff = y * w
            for (x in 1 until w - 1) {
                val c = lum[rowOff + x]
                val l = 4 * c - lum[rowOff + x - 1] - lum[rowOff + x + 1] -
                        lum[rowOff - w + x] - lum[rowOff + w + x]
                val v = abs(l).toDouble()
                sum += v; sqSum += v * v; n++
            }
        }
        if (n == 0) return 0.0
        val mean = sum / n
        return (sqSum / n) - mean * mean
    }

    /** Mean of the top-1 % brightest pixels — flags localized glare hot-spots. */
    private fun topOnePercentMean(lum: IntArray): Int {
        if (lum.isEmpty()) return 0
        val sorted = lum.sortedArray()
        val cutoff = (sorted.size * 0.99).toInt().coerceIn(0, sorted.size - 1)
        var s = 0L; var n = 0
        for (i in cutoff until sorted.size) { s += sorted[i]; n++ }
        return if (n > 0) (s / n).toInt() else 0
    }
}
