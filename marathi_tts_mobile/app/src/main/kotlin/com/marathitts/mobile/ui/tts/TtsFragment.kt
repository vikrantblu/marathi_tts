package com.marathitts.mobile.ui.tts

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import com.google.android.material.slider.LabelFormatter
import com.google.android.material.slider.Slider
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentTtsBinding
import com.marathitts.mobile.service.AudioPlayerService
import com.marathitts.mobile.service.TtsEngineManager

class TtsFragment : Fragment() {

    private var _binding: FragmentTtsBinding? = null
    private val binding get() = _binding!!

    private val viewModel: TtsViewModel by viewModels()
    private val audioPlayer = AudioPlayerService()

    companion object {
        val EMOTIONS = listOf(
            "auto (detect)", "neutral", "happy", "sad", "angry",
            "fearful", "surprised", "disgusted", "calm", "excited"
        )
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentTtsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Accept text passed from other fragments (STT / Correction / PDF / Web)
        arguments?.getString("tts_text")?.let { binding.textInput.setText(it) }

        // ── Engine spinner ───────────────────────────────────────────
        val engineAdapter = ArrayAdapter(
            requireContext(), android.R.layout.simple_spinner_item,
            TtsEngineManager.ENGINE_NAMES
        )
        engineAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.engineSpinner.adapter = engineAdapter
        binding.engineSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                binding.engineInfo.text = TtsEngineManager.ENGINE_DESCRIPTIONS[pos]
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        binding.engineSpinner.setSelection(0) // Auto

        // ── Language spinner ─────────────────────────────────────────
        val langAdapter = ArrayAdapter(
            requireContext(), android.R.layout.simple_spinner_item,
            TtsEngineManager.LANGUAGE_NAMES
        )
        langAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.languageSpinner.adapter = langAdapter

        // Emotion spinner
        val adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, EMOTIONS)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.emotionSpinner.adapter = adapter

        // Character count watcher
        binding.textInput.addTextChangedListener(object : android.text.TextWatcher {
            override fun afterTextChanged(s: android.text.Editable?) {
                binding.charCount.text = "${s?.length ?: 0} chars"
            }
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
        })

        // Slider labels — values are integers 1-20, divided by 10 to get 0.1-2.0
        val labelFmt = LabelFormatter { value -> "%.1f".format(value / 10f) }
        binding.speedSlider.setLabelFormatter(labelFmt)
        binding.pitchSlider.setLabelFormatter(labelFmt)
        binding.volumeSlider.setLabelFormatter(labelFmt)

        binding.generateBtn.setOnClickListener {
            val text = binding.textInput.text.toString().trim()
            if (text.isEmpty()) {
                Toast.makeText(context, "Please enter Marathi text", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            val selectedEmotion = EMOTIONS[binding.emotionSpinner.selectedItemPosition]
            val emotion: String? = when {
                binding.autoDetectCheck.isChecked || selectedEmotion == "auto (detect)" -> null
                else -> selectedEmotion
            }
            val autoDetect = binding.autoDetectCheck.isChecked || selectedEmotion == "auto (detect)"

            viewModel.generateAudio(
                text = text,
                engineIndex = binding.engineSpinner.selectedItemPosition,
                langCode = TtsEngineManager.LANGUAGE_CODES[binding.languageSpinner.selectedItemPosition],
                speed = binding.speedSlider.value / 10f,
                pitch = binding.pitchSlider.value / 10f,
                volume = binding.volumeSlider.value / 10f,
                emotion = emotion,
                isVerse = binding.verseCheck.isChecked,
                autoDetect = autoDetect
            )
        }

        binding.playBtn.setOnClickListener {
            val path = viewModel.state.value?.audioPath ?: return@setOnClickListener
            audioPlayer.play(path) {
                requireActivity().runOnUiThread { binding.statusText.text = "Playback complete" }
            }
            binding.statusText.text = "Playing…"
        }

        binding.stopBtn.setOnClickListener {
            audioPlayer.stop()
            binding.statusText.text = "Stopped"
        }

        binding.saveAudioBtn.setOnClickListener {
            val path = viewModel.state.value?.audioPath ?: return@setOnClickListener
            Toast.makeText(context, "Audio saved: $path", Toast.LENGTH_LONG).show()
        }

        binding.feedbackBtn.setOnClickListener { showFeedbackDialog() }

        binding.clearBtn.setOnClickListener { binding.textInput.text?.clear() }

        // Observe state
        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.generateBtn.isEnabled = !state.isLoading
            binding.statusText.text = state.status

            // Engine label
            binding.engineLabel.text = state.engine.takeIf { it.isNotEmpty() }
                ?.let { "Engine: $it" } ?: ""

            val hasAudio = state.audioPath != null && !state.isLoading
            binding.audioControlGroup.visibility = if (hasAudio) View.VISIBLE else View.GONE
            binding.playBtn.isEnabled = hasAudio
            binding.stopBtn.isEnabled = hasAudio
            binding.saveAudioBtn.isEnabled = hasAudio
            binding.feedbackBtn.isEnabled = hasAudio
        }
    }

    private fun showFeedbackDialog() {
        val ratingsItems = arrayOf("⭐ Poor", "⭐⭐ Fair", "⭐⭐⭐ Good", "⭐⭐⭐⭐ Very Good", "⭐⭐⭐⭐⭐ Excellent")
        var selectedRating = 2
        AlertDialog.Builder(requireContext())
            .setTitle("Rate this TTS output")
            .setSingleChoiceItems(ratingsItems, selectedRating) { _, which -> selectedRating = which }
            .setPositiveButton("Submit") { _, _ ->
                val stars = selectedRating + 1
                Toast.makeText(context, "Thanks for rating: $stars ⭐", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        audioPlayer.stop()
        _binding = null
    }
}
