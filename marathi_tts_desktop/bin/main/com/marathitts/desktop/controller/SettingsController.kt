package com.marathitts.desktop.controller

import com.marathitts.desktop.model.HistoryManager
import javafx.application.Platform
import javafx.event.ActionEvent
import javafx.fxml.FXML
import javafx.fxml.Initializable
import javafx.scene.control.*
import java.net.URL
import java.util.ResourceBundle
import java.util.prefs.Preferences

/** Controller for the Settings tab. */
class SettingsController : Initializable {

    @FXML lateinit var defaultEngineCombo: ComboBox<String>
    @FXML lateinit var defaultGenderCombo: ComboBox<String>
    @FXML lateinit var defaultSpeedSlider: Slider
    @FXML lateinit var defaultPitchSlider: Slider
    @FXML lateinit var defaultVolumeSlider: Slider
    @FXML lateinit var defaultSpeedLabel: Label
    @FXML lateinit var defaultPitchLabel: Label
    @FXML lateinit var defaultVolumeLabel: Label
    @FXML lateinit var statusLabel: Label

    // Shared prefs nodes — same keys used by TtsController and WebFetchController
    private val ttsPrefs = Preferences.userRoot().node("com/marathitts/desktop/controller/TtsController")
    private val webPrefs = Preferences.userRoot().node("com/marathitts/desktop/controller/WebFetchController")

    private val engines = listOf("Auto (best available)", "Google TTS", "System TTS")
    private val engineCodes = mapOf(
        "Auto (best available)" to "auto", "Google TTS" to "google", "System TTS" to "system"
    )
    private val genders = listOf("स्त्री (Female)", "पुरुष (Male)")
    private val genderCodes = mapOf("स्त्री (Female)" to "female", "पुरुष (Male)" to "male")

    override fun initialize(location: URL?, resources: ResourceBundle?) {
        defaultEngineCombo.items.addAll(engines)
        defaultGenderCombo.items.addAll(genders)

        // Restore current saved defaults
        val savedEngine = ttsPrefs.get("tts_engine", "auto")
        val savedGender = ttsPrefs.get("tts_gender", "female")
        engines.firstOrNull { engineCodes[it] == savedEngine }
               ?.let { defaultEngineCombo.selectionModel.select(it) }
               ?: defaultEngineCombo.selectionModel.selectFirst()
        genders.firstOrNull { genderCodes[it] == savedGender }
               ?.let { defaultGenderCombo.selectionModel.select(it) }
               ?: defaultGenderCombo.selectionModel.selectFirst()

        defaultSpeedSlider.value  = ttsPrefs.getDouble("tts_speed", 1.0)
        defaultPitchSlider.value  = ttsPrefs.getDouble("tts_pitch", 1.0)
        defaultVolumeSlider.value = ttsPrefs.getDouble("tts_volume", 1.0)

        updateLabels()

        // Live-save when user moves sliders / selects combo
        defaultEngineCombo.selectionModel.selectedItemProperty().addListener { _, _, v ->
            ttsPrefs.put("tts_engine", engineCodes[v] ?: "auto")
        }
        defaultGenderCombo.selectionModel.selectedItemProperty().addListener { _, _, v ->
            ttsPrefs.put("tts_gender", genderCodes[v] ?: "female")
        }
        defaultSpeedSlider.valueProperty().addListener { _, _, v ->
            ttsPrefs.putDouble("tts_speed", v.toDouble())
            defaultSpeedLabel.text = "%.1f×".format(v.toDouble())
        }
        defaultPitchSlider.valueProperty().addListener { _, _, v ->
            ttsPrefs.putDouble("tts_pitch", v.toDouble())
            defaultPitchLabel.text = "%.1f".format(v.toDouble())
        }
        defaultVolumeSlider.valueProperty().addListener { _, _, v ->
            ttsPrefs.putDouble("tts_volume", v.toDouble())
            defaultVolumeLabel.text = "%.0f%%".format(v.toDouble() * 100)
        }
    }

    private fun updateLabels() {
        defaultSpeedLabel.text  = "%.1f×".format(defaultSpeedSlider.value)
        defaultPitchLabel.text  = "%.1f".format(defaultPitchSlider.value)
        defaultVolumeLabel.text = "%.0f%%".format(defaultVolumeSlider.value * 100)
    }

    // ── Data Management ────────────────────────────────────────────────────

    @FXML
    fun onClearHistory(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        val alert = Alert(Alert.AlertType.CONFIRMATION,
            "Clear all generation history?", ButtonType.YES, ButtonType.CANCEL)
        alert.headerText = "Clear History"
        if (alert.showAndWait().orElse(ButtonType.CANCEL) == ButtonType.YES) {
            HistoryManager.clear()
            setStatus("History cleared ✓")
        }
    }

    @FXML
    fun onClearDraft(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        ttsPrefs.remove("tts_draft")
        setStatus("TTS draft cleared ✓")
    }

    @FXML
    fun onClearBookmarks(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        webPrefs.remove("web_bookmarks")
        setStatus("URL bookmarks cleared ✓")
    }

    @FXML
    fun onClearRecentChips(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        ttsPrefs.remove("tts_recent")
        setStatus("Recent TTS inputs cleared ✓")
    }

    @FXML
    fun onResetDefaults(@Suppress("UNUSED_PARAMETER") event: ActionEvent) {
        ttsPrefs.putDouble("tts_speed",  1.0)
        ttsPrefs.putDouble("tts_pitch",  1.0)
        ttsPrefs.putDouble("tts_volume", 1.0)
        ttsPrefs.put("tts_engine", "auto")
        ttsPrefs.put("tts_gender", "female")

        // Reset sliders in UI
        defaultSpeedSlider.value  = 1.0
        defaultPitchSlider.value  = 1.0
        defaultVolumeSlider.value = 1.0
        engines.firstOrNull { engineCodes[it] == "auto" }
               ?.let { defaultEngineCombo.selectionModel.select(it) }
        genders.firstOrNull { genderCodes[it] == "female" }
               ?.let { defaultGenderCombo.selectionModel.select(it) }

        setStatus("Defaults reset ✓  (re-open TTS tab to see effect)")
    }

    private fun setStatus(msg: String) = Platform.runLater { statusLabel.text = msg }
}
