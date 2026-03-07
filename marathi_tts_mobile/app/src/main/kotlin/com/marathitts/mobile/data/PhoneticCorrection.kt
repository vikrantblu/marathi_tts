package com.marathitts.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * User-submitted phonetic correction — overrides the built-in G2P exception lexicon.
 * The [word] is the Devanagari word as written; [correctedForm] is the corrected
 * pronunciation form to feed to the TTS engine.
 */
@Entity(tableName = "phonetic_corrections")
data class PhoneticCorrection(
    @PrimaryKey val word: String,
    val correctedForm: String,
    val timestamp: Long = System.currentTimeMillis()
)
