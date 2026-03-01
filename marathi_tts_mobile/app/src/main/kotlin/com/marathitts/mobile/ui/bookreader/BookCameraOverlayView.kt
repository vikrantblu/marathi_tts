package com.marathitts.mobile.ui.bookreader

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View

/**
 * Transparent overlay drawn on top of the CameraX preview.
 *
 * Shows:
 *   • A dimmed area OUTSIDE the book zone
 *   • A bright rectangle = "place your open book here"
 *   • A dashed vertical center line = spine guide
 *   • Corner brackets for easy alignment
 *   • Instruction text at the top
 *
 * The guide occupies 96 % of width and 90 % of height, centered.
 */
class BookCameraOverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    /** true → two-page spread (shows spine line); false → single page */
    var isSpreadMode: Boolean = true
        set(value) { field = value; invalidate() }

    /**
     * Reserve this many px on the RIGHT so the guide frame doesn't overlap
     * the shutter panel. Set from the Activity after measuring the panel width.
     */
    var rightInsetPx: Float = 0f
        set(value) { field = value; invalidate() }

    /**
     * Reserve this many px at the TOP so the guide frame doesn't overlap
     * the slim top bar.
     */
    var topInsetPx: Float = 0f
        set(value) { field = value; invalidate() }

    // ── Paints ───────────────────────────────────────────────────

    private val dimPaint = Paint().apply {
        color = Color.argb(120, 0, 0, 0)    // semi-transparent black overlay
        style = Paint.Style.FILL
    }

    private val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }

    private val spinePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(200, 255, 165, 0) // orange dashed line
        style = Paint.Style.STROKE
        strokeWidth = 3f
        pathEffect = DashPathEffect(floatArrayOf(18f, 12f), 0f)
    }

    private val cornerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 5f
        strokeCap = Paint.Cap.ROUND
    }

    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 42f
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
        setShadowLayer(4f, 0f, 2f, Color.BLACK)
    }

    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(200, 255, 165, 0)
        textSize = 34f
        textAlign = Paint.Align.CENTER
        setShadowLayer(4f, 0f, 2f, Color.BLACK)
    }

    private val guidePath = Path()

    /**
     * Returns the guide-frame boundaries as fractions of the view's width/height.
     * Used by the Activity to pre-crop the captured JPEG to the book region before
     * running PageEdgeDetector and OCR, so background noise is excluded.
     *
     * NOTE: topInsetPx is intentionally NOT subtracted from the top fraction.
     * The top bar is a transparent UI overlay — the JPEG from the ViewPort
     * capture includes the full previewView area (including behind the top bar),
     * so the book page content starts at the very top of the JPEG.  Only the
     * shutter panel (rightInsetPx) represents dead screen real-estate where the
     * user CANNOT place book content, so that exclusion is kept.
     */
    fun getFrameFractions(): RectF {
        val w = width.toFloat()
        val h = height.toFloat()
        if (w == 0f || h == 0f) {
            // Fallback: near-full spread fractions
            return RectF(0.01f, 0.01f, 0.88f, 0.99f)
        }
        val hPad = w * 0.01f
        val vPad = h * 0.01f
        return RectF(
            hPad / w,
            vPad / h,                          // top: 1% — do NOT include topInsetPx
            (w - hPad - rightInsetPx) / w,     // right: exclude shutter panel
            (h - vPad) / h
        )
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()

        // ── Book zone: fill the available space (minus UI panel insets) ─
        // Small horizontal pad (1 %) + respect the shutter panel on the right
        // and the top bar above.
        val hPad   = w * 0.01f
        val vPad   = h * 0.02f
        val rect = RectF(
            hPad,
            topInsetPx + vPad,
            w - hPad - rightInsetPx,
            h - vPad
        )

        // ── Dim everything outside the book zone ─────────────────
        canvas.save()
        canvas.clipOutRect(rect.left, rect.top, rect.right, rect.bottom)
        canvas.drawRect(0f, 0f, w, h, dimPaint)
        canvas.restore()

        // ── Book outline ─────────────────────────────────────────
        canvas.drawRoundRect(rect, 12f, 12f, borderPaint)

        // ── Corner brackets (4 corners, L-shaped) ────────────────
        val cornerLen = 32f
        // Top-left
        canvas.drawLine(rect.left, rect.top + cornerLen, rect.left, rect.top, cornerPaint)
        canvas.drawLine(rect.left, rect.top, rect.left + cornerLen, rect.top, cornerPaint)
        // Top-right
        canvas.drawLine(rect.right - cornerLen, rect.top, rect.right, rect.top, cornerPaint)
        canvas.drawLine(rect.right, rect.top, rect.right, rect.top + cornerLen, cornerPaint)
        // Bottom-left
        canvas.drawLine(rect.left, rect.bottom - cornerLen, rect.left, rect.bottom, cornerPaint)
        canvas.drawLine(rect.left, rect.bottom, rect.left + cornerLen, rect.bottom, cornerPaint)
        // Bottom-right
        canvas.drawLine(rect.right - cornerLen, rect.bottom, rect.right, rect.bottom, cornerPaint)
        canvas.drawLine(rect.right, rect.bottom - cornerLen, rect.right, rect.bottom, cornerPaint)

        // ── Spine center line (only in spread mode) ──────────────
        if (isSpreadMode) {
            val cx = rect.centerX()
            guidePath.reset()
            guidePath.moveTo(cx, rect.top + 16f)
            guidePath.lineTo(cx, rect.bottom - 16f)
            canvas.drawPath(guidePath, spinePaint)

            // Spine + page labels drawn INSIDE the frame so they're always visible
            canvas.drawText("↕ Spine", cx, rect.centerY(), labelPaint)
            canvas.drawText("Left Page", rect.left + (cx - rect.left) / 2f, rect.top + 48f, labelPaint)
            canvas.drawText("Right Page", cx + (rect.right - cx) / 2f, rect.top + 48f, labelPaint)
        }

        // ── Instruction text (above the frame or at top of screen) ─────
        val msg = if (isSpreadMode) "Fill frame: both pages edge-to-edge" else "Fill frame: page edge-to-edge"
        // Draw inside the frame near the very top so it's always visible
        canvas.drawText(msg, w / 2f, rect.top + textPaint.textSize + 8f, textPaint)
    }
}
