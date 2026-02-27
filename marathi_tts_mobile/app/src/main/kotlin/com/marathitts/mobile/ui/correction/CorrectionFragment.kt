package com.marathitts.mobile.ui.correction

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.google.android.material.textfield.TextInputEditText
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentCorrectionBinding

class CorrectionFragment : Fragment() {

    private var _binding: FragmentCorrectionBinding? = null
    private val binding get() = _binding!!
    private val viewModel: CorrectionViewModel by viewModels()

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _binding = FragmentCorrectionBinding.inflate(i, c, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.correctBtn.setOnClickListener {
            val text = binding.inputText.text.toString().trim()
            if (text.isNotEmpty()) viewModel.correctText(text)
        }

        binding.formatBtn.setOnClickListener {
            val text = binding.inputText.text.toString().trim()
            if (text.isNotEmpty()) viewModel.formatText(text)
        }

        binding.clearBtn.setOnClickListener {
            binding.inputText.text?.clear()
            binding.outputText.text?.clear()
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.outputText.text.toString()
            if (text.isNotBlank()) {
                val bundle = Bundle().apply { putString("tts_text", text) }
                findNavController().navigate(R.id.ttsFragment, bundle)
            }
        }

        binding.suggestBtn.setOnClickListener {
            showSuggestionDialog()
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.correctBtn.isEnabled = !state.isLoading
            binding.formatBtn.isEnabled = !state.isLoading
            binding.statusText.text = state.status

            if (state.correctedText != null) {
                binding.outputText.setText(state.correctedText)
                binding.methodLabel.text = state.method?.let { "Method: $it" } ?: ""
                binding.sendToTtsBtn.isEnabled = true
                binding.suggestBtn.isEnabled = true
            }
        }
    }

    private fun showSuggestionDialog() {
        val incorrect = binding.inputText.text.toString().trim()
        val correct = binding.outputText.text.toString().trim()

        val editText = TextInputEditText(requireContext()).apply {
            hint = "Optional: enter correct version"
            setText(correct)
            setPadding(48, 16, 48, 16)
        }

        AlertDialog.Builder(requireContext())
            .setTitle("Suggest Correction")
            .setMessage("Submit \"$incorrect\" → corrected form as a learning example?")
            .setView(editText)
            .setPositiveButton("Submit") { _, _ ->
                val finalCorrect = editText.text.toString().trim().ifEmpty { correct }
                if (incorrect.isNotEmpty() && finalCorrect.isNotEmpty()) {
                    viewModel.suggestCorrection(incorrect, finalCorrect)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onDestroyView() { super.onDestroyView(); _binding = null }
}
