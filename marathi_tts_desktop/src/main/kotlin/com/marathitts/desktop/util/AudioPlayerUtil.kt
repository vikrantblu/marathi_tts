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

    /** Audio duration in milliseconds, or -1.0 if unknown. */
    val durationMs: Double
        get() = mediaPlayer?.totalDuration?.toMillis() ?: -1.0

    /** Current playback position in milliseconds. */
    val currentTimeMs: Double
        get() = mediaPlayer?.currentTime?.toMillis() ?: 0.0

    /** Register a callback for when media is ready (duration available). */
    fun setOnReady(action: () -> Unit) {
        mediaPlayer?.setOnReady(action)
    }

    /** Register a callback for when playback finishes. */
    fun setOnEndOfMedia(action: () -> Unit) {
        mediaPlayer?.setOnEndOfMedia(action)
    }

    /**
     * Play a queue of audio files sequentially.
     * Each file plays to completion, then the next starts automatically.
     * [onAllFinished] is called after the last file finishes.
     */
    fun playQueue(filePaths: List<String>, onAllFinished: (() -> Unit)? = null) {
        if (filePaths.isEmpty()) { onAllFinished?.invoke(); return }
        stop()
        playQueueInternal(filePaths, 0, onAllFinished)
    }

    private fun playQueueInternal(paths: List<String>, index: Int, onAllFinished: (() -> Unit)?) {
        if (index >= paths.size) {
            onAllFinished?.invoke()
            return
        }
        val file = java.io.File(paths[index])
        if (!file.exists() || file.length() == 0L) {
            System.err.println("Skipping missing/empty chunk: ${paths[index]}")
            playQueueInternal(paths, index + 1, onAllFinished)
            return
        }
        val uri = file.toURI().toString()
        val media = Media(uri)
        mediaPlayer = MediaPlayer(media).apply {
            this.rate = this@AudioPlayerUtil.rate
            this.volume = this@AudioPlayerUtil.volume
            setOnEndOfMedia {
                dispose()
                playQueueInternal(paths, index + 1, onAllFinished)
            }
            setOnError {
                System.err.println("Playback error on chunk $index: ${this.error?.message}")
                dispose()
                playQueueInternal(paths, index + 1, onAllFinished)
            }
            play()
        }
    }

    val isPlaying: Boolean
        get() = mediaPlayer?.status == MediaPlayer.Status.PLAYING
}
