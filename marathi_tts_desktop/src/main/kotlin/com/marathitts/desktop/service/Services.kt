package com.marathitts.desktop.service

import javafx.concurrent.Task

/** Generate TTS audio and return the path to the output mp3. */
class TtsService(private val projectRoot: String? = null) {

    /** Resolve the stotra audio library directory. */
    private fun findStotraDir(): String? {
        // 1. Explicit env var
        System.getenv("STOTRA_AUDIO_DIR")?.takeIf { java.io.File(it).isDirectory }?.let { return it }
        // 2. Alongside the running app (dev: marathi_tts_desktop/stotras)
        val candidates = listOfNotNull(
            projectRoot?.let { java.nio.file.Path.of(it, "marathi_tts_desktop", "stotras") },
            // In case projectRoot is already marathi_tts_desktop
            projectRoot?.let { java.nio.file.Path.of(it, "stotras") },
            // Relative to working directory (gradle run)
            java.nio.file.Path.of("stotras"),
            java.nio.file.Path.of("marathi_tts_desktop", "stotras"),
            // Relative to JAR location
            TtsService::class.java.protectionDomain?.codeSource?.location?.toURI()?.let {
                java.nio.file.Path.of(it).parent?.resolve("stotras")
            }
        )
        return candidates.firstOrNull { java.nio.file.Files.isDirectory(it) }?.toAbsolutePath()?.toString()
    }

    fun generateAudio(
        text: String,
        speed: Double = 1.0,
        pitch: Double = 1.0,
        volume: Double = 1.0,
        emotion: String? = null,
        isVerse: Boolean = false,
        outputPath: String? = null
    ): Task<Map<String, Any?>> = object : Task<Map<String, Any?>>() {
        override fun call(): Map<String, Any?> {
            val args = mutableListOf("--text", text, "--speed", speed.toString(),
                "--pitch", pitch.toString(), "--volume", volume.toString())
            if (emotion != null) args += listOf("--emotion", emotion)
            if (isVerse) args += "--verse"
            val stotraDir = findStotraDir()
            if (stotraDir != null) args += listOf("--stotra-dir", stotraDir)
            if (outputPath != null) args += listOf("--output", outputPath)
            return PythonBridge.run("tts_bridge.py", args, projectRoot)
        }
    }
}

/** Analyse emotion in a Marathi text. */
class EmotionService(private val projectRoot: String? = null) {
    fun analyze(text: String): Task<Map<String, Any?>> = object : Task<Map<String, Any?>>() {
        override fun call() = PythonBridge.run("emotion_bridge.py", listOf("--text", text), projectRoot)
    }
}

/** Extract text from an image using OCR. */
class OcrService(private val projectRoot: String? = null) {
    fun extractFromImage(imagePath: String): Task<Map<String, Any?>> = object : Task<Map<String, Any?>>() {
        override fun call() = PythonBridge.run("ocr_bridge.py", listOf("--image", imagePath), projectRoot)
    }
}

/** Correct Marathi text using the AI model or grammar engine. */
class CorrectionService(private val projectRoot: String? = null) {
    fun correct(text: String): Task<Map<String, Any?>> = object : Task<Map<String, Any?>>() {
        override fun call() = PythonBridge.run("correction_bridge.py", listOf("correct", "--text", text), projectRoot)
    }
}

/** Format/clean Marathi text (remove OCR noise, fix punctuation). */
class FormatService(private val projectRoot: String? = null) {
    fun format(text: String): Task<Map<String, Any?>> = object : Task<Map<String, Any?>>() {
        override fun call() = PythonBridge.run("correction_bridge.py", listOf("format", "--text", text), projectRoot)
    }
}

/** Submit an incorrect→correct word pair for model retraining. */
class SuggestCorrectionService(private val projectRoot: String? = null) {
    fun suggest(incorrect: String, correct: String, category: String = "general"): Task<Map<String, Any?>> =
        object : Task<Map<String, Any?>>() {
            override fun call() = PythonBridge.run(
                "correction_bridge.py",
                listOf("suggest", "--incorrect", incorrect, "--correct", correct, "--category", category),
                projectRoot
            )
        }
}

/** Extract text from a PDF file. */
class PdfService(private val projectRoot: String? = null) {
    fun extractFromPdf(pdfPath: String): Task<Map<String, Any?>> = object : Task<Map<String, Any?>>() {
        override fun call() = PythonBridge.run("pdf_bridge.py", listOf("--pdf", pdfPath), projectRoot)
    }
}

/** Fetch and clean text from a web URL. */
class WebFetchService(private val projectRoot: String? = null) {
    fun fetchUrl(url: String, includeImages: Boolean = false): Task<Map<String, Any?>> =
        object : Task<Map<String, Any?>>() {
            override fun call(): Map<String, Any?> {
                val args = mutableListOf("--url", url)
                if (!includeImages) args += "--no-images"
                return PythonBridge.run("web_bridge.py", args, projectRoot)
            }
        }
}

/** Speech-to-Text via Whisper. */
class SttService(private val projectRoot: String? = null) {
    fun transcribe(audioPath: String, language: String = "mr"): Task<Map<String, Any?>> =
        object : Task<Map<String, Any?>>() {
            override fun call() = PythonBridge.run(
                "stt_bridge.py",
                listOf("transcribe", "--audio", audioPath, "--language", language),
                projectRoot
            )
        }

    fun recordAndTranscribe(durationSeconds: Int = 5, language: String = "mr"): Task<Map<String, Any?>> =
        object : Task<Map<String, Any?>>() {
            override fun call() = PythonBridge.run(
                "stt_bridge.py",
                listOf("record", "--duration", durationSeconds.toString(), "--language", language),
                projectRoot
            )
        }
}

/** Convert between scripts: Modi ↔ Devanagari, IAST ↔ Devanagari. */
class ScriptConverterService(private val projectRoot: String? = null) {
    fun convert(text: String, mode: String = "modi_to_devanagari"): Task<Map<String, Any?>> =
        object : Task<Map<String, Any?>>() {
            override fun call() = PythonBridge.run(
                "script_converter_bridge.py",
                listOf("--text", text, "--mode", mode),
                projectRoot
            )
        }
}
