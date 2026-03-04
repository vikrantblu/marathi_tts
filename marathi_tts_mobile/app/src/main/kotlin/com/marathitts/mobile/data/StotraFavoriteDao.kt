package com.marathitts.mobile.data

import androidx.lifecycle.LiveData
import androidx.room.*

@Dao
interface StotraFavoriteDao {
    @Query("SELECT * FROM stotra_favorites ORDER BY timestamp DESC")
    fun getAll(): LiveData<List<StotraFavorite>>

    @Query("SELECT stotraId FROM stotra_favorites")
    fun getAllIds(): LiveData<List<String>>

    @Query("SELECT EXISTS(SELECT 1 FROM stotra_favorites WHERE stotraId = :stotraId)")
    suspend fun isFavorite(stotraId: String): Boolean

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(fav: StotraFavorite)

    @Query("DELETE FROM stotra_favorites WHERE stotraId = :stotraId")
    suspend fun delete(stotraId: String)
}
