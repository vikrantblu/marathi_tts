package com.marathitts.mobile.ui.stotra

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognizerIntent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.os.bundleOf
import androidx.core.widget.addTextChangedListener
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentStotraBinding
import com.marathitts.mobile.service.AudioPlayerService

class StotraFragment : Fragment() {

    private var _binding: FragmentStotraBinding? = null
    private val binding get() = _binding!!

    private val viewModel: StotraViewModel by viewModels()
    private val audioPlayer = AudioPlayerService()
    private lateinit var adapter: StotraAdapter
    // Track which audio path we already started playing so state re-emissions
    // (e.g. status-text updates) don't restart playback from the beginning.
    private var lastPlayedPath: String? = null

    // FEAT-60: Voice search via SpeechRecognizer
    private val voiceSearchLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val matches = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val text = matches?.firstOrNull()
            if (!text.isNullOrBlank()) {
                binding.searchInput.setText(text)
                binding.searchInput.setSelection(text.length)
            }
        }
    }

    private val micPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) launchVoiceSearch()
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentStotraBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // ── List setup ──
        adapter = StotraAdapter(
            onClick = { stotra ->
                val s = viewModel.state.value
                if (s?.isPlaylistMode == true) {
                    viewModel.togglePlaylistSelection(stotra.id)
                } else {
                    viewModel.selectStotra(stotra)
                }
            },
            onLongClick = { _ ->
                if (viewModel.state.value?.isPlaylistMode != true) {
                    viewModel.togglePlaylistMode()
                }
            }
        )
        binding.stotraList.layoutManager = LinearLayoutManager(requireContext())
        binding.stotraList.adapter = adapter

        // Search
        binding.searchInput.addTextChangedListener { viewModel.search(it?.toString() ?: "") }

        // FEAT-60: Voice search
        binding.voiceSearchBtn.setOnClickListener {
            if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.RECORD_AUDIO)
                == PackageManager.PERMISSION_GRANTED) {
                launchVoiceSearch()
            } else {
                micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }

        // Deity filter chips
        val chipMap = mapOf(
            R.id.chip_all to null,
            R.id.chip_ganesh to "गणेश",
            R.id.chip_vishnu to "विष्णु",
            R.id.chip_shiv to "शिव",
            R.id.chip_devi to "देवी",
            R.id.chip_hanuman to "हनुमान",
            R.id.chip_ram to "राम"
        )
        binding.filterChips.setOnCheckedStateChangeListener { _, checkedIds ->
            val chipId = checkedIds.firstOrNull() ?: R.id.chip_all
            viewModel.filterByDeity(chipMap[chipId])
        }

        // ── Playlist controls ──
        setupPlaylistControls()

        // ── Detail controls ──
        binding.backBtn.setOnClickListener {
            audioPlayer.stop()
            lastPlayedPath = null
            viewModel.clearSelection()
        }

        binding.playTtsBtn.setOnClickListener {
            lastPlayedPath = null   // allow re-generation to be played
            viewModel.playWithTts()
        }

        binding.stopBtn.setOnClickListener {
            audioPlayer.stop()
            lastPlayedPath = null
            binding.stopBtn.visibility = View.GONE
            binding.detailStatus.text = "Stopped"
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = viewModel.state.value?.stotraText ?: return@setOnClickListener
            // Navigate to TTS fragment with the stotra text
            findNavController().navigate(
                R.id.inputFragment,
                bundleOf("tts_text" to text)
            )
        }

        // ── Observe state ──
        viewModel.state.observe(viewLifecycleOwner) { state ->
            // List vs detail visibility
            if (state.selectedStotra != null) {
                binding.listContainer.visibility = View.GONE
                binding.detailContainer.visibility = View.VISIBLE
                showDetail(state)
            } else {
                binding.listContainer.visibility = View.VISIBLE
                binding.detailContainer.visibility = View.GONE
                adapter.submitList(state.filteredStotras)
                binding.stotraCount.text = "${state.filteredStotras.size} stotras"

                // FEAT-60: Content search results
                updateContentSearch(state)

                // Playlist mode UI
                updatePlaylistUI(state)
            }
        }
    }

    private fun setupPlaylistControls() {
        binding.playlistToggleBtn.setOnClickListener {
            viewModel.togglePlaylistMode()
        }

        binding.playlistSelectAllBtn.setOnClickListener {
            viewModel.selectAllForPlaylist()
        }

        binding.playlistGenerateBtn.setOnClickListener {
            viewModel.generatePlaylist()
        }

        binding.playlistStopBtn.setOnClickListener {
            val s = viewModel.state.value ?: return@setOnClickListener
            if (s.isGenerating) {
                viewModel.cancelPlaylist()
            } else if (s.isPlaylistPlaying) {
                audioPlayer.stop()
                viewModel.setPlaylistPlaying(false)
            }
        }
    }

    private fun updatePlaylistUI(state: StotraListState) {
        val inPlaylist = state.isPlaylistMode
        adapter.isPlaylistMode = inPlaylist
        adapter.playlistSelection = state.playlistSelection

        // Toggle button text
        binding.playlistToggleBtn.text = if (inPlaylist) {
            getString(R.string.playlist_mode_exit)
        } else {
            getString(R.string.playlist_mode)
        }

        // Action bar visibility
        binding.playlistActionBar.visibility = if (inPlaylist) View.VISIBLE else View.GONE

        if (inPlaylist) {
            val count = state.playlistSelection.size
            binding.playlistSelectionCount.text = getString(R.string.playlist_selected, count)
            binding.playlistGenerateBtn.isEnabled = count > 0 && !state.isGenerating
        }

        // Status bar: visible during generation or playback
        val showStatus = state.isGenerating || state.isPlaylistPlaying ||
                         state.playlistPaths.isNotEmpty()
        binding.playlistStatusBar.visibility = if (showStatus) View.VISIBLE else View.GONE

        if (state.isGenerating) {
            binding.playlistStatus.text = getString(
                R.string.playlist_generating,
                state.playlistProgress,
                state.playlistTotal
            )
            binding.playlistProgress.max = state.playlistTotal
            binding.playlistProgress.progress = state.playlistProgress
            binding.playlistProgress.visibility = View.VISIBLE
            binding.playlistStopBtn.text = getString(R.string.playlist_stop)
            binding.playlistStopBtn.visibility = View.VISIBLE
        } else if (state.playlistPaths.isNotEmpty() && !state.isPlaylistPlaying) {
            // Ready to play — auto-start
            startPlaylistPlayback(state.playlistPaths)
        }

        if (state.isPlaylistPlaying) {
            val current = state.playlistCurrentIndex + 1
            val total = state.playlistPaths.size
            binding.playlistStatus.text = getString(R.string.playlist_playing, current, total)
            binding.playlistProgress.max = total
            binding.playlistProgress.progress = current
            binding.playlistProgress.visibility = View.VISIBLE
            binding.playlistStopBtn.text = getString(R.string.playlist_stop)
            binding.playlistStopBtn.visibility = View.VISIBLE
        }
    }

    private var playlistStarted = false

    private fun startPlaylistPlayback(paths: List<String>) {
        if (playlistStarted) return
        playlistStarted = true
        viewModel.setPlaylistPlaying(true, 0)

        audioPlayer.playQueueAsync(
            paths = paths,
            onChunkStart = { index ->
                requireActivity().runOnUiThread {
                    viewModel.setPlaylistPlaying(true, index)
                }
            },
            onAllComplete = {
                requireActivity().runOnUiThread {
                    viewModel.setPlaylistPlaying(false)
                    playlistStarted = false
                    binding.playlistStopBtn.visibility = View.GONE
                    binding.playlistStatus.text = "Playlist complete"
                }
            },
            onError = { msg ->
                requireActivity().runOnUiThread {
                    viewModel.setPlaylistPlaying(false)
                    playlistStarted = false
                    Toast.makeText(context, "Playback error: $msg", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    /** FEAT-60: Launch Android voice recognition for Marathi/Sanskrit. */
    private fun launchVoiceSearch() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "mr-IN")
            putExtra(RecognizerIntent.EXTRA_PROMPT, getString(R.string.voice_search_listening))
        }
        try {
            voiceSearchLauncher.launch(intent)
        } catch (_: Exception) {
            Toast.makeText(context, R.string.voice_search_error, Toast.LENGTH_SHORT).show()
        }
    }

    /** FEAT-60: Display content search results card. */
    private fun updateContentSearch(state: StotraListState) {
        if (state.isContentSearchActive && state.contentMatches.isNotEmpty()) {
            binding.contentSearchCard.visibility = View.VISIBLE
            binding.contentSearchHeader.text =
                getString(R.string.content_search_header, state.contentMatches.size)
            val sb = StringBuilder()
            for ((i, match) in state.contentMatches.withIndex()) {
                if (i > 0) sb.append("\n\n")
                sb.append("► ${match.stotra.title}\n")
                sb.append(match.excerpt)
                if (i >= 4) break  // show max 5 results
            }
            binding.contentSearchResults.text = sb.toString()
            // Tap on the card navigates to the first match
            binding.contentSearchCard.setOnClickListener {
                val first = state.contentMatches.firstOrNull() ?: return@setOnClickListener
                viewModel.selectStotra(first.stotra)
            }
        } else {
            binding.contentSearchCard.visibility = View.GONE
        }
    }

    private fun showDetail(state: StotraListState) {
        val stotra = state.selectedStotra ?: return
        binding.detailTitle.text = stotra.title
        binding.detailTitleEn.text = stotra.titleEn
        binding.detailDescription.text = stotra.description
        binding.detailText.text = state.stotraText ?: "(Loading…)"

        // Show/hide pre-recorded badge and set button label — consolidate into one block
        // that accounts for both hasPreRecordedAudio and isGenerating states.
        binding.preRecordedBadge.visibility = if (state.hasPreRecordedAudio) View.VISIBLE else View.GONE
        binding.playTtsBtn.isEnabled = !state.isGenerating
        binding.playTtsBtn.text = when {
            state.isGenerating && state.hasPreRecordedAudio -> "Loading…"
            state.isGenerating -> "Generating…"
            state.hasPreRecordedAudio -> "Play"
            else -> "Play (TTS)"
        }

        // Status
        if (state.statusMessage != null) {
            binding.detailStatus.visibility = View.VISIBLE
            binding.detailStatus.text = state.statusMessage
        } else {
            binding.detailStatus.visibility = View.GONE
        }

        // Auto-play when a NEW audio path arrives (guard against state re-emissions).
        if (state.audioPath != null && state.audioPath != lastPlayedPath) {
            lastPlayedPath = state.audioPath
            try {
                audioPlayer.playAsync(state.audioPath,
                    onReady = {
                        requireActivity().runOnUiThread {
                            binding.stopBtn.visibility = View.VISIBLE
                            binding.detailStatus.text = "Playing…"
                        }
                    },
                    onComplete = {
                        requireActivity().runOnUiThread {
                            binding.stopBtn.visibility = View.GONE
                            binding.detailStatus.text = "Playback complete"
                        }
                    }
                )
            } catch (e: Exception) {
                Toast.makeText(context, "Playback error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        audioPlayer.stop()
        playlistStarted = false
        _binding = null
        super.onDestroyView()
    }
}
