package com.marathitts.mobile.service

import android.media.MediaPlayer
import android.media.PlaybackParams
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import java.io.File

/** Wrapper around Android MediaPlayer for audio playback. */
class AudioPlayerService {

    companion object {
        private const val TAG = "AudioPlayerService"
    }

    private var mediaPlayer: MediaPlayer? = null
    private var retryHandler: Handler? = null

    /**
     * Synchronous play — use only when already on a background thread.
     * Prefer [playAsync] from the UI thread to avoid ANR on large files.
     */
    fun play(filePath: String, onComplete: (() -> Unit)? = null) {
        stop()
        mediaPlayer = MediaPlayer().apply {
            setDataSource(filePath)
            prepare()          // blocks — OK only on background thread
            start()
            setOnCompletionListener { onComplete?.invoke() }
        }
    }

    /**
     * Async play — safe to call from the UI / main thread.
     * Uses [MediaPlayer.prepareAsync] so it never blocks.
     *
     * @param onReady    called (on MediaPlayer's internal thread) when playback starts
     * @param onComplete called when playback finishes
     * @param onError    called on prepare / playback error
     */
    fun playAsync(
        filePath: String,
        onReady: (() -> Unit)? = null,
        onComplete: (() -> Unit)? = null,
        onError: ((String) -> Unit)? = null
    ) {
        stop()
        Log.i(TAG, "playAsync: $filePath")
        mediaPlayer = MediaPlayer().apply {
            try {
                setDataSource(filePath)
                setOnPreparedListener { mp ->
                    Log.i(TAG, "prepareAsync ready, starting playback")
                    mp.start()
                    onReady?.invoke()
                }
                setOnCompletionListener {
                    Log.i(TAG, "playback complete")
                    onComplete?.invoke()
                }
                setOnErrorListener { _, what, extra ->
                    Log.e(TAG, "MediaPlayer error what=$what extra=$extra")
                    onError?.invoke("MediaPlayer error what=$what extra=$extra")
                    true
                }
                prepareAsync()   // non-blocking
            } catch (e: Exception) {
                Log.e(TAG, "playAsync setup failed: ${e.message}")
                onError?.invoke(e.message ?: "Unknown error")
            }
        }
    }

    fun stop() {
        retryHandler?.removeCallbacksAndMessages(null)
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

    /**
     * Play a list of audio files sequentially (streaming / chunked TTS).
     * The first chunk starts as soon as [paths[0]] is available; subsequent chunks
     * are chained via [onComplete] callbacks so there is no gap between segments.
     *
     * @param paths          Ordered list of audio file paths.
     * @param onChunkStart   Called with the index of each chunk as playback begins.
     * @param onAllComplete  Called after the last chunk finishes.
     * @param onError        Called on any MediaPlayer error; playback is aborted.
     */
    fun playQueueAsync(
        paths: List<String>,
        onChunkStart: ((index: Int) -> Unit)? = null,
        onAllComplete: (() -> Unit)? = null,
        onError: ((String) -> Unit)? = null
    ) {
        if (paths.isEmpty()) { onAllComplete?.invoke(); return }
        fun playIndex(index: Int) {
            if (index >= paths.size) {
                Log.i(TAG, "playQueueAsync: all ${paths.size} chunks played")
                onAllComplete?.invoke()
                return
            }
            val path = paths[index]
            Log.i(TAG, "playQueueAsync chunk $index/${paths.size - 1}: $path")
            stop()                        // release any previous player
            mediaPlayer = MediaPlayer().apply {
                try {
                    setDataSource(path)
                    setOnPreparedListener { mp ->
                        Log.i(TAG, "playQueueAsync chunk $index prepared, starting")
                        mp.start()
                        onChunkStart?.invoke(index)
                    }
                    setOnCompletionListener {
                        Log.i(TAG, "playQueueAsync chunk $index completed")
                        playIndex(index + 1)
                    }
                    setOnErrorListener { _, what, extra ->
                        val msg = "MediaPlayer error chunk=$index what=$what extra=$extra"
                        Log.e(TAG, msg)
                        onError?.invoke(msg)
                        true
                    }
                    prepareAsync()
                } catch (e: Exception) {
                    Log.e(TAG, "playQueueAsync setup failed at chunk $index: ${e.message}")
                    onError?.invoke(e.message ?: "Unknown error")
                }
            }
        }
        playIndex(0)
    }

    /**
     * Play a growing queue of audio files — starts immediately with whatever is available
     * and waits for more chunks when generation is still in progress.
     *
     * @param getPathAtIndex  Returns the file path for chunk [index], or null if not yet ready.
     * @param isComplete      Returns true when no more chunks will be produced.
     * @param onChunkStart    Called with each chunk index as playback begins.
     * @param onAllComplete   Called after the last chunk finishes.
     * @param onError         Called on any MediaPlayer error (playback continues to next chunk).
     */
    fun playProgressiveQueue(
        getPathAtIndex: (Int) -> String?,
        isComplete: () -> Boolean,
        onChunkStart: ((index: Int) -> Unit)? = null,
        onAllComplete: (() -> Unit)? = null,
        onError: ((String) -> Unit)? = null
    ) {
        retryHandler?.removeCallbacksAndMessages(null)
        retryHandler = Handler(Looper.getMainLooper())

        fun playIndex(index: Int) {
            val path = getPathAtIndex(index)
            if (path != null && File(path).exists()) {
                stop()
                mediaPlayer = MediaPlayer().apply {
                    try {
                        setDataSource(path)
                        setOnPreparedListener { mp ->
                            Log.i(TAG, "progressive chunk $index prepared, starting")
                            mp.start()
                            onChunkStart?.invoke(index)
                        }
                        setOnCompletionListener {
                            Log.i(TAG, "progressive chunk $index completed")
                            playIndex(index + 1)
                        }
                        setOnErrorListener { _, what, extra ->
                            Log.e(TAG, "progressive error chunk=$index what=$what extra=$extra")
                            onError?.invoke("chunk $index error what=$what")
                            playIndex(index + 1) // skip bad chunk
                            true
                        }
                        prepareAsync()
                    } catch (e: Exception) {
                        Log.e(TAG, "progressive setup failed chunk $index: ${e.message}")
                        playIndex(index + 1)
                    }
                }
            } else if (!isComplete()) {
                // Chunk not ready yet — wait and retry
                Log.d(TAG, "progressive chunk $index not ready, waiting 300ms")
                retryHandler?.postDelayed({ playIndex(index) }, 300)
            } else {
                // Generation complete, no more chunks
                Log.i(TAG, "progressive queue done after $index chunks")
                onAllComplete?.invoke()
            }
        }
        playIndex(0)
    }
}
