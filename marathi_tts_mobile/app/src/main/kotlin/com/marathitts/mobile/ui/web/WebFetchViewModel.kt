package com.marathitts.mobile.ui.web

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.PythonBridge
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class WebFetchState(
    val isLoading: Boolean = false,
    val text: String? = null,
    val title: String? = null,
    val error: String? = null,
    val status: String = "Enter a URL and tap Fetch"
)

class WebFetchViewModel(app: Application) : AndroidViewModel(app) {
    private val _state = MutableLiveData(WebFetchState())
    val state: LiveData<WebFetchState> get() = _state

    init { PythonBridge.init(app) }

    fun fetchUrl(url: String) {
        _state.value = WebFetchState(isLoading = true, status = "Fetching content…")
        viewModelScope.launch {
            val result: JSONObject = withContext(Dispatchers.IO) {
                PythonBridge.call("web_bridge", "fetch_url", kwargs = mapOf("url" to url))
            }
            if (PythonBridge.isSuccess(result)) {
                _state.value = WebFetchState(
                    text = result.optString("text"),
                    title = result.optString("title"),
                    status = "Content fetched ✓"
                )
            } else {
                _state.value = WebFetchState(error = PythonBridge.getError(result),
                    status = "Error: ${PythonBridge.getError(result)}")
            }
        }
    }
}
