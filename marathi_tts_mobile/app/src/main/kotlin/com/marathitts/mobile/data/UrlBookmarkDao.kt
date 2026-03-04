package com.marathitts.mobile.data

import androidx.lifecycle.LiveData
import androidx.room.*

@Dao
interface UrlBookmarkDao {
    @Query("SELECT * FROM url_bookmarks ORDER BY timestamp DESC LIMIT 20")
    fun getRecent(): LiveData<List<UrlBookmark>>

    @Insert
    suspend fun insert(bookmark: UrlBookmark)

    /** Prevent duplicate URLs — delete older entry before inserting. */
    @Query("DELETE FROM url_bookmarks WHERE url = :url")
    suspend fun deleteByUrl(url: String)

    @Query("DELETE FROM url_bookmarks")
    suspend fun deleteAll()

    /** Keep only the 20 most recent. */
    @Query("DELETE FROM url_bookmarks WHERE id NOT IN (SELECT id FROM url_bookmarks ORDER BY timestamp DESC LIMIT 20)")
    suspend fun trimOld()
}
