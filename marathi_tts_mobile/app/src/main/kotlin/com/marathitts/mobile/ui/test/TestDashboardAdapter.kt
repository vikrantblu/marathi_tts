package com.marathitts.mobile.ui.test

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.marathitts.mobile.R

// Two view types: section header chip, individual test result row
private const val TYPE_HEADER = 0
private const val TYPE_ROW    = 1

/** Sealed union presented to the RecyclerView adapter. */
sealed class TestRow {
    data class Header(val group: TestGroup) : TestRow()
    data class Row(val result: TestResult)  : TestRow()
}

class TestDashboardAdapter(
    private val onPlayClicked: (TestResult) -> Unit
) : ListAdapter<TestRow, RecyclerView.ViewHolder>(DIFF) {

    // ── Diff ──────────────────────────────────────────────────────────────────
    companion object {
        val DIFF = object : DiffUtil.ItemCallback<TestRow>() {
            override fun areItemsTheSame(a: TestRow, b: TestRow): Boolean = when {
                a is TestRow.Header && b is TestRow.Header -> a.group == b.group
                a is TestRow.Row    && b is TestRow.Row    -> a.result.testCase.id == b.result.testCase.id
                else -> false
            }
            override fun areContentsTheSame(a: TestRow, b: TestRow) = a == b
        }
    }

    // ── ViewHolder — header ───────────────────────────────────────────────────
    inner class HeaderVH(v: View) : RecyclerView.ViewHolder(v) {
        private val chip: TextView = v.findViewById(R.id.group_chip)

        fun bind(h: TestRow.Header) {
            chip.text = h.group.label
            chip.backgroundTintList =
                android.content.res.ColorStateList.valueOf(h.group.color)
        }
    }

    // ── ViewHolder — test row ─────────────────────────────────────────────────
    inner class RowVH(v: View) : RecyclerView.ViewHolder(v) {
        private val dot      : View     = v.findViewById(R.id.status_dot)
        private val title    : TextView = v.findViewById(R.id.test_name)
        private val detail   : TextView = v.findViewById(R.id.result_message)
        private val elapsed  : TextView = v.findViewById(R.id.duration_text)
        private val playBtn  : View     = v.findViewById(R.id.play_btn)

        fun bind(row: TestRow.Row) {
            val r = row.result
            val tc = r.testCase

            title.text = "[${tc.id}] ${tc.name}"

            // Status dot colour
            val dotColor = when (r.status) {
                TestStatus.IDLE    -> Color.parseColor("#BDBDBD")  // grey
                TestStatus.RUNNING -> Color.parseColor("#1976D2")  // blue
                TestStatus.PASS    -> Color.parseColor("#388E3C")  // green
                TestStatus.FAIL    -> Color.parseColor("#D32F2F")  // red
            }
            dot.background.setTint(dotColor)

            // Detail — show description when IDLE, result msg otherwise
            detail.text = when {
                r.status == TestStatus.IDLE   -> tc.description
                r.message.isNotBlank()        -> r.message
                else                          -> tc.description
            }
            detail.visibility = View.VISIBLE
            // Also update the description field if it exists
            itemView.findViewById<TextView?>(R.id.test_description)?.text = tc.description

            // Elapsed
            elapsed.text = when {
                r.status == TestStatus.IDLE    -> ""
                r.status == TestStatus.RUNNING -> "…"
                else                           -> "${r.durationMs} ms"
            }
            elapsed.visibility = if (r.status == TestStatus.IDLE) View.GONE else View.VISIBLE

            // Play button — only when we have audio and test passed
            val hasAudio = r.audioPath != null && r.status == TestStatus.PASS
            (playBtn as? com.google.android.material.button.MaterialButton)?.visibility =
                if (hasAudio) View.VISIBLE else View.GONE
            if (hasAudio) {
                playBtn.setOnClickListener { onPlayClicked(r) }
            }
        }
    }

    // ── Inflate ───────────────────────────────────────────────────────────────
    override fun getItemViewType(position: Int) = when (getItem(position)) {
        is TestRow.Header -> TYPE_HEADER
        is TestRow.Row    -> TYPE_ROW
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return if (viewType == TYPE_HEADER) {
            HeaderVH(inflater.inflate(R.layout.item_test_group_header, parent, false))
        } else {
            RowVH(inflater.inflate(R.layout.item_test_row, parent, false))
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        when (val item = getItem(position)) {
            is TestRow.Header -> (holder as HeaderVH).bind(item)
            is TestRow.Row    -> (holder as RowVH).bind(item)
        }
    }

    // ── Helper: build flat list from grouped results ───────────────────────────
    fun buildRows(results: List<TestResult>): List<TestRow> {
        val rows = mutableListOf<TestRow>()
        TestGroup.values().forEach { group ->
            val groupResults = results.filter { it.testCase.group == group }
            if (groupResults.isNotEmpty()) {
                rows += TestRow.Header(group)
                rows += groupResults.map { TestRow.Row(it) }
            }
        }
        return rows
    }
}
