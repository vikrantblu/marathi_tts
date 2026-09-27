package com.marathitts.mobile.ui

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import com.marathitts.mobile.service.AudioPlayerService

/**
 * Activity-scoped ViewModel that survives tab switches.
 * Owns the single AudioPlayerService instance so playback continues
 * when the user navigates between Input / Output / Me tabs.
 */
class PlaybackViewModel(app: Application) : AndroidViewModel(app) {

    companion object {
        private const val TAG = "PlaybackViewModel"
    }

    /** The shared audio player — one per activity lifecycle. */
    val audioPlayer = AudioPlayerService()

    data class PlaybackState(
        val isPlaying: Boolean = false,
        val isPaused: Boolean = false,
        val currentChunkIndex: Int = -1,
        val totalChunks: Int = 0,
        val inputText: String = "",
        val audioFiles: List<String> = emptyList()
    )

    private val _playback = MutableLiveData(PlaybackState())
    val playback: LiveData<PlaybackState> get() = _playback

    /**
     * Start playback of one or more audio files.
     * Called from OutputFragment when generation completes.
     */
    fun startPlayback(
        files: List<String>,
        inputText: String,
        onChunkStart: ((Int) -> Unit)? = null,
        onAllComplete: (() -> Unit)? = null,
        onError: ((String) -> Unit)? = null
    ) {
        if (files.isEmpty()) return
        Log.i(TAG, "startPlayback: ${files.size} file(s), text='${inputText.take(40)}'")

        _playback.value = PlaybackState(
            isPlaying = true,
            currentChunkIndex = 0,
            totalChunks = files.size,
            inputText = inputText,
            audioFiles = files
        )

        if (files.size > 1) {
            audioPlayer.playQueueAsync(
                paths = files,
                onChunkStart = { idx ->
                    _playback.postValue(_playback.value?.copy(currentChunkIndex = idx))
                    onChunkStart?.invoke(idx)
                },
                onAllComplete = {
                    _playback.postValue(PlaybackState(inputText = inputText, audioFiles = files))
                    onAllComplete?.invoke()
                },
                onError = { err ->
                    Log.e(TAG, "Playback error: $err")
                    _playback.postValue(PlaybackState(inputText = inputText, audioFiles = files))
                    onError?.invoke(err)
                }
            )
        } else {
            audioPlayer.playAsync(
                filePath = files[0],
                onReady = {
                    _playback.postValue(_playback.value?.copy(isPlaying = true, currentChunkIndex = 0))
                },
                onComplete = {
                    _playback.postValue(PlaybackState(inputText = inputText, audioFiles = files))
                    onAllComplete?.invoke()
                },
                onError = { err ->
                    Log.e(TAG, "Playback error: $err")
                    _playback.postValue(PlaybackState(inputText = inputText, audioFiles = files))
                    onError?.invoke(err)
                }
            )
        }
    }

    /**
     * Start progressive playback for streaming — plays chunks as they arrive.
     * Uses a provider function instead of a fixed path list.
     */
    fun startProgressivePlayback(
        getPathAtIndex: (Int) -> String?,
        isComplete: () -> Boolean,
        inputText: String,
        onChunkStart: ((Int) -> Unit)? = null,
        onAllComplete: (() -> Unit)? = null,
        onError: ((String) -> Unit)? = null
    ) {
        Log.i(TAG, "startProgressivePlayback")

        _playback.value = PlaybackState(
            isPlaying = true,
            currentChunkIndex = 0,
            totalChunks = 0,
            inputText = inputText,
            audioFiles = emptyList()
        )

        audioPlayer.playProgressiveQueue(
            getPathAtIndex = getPathAtIndex,
            isComplete = isComplete,
            onChunkStart = { idx ->
                _playback.postValue(_playback.value?.copy(currentChunkIndex = idx))
                onChunkStart?.invoke(idx)
            },
            onAllComplete = {
                _playback.postValue(PlaybackState(inputText = inputText))
                onAllComplete?.invoke()
            },
            onError = { err ->
                Log.e(TAG, "Progressive playback error: $err")
                _playback.postValue(PlaybackState(inputText = inputText))
                onError?.invoke(err)
            }
        )
    }

    fun pause() {
        audioPlayer.pause()
        _playback.value = _playback.value?.copy(isPlaying = false, isPaused = true)
    }

    fun resume() {
        audioPlayer.resume()
        _playback.value = _playback.value?.copy(isPlaying = true, isPaused = false)
    }

    fun stop() {
        audioPlayer.stop()
        _playback.value = _playback.value?.copy(isPlaying = false, isPaused = false, currentChunkIndex = -1)
    }

    fun setSpeed(speed: Float) {
        audioPlayer.setSpeed(speed)
    }

    /** Whether audio is currently playing or paused (i.e. not fully stopped). */
    val hasActivePlayback: Boolean
        get() {
            val s = _playback.value ?: return false
            return s.isPlaying || s.isPaused
        }

    override fun onCleared() {
        super.onCleared()
        audioPlayer.stop()
    }
}
