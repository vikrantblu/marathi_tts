package com.marathitts.mobile.ui.stotra

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
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

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentStotraBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // ── List setup ──
        adapter = StotraAdapter { stotra -> viewModel.selectStotra(stotra) }
        binding.stotraList.layoutManager = LinearLayoutManager(requireContext())
        binding.stotraList.adapter = adapter

        // Search
        binding.searchInput.addTextChangedListener { viewModel.search(it?.toString() ?: "") }

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

        // ── Detail controls ──
        binding.backBtn.setOnClickListener {
            audioPlayer.stop()
            viewModel.clearSelection()
        }

        binding.playTtsBtn.setOnClickListener {
            viewModel.playWithTts()
        }

        binding.stopBtn.setOnClickListener {
            audioPlayer.stop()
            binding.stopBtn.visibility = View.GONE
            binding.detailStatus.text = "Stopped"
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = viewModel.state.value?.stotraText ?: return@setOnClickListener
            // Navigate to TTS fragment with the stotra text
            findNavController().navigate(
                R.id.ttsFragment,
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
            }
        }
    }

    private fun showDetail(state: StotraListState) {
        val stotra = state.selectedStotra ?: return
        binding.detailTitle.text = stotra.title
        binding.detailTitleEn.text = stotra.titleEn
        binding.detailDescription.text = stotra.description
        binding.detailText.text = state.stotraText ?: "(Loading…)"

        // Status
        if (state.statusMessage != null) {
            binding.detailStatus.visibility = View.VISIBLE
            binding.detailStatus.text = state.statusMessage
        } else {
            binding.detailStatus.visibility = View.GONE
        }

        // Loading state
        binding.playTtsBtn.isEnabled = !state.isGenerating
        binding.playTtsBtn.text = if (state.isGenerating) "Generating…" else "Play (TTS)"

        // Auto-play when audio path arrives
        if (state.audioPath != null && !audioPlayer.isPlaying) {
            try {
                audioPlayer.play(state.audioPath) {
                    requireActivity().runOnUiThread {
                        binding.stopBtn.visibility = View.GONE
                        binding.detailStatus.text = "Playback complete"
                    }
                }
                binding.stopBtn.visibility = View.VISIBLE
                binding.detailStatus.text = "Playing…"
            } catch (e: Exception) {
                Toast.makeText(context, "Playback error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        audioPlayer.stop()
        _binding = null
        super.onDestroyView()
    }
}
