package com.marathitts.mobile

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.ActionBarDrawerToggle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.os.bundleOf
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.NavigationUI
import com.marathitts.mobile.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    companion object {
        private const val TAG = "MainActivity"
        // Intent extras for headless automation
        const val EXTRA_NAVIGATE_TO   = "navigate_to"        // e.g. "testDashboard"
        const val EXTRA_AUTO_RUN      = "auto_run"           // boolean
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

        // Register ALL fragments as top-level destinations so drawer opens from each
        val appBarConfiguration = AppBarConfiguration(
            setOf(
                R.id.ttsFragment, R.id.emotionFragment, R.id.ocrFragment,
                R.id.correctionFragment, R.id.pdfFragment, R.id.webFetchFragment,
                R.id.sttFragment, R.id.modiFragment, R.id.stotraFragment,
                R.id.bookReaderFragment, R.id.testDashboardFragment
            ),
            binding.drawerLayout
        )
        NavigationUI.setupActionBarWithNavController(this, navController, appBarConfiguration)

        // Drawer toggle (hamburger icon)
        val toggle = ActionBarDrawerToggle(
            this,
            binding.drawerLayout,
            binding.toolbar,
            R.string.navigation_drawer_open,
            R.string.navigation_drawer_close
        )
        binding.drawerLayout.addDrawerListener(toggle)
        toggle.syncState()

        // Wire NavigationView items to Navigation Component
        NavigationUI.setupWithNavController(binding.navView, navController)

        // ── Intent-driven automation (adb am start extras) ─────────────────
        handleLaunchIntent(navController)
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
}
