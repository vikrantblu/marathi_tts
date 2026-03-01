package com.marathitts.mobile.ui.bookreader

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PointF
import android.graphics.RectF
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.hypot

/**
 * Interactive perspective-crop view for document/book photos.
 *
 * Displays the captured bitmap with 4 draggable corner handles (TL, TR, BR, BL).
 * The user drags the corners to align with the actual book corners.
 * Call [applyCrop] to get a perspective-corrected Bitmap.
 *
 * Handles are large (40dp) for easy finger dragging.
 * The area outside the selected quad is dimmed.
 */
class PerspectiveCropView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private var bitmap: Bitmap? = null
    private var bitmapRect = RectF()   // where bitmap is drawn (letterboxed)

    // 4 corners in VIEW coordinates: [TL, TR, BR, BL]
    private val corners = Array(4) { PointF() }
    private var dragIndex = -1

    private val density = context.resources.displayMetrics.density
    private val HANDLE_RADIUS = 22f * density          // 22dp touch handle
    private val HANDLE_TOUCH_RADIUS = 46f * density    // 46dp touch target

    // ── Paints ──────────────────────────────────────────────────

    private val dimPaint = Paint().apply {
        color = Color.argb(160, 0, 0, 0)
        style = Paint.Style.FILL
    }

    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        strokeWidth = 3f * density
        style = Paint.Style.STROKE
    }

    /** Edge lines that are more prominent (inner guide lines). */
    private val edgePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(220, 33, 150, 243)  // blue
        strokeWidth = 2.5f * density
        style = Paint.Style.STROKE
    }

    private val handleFillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.FILL
    }

    private val handleBorderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(230, 33, 150, 243)  // Material blue
        style = Paint.Style.STROKE
        strokeWidth = 4f * density
    }

    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 14f * density
        textAlign = Paint.Align.CENTER
        isFakeBoldText = true
        setShadowLayer(4f, 0f, 2f, Color.BLACK)
    }

    private val cornerLabels = arrayOf("◤ TL", "TR ◥", "BR ◢", "◣ BL")

    // ─────────────────────────────────────────────────────────────

    fun setBitmap(bmp: Bitmap) {
        bitmap = bmp
        if (width > 0 && height > 0) {
            initFromBitmap(bmp, width.toFloat(), height.toFloat())
        }
        invalidate()
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        bitmap?.let { initFromBitmap(it, w.toFloat(), h.toFloat()) }
    }

    /**
     * Compute the letterbox rect and initialise corners to the full extent of
     * the displayed bitmap (tiny 0.5 % inset just so handles aren't on the
     * very pixel edge).  The pre-crop in BookCameraActivity already removed
     * everything outside the overlay guide, so there is NO reason to add a
     * further margin here — doing so was cutting significant text off every edge.
     *
     * Users who need to fine-tune can drag the handles inward; tapping Confirm
     * immediately will keep the full page content.
     */
    private fun initFromBitmap(bmp: Bitmap, vw: Float, vh: Float) {
        val bw = bmp.width.toFloat()
        val bh = bmp.height.toFloat()
        val scale = minOf(vw / bw, vh / bh)
        val dw = bw * scale
        val dh = bh * scale
        val left = (vw - dw) / 2f
        val top = (vh - dh) / 2f
        bitmapRect = RectF(left, top, left + dw, top + dh)

        // Start handles at the full bitmap boundary (0.5 % inset to keep
        // handles visible and touchable at the very corner).
        val hInset = dw * 0.005f
        val vInset = dh * 0.005f
        corners[0].set(bitmapRect.left  + hInset, bitmapRect.top    + vInset)  // TL
        corners[1].set(bitmapRect.right - hInset, bitmapRect.top    + vInset)  // TR
        corners[2].set(bitmapRect.right - hInset, bitmapRect.bottom - vInset)  // BR
        corners[3].set(bitmapRect.left  + hInset, bitmapRect.bottom - vInset)  // BL
    }

    // ── Drawing ──────────────────────────────────────────────────

    override fun onDraw(canvas: Canvas) {
        val bmp = bitmap ?: return

        // 1. Letterboxed bitmap
        canvas.drawBitmap(bmp, null, bitmapRect, Paint(Paint.FILTER_BITMAP_FLAG))

        // 2. Dim area outside the quad
        val quadPath = buildQuadPath()
        canvas.save()
        canvas.clipOutPath(quadPath)
        canvas.drawRect(bitmapRect, dimPaint)
        canvas.restore()

        // 3. Edge lines (inner highlight guide lines)
        canvas.drawPath(quadPath, edgePaint)
        canvas.drawPath(quadPath, linePaint)

        // 4. Cross-hairs at midpoints for alignment aid (thin, translucent)
        drawMidLines(canvas)

        // 5. Corner handles
        for (i in corners.indices) {
            canvas.drawCircle(corners[i].x, corners[i].y, HANDLE_RADIUS, handleFillPaint)
            canvas.drawCircle(corners[i].x, corners[i].y, HANDLE_RADIUS, handleBorderPaint)
        }
    }

    private fun buildQuadPath(): Path {
        return Path().apply {
            moveTo(corners[0].x, corners[0].y)
            lineTo(corners[1].x, corners[1].y)
            lineTo(corners[2].x, corners[2].y)
            lineTo(corners[3].x, corners[3].y)
            close()
        }
    }

    private fun drawMidLines(canvas: Canvas) {
        val midPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.argb(90, 255, 255, 255)
            strokeWidth = 1.5f * density
            style = Paint.Style.STROKE
        }
        // Top-mid → Bottom-mid and Left-mid → Right-mid
        val tmx = (corners[0].x + corners[1].x) / 2f
        val tmy = (corners[0].y + corners[1].y) / 2f
        val bmx = (corners[2].x + corners[3].x) / 2f
        val bmy = (corners[2].y + corners[3].y) / 2f
        canvas.drawLine(tmx, tmy, bmx, bmy, midPaint)

        val lmx = (corners[0].x + corners[3].x) / 2f
        val lmy = (corners[0].y + corners[3].y) / 2f
        val rmx = (corners[1].x + corners[2].x) / 2f
        val rmy = (corners[1].y + corners[2].y) / 2f
        canvas.drawLine(lmx, lmy, rmx, rmy, midPaint)
    }

    // ── Touch handling ───────────────────────────────────────────

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                dragIndex = findClosestHandle(event.x, event.y)
                if (dragIndex >= 0) { parent.requestDisallowInterceptTouchEvent(true) }
                return dragIndex >= 0
            }
            MotionEvent.ACTION_MOVE -> {
                if (dragIndex >= 0) {
                    corners[dragIndex].x = event.x.coerceIn(bitmapRect.left, bitmapRect.right)
                    corners[dragIndex].y = event.y.coerceIn(bitmapRect.top, bitmapRect.bottom)
                    invalidate()
                    return true
                }
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                dragIndex = -1
                parent.requestDisallowInterceptTouchEvent(false)
            }
        }
        return super.onTouchEvent(event)
    }

    private fun findClosestHandle(x: Float, y: Float): Int {
        var best = -1
        var bestDist = Float.MAX_VALUE
        for ((i, pt) in corners.withIndex()) {
            val dist = hypot(pt.x - x, pt.y - y)
            if (dist < HANDLE_TOUCH_RADIUS && dist < bestDist) {
                best = i
                bestDist = dist
            }
        }
        return best
    }

    // ── Programmatic corner setter (for auto-detection) ────────────

    /**
     * Set corners from auto-detected bitmap-pixel coordinates.
     * Call AFTER [setBitmap] so that [bitmapRect] is already initialised.
     * Coordinates are in the source bitmap's pixel space (not view space).
     *
     * @param tl top-left, @param tr top-right, @param br bottom-right, @param bl bottom-left
     */
    fun setDetectedCorners(tl: PointF, tr: PointF, br: PointF, bl: PointF) {
        val bmp = bitmap ?: return
        val sx = bitmapRect.width()  / bmp.width
        val sy = bitmapRect.height() / bmp.height
        fun toView(pt: PointF) = PointF(
            (bitmapRect.left + pt.x * sx).coerceIn(bitmapRect.left, bitmapRect.right),
            (bitmapRect.top  + pt.y * sy).coerceIn(bitmapRect.top,  bitmapRect.bottom)
        )
        corners[0].set(toView(tl))
        corners[1].set(toView(tr))
        corners[2].set(toView(br))
        corners[3].set(toView(bl))
        invalidate()
    }

    // ── Perspective correction ───────────────────────────────────

    /**
     * Applies perspective warp using the current interactive corner positions.
     * Corners are in VIEW coordinates — ONLY call this when the view is visible
     * and has been measured (width/height > 0). For the silent auto-apply path
     * use the companion [perspectiveCropDirect] instead.
     */
    fun applyCrop(): Bitmap {
        val bmp = bitmap ?: error("No bitmap loaded")
        // View-space → bitmap-pixel-space
        val sx = bmp.width  / bitmapRect.width()
        val sy = bmp.height / bitmapRect.height()
        fun toPx(pt: PointF) = PointF(
            (pt.x - bitmapRect.left) * sx,
            (pt.y - bitmapRect.top)  * sy
        )
        return perspectiveCropDirect(
            bmp,
            toPx(corners[0]), toPx(corners[1]),
            toPx(corners[2]), toPx(corners[3])
        )
    }

    companion object {
        /**
         * Perspective-warp [bmp] using corners already in BITMAP PIXEL space.
         * This does NOT require the view to be visible or measured — safe to call
         * from background tasks or when the crop container is GONE.
         *
         * @param tl top-left   @param tr top-right
         * @param br bottom-right @param bl bottom-left
         * (all in bitmap pixel coordinates)
         */
        fun perspectiveCropDirect(
            bmp: Bitmap,
            tl: PointF, tr: PointF, br: PointF, bl: PointF
        ): Bitmap {
            val topW  = hypot(tr.x - tl.x, tr.y - tl.y)
            val botW  = hypot(br.x - bl.x, br.y - bl.y)
            val leftH = hypot(bl.x - tl.x, bl.y - tl.y)
            val rightH= hypot(br.x - tr.x, br.y - tr.y)

            // Clamp to sane range; NaN/0 would crash Bitmap.createBitmap
            val outW = maxOf(topW,  botW ).toInt().coerceIn(100, 8192)
            val outH = maxOf(leftH, rightH).toInt().coerceIn(100, 8192)

            val matrix = Matrix()
            matrix.setPolyToPoly(
                floatArrayOf(tl.x, tl.y, tr.x, tr.y, br.x, br.y, bl.x, bl.y), 0,
                floatArrayOf(0f, 0f, outW.toFloat(), 0f,
                              outW.toFloat(), outH.toFloat(), 0f, outH.toFloat()), 0,
                4
            )
            val output = Bitmap.createBitmap(outW, outH, Bitmap.Config.ARGB_8888)
            Canvas(output).drawBitmap(bmp, matrix, Paint(Paint.FILTER_BITMAP_FLAG))
            return output
        }
    }
}
