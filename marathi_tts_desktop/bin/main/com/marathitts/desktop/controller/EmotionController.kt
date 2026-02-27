package com.marathitts.desktop.controller

import com.marathitts.desktop.service.EmotionService
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.chart.BarChart
import javafx.scene.chart.XYChart
import javafx.scene.control.*
import javafx.scene.paint.Color
import javafx.scene.shape.Rectangle
import javafx.scene.layout.HBox
import java.net.URL
import java.util.ResourceBundle
import java.util.concurrent.Executors

/**
 * Controller for the Emotion Analysis tab.
 *
 * Features:
 *  - Text input
 *  - Analyse button → calls PythonBridge emotion_bridge.py
 *  - Dominant emotion colour badge
 *  - Bar chart of emotion scores
 *  - Copy text/result to TTS tab pass-through
 */
class EmotionController : Initializable {

    @FXML lateinit var textArea: TextArea
    @FXML lateinit var analyzeBtn: Button
    @FXML lateinit var statusLabel: Label
    @FXML lateinit var progressBar: ProgressBar
    @FXML lateinit var resultLabel: Label
    @FXML lateinit var emotionBadge: Label
    @FXML lateinit var emotionColorRect: Rectangle
    @FXML lateinit var scoreChart: BarChart<String, Number>
    @FXML lateinit var resultPane: javafx.scene.layout.VBox

    var projectRoot: (() -> String?)? = null

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "emotion-worker").also { it.isDaemon = true }
    }

    // Colour mapping matching emotion_constants
    private val emotionColors = mapOf(
        "happy" to "#FFD700", "sad" to "#4169E1", "angry" to "#DC143C",
        "fearful" to "#9400D3", "surprised" to "#FF8C00", "disgusted" to "#228B22",
        "calm" to "#00CED1", "excited" to "#FF69B4", "neutral" to "#808080"
    )

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        resultPane.isVisible = false
        progressBar.isVisible = false
        scoreChart.isLegendVisible = false
    }

    @FXML
    fun onAnalyze(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val text = textArea.text.trim()
        if (text.isEmpty()) {
            setStatus("Please enter Marathi text.")
            return
        }

        setStatus("Analysing emotion…", busy = true)
        analyzeBtn.isDisable = true

        val task = EmotionService(projectRoot?.invoke()).analyze(text)

        task.setOnSucceeded {
            val result = task.value
            analyzeBtn.isDisable = false
            if (result["success"] == true) {
                val emotion = result["emotion"] as? String ?: "neutral"
                @Suppress("UNCHECKED_CAST")
                val scores = result["scores"] as? Map<String, Number>

                updateUI(emotion, scores)
                setStatus("Analysis complete ✓")
            } else {
                setStatus("Error: ${result["error"]}")
            }
        }
        task.setOnFailed {
            analyzeBtn.isDisable = false
            setStatus("Failed: ${task.exception?.message}")
        }

        executor.submit(task)
    }

    private fun updateUI(emotion: String, scores: Map<String, Number>?) = Platform.runLater {
        emotionBadge.text = emotion.replaceFirstChar { it.uppercase() }
        val color = emotionColors[emotion.lowercase()] ?: "#808080"
        emotionColorRect.fill = Color.web(color)
        emotionBadge.style = "-fx-background-color: ${color}22; -fx-text-fill: $color; " +
                "-fx-font-size: 18px; -fx-font-weight: bold; -fx-padding: 8 16;"

        scoreChart.data.clear()
        if (scores != null) {
            val series = XYChart.Series<String, Number>()
            scores.entries.sortedByDescending { it.value.toDouble() }.forEach { (k, v) ->
                series.data.add(XYChart.Data(k, v))
            }
            scoreChart.data.add(series)
        }
        resultPane.isVisible = true
    }

    @FXML
    fun onClear(@Suppress("UNUSED_PARAMETER") e: ActionEvent) {
        textArea.clear()
        resultPane.isVisible = false
    }

    private fun setStatus(msg: String, busy: Boolean = false) = Platform.runLater {
        statusLabel.text = msg
        progressBar.isVisible = busy
        progressBar.progress = if (busy) -1.0 else 0.0
    }
}
