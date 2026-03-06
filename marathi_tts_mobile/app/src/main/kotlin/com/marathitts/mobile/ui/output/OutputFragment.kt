package com.marathitts.mobile.ui.output

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentOutputBinding
import com.marathitts.mobile.service.AudioPlayerService
import com.marathitts.mobile.util.OutputActions

class OutputFragment : Fragment() {

    private var _binding: FragmentOutputBinding? = null
    private val binding get() = _binding!!

    private val audioPlayer = AudioPlayerService()
    private var currentAudioPath: String? = null
    private var inputText: String = ""

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentOutputBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Read arguments passed from InputFragment
        inputText = arguments?.getString("input_text").orEmpty()

        if (inputText.isNotBlank()) {
            showPlayerUI(inputText)
        }

        setupPlaybackControls()
        setupOutputActions()
    }

    private fun showPlayerUI(text: String) {
        binding.emptyState.visibility = View.GONE
        binding.playerCard.visibility = View.VISIBLE
        binding.textPreviewCard.visibility = View.VISIBLE
        binding.txtInputPreview.text = text
    }

    private fun setupPlaybackControls() {
        binding.btnPlay.setOnClickListener {
            val path = currentAudioPath
            if (path != null) {
                audioPlayer.playAsync(path)
            } else {
                Toast.makeText(requireContext(), "No audio generated yet", Toast.LENGTH_SHORT).show()
            }
        }

        binding.btnStop.setOnClickListener {
            audioPlayer.stop()
        }
    }

    private fun setupOutputActions() {
        binding.btnCopy.setOnClickListener {
            OutputActions.copyText(requireContext(), inputText)
        }

        binding.btnShare.setOnClickListener {
            val path = currentAudioPath
            if (path != null) {
                OutputActions.shareAudio(requireContext(), path)
            } else {
                OutputActions.shareText(requireContext(), inputText)
            }
        }

        binding.btnSave.setOnClickListener {
            val path = currentAudioPath
            if (path != null) {
                OutputActions.saveAudioToDownloads(requireContext(), path)
            } else {
                Toast.makeText(requireContext(), "No audio to save", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        audioPlayer.stop()
        _binding = null
    }
}
