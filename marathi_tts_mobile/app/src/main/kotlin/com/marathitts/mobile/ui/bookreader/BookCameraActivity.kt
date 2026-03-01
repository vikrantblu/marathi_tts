package com.marathitts.mobile.ui.bookreader

import android.app.Activity
import android.content.Intent
import android.content.pm.ActivityInfo
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.graphics.RectF
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.view.WindowInsetsController
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.camera2.interop.Camera2Interop
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
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
 * Phase 1 — Live preview with a [BookCameraOverlayView] alignment guide.
 *            Camera2 interop sets CONTINUOUS_PICTURE autofocus and
 *            MAXIMIZE_QUALITY capture so the text is crisp across the full page.
 *
 * Phase 2 — [PerspectiveCropView] lets the user drag 4 corner handles to
 *            correct perspective distortion (common when shooting at an angle).
 *            The cropped, de-warped bitmap is saved to cache and the path is
 *            returned via [Activity.RESULT_OK].
 *
 * Caller keys:
 *   Input  → EXTRA_SPREAD_MODE (Boolean, default true)
 *   Output → EXTRA_IMAGE_PATH  (String, absolute path of corrected JPEG)
 *            EXTRA_SPREAD_MODE (Boolean, current mode after possible toggle)
 */
class BookCameraActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SPREAD_MODE = "spread_mode"
        const val EXTRA_IMAGE_PATH  = "image_path"
        private const val TAG = "BookCameraActivity"
    }

    private lateinit var binding: ActivityBookCameraBinding
    private lateinit var cameraExecutor: ExecutorService
    private var imageCapture: ImageCapture? = null
    private var isSpreadMode = true
    private var rawFile: File? = null

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

        cameraExecutor = Executors.newSingleThreadExecutor()

        startCamera()

        // ── Phase 1 controls ─────────────────────────────────────

        binding.backBtn.setOnClickListener { finish() }

        binding.modeToggleBtn.setOnClickListener {
            isSpreadMode = !isSpreadMode
            applyOrientation()
            binding.overlayView.isSpreadMode = isSpreadMode
            binding.modeLabel.text = if (isSpreadMode) "Two-Page Spread" else "Single Page"
        }

        binding.shutterButton.setOnClickListener { takePhoto() }

    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
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
                        .setViewPort(viewport)
                        .build()
                    cameraProvider.bindToLifecycle(
                        this, CameraSelector.DEFAULT_BACK_CAMERA, useCaseGroup
                    )
                    Log.d(TAG, "Bound with ViewPort (aspect=${viewport.aspectRatio})")
                } else {
                    Log.w(TAG, "ViewPort not ready — binding without crop alignment")
                    cameraProvider.bindToLifecycle(
                        this, CameraSelector.DEFAULT_BACK_CAMERA, preview, capture
                    )
                }
            } catch (e: Exception) {
                Toast.makeText(this, "Camera init failed: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    // ── Phase 1 — Capture ────────────────────────────────────────

    private fun takePhoto() {
        val capture = imageCapture ?: return
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
                    showDetectingIndicator(false)
                    binding.shutterButton.isEnabled = true
                    Toast.makeText(this@BookCameraActivity, "Could not load photo", Toast.LENGTH_SHORT).show()
                }
                return@launch
            }
            Log.d(TAG, "Loaded: ${fullBmp.width}x${fullBmp.height}")

            // ── Step 2: Pre-crop to the overlay guide frame ──────────────
            // The overlay guide frame IS the mask — whatever is outside it
            // (desk, hands, background) is already excluded by the camera guide.
            // We skip PageEdgeDetector entirely because luminance-based edge
            // detection fails when the book page and desk surface have similar
            // brightness (both beige/cream tones).  The user positioned the book
            // inside the guide; trust that crop and let them confirm/adjust.
            val frameFrac: RectF = withContext(Dispatchers.Main) {
                binding.overlayView.getFrameFractions()
            }
            val bmp = cropToFractions(fullBmp, frameFrac)
            if (bmp !== fullBmp) fullBmp.recycle()
            Log.d(TAG, "Pre-cropped to frame: ${bmp.width}x${bmp.height} (frac=$frameFrac)")

            withContext(Dispatchers.Main) {
                showDetectingIndicator(false)
                binding.shutterButton.isEnabled = true
                // Show crop UI with the frame-pre-cropped image.
                // Handles default to full extents of bmp — user can fine-tune
                // and tap Confirm to send to OCR.
                binding.cropView.setBitmap(bmp)
                showCropPhase()
            }
        }
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
