package com.marathitts.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/** A stotra marked as favourite by the user. Stores the stotra ID from the catalog. */
@Entity(tableName = "stotra_favorites")
data class StotraFavorite(
    @PrimaryKey val stotraId: String,   // matches StotraRepository.Stotra.id
    val title: String,
    val titleEn: String,
    val deity: String,
    val timestamp: Long = System.currentTimeMillis()
)
