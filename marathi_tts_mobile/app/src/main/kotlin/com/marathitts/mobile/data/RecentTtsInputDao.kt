package com.marathitts.mobile.data

import androidx.lifecycle.LiveData
import androidx.room.*

@Dao
interface RecentTtsInputDao {
    @Query("SELECT * FROM recent_tts_inputs ORDER BY timestamp DESC LIMIT 5")
    fun getRecent(): LiveData<List<RecentTtsInput>>

    @Insert
    suspend fun insert(input: RecentTtsInput)

    /** Prevent duplicate texts — delete older entry before inserting. */
    @Query("DELETE FROM recent_tts_inputs WHERE text = :text")
    suspend fun deleteByText(text: String)

    /** Keep only the 5 most recent. */
    @Query("DELETE FROM recent_tts_inputs WHERE id NOT IN (SELECT id FROM recent_tts_inputs ORDER BY timestamp DESC LIMIT 5)")
    suspend fun trimOld()
}
