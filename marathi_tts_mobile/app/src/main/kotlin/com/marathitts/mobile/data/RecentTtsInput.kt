package com.marathitts.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/** A recently used TTS input text for quick re-generate chips. */
@Entity(tableName = "recent_tts_inputs")
data class RecentTtsInput(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val text: String,
    val timestamp: Long = System.currentTimeMillis()
)
