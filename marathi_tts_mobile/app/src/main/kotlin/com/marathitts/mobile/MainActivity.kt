package com.marathitts.mobile

import android.os.Bundle
import android.util.Log
import android.view.View
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
    }

    override fun onSupportNavigateUp(): Boolean {
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        return navHostFragment.navController.navigateUp() || super.onSupportNavigateUp()
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
