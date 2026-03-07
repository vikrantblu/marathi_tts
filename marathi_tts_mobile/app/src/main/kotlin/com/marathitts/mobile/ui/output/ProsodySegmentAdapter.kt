package com.marathitts.mobile.ui.output

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.marathitts.mobile.R

/**
 * RecyclerView adapter for FEAT-51 prosody preview segments.
 * Each item shows the segment text, verse/prose badge, metre, pause, and rate.
 * Tap triggers FEAT-52 per-sentence regeneration via [onSegmentClick].
 * Long-press triggers FEAT-55 phonetic explainer via [onSegmentLongClick].
 */
class ProsodySegmentAdapter(
    private val onSegmentClick: (ProsodySegment) -> Unit,
    private val onSegmentLongClick: ((ProsodySegment) -> Unit)? = null
) : ListAdapter<ProsodySegment, ProsodySegmentAdapter.ViewHolder>(DIFF) {

    var regeneratingIndex: Int = -1
        set(value) {
            val old = field
            field = value
            if (old >= 0 && old < itemCount) notifyItemChanged(old)
            if (value >= 0 && value < itemCount) notifyItemChanged(value)
        }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_prosody_segment, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val segment = getItem(position)
        holder.bind(segment, regeneratingIndex == position, onSegmentClick, onSegmentLongClick)
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val txtText: TextView = view.findViewById(R.id.txt_segment_text)
        private val badgeType: TextView = view.findViewById(R.id.badge_type)
        private val txtMetre: TextView = view.findViewById(R.id.txt_metre)
        private val txtPause: TextView = view.findViewById(R.id.txt_pause)
        private val txtRate: TextView = view.findViewById(R.id.txt_rate)
        private val regenProgress: LinearProgressIndicator = view.findViewById(R.id.regen_progress)

        fun bind(
            segment: ProsodySegment,
            isRegenerating: Boolean,
            onClick: (ProsodySegment) -> Unit,
            onLongClick: ((ProsodySegment) -> Unit)? = null
        ) {
            val ctx = itemView.context
            txtText.text = segment.text

            // Verse/Prose badge
            if (segment.isVerse) {
                badgeType.text = ctx.getString(R.string.prosody_verse_badge)
            } else {
                badgeType.text = ctx.getString(R.string.prosody_prose_badge)
            }

            // Metre name
            if (segment.metreName.isNotEmpty()) {
                txtMetre.text = ctx.getString(R.string.prosody_metre_label, segment.metreName)
                txtMetre.visibility = View.VISIBLE
            } else {
                txtMetre.visibility = View.GONE
            }

            // Pause and rate info
            if (segment.pauseAfterMs > 0) {
                txtPause.text = ctx.getString(R.string.prosody_pause_label, segment.pauseAfterMs)
                txtPause.visibility = View.VISIBLE
            } else {
                txtPause.visibility = View.GONE
            }

            txtRate.text = ctx.getString(R.string.prosody_rate_label, segment.ttsRate)

            // Regen progress
            regenProgress.visibility = if (isRegenerating) View.VISIBLE else View.GONE

            // FEAT-52: tap to regenerate
            itemView.setOnClickListener { onClick(segment) }

            // FEAT-55: long-press for phonetic explainer
            if (onLongClick != null) {
                itemView.setOnLongClickListener {
                    onLongClick(segment)
                    true
                }
            }
        }
    }

    companion object {
        private val DIFF = object : DiffUtil.ItemCallback<ProsodySegment>() {
            override fun areItemsTheSame(a: ProsodySegment, b: ProsodySegment) =
                a.index == b.index
            override fun areContentsTheSame(a: ProsodySegment, b: ProsodySegment) =
                a == b
        }
    }
}
