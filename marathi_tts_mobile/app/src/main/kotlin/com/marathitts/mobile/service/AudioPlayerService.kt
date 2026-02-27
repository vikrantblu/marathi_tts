package com.marathitts.mobile.service

import android.media.MediaPlayer
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
}
