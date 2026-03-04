package com.marathitts.mobile.data

import androidx.lifecycle.LiveData
import androidx.room.*

@Dao
interface HistoryDao {
    @Query("SELECT * FROM history ORDER BY timestamp DESC")
    fun getAll(): LiveData<List<HistoryEntry>>

    @Query("SELECT * FROM history WHERE category = :category ORDER BY timestamp DESC")
    fun getByCategory(category: String): LiveData<List<HistoryEntry>>

    @Insert
    suspend fun insert(entry: HistoryEntry)

    @Delete
    suspend fun delete(entry: HistoryEntry)

    @Query("DELETE FROM history")
    suspend fun deleteAll()

    /** Keep only the most recent 200 entries to prevent unbounded growth. */
    @Query("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY timestamp DESC LIMIT 200)")
    suspend fun trimOld()
}
