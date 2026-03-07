package com.marathitts.mobile.ui.stotra

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.marathitts.mobile.databinding.ItemStotraBinding
import com.marathitts.mobile.service.StotraRepository

class StotraAdapter(
    private val onClick: (StotraRepository.Stotra) -> Unit,
    private val onLongClick: ((StotraRepository.Stotra) -> Unit)? = null
) : ListAdapter<StotraRepository.Stotra, StotraAdapter.VH>(DIFF) {

    /** IDs of stotras selected for playlist (empty = not in playlist mode). */
    var playlistSelection: Set<String> = emptySet()
        set(value) { field = value; notifyDataSetChanged() }

    /** Whether playlist mode is active (shows checkboxes). */
    var isPlaylistMode: Boolean = false
        set(value) { field = value; notifyDataSetChanged() }

    companion object {
        private val LANG_LABELS = mapOf(
            "sa" to "संस्कृत",
            "hi" to "हिंदी",
            "mr" to "मराठी"
        )
        private val CATEGORY_LABELS = mapOf(
            "stotra" to "स्तोत्र",
            "chalisa" to "चालीसा",
            "sahasranama" to "सहस्रनाम",
            "ashtakam" to "अष्टक",
            "kavach" to "कवच",
            "gita" to "गीता",
            "pothi" to "पोथी",
            "shloka" to "श्लोक"
        )

        private val DIFF = object : DiffUtil.ItemCallback<StotraRepository.Stotra>() {
            override fun areItemsTheSame(a: StotraRepository.Stotra, b: StotraRepository.Stotra) =
                a.id == b.id
            override fun areContentsTheSame(a: StotraRepository.Stotra, b: StotraRepository.Stotra) =
                a == b
        }
    }

    inner class VH(private val binding: ItemStotraBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(stotra: StotraRepository.Stotra) {
            binding.stotraTitle.text = stotra.title
            binding.stotraTitleEn.text = stotra.titleEn
            binding.deityChip.text = stotra.deity
            binding.langChip.text = LANG_LABELS[stotra.language] ?: stotra.language
            binding.categoryChip.text = CATEGORY_LABELS[stotra.category] ?: stotra.category
            binding.verseCount.text = "${stotra.verseCount} verses"

            // Playlist mode: show check indicator
            val isSelected = stotra.id in playlistSelection
            binding.playlistCheck.visibility = if (isPlaylistMode) View.VISIBLE else View.GONE
            binding.playlistCheck.text = if (isSelected) "✓" else ""
            binding.root.isChecked = isPlaylistMode && isSelected

            binding.root.setOnClickListener { onClick(stotra) }
            binding.root.setOnLongClickListener {
                onLongClick?.invoke(stotra)
                onLongClick != null
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemStotraBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        holder.bind(getItem(position))
    }
}
