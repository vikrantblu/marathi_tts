package com.marathitts.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/** A recently used URL in the Web Fetch screen. */
@Entity(tableName = "url_bookmarks")
data class UrlBookmark(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val url: String,
    val title: String? = null,
    val timestamp: Long = System.currentTimeMillis()
)
