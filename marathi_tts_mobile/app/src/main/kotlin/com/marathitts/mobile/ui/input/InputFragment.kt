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

class InputFragment : Fragment() {

    private var _binding: FragmentInputBinding? = null
    private val binding get() = _binding!!

    companion object {
        private val LANGUAGES = listOf("Marathi", "Sanskrit", "Hindi")
        private val LANG_CODES = listOf("mr", "sa", "hi")
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

        // Accept text passed from other screens (Correction, Emotion, History, Modi, Stotra)
        arguments?.getString("tts_text")?.let { binding.textInput.setText(it) }

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
            val langCode = LANG_CODES.getOrElse(langIndex) { "mr" }
            val isVerse = binding.switchVerse.isChecked

            val bundle = Bundle().apply {
                putString("input_text", text)
                putString("language", langCode)
                putBoolean("is_verse", isVerse)
            }
            findNavController().navigate(R.id.action_input_to_output, bundle)
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
