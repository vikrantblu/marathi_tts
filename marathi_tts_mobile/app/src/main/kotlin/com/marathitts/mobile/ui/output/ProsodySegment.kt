package com.marathitts.mobile.ui.output

/**
 * Represents a single prosody segment returned by analyze_prosody().
 * Used for FEAT-51 prosody preview and FEAT-52 per-sentence regeneration.
 */
data class ProsodySegment(
    val index: Int,
    val text: String,
    val pauseAfterMs: Int,
    val emotion: String,
    val emphasis: Float,
    val pitchShift: Float,
    val isVerse: Boolean,
    val metreName: String,
    val ttsRate: Float,
    /** Audio file path for this segment (populated after generation) */
    var audioPath: String? = null
)
