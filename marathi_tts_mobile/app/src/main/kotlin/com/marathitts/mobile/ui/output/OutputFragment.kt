package com.marathitts.mobile.ui.output

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.recyclerview.widget.LinearLayoutManager
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
    private var language: String = "mr"
    private var isVerse: Boolean = false

    private lateinit var prosodyAdapter: ProsodySegmentAdapter

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

        setupProsodyPreview()
        setupPlaybackControls()
        setupOutputActions()
        setupEmotionIntensity()
        setupAccentChips()
        applySmartSpeed(isVerse)
        observeState()
        observePhoneticExplanation()
        observeCorrectionSaved()

        // Auto-trigger generation when text is provided
        if (inputText.isNotBlank()) {
            viewModel.generate(inputText, language, isVerse)
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
                binding.txtEngine.text = state.engine.takeIf { it.isNotEmpty() }
                    ?.let { "Engine: $it" } ?: ""
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
            } else {
                binding.prosodyPreviewCard.visibility = View.GONE
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

    /** FEAT-57: Accent profile chip wiring. */
    private fun setupAccentChips() {
        val chipToAccent = mapOf(
            R.id.chip_accent_standard to "standard",
            R.id.chip_accent_mumbai to "mumbai",
            R.id.chip_accent_northern to "northern",
            R.id.chip_accent_konkanastha to "konkanastha",
            R.id.chip_accent_deccani to "deccani"
        )
        val accentToDesc = mapOf(
            "standard" to R.string.accent_standard_desc,
            "mumbai" to R.string.accent_mumbai_desc,
            "northern" to R.string.accent_northern_desc,
            "konkanastha" to R.string.accent_konkanastha_desc,
            "deccani" to R.string.accent_deccani_desc
        )
        binding.accentChips.setOnCheckedStateChangeListener { _, checkedIds ->
            val chipId = checkedIds.firstOrNull() ?: R.id.chip_accent_standard
            val accent = chipToAccent[chipId] ?: "standard"
            viewModel.setAccent(accent)
            binding.accentDescription.text =
                getString(accentToDesc[accent] ?: R.string.accent_standard_desc)
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
        audioPlayer.stop()
        _binding = null
    }
}
