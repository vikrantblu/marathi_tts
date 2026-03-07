package com.marathitts.mobile.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        HistoryEntry::class,
        StotraFavorite::class,
        UrlBookmark::class,
        RecentTtsInput::class,
        PhoneticCorrection::class
    ],
    version = 2,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun historyDao(): HistoryDao
    abstract fun stotraFavoriteDao(): StotraFavoriteDao
    abstract fun urlBookmarkDao(): UrlBookmarkDao
    abstract fun recentTtsInputDao(): RecentTtsInputDao
    abstract fun phoneticCorrectionDao(): PhoneticCorrectionDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "marathi_tts.db"
                ).fallbackToDestructiveMigration()
                .build().also { INSTANCE = it }
            }
        }
    }
}
