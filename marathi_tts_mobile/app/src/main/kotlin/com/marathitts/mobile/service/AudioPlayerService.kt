package com.marathitts.mobile.service

import android.media.MediaPlayer
import android.media.PlaybackParams
import android.os.Build
import java.io.File

/** Wrapper around Android MediaPlayer for audio playback. */
class AudioPlayerService {

    private var mediaPlayer: MediaPlayer? = null

    fun play(filePath: String, onComplete: (() -> Unit)? = null) {
        stop()
        mediaPlayer = MediaPlayer().apply {
            setDataSource(filePath)
            prepare()
            start()
            setOnCompletionListener { onComplete?.invoke() }
        }
    }

    fun stop() {
        mediaPlayer?.apply {
            if (isPlaying) stop()
            release()
        }
        mediaPlayer = null
    }

    fun pause() { mediaPlayer?.pause() }
    fun resume() { mediaPlayer?.start() }

    val isPlaying: Boolean get() = mediaPlayer?.isPlaying == true

    /** Audio duration in milliseconds, or 0 if not available. */
    val durationMs: Int
        get() = try { mediaPlayer?.duration ?: 0 } catch (_: Exception) { 0 }

    /** Current playback position in milliseconds. */
    val currentPositionMs: Int
        get() = try { mediaPlayer?.currentPosition ?: 0 } catch (_: Exception) { 0 }

    /** Set playback speed in real-time (requires API 23+). */
    fun setSpeed(speed: Float) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            mediaPlayer?.let { mp ->
                try {
                    val params = mp.playbackParams
                    params.speed = speed.coerceIn(0.25f, 4.0f)
                    mp.playbackParams = params
                } catch (_: Exception) {}
            }
        }
    }

    /** Set playback volume in real-time (0.0 to 1.0). */
    fun setVolume(volume: Float) {
        mediaPlayer?.let { mp ->
            try {
                val v = volume.coerceIn(0f, 1f)
                mp.setVolume(v, v)
            } catch (_: Exception) {}
        }
    }
}
