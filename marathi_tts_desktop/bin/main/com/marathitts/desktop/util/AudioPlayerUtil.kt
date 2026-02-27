package com.marathitts.desktop.util

import javafx.scene.media.Media
import javafx.scene.media.MediaPlayer
import java.io.File

/**
 * Audio player wrapper for JavaFX MediaPlayer with live parameter control.
 *
 * [volume] and [rate] (speed) can be changed while audio is playing
 * and take effect immediately. Pitch cannot be changed independently of
 * speed in JavaFX MediaPlayer — a pitch change requires audio re-generation.
 */
class AudioPlayerUtil {

    private var mediaPlayer: MediaPlayer? = null

    /** Current playback rate (speed). Updated live while playing. */
    var rate: Double = 1.0
        set(value) {
            field = value.coerceIn(0.125, 8.0)
            mediaPlayer?.rate = field
        }

    /**
     * Current playback volume (0.0–1.0).
     * Values above 1.0 from the UI are clamped; full volume boost is baked
     * into the generated audio by pydub.
     */
    var volume: Double = 1.0
        set(value) {
            field = value.coerceIn(0.0, 1.0)
            mediaPlayer?.volume = field
        }

    fun play(filePath: String) {
        stop()
        val uri = File(filePath).toURI().toString()
        val media = Media(uri)
        mediaPlayer = MediaPlayer(media).apply {
            this.rate = this@AudioPlayerUtil.rate
            this.volume = this@AudioPlayerUtil.volume
            play()
        }
    }

    fun stop() {
        mediaPlayer?.stop()
        mediaPlayer?.dispose()
        mediaPlayer = null
    }

    fun pause() {
        mediaPlayer?.pause()
    }

    fun resume() {
        mediaPlayer?.play()
    }

    val isPlaying: Boolean
        get() = mediaPlayer?.status == MediaPlayer.Status.PLAYING
}
