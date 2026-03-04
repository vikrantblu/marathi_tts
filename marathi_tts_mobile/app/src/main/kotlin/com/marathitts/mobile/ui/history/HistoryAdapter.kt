package com.marathitts.mobile.ui.history

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.marathitts.mobile.R
import com.marathitts.mobile.data.HistoryEntry
import java.text.SimpleDateFormat
import java.util.*

class HistoryAdapter(
    private val onTap: (HistoryEntry) -> Unit,
    private val onDelete: (HistoryEntry) -> Unit
) : ListAdapter<HistoryEntry, HistoryAdapter.VH>(DIFF) {

    companion object {
        private val DATE_FMT = SimpleDateFormat("dd MMM, HH:mm", Locale.getDefault())

        private val CATEGORY_ICONS = mapOf(
            "TTS" to "🔊",
            "STT" to "🎙️",
            "OCR" to "📷",
            "PDF" to "📄",
            "WEB" to "🌐",
            "CORRECTION" to "✏️",
            "MODI" to "𑘦",
            "EMOTION" to "😊",
            "STOTRA" to "🙏",
            "BOOK_READER" to "📖"
        )

        private val DIFF = object : DiffUtil.ItemCallback<HistoryEntry>() {
            override fun areItemsTheSame(a: HistoryEntry, b: HistoryEntry) = a.id == b.id
            override fun areContentsTheSame(a: HistoryEntry, b: HistoryEntry) = a == b
        }
    }

    inner class VH(view: View) : RecyclerView.ViewHolder(view) {
        private val categoryIcon: TextView = view.findViewById(R.id.category_icon)
        private val categoryBadge: TextView = view.findViewById(R.id.category_badge)
        private val timestamp: TextView = view.findViewById(R.id.timestamp)
        private val previewText: TextView = view.findViewById(R.id.preview_text)
        private val engineText: TextView = view.findViewById(R.id.engine_text)
        private val deleteBtn: ImageButton = view.findViewById(R.id.delete_btn)

        fun bind(entry: HistoryEntry) {
            categoryIcon.text = CATEGORY_ICONS[entry.category] ?: "📝"
            categoryBadge.text = entry.category
            timestamp.text = DATE_FMT.format(Date(entry.timestamp))

            // Show output text preview (first 120 chars)
            val preview = entry.outputText.take(120).replace("\n", " ")
            previewText.text = if (entry.outputText.length > 120) "$preview…" else preview

            engineText.text = entry.engine ?: ""
            engineText.visibility = if (entry.engine.isNullOrEmpty()) View.GONE else View.VISIBLE

            itemView.setOnClickListener { onTap(entry) }
            deleteBtn.setOnClickListener { onDelete(entry) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_history, parent, false)
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        holder.bind(getItem(position))
    }
}
