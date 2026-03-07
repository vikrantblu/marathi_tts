package com.marathitts.mobile.ui.history

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import com.marathitts.mobile.R
import com.marathitts.mobile.data.HistoryEntry
import com.marathitts.mobile.databinding.FragmentHistoryBinding
import com.marathitts.mobile.util.OutputActions

class HistoryFragment : Fragment() {

    private var _binding: FragmentHistoryBinding? = null
    private val binding get() = _binding!!
    private val viewModel: HistoryViewModel by viewModels()
    private lateinit var adapter: HistoryAdapter

    /** Currently active category filter (null = All) */
    private var activeFilter: String? = null

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _binding = FragmentHistoryBinding.inflate(i, c, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = HistoryAdapter(
            onTap = { entry -> onHistoryTap(entry) },
            onDelete = { entry -> viewModel.deleteEntry(entry) }
        )
        binding.historyList.layoutManager = LinearLayoutManager(requireContext())
        binding.historyList.adapter = adapter

        // Filter chip map:  chip-id → category string (null = all)
        val filterMap = mapOf(
            R.id.chip_all to null,
            R.id.chip_tts to "TTS",
            R.id.chip_stt to "STT",
            R.id.chip_ocr to "OCR",
            R.id.chip_stotra to "STOTRA",
            R.id.chip_other to "__OTHER__"
        )

        binding.filterChips.setOnCheckedStateChangeListener { _, checkedIds ->
            val chipId = checkedIds.firstOrNull() ?: R.id.chip_all
            activeFilter = filterMap[chipId]
            applyFilter(viewModel.allHistory.value ?: emptyList())
        }

        binding.clearAllBtn.setOnClickListener {
            AlertDialog.Builder(requireContext())
                .setTitle("Clear History")
                .setMessage("Delete all history entries?")
                .setPositiveButton("Delete") { _, _ -> viewModel.clearAll() }
                .setNegativeButton("Cancel", null)
                .show()
        }

        // Observe all history, apply local filter
        viewModel.allHistory.observe(viewLifecycleOwner) { list ->
            applyFilter(list)
        }
    }

    private fun applyFilter(list: List<HistoryEntry>) {
        val filtered = when (activeFilter) {
            null -> list
            "__OTHER__" -> list.filter { it.category !in setOf("TTS", "STT", "OCR", "STOTRA") }
            else -> list.filter { it.category == activeFilter }
        }
        adapter.submitList(filtered)
        binding.emptyState.visibility = if (filtered.isEmpty()) View.VISIBLE else View.GONE
        binding.historyList.visibility = if (filtered.isEmpty()) View.GONE else View.VISIBLE
    }

    /** Tap a history entry → copy text; long-press re-send to TTS */
    private fun onHistoryTap(entry: HistoryEntry) {
        // Show options dialog
        val options = mutableListOf("Copy text", "Share text", "Send to TTS")
        AlertDialog.Builder(requireContext())
            .setTitle(entry.category)
            .setItems(options.toTypedArray()) { _, which ->
                when (which) {
                    0 -> OutputActions.copyText(requireContext(), entry.outputText, "History")
                    1 -> OutputActions.shareText(requireContext(), entry.outputText, "History")
                    2 -> {
                        val bundle = Bundle().apply { putString("tts_text", entry.outputText) }
                        findNavController().navigate(R.id.inputFragment, bundle)
                    }
                }
            }
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
