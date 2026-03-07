package com.marathitts.mobile.ui.stt

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentSttBinding
import com.marathitts.mobile.util.HistoryLogger
import java.io.File

class SttFragment : Fragment() {

    private var _binding: FragmentSttBinding? = null
    private val binding get() = _binding!!
    private val viewModel: SttViewModel by viewModels()

    private var selectedAudioPath: String? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var recognizerIntent: Intent? = null
    private var mediaPlayer: MediaPlayer? = null
    private var isRecording = false
    private var isPlaybackTranscribing = false
    private var savedNotifVolume = -1
    private val accumulatedTranscript = StringBuilder()
    private var segmentCount = 0
    private var lastLoggedSttHash = 0

    // Chunked loopback state
    private val pendingChunks = ArrayDeque<String>()
    private var totalChunkCount = 0
    private var currentChunkIdx = 0

    private val handler = Handler(Looper.getMainLooper())

    private val languages = listOf("Marathi (mr)", "Hindi (hi)", "English (en)", "Auto-detect")
    private val languageCodes = listOf("mr", "hi", "en", "")

    // File picker — copies URI to a real cache path so Python bridge can read it
    private val pickAudio = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            val cached = copyUriToCache(uri)
            if (cached != null) {
                selectedAudioPath = cached.absolutePath
                binding.audioFileLabel.text = cached.name
            } else {
                val path = uri.path ?: uri.toString()
                selectedAudioPath = path
                binding.audioFileLabel.text = path.substringAfterLast("/")
            }
            binding.transcribeBtn.isEnabled = true
        }
    }

    private val requestAudioPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) startNativeRecognizer()
        else Toast.makeText(context, "Microphone permission needed", Toast.LENGTH_SHORT).show()
    }

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _binding = FragmentSttBinding.inflate(i, c, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val adapter = ArrayAdapter(requireContext(),
            android.R.layout.simple_spinner_item, languages)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.languageSpinner.adapter = adapter

        binding.browseAudioBtn.setOnClickListener { pickAudio.launch("audio/*") }

        binding.transcribeBtn.setOnClickListener {
            if (isPlaybackTranscribing) { stopPlaybackTranscription(); return@setOnClickListener }
            val path = selectedAudioPath ?: return@setOnClickListener
            val lang = languageCodes[binding.languageSpinner.selectedItemPosition]
            viewModel.transcribeFile(path, lang.ifEmpty { "mr" })
        }

        binding.recordBtn.setOnClickListener {
            if (isPlaybackTranscribing) { stopPlaybackTranscription(); return@setOnClickListener }
            if (ContextCompat.checkSelfPermission(requireContext(),
                    Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                toggleRecording()
            } else {
                requestAudioPermission.launch(Manifest.permission.RECORD_AUDIO)
            }
        }

        binding.clearBtn.setOnClickListener {
            stopPlaybackTranscription()
            viewModel.clear()
            selectedAudioPath = null
            binding.audioFileLabel.text = getString(R.string.no_file_selected)
            binding.transcribeBtn.isEnabled = false
            binding.transcribeBtn.text = "Transcribe"
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.transcriptText.text.toString()
            if (text.isNotBlank()) {
                findNavController().previousBackStackEntry
                    ?.savedStateHandle?.set("extracted_text", text)
                findNavController().popBackStack()
            }
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.statusText.text = state.status
            binding.recordBtn.isEnabled = !state.isLoading
            binding.transcribeBtn.isEnabled = !state.isLoading && selectedAudioPath != null

            if (state.transcript.isNotEmpty()) {
                binding.transcriptText.setText(state.transcript)
                binding.sendToTtsBtn.isEnabled = true
                binding.engineLabel.text = state.engine.takeIf { it.isNotEmpty() }
                    ?.let { "Engine: $it" } ?: ""
                val h = state.transcript.hashCode()
                if (h != lastLoggedSttHash) {
                    lastLoggedSttHash = h
                    HistoryLogger.log(requireContext(), "STT",
                        selectedAudioPath ?: "mic", state.transcript)
                }
            }

            if (state.segments.isNotEmpty()) {
                binding.segmentsText.visibility = View.VISIBLE
                binding.segmentsLabel.visibility = View.VISIBLE
                binding.segmentsText.setText(state.segments.joinToString("\n"))
            } else {
                binding.segmentsText.visibility = View.GONE
                binding.segmentsLabel.visibility = View.GONE
            }

            if (state.useNativeStt) {
                viewModel.clearNativeSttFlag()
                when {
                    state.nativeChunks.size > 1 ->
                        startChunkedPlaybackTranscription(state.nativeChunks)
                    state.nativeAudioPath != null ->
                        startPlaybackTranscription(state.nativeAudioPath)
                    hasMicPermission() -> startNativeRecognizer()
                    else -> requestAudioPermission.launch(Manifest.permission.RECORD_AUDIO)
                }
            }
        }
    }

    private fun hasMicPermission(): Boolean =
        ContextCompat.checkSelfPermission(requireContext(),
            Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    // ══════════════════════════════════════════════════════════════════
    //  Chunked loopback entry point
    // ══════════════════════════════════════════════════════════════════

    fun startChunkedPlaybackTranscription(chunks: List<String>) {
        pendingChunks.clear()
        pendingChunks.addAll(chunks.drop(1))    // first chunk played immediately
        totalChunkCount = chunks.size
        currentChunkIdx = 0
        startPlaybackTranscription(chunks[0])
    }

    // ══════════════════════════════════════════════════════════════════
    //  Playback Loopback — play audio through speaker, mic listens
    // ══════════════════════════════════════════════════════════════════

    private fun startPlaybackTranscription(audioPath: String) {
        if (isPlaybackTranscribing) return
        val file = File(audioPath)
        if (!file.exists()) { binding.statusText.text = "Audio file not found"; return }

        isPlaybackTranscribing = true
        accumulatedTranscript.clear()
        segmentCount = 0
        binding.transcriptText.text?.clear()
        binding.transcribeBtn.text = "Cancel"
        binding.recordBtn.isEnabled = false
        binding.progressBar.visibility = View.VISIBLE
        val ci = if (totalChunkCount > 1) " (Chunk 1 / $totalChunkCount)" else ""
        binding.statusText.text = "🔊 Playing audio$ci…\nStay in a quiet place."

        val am = requireContext().getSystemService(
            android.content.Context.AUDIO_SERVICE) as AudioManager
        try {
            savedNotifVolume = am.getStreamVolume(AudioManager.STREAM_NOTIFICATION)
            am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, 0, 0)
        } catch (_: Exception) { savedNotifVolume = -1 }
        try {
            val maxVol = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            am.setStreamVolume(AudioManager.STREAM_MUSIC, (maxVol * 0.8).toInt(), 0)
        } catch (_: Exception) {}

        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                setDataSource(audioPath)
                setAudioAttributes(AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .setUsage(AudioAttributes.USAGE_MEDIA).build())
                prepare()
                setOnCompletionListener { onChunkComplete() }
                setOnErrorListener { _, _, _ ->
                    binding.statusText.text = "Error playing audio"
                    stopPlaybackTranscription(); true
                }
            }
        } catch (e: Exception) {
            binding.statusText.text = "Cannot play audio: ${e.message}"
            stopPlaybackTranscription(); return
        }

        setupContinuousRecognizer()
        speechRecognizer?.startListening(recognizerIntent)
        mediaPlayer?.start()
    }

    /** After a chunk completes, wait for last recognition then advance or finish. */
    private fun onChunkComplete() {
        handler.postDelayed({
            speechRecognizer?.stopListening()
            handler.postDelayed({
                if (pendingChunks.isNotEmpty() && isPlaybackTranscribing) {
                    currentChunkIdx++
                    val next = pendingChunks.removeFirst()
                    binding.statusText.text =
                        "🔊 Chunk ${currentChunkIdx + 1} / $totalChunkCount…\n" +
                        "($segmentCount segments captured so far)"
                    playChunk(next)
                } else {
                    finishPlaybackTranscription()
                }
            }, 500)
        }, 1500)
    }

    /** Play a subsequent chunk without re-running full setup. */
    private fun playChunk(audioPath: String) {
        if (!isPlaybackTranscribing) return
        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                setDataSource(audioPath)
                setAudioAttributes(AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .setUsage(AudioAttributes.USAGE_MEDIA).build())
                prepare()
                setOnCompletionListener { onChunkComplete() }
                setOnErrorListener { _, _, _ ->
                    handler.postDelayed({
                        if (pendingChunks.isNotEmpty() && isPlaybackTranscribing) {
                            currentChunkIdx++; playChunk(pendingChunks.removeFirst())
                        } else finishPlaybackTranscription()
                    }, 300); true
                }
            }
            speechRecognizer?.startListening(recognizerIntent)
            mediaPlayer?.start()
        } catch (e: Exception) {
            binding.statusText.text = "Cannot play chunk: ${e.message}"
            stopPlaybackTranscription()
        }
    }

    private fun setupContinuousRecognizer() {
        speechRecognizer?.destroy()
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(requireContext())
        val langCode = languageCodes[binding.languageSpinner.selectedItemPosition]
        val bcp47 = when (langCode) { "hi" -> "hi-IN"; "en" -> "en-IN"; else -> "mr-IN" }
        recognizerIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, bcp47)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra("android.speech.extra.SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS", 3000L)
            putExtra("android.speech.extra.SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS", 2000L)
            putExtra("android.speech.extra.SPEECH_INPUT_MINIMUM_LENGTH_MILLIS", 5000L)
        }
        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(p: Bundle?) {}
            override fun onPartialResults(partial: Bundle?) {
                val r = partial?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!r.isNullOrEmpty() && r[0].isNotBlank() && isPlaybackTranscribing) {
                    val display = buildString {
                        append(accumulatedTranscript)
                        if (accumulatedTranscript.isNotEmpty()) append(" ")
                        append(r[0])
                    }
                    binding.transcriptText.setText(display)
                    val chunkInfo = if (totalChunkCount > 1)
                        " • Chunk ${currentChunkIdx + 1}/$totalChunkCount" else ""
                    binding.statusText.text = "🔊 Transcribing$chunkInfo… ($segmentCount segments)"
                }
            }
            override fun onResults(results: Bundle?) {
                val texts = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!texts.isNullOrEmpty() && texts[0].isNotBlank()) {
                    segmentCount++
                    if (accumulatedTranscript.isNotEmpty()) accumulatedTranscript.append(" ")
                    accumulatedTranscript.append(texts[0])
                    binding.transcriptText.setText(accumulatedTranscript.toString())
                    binding.sendToTtsBtn.isEnabled = true
                }
                restartListeningIfPlaying()
            }
            override fun onError(error: Int) { restartListeningIfPlaying() }
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rms: Float) {}
            override fun onBufferReceived(b: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onEvent(t: Int, p: Bundle?) {}
        })
    }

    private fun restartListeningIfPlaying() {
        if (isPlaybackTranscribing && mediaPlayer?.isPlaying == true) {
            handler.postDelayed({
                if (isPlaybackTranscribing && mediaPlayer?.isPlaying == true) {
                    try {
                        speechRecognizer?.startListening(recognizerIntent)
                    } catch (_: Exception) {
                        setupContinuousRecognizer()
                        speechRecognizer?.startListening(recognizerIntent)
                    }
                }
            }, 250)
        }
    }

    private fun restoreNotificationVolume() {
        if (savedNotifVolume >= 0) {
            try {
                val am = requireContext().getSystemService(
                    android.content.Context.AUDIO_SERVICE) as AudioManager
                am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, savedNotifVolume, 0)
            } catch (_: Exception) {}
            savedNotifVolume = -1
        }
    }

    private fun finishPlaybackTranscription() {
        if (!isPlaybackTranscribing) return
        isPlaybackTranscribing = false
        handler.removeCallbacksAndMessages(null)
        mediaPlayer?.release(); mediaPlayer = null
        speechRecognizer?.stopListening()
        restoreNotificationVolume()
        pendingChunks.clear()
        binding.transcribeBtn.text = "Transcribe"
        binding.recordBtn.isEnabled = true
        binding.progressBar.visibility = View.GONE
        val text = accumulatedTranscript.toString().trim()
        if (text.isNotEmpty()) {
            binding.transcriptText.setText(text)
            val chunkInfo = if (totalChunkCount > 1) " ($totalChunkCount chunks)" else ""
            binding.statusText.text = "Transcription complete ✓$chunkInfo"
            binding.engineLabel.text = "Engine: playback-loopback$chunkInfo"
            binding.sendToTtsBtn.isEnabled = true
        } else {
            binding.statusText.text =
                "No speech detected.\nEnsure audio is clear and volume is adequate."
        }
    }

    private fun stopPlaybackTranscription() {
        if (!isPlaybackTranscribing) return
        isPlaybackTranscribing = false
        handler.removeCallbacksAndMessages(null)
        try { mediaPlayer?.stop() } catch (_: Exception) {}
        mediaPlayer?.release(); mediaPlayer = null
        speechRecognizer?.stopListening()
        restoreNotificationVolume()
        pendingChunks.clear()
        binding.transcribeBtn.text = "Transcribe"
        binding.recordBtn.isEnabled = true
        binding.progressBar.visibility = View.GONE
        val text = accumulatedTranscript.toString().trim()
        if (text.isNotEmpty()) {
            binding.transcriptText.setText(text)
            binding.statusText.text = "Cancelled (partial result kept)"
            binding.sendToTtsBtn.isEnabled = true
        } else {
            binding.statusText.text = "Transcription cancelled"
        }
    }

    // ══════════════════════════════════════════════════════════════════
    //  Live Mic Recording
    // ══════════════════════════════════════════════════════════════════

    private fun toggleRecording() {
        if (isRecording) stopRecording() else startNativeRecognizer()
    }

    private fun stopRecording() {
        speechRecognizer?.stopListening()
        isRecording = false
        binding.recordBtn.text = getString(R.string.btn_record)
        binding.statusText.text = "Stopped"
    }

    private fun startNativeRecognizer() {
        speechRecognizer?.destroy()
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(requireContext())
        val langCode = languageCodes[binding.languageSpinner.selectedItemPosition]
        val bcp47 = when (langCode) { "hi" -> "hi-IN"; "en" -> "en-IN"; else -> "mr-IN" }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, bcp47)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        }
        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(p: Bundle?) {
                isRecording = true
                binding.statusText.text = "Listening…"
                binding.recordBtn.text = "Stop"
            }
            override fun onPartialResults(partial: Bundle?) {
                val r = partial?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!r.isNullOrEmpty()) binding.transcriptText.setText(r[0])
            }
            override fun onResults(results: Bundle?) {
                isRecording = false
                val texts = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!texts.isNullOrEmpty()) {
                    binding.transcriptText.setText(texts[0])
                    binding.sendToTtsBtn.isEnabled = true
                }
                binding.statusText.text = "Done ✓"
                binding.recordBtn.text = getString(R.string.btn_record)
            }
            override fun onError(error: Int) {
                isRecording = false
                val msg = when (error) {
                    SpeechRecognizer.ERROR_NO_MATCH,
                    SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech detected"
                    SpeechRecognizer.ERROR_NETWORK,
                    SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network error"
                    SpeechRecognizer.ERROR_AUDIO -> "Audio error"
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Mic permission needed"
                    else -> "Recognition error ($error)"
                }
                binding.statusText.text = msg
                binding.recordBtn.text = getString(R.string.btn_record)
            }
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rms: Float) {}
            override fun onBufferReceived(b: ByteArray?) {}
            override fun onEndOfSpeech() { binding.statusText.text = "Processing…" }
            override fun onEvent(t: Int, p: Bundle?) {}
        })
        speechRecognizer?.startListening(intent)
    }

    // ══════════════════════════════════════════════════════════════════
    //  Helpers
    // ══════════════════════════════════════════════════════════════════

    /** Copy a content:// URI to app cache so Python bridge can open it as a real file. */
    private fun copyUriToCache(uri: Uri): File? {
        return try {
            val mimeType = requireContext().contentResolver.getType(uri) ?: ""
            val ext = when {
                mimeType.contains("mp3") || mimeType.endsWith("mpeg") -> "mp3"
                mimeType.contains("mp4") || mimeType.contains("m4a") -> "m4a"
                mimeType.contains("ogg") -> "ogg"
                mimeType.contains("flac") -> "flac"
                mimeType.contains("aac") -> "aac"
                else -> "wav"
            }
            val cache = File(requireContext().cacheDir, "stt_audio.$ext")
            requireContext().contentResolver.openInputStream(uri)?.use { input ->
                cache.outputStream().use { out -> input.copyTo(out) }
            }
            if (cache.exists() && cache.length() > 0) cache else null
        } catch (e: Exception) { null }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        isRecording = false
        if (isPlaybackTranscribing) {
            isPlaybackTranscribing = false
            restoreNotificationVolume()
        }
        handler.removeCallbacksAndMessages(null)
        mediaPlayer?.release(); mediaPlayer = null
        speechRecognizer?.destroy()
        _binding = null
    }
}
