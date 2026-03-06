package com.marathitts.mobile.ui.me

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.BuildConfig
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentMeBinding
import com.marathitts.mobile.util.AppPreferences

class MeFragment : Fragment() {

    private var _binding: FragmentMeBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentMeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.txtVersion.text = "v${BuildConfig.VERSION_NAME}"

        binding.cardStotra.setOnClickListener {
            findNavController().navigate(R.id.action_me_to_stotra)
        }

        binding.cardHistory.setOnClickListener {
            findNavController().navigate(R.id.action_me_to_history)
        }

        binding.cardModi.setOnClickListener {
            findNavController().navigate(R.id.modiFragment)
        }

        binding.cardSettings.setOnClickListener {
            findNavController().navigate(R.id.action_me_to_settings)
        }

        // Developer mode: show test dashboard card
        if (AppPreferences.isDevModeEnabled(requireContext())) {
            binding.cardTest.visibility = View.VISIBLE
        }
        binding.cardTest.setOnClickListener {
            findNavController().navigate(R.id.action_me_to_test)
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
