package com.marathitts.mobile.ui.stotra

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.marathitts.mobile.databinding.ItemStotraBinding
import com.marathitts.mobile.service.StotraRepository

class StotraAdapter(
    private val onClick: (StotraRepository.Stotra) -> Unit
) : ListAdapter<StotraRepository.Stotra, StotraAdapter.VH>(DIFF) {

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
            binding.root.setOnClickListener { onClick(stotra) }
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
