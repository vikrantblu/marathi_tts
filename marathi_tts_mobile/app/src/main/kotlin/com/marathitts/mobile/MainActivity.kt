package com.marathitts.mobile

import android.os.Bundle
import androidx.appcompat.app.ActionBarDrawerToggle
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.NavigationUI
import com.marathitts.mobile.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

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
                R.id.sttFragment, R.id.modiFragment, R.id.stotraFragment
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
    }
}
