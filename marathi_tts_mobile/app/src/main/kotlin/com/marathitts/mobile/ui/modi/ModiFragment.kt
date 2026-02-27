package com.marathitts.mobile.ui.modi

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentModiBinding

class ModiFragment : Fragment() {

    private var _binding: FragmentModiBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ModiViewModel by viewModels()

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _binding = FragmentModiBinding.inflate(i, c, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Mode spinner
        val adapter = ArrayAdapter(requireContext(),
            android.R.layout.simple_spinner_item, ModiViewModel.MODE_LABELS)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        binding.modeSpinner.adapter = adapter

        binding.modeSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                binding.modeHintText.text = ModiViewModel.MODE_HINTS[pos]
            }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
        binding.modeHintText.text = ModiViewModel.MODE_HINTS[0]

        // Character count watcher
        binding.inputText.addTextChangedListener(object : android.text.TextWatcher {
            override fun afterTextChanged(s: android.text.Editable?) {
                binding.inputCharCount.text = "${s?.length ?: 0} chars"
            }
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
        })

        binding.convertBtn.setOnClickListener {
            val text = binding.inputText.text.toString().trim()
            if (text.isEmpty()) {
                Toast.makeText(context, "Please enter text to convert", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            viewModel.convert(text, binding.modeSpinner.selectedItemPosition)
        }

        binding.clearBtn.setOnClickListener {
            binding.inputText.text.clear()
            binding.outputText.setText("")
            viewModel.clear()
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.outputText.text.toString()
            if (text.isNotBlank()) {
                val bundle = Bundle().apply { putString("tts_text", text) }
                findNavController().navigate(R.id.ttsFragment, bundle)
            }
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.convertBtn.isEnabled = !state.isLoading
            binding.statusText.text = state.status

            if (state.output.isNotEmpty()) {
                binding.outputText.setText(state.output)
                binding.outputCharCount.text = "${state.outputCharCount} chars"
                binding.sendToTtsBtn.isEnabled = true
            }
        }
    }

    override fun onDestroyView() { super.onDestroyView(); _binding = null }
}
