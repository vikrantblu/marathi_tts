package com.marathitts.mobile.ui.output

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.fragment.app.viewModels
import androidx.recyclerview.widget.LinearLayoutManager
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentOutputBinding
import com.marathitts.mobile.ui.PlaybackViewModel
import com.marathitts.mobile.util.OutputActions

class OutputFragment : Fragment() {

    private var _binding: FragmentOutputBinding? = null
    private val binding get() = _binding!!

    private val viewModel: OutputViewModel by viewModels()
    private val playbackVM: PlaybackViewModel by activityViewModels()

    companion object {
        private const val TAG = "OutputFragment"
    }

    private var inputText: String = ""
    private var language: String = "mr"
    private var isVerse: Boolean = false
    private var accent: String = "standard"
    private var gender: String = "female"

    private lateinit var prosodyAdapter: ProsodySegmentAdapter
    private var hasAutoPlayed = false

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentOutputBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        inputText = arguments?.getString("input_text").orEmpty()
        language = arguments?.getString("language") ?: "mr"
        isVerse = arguments?.getBoolean("is_verse", false) ?: false
        accent = arguments?.getString("accent") ?: "standard"
        gender = arguments?.getString("gender") ?: "female"

        // Apply accent/gender from Input screen before generation starts
        viewModel.setAccent(accent)
        viewModel.setGender(gender)

        setupProsodyPreview()
        setupPlaybackControls()
        setupOutputActions()
        setupEmotionIntensity()
        applySmartSpeed(isVerse)
        observeState()
        observePhoneticExplanation()
        observeCorrectionSaved()

        // Auto-trigger generation when text is provided
        if (inputText.isNotBlank()) {
            Log.i(TAG, "Auto-triggering generate: len=${inputText.length} lang=$language verse=$isVerse")
            hasAutoPlayed = false
            viewModel.generate(inputText, language, isVerse)
        } else {
            Log.w(TAG, "No input text — generation skipped")
        }
    }

    private fun setupProsodyPreview() {
        prosodyAdapter = ProsodySegmentAdapter(
            onSegmentClick = { segment ->
                // FEAT-52: tap to regenerate this segment
                val speed = binding.sliderSpeed.value
                viewModel.regenerateSegment(
                    segmentIndex = segment.index,
                    text = segment.text,
                    speed = speed,
                    language = language,
                    isVerse = segment.isVerse
                )
            },
            onSegmentLongClick = { segment ->
                // FEAT-55: long-press to explain phonetics
                viewModel.explainPhonetics(segment.text, language)
            }
        )
        binding.rvProsodySegments.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = prosodyAdapter
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
                val engineLabel = state.engine.takeIf { it.isNotEmpty() }
                    ?.let { "Engine: $it" } ?: ""
                val noteLabel = state.voiceNote?.let { "\n⚠ $it" } ?: ""
                binding.txtEngine.text = "$engineLabel$noteLabel"
            }

            // Input text preview
            if (inputText.isNotBlank() && !state.isLoading) {
                binding.textPreviewCard.visibility = View.VISIBLE
                binding.txtInputPreview.text = inputText
            }

            // Emotion card + FEAT-54 intensity slider
            if (state.emotionLabel != null && !state.isLoading) {
                binding.emotionCard.visibility = View.VISIBLE
                binding.txtEmotion.text = state.emotionLabel.replaceFirstChar { it.uppercase() }
                binding.sliderEmotionIntensity.value = state.emotionIntensity
                binding.txtIntensityValue.text =
                    getString(R.string.emotion_intensity_value, (state.emotionIntensity * 100).toInt())
            } else {
                binding.emotionCard.visibility = View.GONE
            }

            // FEAT-51: Prosody preview card
            if (state.prosodySegments.isNotEmpty()) {
                binding.prosodyPreviewCard.visibility = View.VISIBLE
                binding.txtSegmentCount.text =
                    getString(R.string.prosody_segment_count, state.prosodySegments.size)
                prosodyAdapter.submitList(state.prosodySegments)
                prosodyAdapter.regeneratingIndex = state.regeneratingIndex
                prosodyAdapter.activePlayingIndex = state.activePlayingIndex
            } else {
                binding.prosodyPreviewCard.visibility = View.GONE
            }

            // Error — show as toast
            if (state.error != null && !state.isLoading) {
                Toast.makeText(requireContext(), state.error, Toast.LENGTH_LONG).show()
            }

            // Auto-play when generation completes
            if (hasAudio && !hasAutoPlayed && !playbackVM.audioPlayer.isPlaying) {
                Log.i(TAG, "autoPlay triggered: chunks=${state.streamChunks.size} path=${state.audioPath}")
                hasAutoPlayed = true
                autoPlay(state)
            }
        }
    }

    private fun autoPlay(state: OutputState) {
        val files = if (state.streamChunks.size > 1) {
            state.streamChunks
        } else {
            val path = state.audioPath ?: return
            listOf(path)
        }

        binding.txtPlaybackStatus.text = getString(R.string.output_playing)
        // FEAT-75: highlight segment 0 for single file
        if (files.size == 1) viewModel.setActivePlayingIndex(0)

        playbackVM.startPlayback(
            files = files,
            inputText = inputText,
            onChunkStart = { idx ->
                activity?.runOnUiThread {
                    binding.txtPlaybackStatus.text =
                        if (files.size > 1) getString(R.string.output_streaming, idx + 1, files.size)
                        else getString(R.string.output_playing)
                    viewModel.setActivePlayingIndex(idx)
                }
            },
            onAllComplete = {
                activity?.runOnUiThread {
                    binding.txtPlaybackStatus.text = getString(R.string.output_playback_done)
                    viewModel.setActivePlayingIndex(-1)
                }
            },
            onError = { err ->
                activity?.runOnUiThread {
                    binding.txtPlaybackStatus.text = "Playback error: $err"
                    viewModel.setActivePlayingIndex(-1)
                }
            }
        )
    }

    private fun applySmartSpeed(isVerse: Boolean) {
        if (isVerse) {
            binding.sliderSpeed.value = 0.85f
            binding.txtSpeedHint.text = "Verse mode — slower pace recommended"
            binding.txtSpeedHint.visibility = View.VISIBLE
        }
    }

    private fun setupPlaybackControls() {
        binding.btnPlay.setOnClickListener {
            val state = viewModel.state.value ?: return@setOnClickListener
            if (playbackVM.audioPlayer.isPlaying) {
                playbackVM.pause()
                return@setOnClickListener
            }
            val pbState = playbackVM.playback.value
            if (pbState?.isPaused == true) {
                playbackVM.resume()
                return@setOnClickListener
            }
            autoPlay(state)
        }

        binding.btnStop.setOnClickListener {
            playbackVM.stop()
            binding.txtPlaybackStatus.text = getString(R.string.output_stopped)
            viewModel.setActivePlayingIndex(-1)
        }

        binding.btnCancel.setOnClickListener {
            viewModel.cancelGeneration()
        }

        binding.sliderSpeed.addOnChangeListener { _, value, _ ->
            playbackVM.setSpeed(value)
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

        // FEAT-76: Export with metadata to Music library
        binding.btnExport.setOnClickListener {
            val state = viewModel.state.value ?: return@setOnClickListener
            // For streaming, concatenate chunks first; otherwise use single file
            val path = if (state.streamChunks.size > 1) {
                val merged = java.io.File(requireContext().cacheDir, "export_merged.mp3").absolutePath
                if (OutputActions.concatenateAudioChunks(state.streamChunks, merged)) merged else null
            } else {
                state.audioPath
            }
            if (path == null) {
                Toast.makeText(requireContext(), "No audio to export", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            showExportDialog(path)
        }
    }

    /** FEAT-76: Show export dialog for MP3 title metadata. */
    private fun showExportDialog(audioPath: String) {
        val titleInput = EditText(requireContext()).apply {
            setText(inputText.take(80))
            hint = getString(R.string.export_title_hint)
            setPadding(48, 24, 48, 24)
        }
        AlertDialog.Builder(requireContext())
            .setTitle(getString(R.string.export_dialog_title))
            .setView(titleInput)
            .setPositiveButton(getString(R.string.action_export)) { _, _ ->
                val title = titleInput.text.toString().trim().ifBlank { "Marathi TTS" }
                OutputActions.exportAudioWithMetadata(
                    context = requireContext(),
                    audioPath = audioPath,
                    title = title
                )
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /** FEAT-54: Emotion intensity slider wiring. */
    private fun setupEmotionIntensity() {
        binding.sliderEmotionIntensity.addOnChangeListener { _, value, fromUser ->
            if (fromUser) {
                viewModel.setEmotionIntensity(value)
                binding.txtIntensityValue.text =
                    getString(R.string.emotion_intensity_value, (value * 100).toInt())
            }
        }
    }

    /** FEAT-55: Observe phonetic explanation results and show dialog. */
    private fun observePhoneticExplanation() {
        viewModel.phoneticExplanation.observe(viewLifecycleOwner) { explanation ->
            if (explanation == null) return@observe
            val sb = StringBuilder()
            sb.append("\"${explanation.original}\" → \"${explanation.final}\"\n")
            if (explanation.rules.isEmpty()) {
                sb.append("\nNo transformations applied — word passes through unchanged.")
            } else {
                for (rule in explanation.rules) {
                    sb.append("\n━ ${rule.stage}: ${rule.rule}\n")
                    sb.append("  ${rule.description}\n")
                    if (rule.before != rule.after) {
                        sb.append("  ${rule.before} → ${rule.after}\n")
                    }
                }
            }
            AlertDialog.Builder(requireContext())
                .setTitle(getString(R.string.phonetic_explainer_title))
                .setMessage(sb.toString())
                .setPositiveButton(android.R.string.ok, null)
                .setNeutralButton(R.string.suggest_correction) { _, _ ->
                    showCorrectionDialog(explanation.original, explanation.final)
                }
                .setOnDismissListener { viewModel.clearPhoneticExplanation() }
                .show()
        }
    }

    /** FEAT-59: Show dialog for user to submit a pronunciation correction. */
    private fun showCorrectionDialog(word: String, currentPronunciation: String) {
        val input = EditText(requireContext()).apply {
            setText(currentPronunciation)
            hint = getString(R.string.correction_hint)
            setPadding(48, 24, 48, 24)
        }
        AlertDialog.Builder(requireContext())
            .setTitle(getString(R.string.correction_title))
            .setMessage(getString(R.string.correction_message, word))
            .setView(input)
            .setPositiveButton(R.string.correction_save) { _, _ ->
                val corrected = input.text.toString().trim()
                if (corrected.isNotBlank() && corrected != word) {
                    viewModel.submitCorrection(word, corrected)
                }
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /** FEAT-59: Observe correction save result. */
    private fun observeCorrectionSaved() {
        viewModel.correctionSaved.observe(viewLifecycleOwner) { saved ->
            if (saved == true) {
                Toast.makeText(requireContext(), R.string.correction_saved, Toast.LENGTH_SHORT).show()
                viewModel.clearCorrectionSaved()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        // NOTE: Do NOT stop audio here — PlaybackViewModel survives tab switches (FEAT-81)
        _binding = null
    }
}
