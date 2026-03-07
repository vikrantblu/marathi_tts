package com.marathitts.mobile.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface PhoneticCorrectionDao {

    @Query("SELECT * FROM phonetic_corrections ORDER BY timestamp DESC")
    suspend fun getAll(): List<PhoneticCorrection>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(correction: PhoneticCorrection)

    @Query("DELETE FROM phonetic_corrections WHERE word = :word")
    suspend fun deleteByWord(word: String)

    @Query("DELETE FROM phonetic_corrections")
    suspend fun deleteAll()

    @Query("SELECT COUNT(*) FROM phonetic_corrections")
    suspend fun count(): Int
}
