package com.marathitts.desktop.controller

import com.marathitts.desktop.service.TtsService
import com.marathitts.desktop.service.EmotionService
import com.marathitts.desktop.util.AudioPlayerUtil
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import javafx.scene.layout.HBox
import javafx.scene.layout.Region
import javafx.scene.paint.Color
import javafx.scene.shape.Rectangle
import java.net.URL
import java.util.ResourceBundle
import java.util.Timer
import java.util.TimerTask
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.Semaphore

/**
 * Controller for the TTS tab.
 *
 * Features:
 *  - Text input (Marathi Devanagari)
 *  - Voice settings: speed, pitch, volume sliders
 *  - Emotion selector + Auto-detect mode (runs EmotionService first)
 *  - Verse mode toggle
 *  - Word-by-word playback highlighting
 *  - Generate / Play / Stop / Save audio buttons
 *  - Feedback / rating dialog
 */
class TtsController : Initializable {

    @FXML lateinit var textArea: TextArea
    @FXML lateinit var speedSlider: Slider
    @FXML lateinit var pitchSlider: Slider
    @FXML lateinit var volumeSlider: Slider
    @FXML lateinit var speedLabel: Label
    @FXML lateinit var pitchLabel: Label
    @FXML lateinit var volumeLabel: Label
    @FXML lateinit var languageCombo: ComboBox<String>
    @FXML lateinit var engineCombo: ComboBox<String>
    @FXML lateinit var genderCombo: ComboBox<String>
    @FXML lateinit var emotionCombo: ComboBox<String>
    @FXML lateinit var verseModeCheck: CheckBox
    @FXML lateinit var generateBtn: Button
    @FXML lateinit var playBtn: Button
    @FXML lateinit var stopBtn: Button
    @FXML lateinit var saveAudioBtn: Button
    @FXML lateinit var feedbackBtn: Button
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var audioControlBar: HBox
    @FXML lateinit var characterCountLabel: Label
    @FXML lateinit var engineLabel: Label
    @FXML lateinit var emotionBadge: Rectangle
    @FXML lateinit var detectedEmotionLabel: Label
    @FXML lateinit var autoDetectCheck: CheckBox

    // Injected by parent controller
    var projectRoot: (() -> String?)? = null

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "tts-worker").also { it.isDaemon = true }
    }
    private var lastAudioPath: String? = null
    /** Paths of all streaming chunk audio files (empty for single-call). */
    private var streamChunkPaths: List<String> = emptyList()
    private val player = AudioPlayerUtil()
    private var wordHighlightTimer: Timer? = null
    /** Pool for concurrent chunk generation (streaming). */
    private val streamingPool = Executors.newFixedThreadPool(3) { r ->
        Thread(r, "tts-stream").also { it.isDaemon = true }
    }

    // Emotion → badge colour map (matches web/mobile)
    private val emotionColors = mapOf(
        "happy"     to "#F9A825",  // amber
        "sad"       to "#1565C0",  // blue
        "angry"     to "#B71C1C",  // red
        "fearful"   to "#6A1B9A",  // purple
        "surprised" to "#00838F",  // teal
        "disgusted" to "#558B2F",  // green
        "calm"      to "#0288D1",  // light-blue
        "excited"   to "#E65C00",  // saffron
        "neutral"   to "#757575",  // grey
        "love"      to "#E91E63"   // pink
    )

    companion object {
        /** Text longer than this (in chars) triggers streaming on Marathi prose. */
        private const val STREAMING_THRESHOLD = 250

        val EMOTIONS = listOf(
            "auto (detect)", "neutral", "happy", "sad", "angry",
            "fearful", "surprised", "disgusted", "calm", "excited"
        )
        val LANGUAGES = listOf("मराठी (Marathi)", "हिंदी (Hindi)", "संस्कृत (Sanskrit)", "English")
        val LANGUAGE_CODES = mapOf(
            "मराठी (Marathi)" to "mr", "हिंदी (Hindi)" to "hi",
            "संस्कृत (Sanskrit)" to "sa", "English" to "en"
        )
        val ENGINES = listOf("Auto (best available)", "Google TTS", "System TTS")
        val ENGINE_CODES = mapOf(
            "Auto (best available)" to "auto", "Google TTS" to "google", "System TTS" to "system"
        )
        val GENDERS = listOf("स्त्री (Female)", "पुरुष (Male)")
        val GENDER_CODES = mapOf("स्त्री (Female)" to "female", "पुरुष (Male)" to "male")
    }

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        languageCombo.items.addAll(LANGUAGES)
        languageCombo.selectionModel.selectFirst()
        engineCombo.items.addAll(ENGINES)
        engineCombo.selectionModel.selectFirst()
        genderCombo.items.addAll(GENDERS)
        genderCombo.selectionModel.selectFirst()
        emotionCombo.items.addAll(EMOTIONS)
        emotionCombo.selectionModel.selectFirst()

        // Bind slider labels + live playback control
        speedSlider.valueProperty().addListener { _, _, v ->
            val speed = v.toDouble()
            speedLabel.text = "%.1f×".format(speed)
            player.rate = speed          // live speed adjustment during playback
        }
        pitchSlider.valueProperty().addListener { _, _, v ->
            pitchLabel.text = "%.1f".format(v.toDouble())
            // Pitch changes require re-generation (no live control available)
        }
        volumeSlider.valueProperty().addListener { _, _, v ->
            val vol = v.toDouble()
            volumeLabel.text = "%.0f%%".format(vol * 100)
            player.volume = vol.coerceAtMost(1.0)  // live volume during playback
        }

        // Character counter
        textArea.textProperty().addListener { _, _, text ->
            characterCountLabel.text = "${text.length} chars"
        }

        audioControlBar.isVisible = false
        progressBar.isVisible = false
        stopBtn.isDisable = true
        playBtn.isDisable = true
        saveAudioBtn.isDisable = true
        feedbackBtn.isDisable = true
        detectedEmotionLabel.text = ""
    }

    /**
     * Called by MainController when another tab's "Send to TTS" button is clicked.
     * Populates the text area so the user can immediately generate audio.
     */
    fun receiveText(text: String) = Platform.runLater {
        textArea.text = text
        textArea.positionCaret(0)
    }

    @FXML
    fun onGenerate(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = textArea.text.trim()
        if (text.isEmpty()) { setStatus("Please enter Marathi text first."); return }

        setStatus("Generating audio…", busy = true)
        generateBtn.isDisable = true
        player.stop()

        val emotionSelection = emotionCombo.value ?: "auto (detect)"
        val isAuto = emotionSelection.startsWith("auto")

        // If auto-detect, run emotion analysis first then TTS
        if (isAuto || autoDetectCheck.isSelected) {
            val emotionTask = EmotionService(projectRoot?.invoke()).analyze(text)
            emotionTask.setOnSucceeded {
                val eResult = emotionTask.value
                val detectedEmotion = eResult["emotion"] as? String ?: "neutral"
                val scores = eResult["scores"]

                Platform.runLater {
                    updateEmotionBadge(detectedEmotion)
                    detectedEmotionLabel.text = "Detected: $detectedEmotion"
                }
                dispatchGeneration(text, detectedEmotion)
            }
            emotionTask.setOnFailed { dispatchGeneration(text, null) }
            executor.submit(emotionTask)
        } else {
            val emotion = if (emotionSelection == "auto (detect)") null else emotionSelection
            dispatchGeneration(text, emotion)
        }
    }

    /**
     * Route to streaming or single-call based on text length.
     * Long Marathi prose (>250 chars, non-verse) goes through streaming;
     * everything else uses a single PythonBridge call.
     */
    private fun dispatchGeneration(text: String, emotion: String?) {
        val langCode = LANGUAGE_CODES[languageCombo.value] ?: "mr"
        val isVerse = verseModeCheck.isSelected
        if (langCode == "mr" && !isVerse && text.length > STREAMING_THRESHOLD) {
            runStreamingGeneration(text, emotion)
        } else {
            runTtsGeneration(text, emotion)
        }
    }

    /** Split Marathi text into sentence-level chunks at ।, ॥, and Latin punctuation. */
    private fun splitSentences(text: String): List<String> {
        val raw = text.split(Regex("""(?<=[।॥?!])\s*|(?<=[.;])\s+"""))
            .map { it.trim() }
            .filter { it.isNotBlank() }
        if (raw.isEmpty()) return listOf(text)

        // Merge very short fragments (< 20 chars) with next to avoid tiny audio
        val merged = mutableListOf<String>()
        val buf = StringBuilder()
        for (s in raw) {
            buf.append(if (buf.isEmpty()) s else " $s")
            if (buf.length >= 20) {
                merged += buf.toString()
                buf.clear()
            }
        }
        if (buf.isNotEmpty()) {
            if (merged.isNotEmpty() && buf.length < 20) {
                merged[merged.lastIndex] = merged.last() + " $buf"
            } else {
                merged += buf.toString()
            }
        }
        return merged.ifEmpty { listOf(text) }
    }

    /**
     * Streaming generation: split text into sentence chunks, generate
     * audio for each chunk (up to 3 in parallel), then queue playback.
     * Mirrors mobile TtsViewModel.generateAudioStreaming().
     */
    private fun runStreamingGeneration(text: String, emotion: String?) {
        val sentences = splitSentences(text)
        if (sentences.size <= 1) {
            runTtsGeneration(text, emotion)
            return
        }

        setStatus("Streaming: preparing ${sentences.size} chunks…", busy = true)

        val langCode = LANGUAGE_CODES[languageCombo.value] ?: "mr"
        val engineCode = ENGINE_CODES[engineCombo.value] ?: "auto"
        val genderCode = GENDER_CODES[genderCombo.value] ?: "female"
        val speed = speedSlider.value
        val pitch = pitchSlider.value
        val volume = volumeSlider.value
        val root = projectRoot?.invoke()
        val concurrencyLimit = Semaphore(3)
        val completedCount = AtomicInteger(0)
        val total = sentences.size

        executor.submit {
            try {
                // Generate all chunks with limited concurrency
                val futures = sentences.map { chunk ->
                    streamingPool.submit<String?> {
                        concurrencyLimit.acquire()
                        try {
                            val result = TtsService(root).generateAudio(
                                text = chunk,
                                speed = speed, pitch = pitch, volume = volume,
                                emotion = emotion, isVerse = false,
                                language = langCode, engine = engineCode,
                                gender = genderCode
                            ).let { task ->
                                task.run()   // run synchronously in pool thread
                                task.value
                            }
                            if (result["success"] == true) {
                                val done = completedCount.incrementAndGet()
                                Platform.runLater {
                                    setStatus("Streaming: $done of $total ✓", busy = true)
                                }
                                result["audio_path"] as? String
                            } else {
                                System.err.println("Streaming chunk failed: ${result["error"]}")
                                null
                            }
                        } finally {
                            concurrencyLimit.release()
                        }
                    }
                }

                // Collect results in order
                val paths = futures.mapNotNull { it.get() }

                if (paths.isEmpty()) {
                    setStatus("Error: streaming failed — no chunks generated")
                    Platform.runLater { generateBtn.isDisable = false }
                    return@submit
                }

                streamChunkPaths = paths
                lastAudioPath = paths.first()

                Platform.runLater {
                    engineLabel.text = "Engine: stream (${paths.size} chunks)"
                    audioControlBar.isVisible = true
                    playBtn.isDisable = false
                    saveAudioBtn.isDisable = false
                    feedbackBtn.isDisable = false
                    generateBtn.isDisable = false
                }
                setStatus("All ${paths.size} chunks ready \u2713")
            } catch (e: Exception) {
                System.err.println("Streaming error: ${e.javaClass.simpleName}: ${e.message}")
                e.printStackTrace()
                setStatus("Streaming error: ${e.message ?: "unknown"}")
                Platform.runLater { generateBtn.isDisable = false }
            }
        }
    }

    private fun runTtsGeneration(text: String, emotion: String?) {
        val langCode = LANGUAGE_CODES[languageCombo.value] ?: "mr"
        val engineCode = ENGINE_CODES[engineCombo.value] ?: "auto"
        val genderCode = GENDER_CODES[genderCombo.value] ?: "female"
        streamChunkPaths = emptyList()   // reset streaming state
        val task = TtsService(projectRoot?.invoke()).generateAudio(
            text = text,
            speed = speedSlider.value,
            pitch = pitchSlider.value,
            volume = volumeSlider.value,
            emotion = emotion,
            isVerse = verseModeCheck.isSelected,
            language = langCode,
            engine = engineCode,
            gender = genderCode
        )
        task.setOnSucceeded {
            val result = task.value
            if (result["success"] == true) {
                lastAudioPath = result["audio_path"] as? String
                val engine = result["engine"] as? String ?: "tts"
                val stotraName = result["stotra_name"] as? String
                Platform.runLater {
                    if (stotraName != null) {
                        engineLabel.text = "Engine: $engine \u2014 $stotraName"
                    } else {
                        engineLabel.text = "Engine: $engine"
                    }
                    audioControlBar.isVisible = true
                    playBtn.isDisable = false
                    saveAudioBtn.isDisable = false
                    feedbackBtn.isDisable = false
                    generateBtn.isDisable = false
                }
                setStatus("Audio generated ✓")
            } else {
                val err = result["error"] as? String ?: "Unknown error"
                setStatus("Error: $err")
                Platform.runLater { generateBtn.isDisable = false }
            }
        }
        task.setOnFailed {
            setStatus("Failed: ${task.exception?.message}")
            Platform.runLater { generateBtn.isDisable = false }
        }
        executor.submit(task)
    }

    private fun updateEmotionBadge(emotion: String) {
        val hex = emotionColors[emotion.lowercase()] ?: "#757575"
        try {
            emotionBadge.fill = Color.web(hex)
        } catch (_: Exception) {}
    }

    @FXML
    fun onPlay(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        if (streamChunkPaths.size > 1) {
            // Streaming mode: play all chunks sequentially
            player.rate = speedSlider.value
            player.volume = volumeSlider.value.coerceAtMost(1.0)
            player.playQueue(streamChunkPaths) {
                Platform.runLater {
                    stopBtn.isDisable = true
                    setStatus("Finished")
                }
            }
            stopBtn.isDisable = false
            setStatus("Playing ${streamChunkPaths.size} chunks…")
            startWordHighlight()
        } else {
            lastAudioPath?.let {
                player.rate = speedSlider.value
                player.volume = volumeSlider.value.coerceAtMost(1.0)
                player.play(it)
                stopBtn.isDisable = false
                setStatus("Playing…")
                startWordHighlight()
            }
        }
    }

    @FXML
    fun onStop(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        player.stop()
        stopWordHighlight()
        stopBtn.isDisable = true
        setStatus("Stopped")
    }

    @FXML
    fun onSaveAudio(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        lastAudioPath ?: return
        val fc = javafx.stage.FileChooser().apply {
            title = "Save Audio"
            extensionFilters += javafx.stage.FileChooser.ExtensionFilter("MP3 Audio", "*.mp3")
            initialFileName = "marathi_tts_output.mp3"
        }
        val dest = fc.showSaveDialog(textArea.scene.window) ?: return

        if (streamChunkPaths.size > 1) {
            // Concatenate all chunk MP3 files into one
            dest.outputStream().use { out ->
                for (p in streamChunkPaths) {
                    java.io.File(p).inputStream().use { it.copyTo(out) }
                }
            }
        } else {
            java.nio.file.Files.copy(
                java.nio.file.Path.of(lastAudioPath!!),
                dest.toPath(),
                java.nio.file.StandardCopyOption.REPLACE_EXISTING
            )
        }
        setStatus("Saved to ${dest.name}")
    }

    @FXML
    fun onFeedback(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val ratingDialog = Dialog<ButtonType>().apply {
            title = "Rate this Audio"
            headerText = "How would you rate the generated audio?"
            val stars = ToggleGroup()
            val ratingBox = HBox(8.0).apply {
                val buttons = (1..5).map { i ->
                    RadioButton("${"★".repeat(i)}").also { rb ->
                        rb.toggleGroup = stars
                        rb.userData = i
                    }
                }
                children.addAll(buttons)
                buttons[2].isSelected = true // Default: 3 stars
            }
            val commentArea = TextArea().apply { promptText = "Comments (optional)…"; prefRowCount = 3 }
            val box = javafx.scene.layout.VBox(12.0, ratingBox, commentArea).also { it.prefWidth = 380.0 }
            dialogPane.content = box
            dialogPane.buttonTypes.addAll(ButtonType.OK, ButtonType.CANCEL)
        }

        val result = ratingDialog.showAndWait()
        if (result.orElse(ButtonType.CANCEL) == ButtonType.OK) {
            setStatus("Feedback recorded — thank you! ✓")
        }
    }

    @FXML
    fun onClearText(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        textArea.clear()
        detectedEmotionLabel.text = ""
    }

    /** Word-by-word highlighting synced to audio duration. */
    private fun startWordHighlight() {
        stopWordHighlight()
        val text = textArea.text
        val words = text.split("\\s+".toRegex()).filter { it.isNotEmpty() }
        if (words.isEmpty()) return

        var wordIndex = 0
        var charOffset = 0

        // Try to get audio duration for accurate per-word timing
        val audioDuration = player.durationMs
        val msPerWord = if (audioDuration > 0 && words.size > 1) {
            (audioDuration / words.size).toLong().coerceIn(100L, 2000L)
        } else {
            300L // fallback
        }

        wordHighlightTimer = Timer(true)
        wordHighlightTimer?.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                if (!player.isPlaying || wordIndex >= words.size) {
                    cancel()
                    Platform.runLater { textArea.deselect() }
                    return
                }
                // Sync word index to actual audio position when possible
                val currentMs = player.currentTimeMs
                val totalMs = player.durationMs
                if (totalMs > 0 && currentMs > 0) {
                    val expectedIdx = ((currentMs / totalMs) * words.size).toInt()
                    if (expectedIdx > wordIndex) {
                        // Jump ahead to sync
                        wordIndex = expectedIdx.coerceAtMost(words.size - 1)
                        charOffset = 0
                        for (i in 0 until wordIndex) {
                            val pos = text.indexOf(words[i], charOffset)
                            if (pos >= 0) charOffset = pos + words[i].length
                        }
                    }
                }
                val word = words[wordIndex]
                val start = text.indexOf(word, charOffset)
                if (start >= 0) {
                    val end = start + word.length
                    Platform.runLater { textArea.selectRange(start, end) }
                    charOffset = end
                }
                wordIndex++
            }
        }, 0L, msPerWord)

        // Also register end-of-media callback to clear highlighting
        player.setOnEndOfMedia {
            stopWordHighlight()
            Platform.runLater { stopBtn.isDisable = true; setStatus("Finished") }
        }
    }

    private fun stopWordHighlight() {
        wordHighlightTimer?.cancel()
        wordHighlightTimer = null
        Platform.runLater { textArea.deselect() }
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
