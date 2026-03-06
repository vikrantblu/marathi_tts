package com.marathitts.mobile.ui.input

import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentInputBinding
import com.marathitts.mobile.util.AppPreferences

class InputFragment : Fragment() {

    private var _binding: FragmentInputBinding? = null
    private val binding get() = _binding!!
    private var optionsExpanded = false

    companion object {
        private val LANGUAGES = listOf("Auto-detect", "Marathi", "Sanskrit", "Hindi")
        private val LANG_CODES = listOf("auto", "mr", "sa", "hi")
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentInputBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupLanguageSpinner()
        setupQuickActions()
        setupSourceChips()
        setupGenerateButton()
        setupOptionsToggle()

        // Accept text passed from other screens (Correction, Emotion, History, Modi, Stotra)
        val argText = arguments?.getString("tts_text")
        if (argText != null) {
            binding.textInput.setText(argText)
        } else {
            // Restore draft if no argument passed
            val draft = AppPreferences.getTtsDraft(requireContext())
            if (draft.isNotBlank()) {
                binding.textInput.setText(draft)
            }
        }

        // Accept text returned from child screens (OCR, PDF, Web, STT, BookReader)
        findNavController().currentBackStackEntry
            ?.savedStateHandle
            ?.getLiveData<String>("extracted_text")
            ?.observe(viewLifecycleOwner) { text ->
                if (text.isNotBlank()) {
                    binding.textInput.setText(text)
                }
            }
    }

    private fun setupLanguageSpinner() {
        val adapter = ArrayAdapter(
            requireContext(),
            android.R.layout.simple_spinner_item,
            LANGUAGES
        )
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.spinnerLanguage.adapter = adapter
    }

    private fun setupQuickActions() {
        binding.btnPaste.setOnClickListener {
            val clipboard = requireContext().getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = clipboard.primaryClip
            if (clip != null && clip.itemCount > 0) {
                val pasted = clip.getItemAt(0).coerceToText(requireContext()).toString()
                binding.textInput.setText(pasted)
            } else {
                Toast.makeText(requireContext(), "Clipboard empty", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnClear.setOnClickListener {
            binding.textInput.text?.clear()
        }

        binding.btnCorrection.setOnClickListener {
            val text = binding.textInput.text?.toString().orEmpty()
            if (text.isNotBlank()) {
                val bundle = Bundle().apply { putString("correction_text", text) }
                findNavController().navigate(R.id.correctionFragment, bundle)
            }
        }
    }

    private fun setupSourceChips() {
        binding.chipCamera.setOnClickListener {
            findNavController().navigate(R.id.action_input_to_ocr)
        }
        binding.chipPdf.setOnClickListener {
            findNavController().navigate(R.id.action_input_to_pdf)
        }
        binding.chipWeb.setOnClickListener {
            findNavController().navigate(R.id.action_input_to_web)
        }
        binding.chipMic.setOnClickListener {
            findNavController().navigate(R.id.action_input_to_stt)
        }
        binding.chipBook.setOnClickListener {
            findNavController().navigate(R.id.action_input_to_book)
        }
    }

    private fun setupGenerateButton() {
        binding.btnGenerate.setOnClickListener {
            val text = binding.textInput.text?.toString().orEmpty()
            if (text.isBlank()) {
                Toast.makeText(requireContext(), "Enter some text first", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val langIndex = binding.spinnerLanguage.selectedItemPosition
            val rawCode = LANG_CODES.getOrElse(langIndex) { "auto" }
            val langCode = if (rawCode == "auto") detectLanguage(text) else rawCode
            val isVerse = binding.switchVerse.isChecked

            val bundle = Bundle().apply {
                putString("input_text", text)
                putString("language", langCode)
                putBoolean("is_verse", isVerse)
            }
            findNavController().navigate(R.id.action_input_to_output, bundle)
        }
    }

    private fun setupOptionsToggle() {
        binding.btnOptionsToggle.setOnClickListener {
            optionsExpanded = !optionsExpanded
            binding.optionsCard.visibility = if (optionsExpanded) View.VISIBLE else View.GONE
            binding.btnOptionsToggle.setIconResource(
                if (optionsExpanded) R.drawable.ic_expand_less else R.drawable.ic_expand_more
            )
        }
    }

    /**
     * Simple heuristic to detect Sanskrit vs Hindi vs Marathi.
     * Sanskrit indicators: shloka markers (॥), anusvara-heavy text, common Sanskrit suffixes.
     * Hindi indicators: common Hindi postpositions absent in Marathi.
     * Default: Marathi.
     */
    private fun detectLanguage(text: String): String {
        val sanskritMarkers = listOf("॥", "ॐ", "नमः", "स्तोत्र", "श्लोक", "सूक्त", "मन्त्र")
        val hindiMarkers = listOf(" है ", " हैं ", " था ", " थी ", " हूँ ", " में ", " को ")
        val sanskritScore = sanskritMarkers.count { text.contains(it) }
        val hindiScore = hindiMarkers.count { text.contains(it) }
        return when {
            sanskritScore >= 2 -> "sa"
            hindiScore >= 2 -> "hi"
            else -> "mr"
        }
    }

    override fun onPause() {
        super.onPause()
        val text = _binding?.textInput?.text?.toString().orEmpty()
        AppPreferences.setTtsDraft(requireContext(), text)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
