package com.marathitts.mobile.ui.test

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.recyclerview.widget.LinearLayoutManager
import com.marathitts.mobile.databinding.FragmentTestDashboardBinding
import com.marathitts.mobile.service.AudioPlayerService

class TestDashboardFragment : Fragment() {

    companion object {
        private const val TAG = "TestDashboard"
    }

    private var _binding: FragmentTestDashboardBinding? = null
    private val binding get() = _binding!!

    private val viewModel: TestDashboardViewModel by viewModels()
    private lateinit var adapter: TestDashboardAdapter

    private val audioPlayer = AudioPlayerService()

    // Active filter: null = All
    private var activeGroup: TestGroup? = null

    // ─────────────────────────────────────────────────────────────────────────
    // Lifecycle
    // ─────────────────────────────────────────────────────────────────────────

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentTestDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        setupRecyclerView()
        setupButtons()
        setupFilterChips()
        observeViewModel()
        Log.i(TAG, "Test Dashboard ready — ${viewModel.allTestCases.size} tests registered.")
        // Auto-run when launched via ADB intent (no manual tap required)
        if (arguments?.getBoolean("autoRun", false) == true) {
            Log.i(TAG, "autoRun=true detected \u2014 starting test suite automatically")
            binding.root.post { viewModel.runAll() }
        }    }

    override fun onDestroyView() {
        super.onDestroyView()
        audioPlayer.stop()
        _binding = null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Setup
    // ─────────────────────────────────────────────────────────────────────────

    private fun setupRecyclerView() {
        adapter = TestDashboardAdapter(onPlayClicked = { result ->
            result.audioPath?.let { path ->
                Log.i(TAG, "Playing audio: $path")
                audioPlayer.playAsync(
                    filePath   = path,
                    onComplete = { Log.i(TAG, "Playback finished.") }
                )
            }
        })
        binding.testList.apply {
            layoutManager = LinearLayoutManager(context)
            adapter = this@TestDashboardFragment.adapter
            setHasFixedSize(false)
        }
    }

    private fun setupButtons() {
        binding.runAllBtn.setOnClickListener {
            Log.i(TAG, "Starting full test run (${viewModel.allTestCases.size} tests)…")
            viewModel.runAll()
        }
        binding.stopBtn.setOnClickListener {
            viewModel.stopAll()
            Log.i(TAG, "Run cancelled by user.")
        }
        binding.clearBtn.setOnClickListener {
            viewModel.clearAll()
            Log.i(TAG, "Cleared. Ready.")
        }
    }

    private fun setupFilterChips() {
        binding.chipAll.setOnCheckedChangeListener    { _, c -> if (c) setFilter(null) }
        binding.chipTts.setOnCheckedChangeListener    { _, c -> if (c) setFilter(TestGroup.TTS) }
        binding.chipInput.setOnCheckedChangeListener  { _, c -> if (c) setFilter(TestGroup.INPUT) }
        binding.chipNlp.setOnCheckedChangeListener    { _, c -> if (c) setFilter(TestGroup.NLP) }
        binding.chipVoice.setOnCheckedChangeListener  { _, c -> if (c) setFilter(TestGroup.VOICE) }
        binding.chipStotra.setOnCheckedChangeListener { _, c -> if (c) setFilter(TestGroup.STOTRA) }
    }

    private fun setFilter(group: TestGroup?) {
        activeGroup = group
        viewModel.results.value?.let { submitFilteredRows(it) }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Observers
    // ─────────────────────────────────────────────────────────────────────────

    private fun observeViewModel() {
        viewModel.results.observe(viewLifecycleOwner) { results ->
            submitFilteredRows(results)

            val pass    = results.count { it.status == TestStatus.PASS }
            val fail    = results.count { it.status == TestStatus.FAIL }
            val running = results.count { it.status == TestStatus.RUNNING }

            binding.countTotal.text   = results.size.toString()
            binding.countPass.text    = pass.toString()
            binding.countFail.text    = fail.toString()
            binding.countRunning.text = running.toString()
        }

        viewModel.isRunningAll.observe(viewLifecycleOwner) { running ->
            binding.runAllBtn.isEnabled = !running
            binding.stopBtn.isEnabled   = running
            binding.clearBtn.isEnabled  = !running
        }
    }

    private fun submitFilteredRows(results: List<TestResult>) {
        val filtered = if (activeGroup == null) results
                       else results.filter { it.testCase.group == activeGroup }
        adapter.submitList(adapter.buildRows(filtered))
    }
}
