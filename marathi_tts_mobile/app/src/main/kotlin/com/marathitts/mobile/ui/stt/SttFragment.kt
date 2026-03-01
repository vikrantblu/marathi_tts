package com.marathitts.mobile.ui.stt

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
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
import java.util.Locale

class SttFragment : Fragment() {

    private var _binding: FragmentSttBinding? = null
    private val binding get() = _binding!!
    private val viewModel: SttViewModel by viewModels()

    private var selectedAudioPath: String? = null
    private var speechRecognizer: SpeechRecognizer? = null

    private val languages = listOf("Marathi (mr)", "Hindi (hi)", "English (en)", "Auto-detect")
    private val languageCodes = listOf("mr", "hi", "en", "")

    // File picker (audio files)
    private val pickAudio = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            val path = uri.path ?: uri.toString()
            selectedAudioPath = path
            binding.audioFileLabel.text = path.substringAfterLast("/")
            binding.transcribeBtn.isEnabled = true
        }
    }

    // Microphone permission
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

        // Language spinner
        val adapter = ArrayAdapter(requireContext(),
            android.R.layout.simple_spinner_item, languages)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.languageSpinner.adapter = adapter

        binding.browseAudioBtn.setOnClickListener {
            pickAudio.launch("audio/*")
        }

        binding.transcribeBtn.setOnClickListener {
            val path = selectedAudioPath ?: return@setOnClickListener
            val lang = languageCodes[binding.languageSpinner.selectedItemPosition]
            viewModel.transcribeFile(path, lang.ifEmpty { "mr" })
        }

        binding.recordBtn.setOnClickListener {
            if (ContextCompat.checkSelfPermission(requireContext(),
                    Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                startNativeRecognizer()
            } else {
                requestAudioPermission.launch(Manifest.permission.RECORD_AUDIO)
            }
        }

        binding.clearBtn.setOnClickListener {
            viewModel.clear()
            selectedAudioPath = null
            binding.audioFileLabel.text = getString(R.string.no_file_selected)
            binding.transcribeBtn.isEnabled = false
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.transcriptText.text.toString()
            if (text.isNotBlank()) {
                // Navigate back to TTS tab with text
                val bundle = Bundle().apply { putString("tts_text", text) }
                findNavController().navigate(R.id.ttsFragment, bundle)
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
            }

            // Segments
            if (state.segments.isNotEmpty()) {
                binding.segmentsText.visibility = View.VISIBLE
                binding.segmentsLabel.visibility = View.VISIBLE
                binding.segmentsText.setText(state.segments.joinToString("\n"))
            } else {
                binding.segmentsText.visibility = View.GONE
                binding.segmentsLabel.visibility = View.GONE
            }

            // Native STT fallback
            if (state.useNativeStt) {
                startNativeRecognizer()
            }
        }
    }

    private fun startNativeRecognizer() {
        speechRecognizer?.destroy()
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(requireContext())
        val recognizerIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "mr-IN")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        }

        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(p: Bundle?) {
                binding.statusText.text = "Listening…"
                binding.recordBtn.text = "Stop"
            }
            override fun onPartialResults(partial: Bundle?) {
                val results = partial?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!results.isNullOrEmpty()) {
                    binding.transcriptText.setText(results[0])
                }
            }
            override fun onResults(results: Bundle?) {
                val texts = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!texts.isNullOrEmpty()) {
                    binding.transcriptText.setText(texts[0])
                    binding.sendToTtsBtn.isEnabled = true
                }
                binding.statusText.text = "Done ✓"
                binding.recordBtn.text = getString(R.string.btn_record)
            }
            override fun onError(error: Int) {
                binding.statusText.text = "Recognition error $error"
                binding.recordBtn.text = getString(R.string.btn_record)
            }
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rms: Float) {}
            override fun onBufferReceived(b: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onEvent(t: Int, p: Bundle?) {}
        })
        speechRecognizer?.startListening(recognizerIntent)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        speechRecognizer?.destroy()
        _binding = null
    }
}
