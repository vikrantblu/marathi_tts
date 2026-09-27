package com.marathitts.mobile.ui.bookreader

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PointF
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View

/**
 * Transparent overlay drawn on top of the CameraX [androidx.camera.view.PreviewView]
 * to show the **live** detected page outline plus auto-capture feedback.
 *
 * What it draws (when enabled):
 *  • A 4-corner polygon outlining the detected page in view coordinates.
 *    Stroke colour reflects detection state (gray ⇒ no detect, yellow ⇒
 *    adjusting, green ⇒ stable / capturing, red ⇒ blur or glare warning).
 *  • Solid corner dots at each vertex.
 *  • Inside the polygon, a circular **countdown ring** that fills clockwise
 *    while the auto-capture timer is running.
 *  • A small status pill at top-centre showing one short label
 *    (e.g. "Hold steady…", "Bulk: page 3").
 *
 * Inspired by the OSS-DocumentScanner / OpenScan live HUD.  Pure Android
 * Canvas — no third-party dependencies.
 *
 * Coordinates passed to [setQuad] are in **view-pixel** space.  The Activity
 * is responsible for mapping image-space quads (from [LiveEdgeDetector]) onto
 * the PreviewView's display rectangle.
 */
class LiveQuadOverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    enum class State { IDLE, ADJUSTING, STABLE, WARNING }

    private val density = resources.displayMetrics.density

    // ── Paints ───────────────────────────────────────────────────

    private val quadPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 4f * density
        color = Color.GRAY
    }
    private val cornerDotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = Color.WHITE
    }
    private val ringBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 6f * density
        color = Color.argb(120, 255, 255, 255)
    }
    private val ringFgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 6f * density
        strokeCap = Paint.Cap.ROUND
        color = Color.GREEN
    }
    private val pillBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(190, 0, 0, 0)
        style = Paint.Style.FILL
    }
    private val pillTextPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 14f * density
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
    }

    // ── State ────────────────────────────────────────────────────

    private val quad = arrayOf(PointF(), PointF(), PointF(), PointF())
    private var hasQuad = false
    private var state = State.IDLE
    private var countdownProgress = 0f   // 0..1 (0 = empty, 1 = full)
    private var statusText: String? = null

    private val path = Path()
    private val ringRect = RectF()

    // ── Public API ───────────────────────────────────────────────

    /**
     * Update the displayed quad.  Coordinates are in this view's pixel space.
     * Pass `null` (or call [clearQuad]) to hide the polygon.
     */
    fun setQuad(tl: PointF, tr: PointF, br: PointF, bl: PointF, newState: State) {
        quad[0].set(tl); quad[1].set(tr); quad[2].set(br); quad[3].set(bl)
        hasQuad = true
        state = newState
        applyStateColor()
        invalidate()
    }

    fun clearQuad() {
        if (hasQuad || countdownProgress != 0f) {
            hasQuad = false
            countdownProgress = 0f
            state = State.IDLE
            applyStateColor()
            invalidate()
        }
    }

    /** Set the auto-capture progress (0..1).  0 hides the ring. */
    fun setCountdown(progress: Float) {
        val clamped = progress.coerceIn(0f, 1f)
        if (clamped != countdownProgress) {
            countdownProgress = clamped
            invalidate()
        }
    }

    /** Show a small status pill at the top of the view.  Pass null to hide. */
    fun setStatus(text: String?) {
        if (text != statusText) {
            statusText = text
            invalidate()
        }
    }

    private fun applyStateColor() {
        val c = when (state) {
            State.IDLE      -> Color.argb(140, 200, 200, 200)
            State.ADJUSTING -> Color.argb(220, 255, 200, 0)   // yellow
            State.STABLE    -> Color.argb(230, 76, 175, 80)   // green
            State.WARNING   -> Color.argb(230, 244, 67, 54)   // red
        }
        quadPaint.color = c
        ringFgPaint.color = c
    }

    // ── Drawing ──────────────────────────────────────────────────

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        if (hasQuad) {
            path.reset()
            path.moveTo(quad[0].x, quad[0].y)
            for (i in 1..3) path.lineTo(quad[i].x, quad[i].y)
            path.close()
            canvas.drawPath(path, quadPaint)

            val dotR = 6f * density
            for (p in quad) canvas.drawCircle(p.x, p.y, dotR, cornerDotPaint)

            // Countdown ring sits on the polygon's centroid
            if (countdownProgress > 0f) {
                val cx = (quad[0].x + quad[1].x + quad[2].x + quad[3].x) / 4f
                val cy = (quad[0].y + quad[1].y + quad[2].y + quad[3].y) / 4f
                val r  = 28f * density
                ringRect.set(cx - r, cy - r, cx + r, cy + r)
                canvas.drawCircle(cx, cy, r, ringBgPaint)
                canvas.drawArc(ringRect, -90f, 360f * countdownProgress, false, ringFgPaint)
            }
        }

        statusText?.let { txt ->
            val padH = 12f * density
            val padV = 6f  * density
            val tw = pillTextPaint.measureText(txt)
            val pillW = tw + padH * 2
            val pillH = pillTextPaint.textSize + padV * 2
            val cx = width / 2f
            val top = 12f * density
            val rect = RectF(cx - pillW / 2f, top, cx + pillW / 2f, top + pillH)
            canvas.drawRoundRect(rect, pillH / 2f, pillH / 2f, pillBgPaint)
            val textY = top + padV + pillTextPaint.textSize - 4f * density
            canvas.drawText(txt, cx, textY, pillTextPaint)
        }
    }
}
