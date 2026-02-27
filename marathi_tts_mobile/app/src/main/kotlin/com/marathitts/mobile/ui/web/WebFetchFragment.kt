package com.marathitts.mobile.ui.web

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentWebFetchBinding

class WebFetchFragment : Fragment() {

    private var _binding: FragmentWebFetchBinding? = null
    private val binding get() = _binding!!
    private val viewModel: WebFetchViewModel by viewModels()

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _binding = FragmentWebFetchBinding.inflate(i, c, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val doFetch = {
            val url = binding.urlInput.text.toString().trim()
            if (url.isNotEmpty()) viewModel.fetchUrl(url)
        }

        binding.fetchBtn.setOnClickListener { doFetch() }
        binding.urlInput.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_GO) { doFetch(); true } else false
        }
        binding.clearBtn.setOnClickListener {
            binding.urlInput.text?.clear()
            binding.titleText.text = ""
            binding.contentText.text?.clear()
            binding.sendToTtsBtn.isEnabled = false
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.contentText.text.toString()
            if (text.isNotBlank()) {
                val bundle = Bundle().apply { putString("tts_text", text) }
                findNavController().navigate(R.id.ttsFragment, bundle)
            }
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.fetchBtn.isEnabled = !state.isLoading
            binding.statusText.text = state.status
            state.title?.let { binding.titleText.text = it }
            state.text?.let {
                binding.contentText.setText(it)
                binding.sendToTtsBtn.isEnabled = it.isNotBlank()
            }
        }
    }

    override fun onDestroyView() { super.onDestroyView(); _binding = null }
}
