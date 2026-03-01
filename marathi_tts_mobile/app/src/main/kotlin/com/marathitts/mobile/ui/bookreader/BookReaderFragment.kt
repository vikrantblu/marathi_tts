package com.marathitts.mobile.ui.bookreader

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.text.Spannable
import android.text.SpannableString
import android.text.style.BackgroundColorSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.ImageView
import android.widget.SeekBar
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import com.marathitts.mobile.databinding.FragmentBookReaderBinding
import com.marathitts.mobile.service.TtsEngineManager
import java.io.File

class BookReaderFragment : Fragment() {

    private var _binding: FragmentBookReaderBinding? = null
    private val binding get() = _binding!!
    private val viewModel: BookReaderViewModel by viewModels()

    private var isSinglePageMode = false
    private var isAppendMode = false

    /** Prevent observer → spinner → ViewModel feedback loops. */
    private var spinnerUpdating = false

    /** Soft-yellow highlight for the current sentence. */
    private val highlightColor = 0xFFFFF176.toInt()

    /**
     * Receives ACTION_STOP_READING broadcast (fired by the notification's Stop button).
     * Routes to ViewModel and stops the foreground service.
     */
    private val stopReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            viewModel.stopReading()
            stopReaderService()
        }
    }

    // ── Activity Result contracts ────────────────────────────────

    /** Launches BookCameraActivity; receives back the deskewed image path. */
    private val launchBookCamera = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val imagePath = result.data
                ?.getStringExtra(BookCameraActivity.EXTRA_IMAGE_PATH)
                ?: return@registerForActivityResult
            // Sync single/spread mode from what was toggled inside the camera
            val spreadMode = result.data
                ?.getBooleanExtra(BookCameraActivity.EXTRA_SPREAD_MODE, !isSinglePageMode)
                ?: !isSinglePageMode
            isSinglePageMode = !spreadMode
            binding.imagePreview.setImageURI(Uri.fromFile(File(imagePath)))
            processImage(imagePath)
        }
    }

    private val pickImage = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let {
            val file = copyUriToCache(it)
            binding.imagePreview.setImageURI(it)
            processImage(file.absolutePath)
        }
    }

    private val requestCameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) launchCamera()
        else Toast.makeText(context, "Camera permission is required", Toast.LENGTH_SHORT).show()
    }

    // ── Lifecycle ────────────────────────────────────────────────

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, s: Bundle?): View {
        _binding = FragmentBookReaderBinding.inflate(inflater, container, false)
        // Register here (not onStart) so it survives screen-off while service is running
        val filter = IntentFilter(BookReaderForegroundService.ACTION_STOP_READING)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requireContext().registerReceiver(stopReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            requireContext().registerReceiver(stopReceiver, filter)
        }
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // ── Capture buttons ──────────────────────────────────────

        binding.captureSpreadBtn.setOnClickListener {
            isSinglePageMode = false; isAppendMode = false
            checkCameraAndLaunch()
        }

        binding.captureSingleBtn.setOnClickListener {
            isSinglePageMode = true; isAppendMode = false
            checkCameraAndLaunch()
        }

        binding.browseBtn.setOnClickListener {
            isAppendMode = false
            pickImage.launch("image/*")
        }

        // Next Page: capture another page and append text
        binding.nextPageBtn.setOnClickListener {
            isAppendMode = true
            checkCameraAndLaunch()
        }

        // ── Font controls ────────────────────────────────────────

        binding.fontDecreaseBtn.setOnClickListener {
            val current = viewModel.state.value?.fontSize ?: 18f
            viewModel.setFontSize(current - 2f)
        }

        binding.fontIncreaseBtn.setOnClickListener {
            val current = viewModel.state.value?.fontSize ?: 18f
            viewModel.setFontSize(current + 2f)
        }

        // ── Collapsible image (tap card to toggle) ───────────────

        binding.imageCard.setOnClickListener {
            viewModel.toggleImage()
        }

        // ── Inline player controls ───────────────────────────────

        binding.playPauseBtn.setOnClickListener {
            val state = viewModel.state.value ?: return@setOnClickListener
            when {
                !state.isReading -> viewModel.startReading()
                state.isPaused   -> viewModel.resumeReading()
                else             -> viewModel.pauseReading()
            }
        }

        binding.prevSentenceBtn.setOnClickListener {
            viewModel.prevSentence()
        }

        binding.nextSentenceBtn.setOnClickListener {
            viewModel.nextSentence()
        }

        binding.stopReadingBtn.setOnClickListener {
            viewModel.stopReading()
            stopReaderService()
        }

        // ── Clear ────────────────────────────────────────────────

        binding.clearBtn.setOnClickListener {
            viewModel.clearAll()
            binding.imagePreview.setImageDrawable(null)
            binding.emptyStateOverlay.visibility = View.VISIBLE
            stopReaderService()
        }

        // ── View Photo ───────────────────────────────────────────

        binding.viewPhotoBtn.setOnClickListener {
            val path = viewModel.state.value?.lastCapturedImagePath ?: return@setOnClickListener
            showPhotoDialog(path)
        }

        // ── TTS Settings ─────────────────────────────────────────

        binding.ttsSettingsToggleBtn.setOnClickListener {
            viewModel.toggleTtsSettings()
        }

        // Engine spinner
        val engineAdapter = ArrayAdapter(
            requireContext(),
            android.R.layout.simple_spinner_item,
            TtsEngineManager.ENGINE_NAMES
        ).also { it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
        binding.ttsEngineSpinner.adapter = engineAdapter
        binding.ttsEngineSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, pos: Int, id: Long) {
                if (!spinnerUpdating) viewModel.setTtsEngine(pos)
            }
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }

        // Speed seekbar
        binding.ttsSpeedBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(bar: SeekBar, progress: Int, fromUser: Boolean) {
                val value = 0.5f + progress * 0.1f
                binding.ttsSpeedLabel.text = "%.1f×".format(value)
                if (fromUser) viewModel.setTtsSpeed(value)
            }
            override fun onStartTrackingTouch(bar: SeekBar) = Unit
            override fun onStopTrackingTouch(bar: SeekBar) = Unit
        })

        // Pitch seekbar
        binding.ttsPitchBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(bar: SeekBar, progress: Int, fromUser: Boolean) {
                val value = 0.5f + progress * 0.1f
                binding.ttsPitchLabel.text = "%.1f×".format(value)
                if (fromUser) viewModel.setTtsPitch(value)
            }
            override fun onStartTrackingTouch(bar: SeekBar) = Unit
            override fun onStopTrackingTouch(bar: SeekBar) = Unit
        })

        // ── Observe state ────────────────────────────────────────

        viewModel.state.observe(viewLifecycleOwner) { state ->
            // Loading indicator
            binding.progressBar.visibility =
                if (state.isProcessing || state.isGeneratingAudio) View.VISIBLE else View.GONE

            // Collapsible image
            binding.imageCard.visibility =
                if (state.imageExpanded) View.VISIBLE else View.GONE

            // Button states
            binding.captureSpreadBtn.isEnabled = !state.isProcessing
            binding.captureSingleBtn.isEnabled = !state.isProcessing
            binding.browseBtn.isEnabled = !state.isProcessing
            val hasText = state.mergedText.isNotBlank()
            binding.nextPageBtn.isEnabled = hasText && !state.isProcessing
            binding.playerBar.visibility = if (hasText) View.VISIBLE else View.GONE

            // Play / Pause button label
            binding.playPauseBtn.text = when {
                !state.isReading -> "Read Aloud"
                state.isPaused  -> "Resume"
                else            -> "Pause"
            }

            // Text display with sentence highlighting
            updateTextDisplay(state)

            // Font size
            binding.readingText.textSize = state.fontSize
            binding.fontSizeLabel.text = state.fontSize.toInt().toString()

            // Foreground service lifecycle: start when reading, stop when done
            when {
                state.isReading && !state.isProcessing -> {
                    val sentenceText = if (state.currentSentenceIndex >= 0
                            && state.currentSentenceIndex < state.sentences.size)
                        state.sentences[state.currentSentenceIndex].text else ""
                    startOrUpdateReaderService(
                        status = state.status,
                        sentence = sentenceText
                    )
                }
                !state.isReading -> stopReaderService()
            }

            // Sentence progress
            if (state.isReading && state.currentSentenceIndex >= 0) {
                binding.sentenceProgress.text =
                    "Sentence ${state.currentSentenceIndex + 1} / ${state.sentences.size}"
                binding.sentenceProgress.visibility = View.VISIBLE
            } else {
                binding.sentenceProgress.visibility = View.GONE
            }

            // Status
            binding.statusText.text = state.status

            // View Photo button
            binding.viewPhotoBtn.visibility =
                if (state.lastCapturedImagePath != null) View.VISIBLE else View.GONE

            // Empty state overlay
            binding.emptyStateOverlay.visibility =
                if (state.lastCapturedImagePath != null) View.GONE else View.VISIBLE

            // TTS settings panel
            binding.ttsSettingsCard.visibility =
                if (state.ttsSettingsExpanded) View.VISIBLE else View.GONE

            // Sync engine spinner (guard against feedback loop)
            if (binding.ttsEngineSpinner.selectedItemPosition != state.ttsEngine) {
                spinnerUpdating = true
                binding.ttsEngineSpinner.setSelection(state.ttsEngine)
                spinnerUpdating = false
            }

            // Sync speed seekbar
            val speedProgress = ((state.ttsSpeed - 0.5f) / 0.1f).toInt().coerceIn(0, 15)
            if (binding.ttsSpeedBar.progress != speedProgress) {
                binding.ttsSpeedBar.progress = speedProgress
            }
            binding.ttsSpeedLabel.text = "%.1f×".format(state.ttsSpeed)

            // Sync pitch seekbar
            val pitchProgress = ((state.ttsPitch - 0.5f) / 0.1f).toInt().coerceIn(0, 15)
            if (binding.ttsPitchBar.progress != pitchProgress) {
                binding.ttsPitchBar.progress = pitchProgress
            }
            binding.ttsPitchLabel.text = "%.1f×".format(state.ttsPitch)

            // Error toast
            state.error?.let { msg ->
                Toast.makeText(context, msg, Toast.LENGTH_LONG).show()
            }
        }
    }

    // ── Foreground service helpers ────────────────────────────────

    private fun startOrUpdateReaderService(status: String, sentence: String) {
        val intent = Intent(requireContext(), BookReaderForegroundService::class.java).apply {
            putExtra(BookReaderForegroundService.EXTRA_STATUS, status)
            putExtra(BookReaderForegroundService.EXTRA_SENTENCE, sentence)
        }
        ContextCompat.startForegroundService(requireContext(), intent)
    }

    private fun stopReaderService() {
        requireContext().stopService(
            Intent(requireContext(), BookReaderForegroundService::class.java)
        )
    }

    // ── Text highlighting ────────────────────────────────────────

    private fun updateTextDisplay(state: BookReaderState) {
        val text = state.mergedText
        if (text.isBlank()) {
            binding.readingText.text = ""
            return
        }

        if (state.isReading && state.currentSentenceIndex >= 0
            && state.currentSentenceIndex < state.sentences.size
        ) {
            val range = state.sentences[state.currentSentenceIndex]
            val spannable = SpannableString(text)
            val safeStart = range.start.coerceIn(0, text.length)
            val safeEnd = range.end.coerceIn(0, text.length)

            spannable.setSpan(
                BackgroundColorSpan(highlightColor),
                safeStart, safeEnd,
                Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            binding.readingText.text = spannable

            // Auto-scroll so highlighted sentence is visible (~upper third)
            binding.readingText.post {
                val layout = binding.readingText.layout ?: return@post
                val line = layout.getLineForOffset(safeStart)
                val lineTop = layout.getLineTop(line)
                val targetY = lineTop - binding.readingScroll.height / 3
                binding.readingScroll.smoothScrollTo(0, targetY.coerceAtLeast(0))
            }
        } else {
            binding.readingText.text = text
        }
    }

    // ── Camera / Image helpers ───────────────────────────────────

    /**
     * Show a fullscreen dialog with the last captured / processed photo.
     * Buttons: Re-scan (opens camera again) and Re-read (re-runs OCR on same image).
     */
    private fun showPhotoDialog(imagePath: String) {
        val file = File(imagePath)
        if (!file.exists()) {
            Toast.makeText(context, "Image file not found", Toast.LENGTH_SHORT).show()
            return
        }

        val imageView = ImageView(requireContext()).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            scaleType = ImageView.ScaleType.FIT_CENTER
            setImageURI(Uri.fromFile(file))
            setPadding(8, 8, 8, 8)
        }

        AlertDialog.Builder(requireContext())
            .setTitle("Captured Photo")
            .setView(imageView)
            .setPositiveButton("Re-scan") { _, _ ->
                isAppendMode = false
                checkCameraAndLaunch()
            }
            .setNeutralButton("Re-read") { _, _ ->
                viewModel.stopReading()
                stopReaderService()
                viewModel.reprocessLastImage(singlePage = isSinglePageMode)
            }
            .setNegativeButton("Close", null)
            .show()
    }

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
        val intent = Intent(requireContext(), BookCameraActivity::class.java).apply {
            putExtra(BookCameraActivity.EXTRA_SPREAD_MODE, !isSinglePageMode)
        }
        launchBookCamera.launch(intent)
    }

    private fun processImage(imagePath: String) {
        // Stop any ongoing reading session before processing new image
        stopReaderService()
        val append = isAppendMode
        isAppendMode = false

        if (isSinglePageMode) {
            viewModel.processSinglePage(imagePath, append)
        } else {
            viewModel.processBookSpread(imagePath, append)
        }
    }

    private fun copyUriToCache(uri: Uri): File {
        val cacheFile = File(requireContext().cacheDir, "book_reader_input.jpg")
        requireContext().contentResolver.openInputStream(uri)?.use { input ->
            cacheFile.outputStream().use { output -> input.copyTo(output) }
        }
        return cacheFile
    }

    override fun onDestroyView() {
        try { requireContext().unregisterReceiver(stopReceiver) } catch (_: Exception) {}
        super.onDestroyView()
        _binding = null
    }
}
