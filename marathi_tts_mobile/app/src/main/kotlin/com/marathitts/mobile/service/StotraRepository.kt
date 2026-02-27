package com.marathitts.mobile.service

import android.content.Context
import android.util.Log
import org.json.JSONArray

/**
 * Repository for the stotra library.
 * Loads a catalog from assets/stotra_catalog.json and reads text files from assets/stotras/.
 */
class StotraRepository(private val context: Context) {

    companion object {
        private const val TAG = "StotraRepository"
        private const val CATALOG_FILE = "stotra_catalog.json"
    }

    data class Stotra(
        val id: String,
        val title: String,
        val titleEn: String,
        val deity: String,
        val language: String,
        val category: String,
        val meter: String,
        val verseCount: Int,
        val textFile: String,
        val audioFile: String?,
        val durationSec: Int?,
        val description: String
    )

    private var catalog: List<Stotra>? = null

    /** Load the catalog from assets. Cached after first call. */
    fun getAll(): List<Stotra> {
        catalog?.let { return it }
        return try {
            val json = context.assets.open(CATALOG_FILE).bufferedReader().use { it.readText() }
            val arr = JSONArray(json)
            val list = mutableListOf<Stotra>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                list.add(
                    Stotra(
                        id = obj.getString("id"),
                        title = obj.getString("title"),
                        titleEn = obj.getString("titleEn"),
                        deity = obj.getString("deity"),
                        language = obj.getString("language"),
                        category = obj.getString("category"),
                        meter = obj.optString("meter", ""),
                        verseCount = obj.optInt("verseCount", 0),
                        textFile = obj.getString("textFile"),
                        audioFile = obj.optString("audioFile", "").ifEmpty { null },
                        durationSec = if (obj.isNull("durationSec")) null else obj.optInt("durationSec"),
                        description = obj.optString("description", "")
                    )
                )
            }
            catalog = list
            Log.i(TAG, "Loaded ${list.size} stotras from catalog")
            list
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load stotra catalog: ${e.message}")
            emptyList()
        }
    }

    /** Filter by deity name (Devanagari). */
    fun getByDeity(deity: String): List<Stotra> =
        getAll().filter { it.deity == deity }

    /** Filter by language code (sa / hi / mr). */
    fun getByLanguage(langCode: String): List<Stotra> =
        getAll().filter { it.language == langCode }

    /** Filter by category (stotra / chalisa / sahasranama / ...). */
    fun getByCategory(category: String): List<Stotra> =
        getAll().filter { it.category == category }

    /** Get a single stotra by its id. */
    fun getById(id: String): Stotra? =
        getAll().find { it.id == id }

    /** Search by title (Devanagari or English) or deity. Case-insensitive. */
    fun search(query: String): List<Stotra> {
        val q = query.lowercase()
        return getAll().filter {
            it.title.lowercase().contains(q) ||
            it.titleEn.lowercase().contains(q) ||
            it.deity.lowercase().contains(q) ||
            it.description.lowercase().contains(q)
        }
    }

    /** Load the full text of a stotra from its asset file. */
    fun loadText(stotra: Stotra): String {
        return try {
            context.assets.open(stotra.textFile).bufferedReader().use { it.readText() }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load text for ${stotra.id}: ${e.message}")
            "(Text not available)"
        }
    }

    /** Get distinct deities for filter chips. */
    fun getDeities(): List<String> =
        getAll().map { it.deity }.distinct().sorted()

    /** Get distinct categories for filter chips. */
    fun getCategories(): List<String> =
        getAll().map { it.category }.distinct().sorted()

    /** Get distinct language codes. */
    fun getLanguages(): List<String> =
        getAll().map { it.language }.distinct().sorted()
}
