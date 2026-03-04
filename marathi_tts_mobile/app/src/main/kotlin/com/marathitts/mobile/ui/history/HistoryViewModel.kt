package com.marathitts.mobile.ui.history

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.data.AppDatabase
import com.marathitts.mobile.data.HistoryEntry
import kotlinx.coroutines.launch

class HistoryViewModel(app: Application) : AndroidViewModel(app) {

    private val dao = AppDatabase.getInstance(app).historyDao()

    /** Currently selected category filter, null = "All" */
    private val _categoryFilter = MutableLiveData<String?>(null)

    val allHistory: LiveData<List<HistoryEntry>> = dao.getAll()

    fun deleteEntry(entry: HistoryEntry) {
        viewModelScope.launch { dao.delete(entry) }
    }

    fun clearAll() {
        viewModelScope.launch { dao.deleteAll() }
    }
}
