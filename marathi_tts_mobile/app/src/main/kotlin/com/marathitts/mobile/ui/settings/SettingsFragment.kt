package com.marathitts.mobile.ui.settings

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.marathitts.mobile.BuildConfig
import com.marathitts.mobile.R
import com.marathitts.mobile.data.AppDatabase
import com.marathitts.mobile.databinding.FragmentSettingsBinding
import com.marathitts.mobile.util.AppPreferences
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.io.File

class SettingsFragment : Fragment() {

    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!
    private val ioScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        val ctx = requireContext()

        // ── Theme mode ───────────────────────────────────────────────────
        val themeOptions = arrayOf("System default", "Light", "Dark")
        val themeValues = arrayOf("system", "light", "dark")
        val currentTheme = AppPreferences.getThemeModeString(ctx)
        val themeIndex = themeValues.indexOf(currentTheme).coerceAtLeast(0)

        binding.themeSpinner.adapter = ArrayAdapter(ctx,
            android.R.layout.simple_spinner_dropdown_item, themeOptions)
        binding.themeSpinner.setSelection(themeIndex)
        binding.themeSpinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, v: View?, pos: Int, id: Long) {
                val selected = themeValues[pos]
                if (selected != AppPreferences.getThemeModeString(ctx)) {
                    AppPreferences.setThemeMode(ctx, selected)
                }
            }
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
        }

        // ── Default TTS engine ───────────────────────────────────────────
        val engineOptions = arrayOf("Auto (best available)", "Edge-TTS (neural)", "gTTS (Google)", "Native Android TTS")
        val engineValues = arrayOf("auto", "edge-tts", "gtts", "native")
        val currentEngine = AppPreferences.getDefaultEngine(ctx)
        val engineIndex = engineValues.indexOf(currentEngine).coerceAtLeast(0)

        binding.engineSpinner.adapter = ArrayAdapter(ctx,
            android.R.layout.simple_spinner_dropdown_item, engineOptions)
        binding.engineSpinner.setSelection(engineIndex)
        binding.engineSpinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: android.widget.AdapterView<*>?, v: View?, pos: Int, id: Long) {
                AppPreferences.setDefaultEngine(ctx, engineValues[pos])
            }
            override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
        }

        // ── Default speed / pitch / volume sliders ──────────────────────
        binding.speedSlider.value = AppPreferences.getDefaultSpeed(ctx)
        binding.pitchSlider.value = AppPreferences.getDefaultPitch(ctx)
        binding.volumeSlider.value = AppPreferences.getDefaultVolume(ctx)

        binding.speedSlider.addOnChangeListener { _, value, fromUser ->
            if (fromUser) {
                AppPreferences.setDefaultSpeed(ctx, value)
                binding.speedValue.text = String.format("%.2f×", value)
            }
        }
        binding.pitchSlider.addOnChangeListener { _, value, fromUser ->
            if (fromUser) {
                AppPreferences.setDefaultPitch(ctx, value)
                binding.pitchValue.text = String.format("%.2f×", value)
            }
        }
        binding.volumeSlider.addOnChangeListener { _, value, fromUser ->
            if (fromUser) {
                AppPreferences.setDefaultVolume(ctx, value)
                binding.volumeValue.text = String.format("%.0f%%", value * 100)
            }
        }

        // Set initial display values
        binding.speedValue.text = String.format("%.2f×", binding.speedSlider.value)
        binding.pitchValue.text = String.format("%.2f×", binding.pitchSlider.value)
        binding.volumeValue.text = String.format("%.0f%%", binding.volumeSlider.value * 100)

        // ── Clear history ────────────────────────────────────────────────
        binding.clearHistoryBtn.setOnClickListener {
            AlertDialog.Builder(ctx)
                .setTitle("Clear History")
                .setMessage("Delete all generation history entries? This cannot be undone.")
                .setPositiveButton("Clear") { _, _ ->
                    ioScope.launch {
                        AppDatabase.getInstance(ctx).historyDao().deleteAll()
                    }
                    Toast.makeText(ctx, "History cleared", Toast.LENGTH_SHORT).show()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }

        // ── Clear cache ──────────────────────────────────────────────────
        binding.clearCacheBtn.setOnClickListener {
            AlertDialog.Builder(ctx)
                .setTitle("Clear Cache")
                .setMessage("Delete cached audio and temp files?")
                .setPositiveButton("Clear") { _, _ ->
                    ioScope.launch {
                        clearCacheFiles(ctx)
                    }
                    Toast.makeText(ctx, "Cache cleared", Toast.LENGTH_SHORT).show()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }

        // ── Reset defaults ───────────────────────────────────────────────
        binding.resetDefaultsBtn.setOnClickListener {
            AlertDialog.Builder(ctx)
                .setTitle("Reset to Defaults")
                .setMessage("Reset all settings to factory defaults?")
                .setPositiveButton("Reset") { _, _ ->
                    AppPreferences.clearAllPrefs(ctx)
                    // Refresh UI
                    binding.themeSpinner.setSelection(0)
                    binding.engineSpinner.setSelection(0)
                    binding.speedSlider.value = 1.0f
                    binding.pitchSlider.value = 1.0f
                    binding.volumeSlider.value = 1.0f
                    binding.speedValue.text = "1.00×"
                    binding.pitchValue.text = "1.00×"
                    binding.volumeValue.text = "100%"
                    AppPreferences.setThemeMode(ctx, "system")
                    Toast.makeText(ctx, "Settings reset", Toast.LENGTH_SHORT).show()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }

        // ── About section ────────────────────────────────────────────────
        binding.versionText.text = "Version ${BuildConfig.VERSION_NAME} (build ${BuildConfig.VERSION_CODE})"

        // ── Developer mode ───────────────────────────────────────────────
        binding.devModeSwitch.isChecked = AppPreferences.isDevModeEnabled(ctx)
        binding.devModeSwitch.setOnCheckedChangeListener { _, isChecked ->
            AppPreferences.setDevMode(ctx, isChecked)
        }
    }

    private fun clearCacheFiles(ctx: android.content.Context) {
        // Clear app cache dir
        ctx.cacheDir.listFiles()?.forEach { file ->
            if (file.isFile) file.delete()
        }
        // Clear generated TTS audio output
        val outputDir = File(ctx.filesDir, "output")
        if (outputDir.exists()) {
            outputDir.listFiles()?.forEach { file ->
                if (file.isFile) file.delete()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
