package com.marathitts.mobile.ui.emotion

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentEmotionBinding

class EmotionFragment : Fragment() {

    private var _binding: FragmentEmotionBinding? = null
    private val binding get() = _binding!!
    private val viewModel: EmotionViewModel by viewModels()

    private val emotionColors = mapOf(
        "happy" to "#FFD700", "sad" to "#4169E1", "angry" to "#DC143C",
        "fearful" to "#9400D3", "surprised" to "#FF8C00", "disgusted" to "#228B22",
        "calm" to "#00CED1", "excited" to "#FF69B4", "neutral" to "#808080"
    )

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, s: Bundle?): View {
        _binding = FragmentEmotionBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.analyzeBtn.setOnClickListener {
            val text = binding.textInput.text.toString().trim()
            if (text.isNotEmpty()) viewModel.analyzeEmotion(text)
        }

        binding.clearBtn.setOnClickListener {
            binding.textInput.text?.clear()
            binding.resultCard.visibility = View.GONE
            binding.sendToTtsBtn.isEnabled = false
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.textInput.text.toString()
            if (text.isNotBlank()) {
                val emotion = viewModel.state.value?.emotion
                val bundle = Bundle().apply {
                    putString("tts_text", text)
                    if (emotion != null) putString("tts_emotion", emotion)
                }
                findNavController().navigate(R.id.inputFragment, bundle)
            }
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.analyzeBtn.isEnabled = !state.isLoading
            binding.statusText.text = state.status

            if (state.emotion != null) {
                binding.resultCard.visibility = View.VISIBLE
                binding.sendToTtsBtn.isEnabled = true
                binding.emotionLabel.text = state.emotion.replaceFirstChar { it.uppercase() }
                val color = emotionColors[state.emotion.lowercase()] ?: "#808080"
                binding.emotionColorStrip.setBackgroundColor(android.graphics.Color.parseColor(color))

                // Show score list
                val scoreText = state.scores
                    ?.entries
                    ?.sortedByDescending { it.value }
                    ?.joinToString("\n") { (k, v) -> "${k.padEnd(12)} ${"█".repeat((v * 10).toInt())} ${"%.2f".format(v)}" }
                    ?: ""
                binding.scoresText.text = scoreText
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
