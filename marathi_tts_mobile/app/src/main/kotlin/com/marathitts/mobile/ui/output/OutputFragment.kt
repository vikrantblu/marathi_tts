package com.marathitts.mobile.ui.output

import android.os.Bundle
import android.text.Spannable
import android.text.SpannableStringBuilder
import android.text.style.BackgroundColorSpan
import android.util.Log
import android.util.TypedValue
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentOutputBinding
import com.marathitts.mobile.ui.PlaybackViewModel
import com.marathitts.mobile.util.OutputActions

/**
 * Output screen — shows the full input text with sentence-level highlighting
 * during playback. Controls are pinned at the bottom.
 *
 * Uses activity-scoped OutputViewModel so generation state survives tab switches.
 * PlaybackViewModel handles the actual audio playback.
 */
class OutputFragment : Fragment() {

    private var _binding: FragmentOutputBinding? = null
    private val binding get() = _binding!!

    private val viewModel: OutputViewModel by activityViewModels()
    private val playbackVM: PlaybackViewModel by activityViewModels()

    companion object {
        private const val TAG = "OutputFragment"
    }

    private var highlightColor: Int = 0

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentOutputBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Resolve sentence highlight color from theme
        val tv = TypedValue()
        requireContext().theme.resolveAttribute(
            com.google.android.material.R.attr.colorPrimaryContainer, tv, true
        )
        highlightColor = tv.data

        setupControls()
        observeState()
        observePlayback()
    }

    // ── State observation ──────────────────────────────────────────────

    private fun observeState() {
        viewModel.state.observe(viewLifecycleOwner) { state ->
            // Progress card
            binding.progressCard.visibility =
                if (state.isLoading) View.VISIBLE else View.GONE
            binding.txtStatus.text = state.status

            // Empty state — only when nothing has been generated
            val showEmpty = state.inputText.isEmpty() && !state.isLoading && state.error == null
            binding.emptyState.visibility = if (showEmpty) View.VISIBLE else View.GONE

            // Full text with sentence highlighting
            if (state.inputText.isNotEmpty()) {
                binding.textCard.visibility = View.VISIBLE
                binding.txtFullText.text = buildHighlightedText(
                    state.sentences, state.activePlayingIndex
                )
                if (state.activePlayingIndex >= 0) {
                    scrollToSentence(state.sentences, state.activePlayingIndex)
                }
            } else {
                binding.textCard.visibility = View.GONE
            }

            // Controls & actions — visible when audio is ready (even during streaming)
            val hasAudio = state.audioPath != null || state.streamChunks.isNotEmpty()
            binding.controlsRow.visibility = if (hasAudio) View.VISIBLE else View.GONE
            binding.actionsRow.visibility = if (hasAudio && !state.isLoading) View.VISIBLE else View.GONE

            // Error
            if (state.error != null && !state.isLoading) {
                binding.txtError.visibility = View.VISIBLE
                binding.txtError.text = state.error
            } else {
                binding.txtError.visibility = View.GONE
            }

            // Auto-play when generation completes (one-time)
            if (state.autoPlayPending && hasAudio) {
                Log.i(TAG, "Auto-play triggered: chunks=${state.streamChunks.size} path=${state.audioPath}")
                viewModel.consumeAutoPlay()
                startPlayback(state)
            }
        }
    }

    private fun observePlayback() {
        playbackVM.playback.observe(viewLifecycleOwner) { pbState ->
            // Update play/pause icon
            binding.btnPlay.setIconResource(
                if (pbState.isPlaying) android.R.drawable.ic_media_pause
                else android.R.drawable.ic_media_play
            )

            // Clear highlight when playback fully stops
            if (!pbState.isPlaying && !pbState.isPaused) {
                viewModel.setActivePlayingIndex(-1)
            }
        }
    }

    // ── Sentence highlighting ──────────────────────────────────────────

    private fun buildHighlightedText(
        sentences: List<String>, activeIndex: Int
    ): SpannableStringBuilder {
        val builder = SpannableStringBuilder()
        for ((i, sentence) in sentences.withIndex()) {
            val start = builder.length
            builder.append(sentence)
            if (i == activeIndex) {
                builder.setSpan(
                    BackgroundColorSpan(highlightColor),
                    start, builder.length,
                    Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
                )
            }
            if (i < sentences.size - 1) builder.append(" ")
        }
        return builder
    }

    private fun scrollToSentence(sentences: List<String>, index: Int) {
        binding.txtFullText.post {
            val layout = binding.txtFullText.layout ?: return@post
            var charOffset = 0
            for (i in 0 until index) {
                charOffset += sentences[i].length + 1 // +1 for space
            }
            charOffset = charOffset.coerceIn(0, (binding.txtFullText.text.length - 1).coerceAtLeast(0))
            val line = layout.getLineForOffset(charOffset)
            val y = layout.getLineTop(line)
            binding.textScroll.smoothScrollTo(0, (y - 80).coerceAtLeast(0))
        }
    }

    // ── Controls ───────────────────────────────────────────────────────

    private fun setupControls() {
        binding.btnPlay.setOnClickListener {
            if (playbackVM.audioPlayer.isPlaying) {
                playbackVM.pause()
                return@setOnClickListener
            }
            val pbState = playbackVM.playback.value
            if (pbState?.isPaused == true) {
                playbackVM.resume()
                return@setOnClickListener
            }
            // Start/restart playback
            val state = viewModel.state.value ?: return@setOnClickListener
            startPlayback(state)
        }

        binding.btnStop.setOnClickListener {
            playbackVM.stop()
            viewModel.setActivePlayingIndex(-1)
            binding.txtPlaybackStatus.text = getString(R.string.output_stopped)
        }

        binding.btnCancel.setOnClickListener {
            viewModel.cancelGeneration()
        }

        binding.btnCopy.setOnClickListener {
            val text = viewModel.state.value?.inputText.orEmpty()
            if (text.isNotBlank()) OutputActions.copyText(requireContext(), text)
        }

        binding.btnShare.setOnClickListener {
            val state = viewModel.state.value ?: return@setOnClickListener
            val path = state.audioPath
            if (path != null) {
                OutputActions.shareAudio(requireContext(), path)
            } else {
                OutputActions.shareText(requireContext(), state.inputText)
            }
        }

        binding.btnSave.setOnClickListener {
            val path = viewModel.state.value?.audioPath
            if (path != null) {
                OutputActions.saveAudioToDownloads(requireContext(), path)
                Toast.makeText(requireContext(), "Saved to Downloads", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ── Playback ───────────────────────────────────────────────────────

    private fun startPlayback(state: OutputState) {
        // Progressive mode — play chunks as they arrive during streaming
        if (state.isLoading && state.streamChunks.isNotEmpty()) {
            startProgressivePlayback(state)
            return
        }

        val files = if (state.streamChunks.size > 1) {
            state.streamChunks
        } else {
            val path = state.audioPath ?: return
            listOf(path)
        }

        Log.i(TAG, "startPlayback: ${files.size} file(s)")
        binding.txtPlaybackStatus.text = getString(R.string.output_playing)

        // Highlight first sentence for single-file playback
        if (files.size == 1) viewModel.setActivePlayingIndex(0)

        playbackVM.startPlayback(
            files = files,
            inputText = state.inputText,
            onChunkStart = { idx ->
                activity?.runOnUiThread {
                    val sentenceIdx = state.chunkSentenceMap.getOrNull(idx) ?: idx
                    viewModel.setActivePlayingIndex(sentenceIdx)
                    binding.txtPlaybackStatus.text =
                        if (files.size > 1) getString(R.string.output_streaming, idx + 1, files.size)
                        else getString(R.string.output_playing)
                }
            },
            onAllComplete = {
                activity?.runOnUiThread {
                    viewModel.setActivePlayingIndex(-1)
                    binding.txtPlaybackStatus.text = getString(R.string.output_playback_done)
                }
            },
            onError = { err ->
                Log.e(TAG, "Playback error: $err")
                activity?.runOnUiThread {
                    viewModel.setActivePlayingIndex(-1)
                    binding.txtPlaybackStatus.text = "Error: $err"
                }
            }
        )
    }

    private fun startProgressivePlayback(state: OutputState) {
        Log.i(TAG, "startProgressivePlayback: streaming mode")
        binding.txtPlaybackStatus.text = getString(R.string.output_playing)

        playbackVM.startProgressivePlayback(
            getPathAtIndex = { index ->
                viewModel.state.value?.streamChunks?.getOrNull(index)
            },
            isComplete = {
                viewModel.state.value?.isLoading == false
            },
            inputText = state.inputText,
            onChunkStart = { idx ->
                activity?.runOnUiThread {
                    val sentenceIdx = viewModel.state.value?.chunkSentenceMap?.getOrNull(idx) ?: idx
                    viewModel.setActivePlayingIndex(sentenceIdx)
                    val total = viewModel.state.value?.sentences?.size ?: 0
                    binding.txtPlaybackStatus.text =
                        getString(R.string.output_streaming, idx + 1, total)
                }
            },
            onAllComplete = {
                activity?.runOnUiThread {
                    viewModel.setActivePlayingIndex(-1)
                    binding.txtPlaybackStatus.text = getString(R.string.output_playback_done)
                }
            },
            onError = { err ->
                Log.e(TAG, "Progressive playback error: $err")
                activity?.runOnUiThread {
                    viewModel.setActivePlayingIndex(-1)
                    binding.txtPlaybackStatus.text = "Error: $err"
                }
            }
        )
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
