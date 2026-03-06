package com.marathitts.mobile.ui.output

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentOutputBinding
import com.marathitts.mobile.service.AudioPlayerService
import com.marathitts.mobile.util.OutputActions

class OutputFragment : Fragment() {

    private var _binding: FragmentOutputBinding? = null
    private val binding get() = _binding!!

    private val viewModel: OutputViewModel by viewModels()
    private val audioPlayer = AudioPlayerService()
    private var inputText: String = ""

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentOutputBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        inputText = arguments?.getString("input_text").orEmpty()
        val language = arguments?.getString("language") ?: "mr"
        val isVerse = arguments?.getBoolean("is_verse", false) ?: false

        setupPlaybackControls()
        setupOutputActions()
        observeState()

        // Auto-trigger generation when text is provided
        if (inputText.isNotBlank()) {
            viewModel.generate(inputText, language, isVerse)
        }
    }

    private fun observeState() {
        viewModel.state.observe(viewLifecycleOwner) { state ->
            // Progress card
            binding.progressCard.visibility =
                if (state.isLoading) View.VISIBLE else View.GONE
            binding.txtStatus.text = state.status

            // Empty state — only if no generation ever started
            binding.emptyState.visibility =
                if (inputText.isBlank() && !state.isLoading && state.audioPath == null && state.error == null)
                    View.VISIBLE else View.GONE

            // Player card — show when audio is ready
            val hasAudio = (state.audioPath != null || state.streamChunks.isNotEmpty()) && !state.isLoading
            binding.playerCard.visibility = if (hasAudio) View.VISIBLE else View.GONE

            if (hasAudio) {
                binding.txtEngine.text = state.engine.takeIf { it.isNotEmpty() }
                    ?.let { "Engine: $it" } ?: ""
            }

            // Input text preview
            if (inputText.isNotBlank() && !state.isLoading) {
                binding.textPreviewCard.visibility = View.VISIBLE
                binding.txtInputPreview.text = inputText
            }

            // Emotion card
            if (state.emotionLabel != null && !state.isLoading) {
                binding.emotionCard.visibility = View.VISIBLE
                binding.txtEmotion.text = state.emotionLabel.replaceFirstChar { it.uppercase() }
            } else {
                binding.emotionCard.visibility = View.GONE
            }

            // Error — show as toast
            if (state.error != null && !state.isLoading) {
                Toast.makeText(requireContext(), state.error, Toast.LENGTH_LONG).show()
            }

            // Auto-play when generation completes
            if (hasAudio && !audioPlayer.isPlaying) {
                autoPlay(state)
            }
        }
    }

    private fun autoPlay(state: OutputState) {
        if (state.streamChunks.size > 1) {
            binding.txtPlaybackStatus.text = getString(R.string.output_playing)
            audioPlayer.playQueueAsync(
                paths = state.streamChunks,
                onChunkStart = { idx ->
                    activity?.runOnUiThread {
                        binding.txtPlaybackStatus.text =
                            getString(R.string.output_streaming, idx + 1, state.streamChunks.size)
                    }
                },
                onAllComplete = {
                    activity?.runOnUiThread {
                        binding.txtPlaybackStatus.text = getString(R.string.output_playback_done)
                    }
                },
                onError = { err ->
                    activity?.runOnUiThread {
                        binding.txtPlaybackStatus.text = "Playback error: $err"
                    }
                }
            )
        } else {
            val path = state.audioPath ?: return
            binding.txtPlaybackStatus.text = getString(R.string.output_playing)
            audioPlayer.playAsync(
                filePath = path,
                onComplete = {
                    activity?.runOnUiThread {
                        binding.txtPlaybackStatus.text = getString(R.string.output_playback_done)
                    }
                },
                onError = { err ->
                    activity?.runOnUiThread {
                        binding.txtPlaybackStatus.text = "Playback error: $err"
                    }
                }
            )
        }
    }

    private fun setupPlaybackControls() {
        binding.btnPlay.setOnClickListener {
            val state = viewModel.state.value ?: return@setOnClickListener
            if (audioPlayer.isPlaying) {
                audioPlayer.stop()
                return@setOnClickListener
            }
            autoPlay(state)
        }

        binding.btnStop.setOnClickListener {
            audioPlayer.stop()
            binding.txtPlaybackStatus.text = getString(R.string.output_stopped)
        }

        binding.btnCancel.setOnClickListener {
            viewModel.cancelGeneration()
        }

        binding.sliderSpeed.addOnChangeListener { _, value, _ ->
            audioPlayer.setSpeed(value)
        }
    }

    private fun setupOutputActions() {
        binding.btnCopy.setOnClickListener {
            OutputActions.copyText(requireContext(), inputText)
        }

        binding.btnShare.setOnClickListener {
            val path = viewModel.state.value?.audioPath
            if (path != null) {
                OutputActions.shareAudio(requireContext(), path)
            } else {
                OutputActions.shareText(requireContext(), inputText)
            }
        }

        binding.btnSave.setOnClickListener {
            val path = viewModel.state.value?.audioPath
            if (path != null) {
                OutputActions.saveAudioToDownloads(requireContext(), path)
                Toast.makeText(requireContext(), "Saved to Downloads", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(requireContext(), "No audio to save", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        audioPlayer.stop()
        _binding = null
    }
}
