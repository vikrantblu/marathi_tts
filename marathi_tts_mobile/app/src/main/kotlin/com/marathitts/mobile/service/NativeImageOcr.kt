package com.marathitts.mobile.service

import android.graphics.BitmapFactory
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.File
import java.util.logging.Logger
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Native on-device Devanagari OCR using ML Kit.
 *
 * No dependency on Python, pytesseract, PIL, or web app.
 * Works entirely offline once the ML Kit model is downloaded.
 */
object NativeImageOcr {

    private val log = Logger.getLogger(NativeImageOcr::class.java.name)

    private val recognizer by lazy {
        TextRecognition.getClient(DevanagariTextRecognizerOptions.Builder().build())
    }

    /**
     * Extract Devanagari text from an image file.
     *
     * @param imageFile JPEG/PNG file on device storage
     * @return Extracted text or empty string
     */
    suspend fun extract(imageFile: File): String {
        log.info("NativeImageOcr: opening ${imageFile.name} (${imageFile.length()} bytes)")

        val bitmap = BitmapFactory.decodeFile(imageFile.absolutePath)
            ?: throw IllegalArgumentException("Cannot decode image: ${imageFile.name}")

        val inputImage = InputImage.fromBitmap(bitmap, 0)

        return suspendCancellableCoroutine { cont ->
            recognizer.process(inputImage)
                .addOnSuccessListener { visionText ->
                    val text = visionText.text
                    log.info("NativeImageOcr: extracted ${text.length} chars")
                    bitmap.recycle()
                    cont.resume(text)
                }
                .addOnFailureListener { e ->
                    log.warning("NativeImageOcr: recognition failed: ${e.message}")
                    bitmap.recycle()
                    cont.resumeWithException(e)
                }
        }
    }
}
