package com.marathitts.mobile.ui.bookreader

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
import com.marathitts.mobile.databinding.FragmentBookReaderBinding
import java.io.File

class BookReaderFragment : Fragment() {

    private var _binding: FragmentBookReaderBinding? = null
    private val binding get() = _binding!!
    private val viewModel: BookReaderViewModel by viewModels()
    private var capturedPhotoFile: File? = null
    private var isSinglePageMode = false

    // ── Activity Result contracts ────────────────────────────────

    /** Camera capture result */
    private val takePicture = registerForActivityResult(
        ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            capturedPhotoFile?.let { file ->
                showImagePreview(Uri.fromFile(file))
                processImage(file.absolutePath)
            }
        }
    }

    /** Gallery picker */
    private val pickImage = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let {
            val file = copyUriToCache(it)
            showImagePreview(it)
            processImage(file.absolutePath)
        }
    }

    /** Camera permission */
    private val requestCameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) launchCamera()
        else Toast.makeText(context, "Camera permission is required", Toast.LENGTH_SHORT).show()
    }

    // ── Lifecycle ────────────────────────────────────────────────

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, s: Bundle?): View {
        _binding = FragmentBookReaderBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Capture open book spread (two pages) via camera
        binding.captureSpreadBtn.setOnClickListener {
            isSinglePageMode = false
            checkCameraAndLaunch()
        }

        // Capture a single page via camera
        binding.captureSingleBtn.setOnClickListener {
            isSinglePageMode = true
            checkCameraAndLaunch()
        }

        // Browse gallery for a photo of book pages
        binding.browseBtn.setOnClickListener {
            isSinglePageMode = false  // assume spread; can be changed later
            pickImage.launch("image/*")
        }

        // Read the extracted text aloud via TTS
        binding.readAloudBtn.setOnClickListener {
            val text = binding.extractedText.text.toString()
            if (text.isNotBlank()) {
                val bundle = Bundle().apply { putString("tts_text", text) }
                findNavController().navigate(R.id.ttsFragment, bundle)
            }
        }

        // Clear
        binding.clearBtn.setOnClickListener {
            capturedPhotoFile = null
            binding.imagePreview.setImageDrawable(null)
            binding.extractedText.text?.clear()
            binding.readAloudBtn.isEnabled = false
            binding.pageInfo.visibility = View.GONE
            binding.statusText.text = getString(R.string.book_reader_hint)
        }

        // Observe state
        viewModel.state.observe(viewLifecycleOwner) { state ->
            binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
            binding.captureSpreadBtn.isEnabled = !state.isLoading
            binding.captureSingleBtn.isEnabled = !state.isLoading
            binding.browseBtn.isEnabled = !state.isLoading
            binding.statusText.text = state.status

            if (state.mergedText.isNotBlank()) {
                binding.extractedText.setText(state.mergedText)
                binding.readAloudBtn.isEnabled = true

                // Show page info
                if (state.pageCount > 0) {
                    binding.pageInfo.text = "${state.pageCount} page(s) • ${state.mergedText.length} characters"
                    binding.pageInfo.visibility = View.VISIBLE
                }
            }

            if (state.error != null) {
                Toast.makeText(context, state.error, Toast.LENGTH_LONG).show()
            }
        }
    }

    // ── Helpers ──────────────────────────────────────────────────

    private fun checkCameraAndLaunch() {
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) {
            launchCamera()
        } else {
            requestCameraPermission.launch(Manifest.permission.CAMERA)
        }
    }

    private fun launchCamera() {
        val photoFile = File(
            requireContext().cacheDir,
            "book_reader_${System.currentTimeMillis()}.jpg"
        )
        capturedPhotoFile = photoFile
        val uri = FileProvider.getUriForFile(
            requireContext(),
            "${requireContext().packageName}.fileprovider",
            photoFile
        )
        takePicture.launch(uri)
    }

    private fun processImage(imagePath: String) {
        if (isSinglePageMode) {
            viewModel.processSinglePage(imagePath)
        } else {
            viewModel.processBookSpread(imagePath)
        }
    }

    private fun showImagePreview(uri: Uri) {
        binding.imagePreview.setImageURI(uri)
    }

    private fun copyUriToCache(uri: Uri): File {
        val cacheFile = File(requireContext().cacheDir, "book_reader_input.jpg")
        requireContext().contentResolver.openInputStream(uri)?.use { input ->
            cacheFile.outputStream().use { output -> input.copyTo(output) }
        }
        return cacheFile
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
