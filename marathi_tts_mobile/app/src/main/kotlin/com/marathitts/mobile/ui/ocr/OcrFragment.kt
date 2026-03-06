package com.marathitts.mobile.ui.ocr

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import com.marathitts.mobile.R
import com.marathitts.mobile.databinding.FragmentOcrBinding
import java.io.File

class OcrFragment : Fragment() {

    private var _binding: FragmentOcrBinding? = null
    private val binding get() = _binding!!
    private val viewModel: OcrViewModel by viewModels()
    private var selectedImagePath: String? = null
    private var cameraPhotoFile: File? = null

    // Gallery picker
    private val pickImage = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { handleImageUri(it) }
    }

    // Camera capture
    private val takePicture = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) {
            cameraPhotoFile?.let { file ->
                selectedImagePath = file.absolutePath
                binding.imagePreview.setImageURI(Uri.fromFile(file))
                binding.emptyStateOverlay.visibility = View.GONE
                binding.extractBtn.isEnabled = true
                binding.statusText.text = "Photo captured"
            }
        }
    }

    // Permission request
    private val requestCameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) launchCamera() else {
            Toast.makeText(context, "Camera permission is required", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, s: Bundle?): View {
        _binding = FragmentOcrBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Handle image shared from another app (gallery, browser, etc.)
        arguments?.getString("shared_image_uri")?.let { uriString ->
            val uri = Uri.parse(uriString)
            handleImageUri(uri)
        }

        binding.browseBtn.setOnClickListener { pickImage.launch("image/*") }

        binding.cameraBtn.setOnClickListener {
            if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED
            ) {
                launchCamera()
            } else {
                requestCameraPermission.launch(Manifest.permission.CAMERA)
            }
        }

        binding.extractBtn.setOnClickListener {
            selectedImagePath?.let { viewModel.extractFromImage(it) }
                ?: Toast.makeText(context, "Select an image first", Toast.LENGTH_SHORT).show()
        }

        binding.sendToTtsBtn.setOnClickListener {
            val text = binding.extractedText.text.toString()
            if (text.isNotBlank()) {
                findNavController().previousBackStackEntry
                    ?.savedStateHandle?.set("extracted_text", text)
                findNavController().popBackStack()
            }
        }

        binding.clearBtn.setOnClickListener {
            selectedImagePath = null
            binding.imagePreview.setImageDrawable(null)
            binding.emptyStateOverlay.visibility = View.VISIBLE
            binding.extractedText.text?.clear()
            binding.extractBtn.isEnabled = false
            binding.sendToTtsBtn.isEnabled = false
            binding.statusText.text = "Select an image to begin"
        }

        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.extractBtn.isEnabled = !state.isLoading && selectedImagePath != null
            binding.statusText.text = state.status
            if (state.text != null) {
                binding.extractedText.setText(state.text)
                binding.sendToTtsBtn.isEnabled = state.text.isNotBlank()
            }
        }
    }

    private fun launchCamera() {
        val photoFile = File(requireContext().cacheDir, "camera_ocr_${System.currentTimeMillis()}.jpg")
        cameraPhotoFile = photoFile
        val uri = FileProvider.getUriForFile(
            requireContext(),
            "${requireContext().packageName}.fileprovider",
            photoFile
        )
        takePicture.launch(uri)
    }

    private fun handleImageUri(uri: Uri) {
        val cacheFile = File(requireContext().cacheDir, "ocr_input.jpg")
        requireContext().contentResolver.openInputStream(uri)?.use { input ->
            cacheFile.outputStream().use { output -> input.copyTo(output) }
        }
        selectedImagePath = cacheFile.absolutePath
        binding.imagePreview.setImageURI(uri)
        binding.emptyStateOverlay.visibility = View.GONE
        binding.extractBtn.isEnabled = true
        binding.statusText.text = "Image selected"
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
