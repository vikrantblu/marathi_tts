package com.marathitts.mobile.ui.bookreader

import android.app.Activity
import android.content.Intent
import android.content.pm.ActivityInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.graphics.PointF
import android.graphics.RectF
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.util.Size
import android.view.View
import android.view.WindowInsetsController
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.camera2.interop.Camera2Interop
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.UseCaseGroup
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import android.hardware.camera2.CaptureRequest
import androidx.exifinterface.media.ExifInterface
import androidx.lifecycle.lifecycleScope
import com.marathitts.mobile.databinding.ActivityBookCameraBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * CameraX-based activity for capturing open-book photos.
 *
 * Phase 1 — Live preview with a [BookCameraOverlayView] alignment guide and
 *            (in AUTO mode) a [LiveQuadOverlayView] HUD that shows real-time
 *            page-edge detection plus an auto-capture countdown.  Camera2
 *            interop sets CONTINUOUS_PICTURE autofocus and MAXIMIZE_QUALITY
 *            capture so the text is crisp across the full page.
 *
 *            • Auto-capture loop drives [BulkScanController] using
 *              [LiveEdgeDetector] + [FrameQualityAnalyzer] outputs.
 *            • Bulk mode keeps the camera open after each successful capture
 *              and waits for the visual scene to change before firing again.
 *            • In spread mode every captured page is auto-split down the
 *              spine so the caller receives two single pages.
 *
 * Phase 2 — [PerspectiveCropView] lets the user drag 4 corner handles to
 *            correct perspective distortion (kept as a fallback path; the
 *            default flow auto-saves without showing this editor).
 *
 * Caller keys:
 *   Input  → EXTRA_SPREAD_MODE (Boolean, default true)
 *   Output → EXTRA_IMAGE_PATH  (String, first page — kept for backwards compat)
 *            EXTRA_IMAGE_PATHS (ArrayList<String>, all pages from the session)
 *            EXTRA_SPREAD_MODE (Boolean, current mode after possible toggle)
 */
class BookCameraActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SPREAD_MODE = "spread_mode"
        const val EXTRA_IMAGE_PATH  = "image_path"
        const val EXTRA_IMAGE_PATHS = "image_paths"
        private const val TAG = "BookCameraActivity"
    }

    private lateinit var binding: ActivityBookCameraBinding
    private lateinit var cameraExecutor: ExecutorService
    private lateinit var analysisExecutor: ExecutorService
    private var imageCapture: ImageCapture? = null
    private var isSpreadMode = true
    private var rawFile: File? = null

    /** All page JPEGs saved during this activity session (single or bulk). */
    private val capturedPaths = mutableListOf<String>()

    /** Auto-mode scaffolding. */
    private lateinit var bulkController: BulkScanController
    @Volatile private var captureInFlight = false
    @Volatile private var lastFrameLuminance: Int = -1
    @Volatile private var lastFrameQuadCentre: PointF? = null


    // ── Lifecycle ────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookCameraBinding.inflate(layoutInflater)
        setContentView(binding.root)

        isSpreadMode = intent.getBooleanExtra(EXTRA_SPREAD_MODE, true)
        applyOrientation()   // landscape for spread, portrait for single page
        hideSystemBars()     // full-screen immersive — no status bar / nav bar
        supportActionBar?.hide()
        binding.overlayView.isSpreadMode = isSpreadMode
        binding.modeLabel.text = if (isSpreadMode) "Two-Page Spread" else "Single Page"

        // After first layout pass, measure the shutter panel and tell the overlay
        // so the guide frame doesn't overlap the control strip.
        binding.root.post {
            val shutterW = binding.shutterPanel.width.toFloat()
            val topBarDp = 48f   // matches the slim top bar height in the layout
            val topBarPx = topBarDp * resources.displayMetrics.density
            binding.overlayView.rightInsetPx = shutterW
            binding.overlayView.topInsetPx   = topBarPx
        }

        cameraExecutor   = Executors.newSingleThreadExecutor()
        analysisExecutor = Executors.newSingleThreadExecutor()

        // Auto-capture state machine — feeds LiveQuadOverlayView and triggers
        // takePhoto() on its own when stability + quality criteria are met.
        bulkController = BulkScanController(object : BulkScanController.Listener {
            override fun onStateChanged(state: BulkScanController.State, statusText: String) {
                runOnUiThread {
                    val overlayState = when (state) {
                        BulkScanController.State.IDLE              -> LiveQuadOverlayView.State.IDLE
                        BulkScanController.State.ADJUSTING         -> LiveQuadOverlayView.State.ADJUSTING
                        BulkScanController.State.STABLE_HOLDING    -> LiveQuadOverlayView.State.STABLE
                        BulkScanController.State.FIRING            -> LiveQuadOverlayView.State.STABLE
                        BulkScanController.State.POST_CAPTURE_HOLD -> LiveQuadOverlayView.State.STABLE
                        BulkScanController.State.AWAITING_PAGE_CHG -> LiveQuadOverlayView.State.IDLE
                    }
                    // The overlay quad's colour is updated next time setQuad() runs;
                    // we still need to push status text immediately.
                    binding.liveQuadOverlay.setStatus(statusText)
                }
            }

            override fun onCountdown(progress: Float) {
                runOnUiThread { binding.liveQuadOverlay.setCountdown(progress) }
            }

            override fun onAutoFire() {
                runOnUiThread {
                    if (!captureInFlight) takePhoto(viaAuto = true)
                }
            }
        })

        startCamera()

        // ── Phase 1 controls ─────────────────────────────────────

        binding.backBtn.setOnClickListener { finishWithCurrentResult(canceledIfEmpty = true) }

        binding.modeToggleBtn.setOnClickListener {
            isSpreadMode = !isSpreadMode
            applyOrientation()
            binding.overlayView.isSpreadMode = isSpreadMode
            binding.modeLabel.text = if (isSpreadMode) "Two-Page Spread" else "Single Page"
        }

        binding.shutterButton.setOnClickListener { takePhoto(viaAuto = false) }

        // Auto / Manual toggle — gates the BulkScanController auto-fire.
        binding.autoToggleBtn.setOnClickListener {
            val next = !bulkController.isAutoCaptureEnabled()
            bulkController.setAutoCaptureEnabled(next)
            updateAutoToggleUi()
        }
        updateAutoToggleUi()

        // Bulk toggle — keeps the camera open after each capture.
        binding.bulkToggleBtn.setOnClickListener {
            val next = !bulkController.isBulkMode()
            bulkController.setBulkMode(next)
            updateBulkUi()
        }
        updateBulkUi()

        binding.doneBtn.setOnClickListener { finishWithCurrentResult(canceledIfEmpty = false) }

        // ── Phase 2 controls (perspective crop editor) ────────────

        binding.confirmBtn.setOnClickListener { confirmCrop() }

        binding.retakeBtn.setOnClickListener {
            // Discard the crop and go back to camera
            showCameraPhase()
        }

    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        analysisExecutor.shutdown()
    }

    private fun applyOrientation() {
        requestedOrientation = if (isSpreadMode)
            ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        else
            ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
    }

    /** Hide the status bar and navigation bar for a fully immersive camera view. */
    @Suppress("DEPRECATION")
    private fun hideSystemBars() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.insetsController?.let {
                it.hide(
                    android.view.WindowInsets.Type.statusBars() or
                    android.view.WindowInsets.Type.navigationBars()
                )
                it.systemBarsBehavior =
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            )
        }
    }

    // ── Camera setup ─────────────────────────────────────────────

    private fun startCamera() {
        val providerFuture = ProcessCameraProvider.getInstance(this)
        providerFuture.addListener({
            val cameraProvider = providerFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }

            // ── ImageCapture with Camera2 interop for sharp book photos ──
            //
            // CAPTURE_MODE_MAXIMIZE_QUALITY: uses the full sensor resolution,
            //   no speed / latency trade-offs — necessary for small text.
            //
            // CONTROL_AF_MODE_CONTINUOUS_PICTURE: keeps focus locked on the
            //   scene continuously; when the shutter fires the lens is already
            //   focused, unlike CONTINUOUS_VIDEO which can drift.
            //
            // CONTROL_AE_MODE_ON: standard auto-exposure (no flash override)
            //   so the full page is evenly exposed.
            val captureBuilder = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                .setFlashMode(ImageCapture.FLASH_MODE_AUTO)

            Camera2Interop.Extender(captureBuilder)
                .setCaptureRequestOption(
                    CaptureRequest.CONTROL_AF_MODE,
                    CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE
                )
                .setCaptureRequestOption(
                    CaptureRequest.CONTROL_AE_MODE,
                    CaptureRequest.CONTROL_AE_MODE_ON
                )

            val capture = captureBuilder.build()
            imageCapture = capture

            // ── ImageAnalysis use-case for auto-mode HUD ──────────
            // STRATEGY_KEEP_ONLY_LATEST avoids back-pressure: if our analyzer
            // is slow we silently drop frames instead of stalling the pipeline.
            // ~640px target keeps the analysis cheap; the full sensor feed is
            // still used for the actual JPEG via ImageCapture.
            val analysis = ImageAnalysis.Builder()
                .setTargetResolution(Size(640, 480))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(analysisExecutor) { proxy -> handleAnalysisFrame(proxy) } }

            try {
                cameraProvider.unbindAll()
                // Bind Preview + ImageCapture under a shared ViewPort so the
                // captured JPEG is cropped to exactly what the PreviewView shows.
                // Without this, ImageCapture uses the full 4:3 sensor while the
                // preview shows a 16:9 crop — the overlay frame fractions would
                // not match the captured image.
                val viewport = binding.previewView.viewPort
                if (viewport != null) {
                    val useCaseGroup = UseCaseGroup.Builder()
                        .addUseCase(preview)
                        .addUseCase(capture)
                        .addUseCase(analysis)
                        .setViewPort(viewport)
                        .build()
                    cameraProvider.bindToLifecycle(
                        this, CameraSelector.DEFAULT_BACK_CAMERA, useCaseGroup
                    )
                    Log.d(TAG, "Bound with ViewPort (aspect=${viewport.aspectRatio})")
                } else {
                    Log.w(TAG, "ViewPort not ready — binding without crop alignment")
                    cameraProvider.bindToLifecycle(
                        this, CameraSelector.DEFAULT_BACK_CAMERA, preview, capture, analysis
                    )
                }
            } catch (e: Exception) {
                Toast.makeText(this, "Camera init failed: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    // ── Live-frame analysis (auto-mode HUD + auto-capture) ───────

    /**
     * Per-frame callback bound to the ImageAnalysis use-case.  Runs on
     * [analysisExecutor]; **must** call [ImageProxy.close] before returning.
     *
     * Pipeline:
     *   1. Skip while a JPEG capture is in-flight (avoid contention).
     *   2. Run [LiveEdgeDetector] + [FrameQualityAnalyzer] on the YUV proxy.
     *   3. Map the detected quad from rotated image-space → PreviewView pixels.
     *   4. Hand off to [BulkScanController] which decides when to fire.
     *   5. Push the quad and an overlay state to [LiveQuadOverlayView].
     */
    private fun handleAnalysisFrame(proxy: ImageProxy) {
        try {
            if (captureInFlight) return
            val quad = LiveEdgeDetector.detect(proxy)
            val quality = FrameQualityAnalyzer.analyze(proxy)
            lastFrameLuminance = quality.let {
                // Use centre patch luminance recorded during edge detection if
                // present; otherwise fall back to a quick mean derived from the
                // glare metric (good enough for change-detection).
                quad?.let { q -> ((q.confidence * 255).toInt()) } ?: it.glareLuminance
            }

            // Send to controller (it will run on UI thread for state callbacks).
            val centre = quad?.let { PointF((it.tl.x + it.br.x) / 2f, (it.tl.y + it.br.y) / 2f) }
            lastFrameQuadCentre = centre

            // Translate the quad to view-space and update the HUD.
            runOnUiThread {
                if (quad == null) {
                    binding.liveQuadOverlay.clearQuad()
                } else {
                    val viewQuad = mapImageQuadToView(quad)
                    val overlayState = computeOverlayState(quad.confidence, quality.isAcceptable)
                    binding.liveQuadOverlay.setQuad(
                        viewQuad[0], viewQuad[1], viewQuad[2], viewQuad[3], overlayState
                    )
                }
                bulkController.observeFrame(quad, quality)
            }
        } finally {
            proxy.close()
        }
    }

    /** Map the four corners from the analyzer's image space to PreviewView pixels. */
    private fun mapImageQuadToView(quad: LiveEdgeDetector.LiveQuad): Array<PointF> {
        val viewW = binding.previewView.width.toFloat()
        val viewH = binding.previewView.height.toFloat()
        if (viewW <= 0f || viewH <= 0f) {
            return arrayOf(quad.tl, quad.tr, quad.br, quad.bl)
        }
        // The analyzer returns coords in the **rotated** image frame
        // (frameWidth/Height already account for rotation in LiveEdgeDetector).
        val scaleX = viewW / quad.frameWidth.toFloat()
        val scaleY = viewH / quad.frameHeight.toFloat()
        val scale = minOf(scaleX, scaleY)
        val drawW = quad.frameWidth  * scale
        val drawH = quad.frameHeight * scale
        val offX  = (viewW - drawW) / 2f
        val offY  = (viewH - drawH) / 2f
        fun map(p: PointF) = PointF(p.x * scale + offX, p.y * scale + offY)
        return arrayOf(map(quad.tl), map(quad.tr), map(quad.br), map(quad.bl))
    }

    private fun computeOverlayState(confidence: Float, qualityOk: Boolean): LiveQuadOverlayView.State {
        return when {
            !qualityOk          -> LiveQuadOverlayView.State.WARNING
            confidence >= 0.55f -> LiveQuadOverlayView.State.STABLE
            confidence >= 0.30f -> LiveQuadOverlayView.State.ADJUSTING
            else                -> LiveQuadOverlayView.State.IDLE
        }
    }

    // ── Phase 1 — Capture ────────────────────────────────────────

    /**
     * Trigger ImageCapture.  May be called by the manual shutter button or
     * by [BulkScanController.Listener.onAutoFire].
     */
    private fun takePhoto(viaAuto: Boolean) {
        val capture = imageCapture ?: return
        if (captureInFlight) return
        captureInFlight = true
        binding.shutterButton.isEnabled = false

        val file = File(cacheDir, "book_raw_${System.currentTimeMillis()}.jpg")
        rawFile = file
        val outputOptions = ImageCapture.OutputFileOptions.Builder(file).build()

        capture.takePicture(outputOptions, ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    loadAndShowCrop(file)
                }

                override fun onError(exc: ImageCaptureException) {
                    captureInFlight = false
                    binding.shutterButton.isEnabled = true
                    Toast.makeText(
                        this@BookCameraActivity,
                        "Capture failed: ${exc.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            })
    }

    private fun loadAndShowCrop(file: File) {
        binding.shutterButton.isEnabled = false
        showDetectingIndicator(true)

        lifecycleScope.launch(Dispatchers.IO) {
            // ── Step 1: Load with EXIF rotation applied ──────────────────
            val fullBmp = loadBitmapRespectingExif(file.absolutePath)
            if (fullBmp == null) {
                withContext(Dispatchers.Main) {
                    captureInFlight = false
                    showDetectingIndicator(false)
                    binding.shutterButton.isEnabled = true
                    Toast.makeText(this@BookCameraActivity, "Could not load photo", Toast.LENGTH_SHORT).show()
                }
                return@launch
            }
            Log.d(TAG, "Loaded: ${fullBmp.width}x${fullBmp.height}")

            // ── Step 2: Pre-crop to the overlay guide frame ──────────────
            val frameFrac: RectF = withContext(Dispatchers.Main) {
                binding.overlayView.getFrameFractions()
            }
            var bmp = cropToFractions(fullBmp, frameFrac)
            if (bmp !== fullBmp) fullBmp.recycle()
            Log.d(TAG, "Pre-cropped to frame: ${bmp.width}x${bmp.height} (frac=$frameFrac)")

            // ── Step 3: Auto-detect page edges for perspective correction ─
            val detected = PageEdgeDetector.detect(bmp)
            Log.d(TAG, "PageEdgeDetector: conf=${detected?.confidence ?: 0f}")

            if (detected != null && detected.confidence >= 0.30f) {
                Log.d(TAG, "Applying perspective correction (conf=${detected.confidence})")
                val corrected = PerspectiveCropView.perspectiveCropDirect(
                    bmp, detected.tl, detected.tr, detected.br, detected.bl
                )
                bmp.recycle()
                bmp = corrected
            }

            // ── Step 4: Spread auto-split (Open-book) ────────────────────
            // For book spreads we split down the visual spine so the caller
            // gets two single pages — same as OSS-DocumentScanner's open-book
            // mode.  We assume a roughly vertical spine at the midpoint; a
            // more sophisticated darkest-column scan can be added later.
            val newPaths = mutableListOf<String>()
            if (isSpreadMode && bmp.width >= bmp.height) {
                val mid = bmp.width / 2
                val left  = Bitmap.createBitmap(bmp, 0,        0, mid,             bmp.height)
                val right = Bitmap.createBitmap(bmp, mid,      0, bmp.width - mid, bmp.height)
                bmp.recycle()
                newPaths += writeJpeg(left,  "L")
                newPaths += writeJpeg(right, "R")
                left.recycle(); right.recycle()
            } else {
                newPaths += writeJpeg(bmp, "S")
                bmp.recycle()
            }
            rawFile?.delete()
            capturedPaths.addAll(newPaths)

            withContext(Dispatchers.Main) {
                showDetectingIndicator(false)
                binding.shutterButton.isEnabled = true
                captureInFlight = false
                updateBulkUi()

                // Notify BulkScanController of capture success; it transitions
                // to POST_CAPTURE_HOLD and waits for the scene to change.
                bulkController.notifyCaptureCompleted(
                    refLum    = lastFrameLuminance,
                    refCenter = lastFrameQuadCentre
                )

                if (bulkController.isBulkMode()) {
                    // Stay in camera; user keeps flipping pages.
                    Toast.makeText(
                        this@BookCameraActivity,
                        "Captured page ${capturedPaths.size}",
                        Toast.LENGTH_SHORT
                    ).show()
                } else {
                    // Single-shot mode — return immediately.
                    finishWithCurrentResult(canceledIfEmpty = false)
                }
            }
        }
    }

    /** Save bitmap to cache as JPEG and return the absolute path. */
    private fun writeJpeg(bmp: Bitmap, suffix: String): String {
        val out = File(cacheDir, "book_deskewed_${System.currentTimeMillis()}_$suffix.jpg")
        out.outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 95, it) }
        return out.absolutePath
    }

    /**
     * Send results back to the caller and end the activity.
     * Always populates both [EXTRA_IMAGE_PATH] (first page, legacy callers)
     * and [EXTRA_IMAGE_PATHS] (full list, new multi-page callers).
     */
    private fun finishWithCurrentResult(canceledIfEmpty: Boolean) {
        if (capturedPaths.isEmpty()) {
            if (canceledIfEmpty) setResult(Activity.RESULT_CANCELED)
            finish()
            return
        }
        val result = Intent().apply {
            putExtra(EXTRA_IMAGE_PATH, capturedPaths.first())
            putStringArrayListExtra(EXTRA_IMAGE_PATHS, ArrayList(capturedPaths))
            putExtra(EXTRA_SPREAD_MODE, isSpreadMode)
        }
        setResult(Activity.RESULT_OK, result)
        finish()
    }

    private fun updateAutoToggleUi() {
        val on = bulkController.isAutoCaptureEnabled()
        binding.autoToggleBtn.text = if (on) "AUTO" else "MANUAL"
        binding.autoToggleBtn.backgroundTintList =
            android.content.res.ColorStateList.valueOf(
                if (on) 0x664CAF50.toInt() else 0x66607D8B.toInt()
            )
        binding.shutterHint.text = if (on) "Auto" else "Tap"
        // Hide the static guide while live HUD is the source of truth.
        binding.overlayView.visibility = if (on) View.GONE else View.VISIBLE
        if (!on) binding.liveQuadOverlay.clearQuad()
    }

    private fun updateBulkUi() {
        val bulk = bulkController.isBulkMode()
        binding.bulkToggleBtn.text = if (bulk) "BULK ✓" else "BULK"
        binding.bulkToggleBtn.backgroundTintList =
            android.content.res.ColorStateList.valueOf(
                if (bulk) 0x664CAF50.toInt() else 0x66607D8B.toInt()
            )
        val n = capturedPaths.size
        binding.pageCountChip.visibility = if (bulk && n > 0) View.VISIBLE else View.GONE
        binding.pageCountChip.text = "$n page${if (n == 1) "" else "s"}"
        binding.doneBtn.visibility = if (bulk && n > 0) View.VISIBLE else View.GONE
    }

    // ── Bitmap helpers ───────────────────────────────────────────

    /**
     * Loads a JPEG from disk and applies its EXIF orientation tag.
     * Without this, landscape-mode captures arrive portrait-rotated because
     * CameraX saves the raw sensor orientation + an EXIF rotation tag.
     */
    private fun loadBitmapRespectingExif(path: String): Bitmap? {
        val raw = BitmapFactory.decodeFile(path) ?: return null
        val rotation = try {
            when (ExifInterface(path).getAttributeInt(
                ExifInterface.TAG_ORIENTATION,
                ExifInterface.ORIENTATION_NORMAL
            )) {
                ExifInterface.ORIENTATION_ROTATE_90  -> 90f
                ExifInterface.ORIENTATION_ROTATE_180 -> 180f
                ExifInterface.ORIENTATION_ROTATE_270 -> 270f
                else                                 -> 0f
            }
        } catch (e: Exception) {
            Log.w(TAG, "EXIF read failed: ${e.message}"); 0f
        }
        if (rotation == 0f) return raw
        Log.d(TAG, "Applying EXIF rotation: ${rotation.toInt()}°")
        val m = Matrix().apply { postRotate(rotation) }
        val rotated = Bitmap.createBitmap(raw, 0, 0, raw.width, raw.height, m, true)
        raw.recycle()
        return rotated
    }

    /**
     * Crops [bmp] to the fraction rect [frac] (left/top/right/bottom in 0..1).
     * Returns the same instance unchanged if the frac covers the whole bitmap.
     */
    private fun cropToFractions(bmp: Bitmap, frac: RectF): Bitmap {
        val x = (bmp.width  * frac.left  ).toInt().coerceIn(0, bmp.width  - 1)
        val y = (bmp.height * frac.top   ).toInt().coerceIn(0, bmp.height - 1)
        val w = ((bmp.width  * frac.width ())).toInt().coerceAtLeast(1)
        val h = ((bmp.height * frac.height())).toInt().coerceAtLeast(1)
        val safeW = (x + w).coerceAtMost(bmp.width)  - x
        val safeH = (y + h).coerceAtMost(bmp.height) - y
        if (safeW <= 0 || safeH <= 0) return bmp
        if (x == 0 && y == 0 && safeW == bmp.width && safeH == bmp.height) return bmp
        return Bitmap.createBitmap(bmp, x, y, safeW, safeH)
    }

    private fun showDetectingIndicator(show: Boolean) {
        // Re-use the mode label as a brief status — keeps the layout simple
        if (show) binding.modeLabel.text = "Detecting page…"
        else      binding.modeLabel.text = if (isSpreadMode) "Two-Page Spread" else "Single Page"
    }

    // ── Phase 2 — Perspective crop ───────────────────────────────

    private fun confirmCrop() {
        binding.confirmBtn.isEnabled = false
        binding.retakeBtn.isEnabled  = false

        try {
            val corrected = binding.cropView.applyCrop()

            val outFile = File(cacheDir, "book_deskewed_${System.currentTimeMillis()}.jpg")
            outFile.outputStream().use { corrected.compress(Bitmap.CompressFormat.JPEG, 95, it) }
            corrected.recycle()
            rawFile?.delete()  // clean up the raw capture

            val result = Intent().apply {
                putExtra(EXTRA_IMAGE_PATH, outFile.absolutePath)
                putExtra(EXTRA_SPREAD_MODE, isSpreadMode)
            }
            setResult(Activity.RESULT_OK, result)
            finish()

        } catch (e: Exception) {
            Toast.makeText(this, "Deskew failed: ${e.message}", Toast.LENGTH_SHORT).show()
            binding.confirmBtn.isEnabled = true
            binding.retakeBtn.isEnabled  = true
        }
    }

    // ── Phase transitions ────────────────────────────────────────

    private fun showCropPhase() {
        binding.cameraContainer.visibility = View.GONE
        binding.cropContainer.visibility   = View.VISIBLE
    }

    private fun showCameraPhase() {
        binding.cropContainer.visibility   = View.GONE
        binding.cameraContainer.visibility = View.VISIBLE
    }
}
