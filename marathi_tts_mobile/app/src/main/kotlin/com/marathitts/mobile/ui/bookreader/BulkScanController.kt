package com.marathitts.mobile.ui.bookreader

import android.graphics.PointF
import android.os.SystemClock
import kotlin.math.hypot

/**
 * State machine that drives the auto-capture and bulk-scan flow.
 *
 * ## States
 *
 *   IDLE              → Live detector hasn't returned a usable quad recently.
 *   ADJUSTING         → Quad detected but corners are still moving.
 *   STABLE_HOLDING    → Quad has been stationary; counting toward auto-fire.
 *   FIRING            → Auto-fire triggered; the activity should call
 *                       [notifyCaptureCompleted] when the JPEG is saved.
 *   POST_CAPTURE_HOLD → Brief lock-out so the user has time to lift / turn page.
 *   AWAITING_PAGE_CHG → Bulk mode: waiting for the visual scene to change
 *                       enough to constitute a new page.
 *
 * ## Inputs
 *
 *   [observeFrame]            — call from each ImageAnalysis frame with the
 *                               latest [LiveEdgeDetector.LiveQuad] (nullable)
 *                               and [FrameQualityAnalyzer.FrameQuality].
 *   [setBulkMode]             — toggle bulk mode on/off.
 *   [notifyCaptureCompleted]  — call after the activity has finished saving
 *                               the captured JPEG.
 *   [resetForNextPage]        — call when the user wants to start a new
 *                               capture (e.g. tapping "Next" in bulk mode).
 *
 * ## Outputs
 *
 *   [Listener.onStateChanged] — drives the overlay colour + status pill.
 *   [Listener.onCountdown]    — 0..1 ring progress while STABLE_HOLDING.
 *   [Listener.onAutoFire]     — fired exactly once when entering FIRING.
 *
 * Inspired by OSS-DocumentScanner / OpenScan auto-capture loops.
 */
class BulkScanController(
    private val listener: Listener,
    private val stableHoldMs: Long = 800L,
    private val postCaptureLockoutMs: Long = 1200L,
    private val pageChangeDistanceFraction: Float = 0.04f,
    private val pageChangeBrightnessDelta: Int = 18,
    /** Max corner movement (as a fraction of the smaller frame dim) tolerated to remain "stable". */
    private val stabilityToleranceFraction: Float = 0.018f
) {

    enum class State { IDLE, ADJUSTING, STABLE_HOLDING, FIRING, POST_CAPTURE_HOLD, AWAITING_PAGE_CHG }

    interface Listener {
        fun onStateChanged(state: State, statusText: String)
        fun onCountdown(progress: Float)
        fun onAutoFire()
    }

    @Volatile private var bulkMode: Boolean = false
    @Volatile private var autoCaptureEnabled: Boolean = true
    @Volatile private var capturedCount: Int = 0

    private var state: State = State.IDLE

    // Tracking the corner positions across frames for stability checks
    private val lastQuad = arrayOf(PointF(), PointF(), PointF(), PointF())
    private var hasLastQuad = false
    private var stableSince: Long = 0L
    private var postCaptureUntil: Long = 0L

    // Cached "post-capture reference" for page-change detection
    private var refQuadCenter: PointF? = null
    private var refLuminance: Int = -1

    // ── Public toggles ───────────────────────────────────────────

    fun setBulkMode(enabled: Boolean) {
        bulkMode = enabled
        if (!enabled) {
            // Drop any AWAITING_PAGE_CHG lock when leaving bulk mode.
            transition(State.IDLE, statusForState(State.IDLE))
            listener.onCountdown(0f)
        }
    }

    fun isBulkMode(): Boolean = bulkMode
    fun setAutoCaptureEnabled(enabled: Boolean) {
        autoCaptureEnabled = enabled
        if (!enabled) {
            transition(State.IDLE, "Manual")
            listener.onCountdown(0f)
        }
    }
    fun isAutoCaptureEnabled(): Boolean = autoCaptureEnabled
    fun capturedCount(): Int = capturedCount

    /**
     * Call immediately after the JPEG is saved.  Updates internal state
     * based on whether bulk mode is active.
     */
    fun notifyCaptureCompleted(refLum: Int = -1, refCenter: PointF? = null) {
        capturedCount++
        refLuminance = refLum
        refQuadCenter = refCenter
        postCaptureUntil = SystemClock.elapsedRealtime() + postCaptureLockoutMs
        if (bulkMode) {
            transition(State.POST_CAPTURE_HOLD, "Captured ✓ — turn the page")
        } else {
            transition(State.IDLE, "Captured ✓")
        }
        listener.onCountdown(0f)
    }

    fun resetForNextPage() {
        hasLastQuad = false
        stableSince = 0L
        postCaptureUntil = 0L
        refQuadCenter = null
        refLuminance = -1
        transition(State.IDLE, statusForState(State.IDLE))
        listener.onCountdown(0f)
    }

    /**
     * Feed the latest live detection into the state machine.  Pass `null` for
     * [quad] when the detector returned no usable rectangle.
     */
    fun observeFrame(quad: LiveEdgeDetector.LiveQuad?, quality: FrameQualityAnalyzer.FrameQuality) {
        val now = SystemClock.elapsedRealtime()

        // ── Post-capture lock-out (bulk mode) ────────────────────
        if (state == State.POST_CAPTURE_HOLD) {
            if (now < postCaptureUntil) return
            // Lock-out elapsed: switch to AWAITING_PAGE_CHG (or IDLE if not bulk)
            if (bulkMode) {
                transition(State.AWAITING_PAGE_CHG, "Looking for next page…")
            } else {
                transition(State.IDLE, statusForState(State.IDLE))
            }
        }

        if (quad == null) {
            hasLastQuad = false
            stableSince = 0L
            listener.onCountdown(0f)
            if (state != State.AWAITING_PAGE_CHG && state != State.POST_CAPTURE_HOLD) {
                transition(State.IDLE, statusForState(State.IDLE))
            }
            return
        }

        val frameMin = minOf(quad.frameWidth, quad.frameHeight).toFloat()
        val tolerance = frameMin * stabilityToleranceFraction

        // ── Bulk-mode page-change gate ───────────────────────────
        if (state == State.AWAITING_PAGE_CHG) {
            val centre = quadCentre(quad)
            val ref = refQuadCenter
            val centreDist = if (ref != null) hypot((centre.x - ref.x), (centre.y - ref.y)) else Float.MAX_VALUE
            val brightDelta = if (refLuminance >= 0) Math.abs(quality.glareLuminance - refLuminance) else Int.MAX_VALUE
            val pageChangeOk = centreDist > frameMin * pageChangeDistanceFraction ||
                               brightDelta > pageChangeBrightnessDelta
            if (!pageChangeOk) {
                listener.onCountdown(0f)
                listener.onStateChanged(State.AWAITING_PAGE_CHG, "Looking for next page…")
                return
            }
            // Page changed — fall through to normal flow below.
            transition(State.ADJUSTING, "Adjusting…")
        }

        // ── Quality gate ─────────────────────────────────────────
        if (!quality.isAcceptable) {
            stableSince = 0L
            listener.onCountdown(0f)
            val msg = when {
                quality.isBlurry  -> "Hold steady — blurry"
                quality.hasGlare  -> "Move away from glare"
                else              -> "Adjusting…"
            }
            transition(State.ADJUSTING, msg)
            updateLastQuad(quad)
            return
        }

        // ── Stability check ──────────────────────────────────────
        val stable = hasLastQuad && cornersWithinTolerance(quad, tolerance)
        updateLastQuad(quad)

        if (!autoCaptureEnabled) {
            // Manual mode: still show the quad, no countdown/auto-fire.
            transition(if (stable) State.STABLE_HOLDING else State.ADJUSTING, "Manual — tap to capture")
            listener.onCountdown(0f)
            return
        }

        if (!stable) {
            stableSince = 0L
            listener.onCountdown(0f)
            transition(State.ADJUSTING, "Hold steady…")
            return
        }

        if (stableSince == 0L) {
            stableSince = now
            transition(State.STABLE_HOLDING, "Hold steady…")
        }
        val elapsed = now - stableSince
        val progress = (elapsed.toFloat() / stableHoldMs).coerceIn(0f, 1f)
        listener.onCountdown(progress)

        if (elapsed >= stableHoldMs && state == State.STABLE_HOLDING) {
            transition(State.FIRING, "Capturing…")
            stableSince = 0L
            listener.onCountdown(1f)
            listener.onAutoFire()
        }
    }

    // ── Helpers ──────────────────────────────────────────────────

    private fun cornersWithinTolerance(q: LiveEdgeDetector.LiveQuad, tol: Float): Boolean {
        return distanceLessThan(q.tl, lastQuad[0], tol) &&
               distanceLessThan(q.tr, lastQuad[1], tol) &&
               distanceLessThan(q.br, lastQuad[2], tol) &&
               distanceLessThan(q.bl, lastQuad[3], tol)
    }

    private fun distanceLessThan(a: PointF, b: PointF, tol: Float): Boolean {
        val dx = a.x - b.x; val dy = a.y - b.y
        return hypot(dx, dy) <= tol
    }

    private fun updateLastQuad(q: LiveEdgeDetector.LiveQuad) {
        lastQuad[0].set(q.tl); lastQuad[1].set(q.tr); lastQuad[2].set(q.br); lastQuad[3].set(q.bl)
        hasLastQuad = true
    }

    private fun quadCentre(q: LiveEdgeDetector.LiveQuad): PointF {
        return PointF(
            (q.tl.x + q.tr.x + q.br.x + q.bl.x) / 4f,
            (q.tl.y + q.tr.y + q.br.y + q.bl.y) / 4f
        )
    }

    private fun transition(newState: State, status: String) {
        if (state == newState) {
            listener.onStateChanged(newState, status)
            return
        }
        state = newState
        listener.onStateChanged(newState, status)
    }

    private fun statusForState(s: State): String = when (s) {
        State.IDLE              -> "Point at a page"
        State.ADJUSTING         -> "Adjusting…"
        State.STABLE_HOLDING    -> "Hold steady…"
        State.FIRING            -> "Capturing…"
        State.POST_CAPTURE_HOLD -> "Captured ✓"
        State.AWAITING_PAGE_CHG -> "Looking for next page…"
    }
}
