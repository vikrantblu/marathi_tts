package com.marathitts.mobile.ui.pdf

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentPdfBinding
import java.io.File

class PdfFragment : Fragment() {

    private var _binding: FragmentPdfBinding? = null
    private val binding get() = _binding!!
    private val viewModel: PdfViewModel by viewModels()
    private var selectedPdfPath: String? = null

    private val pickPdf = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let {
            val cache = File(requireContext().cacheDir, "selected.pdf")
            requireContext().contentResolver.openInputStream(uri)?.use { i ->
                cache.outputStream().use { o -> i.copyTo(o) }
            }
            selectedPdfPath = cache.absolutePath
            binding.fileLabel.text = uri.lastPathSegment ?: "Selected PDF"
            binding.extractBtn.isEnabled = true
            binding.statusText.text = "PDF selected"
        }
    }

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _binding = FragmentPdfBinding.inflate(i, c, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.browseBtn.setOnClickListener { pickPdf.launch("application/pdf") }
        binding.extractBtn.setOnClickListener {
            selectedPdfPath?.let { viewModel.extractFromPdf(it) }
        }
        binding.clearBtn.setOnClickListener {
            selectedPdfPath = null
            binding.fileLabel.text = "No file selected"
            binding.extractedText.text?.clear()
            binding.extractBtn.isEnabled = false
            binding.sendToTtsBtn.isEnabled = false
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.extractedText.text.toString()
            if (text.isNotBlank()) {
                val bundle = Bundle().apply { putString("tts_text", text) }
                findNavController().navigate(R.id.ttsFragment, bundle)
            }
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.extractBtn.isEnabled = !state.isLoading && selectedPdfPath != null
            binding.statusText.text = state.status
            binding.methodLabel.text = state.method?.let { "Method: $it" } ?: ""
            if (state.text != null) {
                binding.extractedText.setText(state.text)
                binding.sendToTtsBtn.isEnabled = true
            }
        }
    }

    override fun onDestroyView() { super.onDestroyView(); _binding = null }
}
