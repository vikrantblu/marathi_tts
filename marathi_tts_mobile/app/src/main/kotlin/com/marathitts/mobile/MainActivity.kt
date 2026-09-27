package com.marathitts.mobile

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.os.bundleOf
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.NavigationUI
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.marathitts.mobile.databinding.ActivityMainBinding
import com.marathitts.mobile.ui.PlaybackViewModel

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    val playbackViewModel: PlaybackViewModel by viewModels()

    companion object {
        private const val TAG = "MainActivity"
        // Intent extras for headless automation
        const val EXTRA_NAVIGATE_TO   = "navigate_to"        // e.g. "testDashboard"
        const val EXTRA_AUTO_RUN      = "auto_run"           // boolean
        // Widget action (FEAT-77)
        const val ACTION_WIDGET_SPEAK = "com.marathitts.mobile.WIDGET_SPEAK"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Set up Toolbar as ActionBar
        setSupportActionBar(binding.toolbar)

        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHostFragment.navController

        // Three bottom tabs are top-level (no Up arrow)
        val appBarConfiguration = AppBarConfiguration(
            setOf(R.id.inputFragment, R.id.outputFragment, R.id.meFragment)
        )
        NavigationUI.setupActionBarWithNavController(this, navController, appBarConfiguration)

        // Wire BottomNavigationView to Navigation Component
        NavigationUI.setupWithNavController(binding.bottomNav, navController)

        // Hide bottom nav on child destinations, show on tabs
        navController.addOnDestinationChangedListener { _, destination, _ ->
            val isTopLevel = destination.id in setOf(
                R.id.inputFragment, R.id.outputFragment, R.id.meFragment
            )
            binding.bottomNav.visibility = if (isTopLevel) View.VISIBLE else View.VISIBLE
        }

        // ── Intent-driven automation (adb am start extras) ─────────────────
        handleLaunchIntent(navController)

        // ── Handle widget intents (FEAT-77) ────────────────────────────────
        handleWidgetIntent(navController)

        // ── Handle share intents (URLs and images from other apps) ──────────
        handleShareIntent(navController)

        // ── Mini-player wiring (FEAT-81) ───────────────────────────────────
        setupMiniPlayer()

        // ── Back-press dialog when audio is playing (FEAT-82) ──────────────
        setupBackNavDialog(navController)
    }

    override fun onSupportNavigateUp(): Boolean {
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        return navHostFragment.navController.navigateUp() || super.onSupportNavigateUp()
    }

    /** Switch to the Output tab programmatically (called from InputFragment on Generate). */
    fun selectOutputTab() {
        binding.bottomNav.selectedItemId = R.id.outputFragment
    }

    // ── Mini-player (FEAT-81) ──────────────────────────────────────────────

    private fun setupMiniPlayer() {
        val mp = binding.miniPlayer
        val miniCard = mp.miniPlayerCard
        val miniTitle = mp.miniPlayerTitle
        val miniBtnPlayPause = mp.miniBtnPlayPause
        val miniBtnStop = mp.miniBtnStop
        val miniIndicator = mp.miniPlayingIndicator

        playbackViewModel.playback.observe(this) { state ->
            val visible = state.isPlaying || state.isPaused
            miniCard.visibility = if (visible) View.VISIBLE else View.GONE

            if (visible) {
                val label = state.inputText.take(60).ifBlank { "Playing audio…" }
                miniTitle.text = label
                miniTitle.isSelected = true // enable marquee

                // Toggle play/pause icon
                miniBtnPlayPause.setIconResource(
                    if (state.isPlaying) android.R.drawable.ic_media_pause
                    else android.R.drawable.ic_media_play
                )

                // Pulsing indicator
                miniIndicator.alpha = if (state.isPlaying) 1f else 0.4f
            }
        }

        miniBtnPlayPause.setOnClickListener {
            val state = playbackViewModel.playback.value ?: return@setOnClickListener
            if (state.isPlaying) {
                playbackViewModel.pause()
            } else if (state.isPaused) {
                playbackViewModel.resume()
            }
        }

        miniBtnStop.setOnClickListener {
            playbackViewModel.stop()
        }
    }

    // ── Back-nav dialog (FEAT-82) ──────────────────────────────────────────

    private fun setupBackNavDialog(navController: androidx.navigation.NavController) {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (playbackViewModel.hasActivePlayback) {
                    MaterialAlertDialogBuilder(this@MainActivity)
                        .setTitle(getString(R.string.back_nav_dialog_title))
                        .setMessage(getString(R.string.back_nav_dialog_message))
                        .setPositiveButton(R.string.back_nav_stop_and_go) { _, _ ->
                            playbackViewModel.stop()
                            isEnabled = false
                            onBackPressedDispatcher.onBackPressed()
                            isEnabled = true
                        }
                        .setNeutralButton(R.string.back_nav_keep_playing) { _, _ ->
                            // Keep playing, just navigate back
                            isEnabled = false
                            onBackPressedDispatcher.onBackPressed()
                            isEnabled = true
                        }
                        .setNegativeButton(android.R.string.cancel, null)
                        .show()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                    isEnabled = true
                }
            }
        })
    }

    private fun handleLaunchIntent(navController: androidx.navigation.NavController) {
        val destination = intent?.getStringExtra(EXTRA_NAVIGATE_TO) ?: return
        val autoRun     = intent?.getBooleanExtra(EXTRA_AUTO_RUN, false) ?: false
        Log.i(TAG, "Launch intent: navigate_to=$destination  auto_run=$autoRun")
        when (destination) {
            "testDashboard" -> {
                // Navigate after views are fully laid out
                binding.root.post {
                    navController.navigate(
                        R.id.testDashboardFragment,
                        bundleOf("autoRun" to autoRun)
                    )
                }
            }
        }
    }

    /**
     * FEAT-77: Widget "Speak Clipboard" button reads clipboard text and
     * navigates to InputFragment with tts_text + auto_generate flag.
     */
    private fun handleWidgetIntent(navController: androidx.navigation.NavController) {
        if (intent?.action != ACTION_WIDGET_SPEAK) return
        Log.i(TAG, "Widget speak intent received")

        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clipText = clipboard.primaryClip
            ?.takeIf { it.itemCount > 0 }
            ?.getItemAt(0)
            ?.text
            ?.toString()
            ?.trim()

        if (clipText.isNullOrBlank()) {
            Toast.makeText(this, getString(R.string.widget_clipboard_empty), Toast.LENGTH_SHORT).show()
            return
        }

        binding.root.post {
            navController.navigate(
                R.id.inputFragment,
                bundleOf(
                    "tts_text" to clipText,
                    "auto_generate" to true
                )
            )
        }
    }

    private fun handleShareIntent(navController: androidx.navigation.NavController) {
        val action = intent?.action ?: return
        if (action != Intent.ACTION_SEND) return

        val mimeType = intent.type.orEmpty()
        Log.i(TAG, "Share intent: action=$action  type=$mimeType")

        binding.root.post {
            when {
                // Shared image → OCR screen
                mimeType.startsWith("image/") -> {
                    val imageUri = intent.getParcelableExtra<android.net.Uri>(Intent.EXTRA_STREAM)
                    if (imageUri != null) {
                        navController.navigate(
                            R.id.ocrFragment,
                            bundleOf("shared_image_uri" to imageUri.toString())
                        )
                    }
                }
                // Shared text/URL → Web Fetch screen
                mimeType == "text/plain" -> {
                    val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT).orEmpty()
                    if (sharedText.isNotBlank()) {
                        // If it looks like a URL, open web fetch; otherwise put in input
                        if (sharedText.startsWith("http://") || sharedText.startsWith("https://")) {
                            navController.navigate(
                                R.id.webFetchFragment,
                                bundleOf("shared_url" to sharedText)
                            )
                        } else {
                            navController.navigate(
                                R.id.inputFragment,
                                bundleOf("tts_text" to sharedText)
                            )
                        }
                    }
                }
            }
        }
    }
}
