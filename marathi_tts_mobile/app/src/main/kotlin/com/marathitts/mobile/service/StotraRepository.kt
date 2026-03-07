package com.marathitts.mobile.service

import android.content.Context
import android.util.Log
import org.json.JSONArray
import java.io.File

/**
 * Repository for the stotra library.
 * Loads a catalog from assets/stotra_catalog.json and reads text files from assets/stotras/.
 * Supports fingerprint-based matching and pre-recorded audio extraction from assets.
 */
class StotraRepository(private val context: Context) {

    companion object {
        private const val TAG = "StotraRepository"
        private const val CATALOG_FILE = "stotra_catalog.json"
        private const val FINGERPRINT_LENGTH = 60
        /** Minimum viable fingerprint length for reliable stotra matching. */
        private const val MIN_FINGERPRINT_LENGTH = 20

        /**
         * Compute a fingerprint for stotra matching: first [FINGERPRINT_LENGTH] Devanagari
         * characters (U+0900–U+0963, U+0970–U+097F), excluding dandas, digits and whitespace.
         * Mirrors the desktop _fingerprint() function in tts_bridge.py.
         */
        fun computeFingerprint(text: String): String {
            val sb = StringBuilder(FINGERPRINT_LENGTH + 4)
            for (ch in text) {
                val cp = ch.code
                if ((cp in 0x0900..0x0963) || (cp in 0x0970..0x097F)) {
                    sb.append(ch)
                    if (sb.length >= FINGERPRINT_LENGTH) break
                }
            }
            return sb.toString()
        }
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
        val description: String,
        val fingerprints: List<String> = emptyList()
    )

    private var catalog: List<Stotra>? = null
    // Fingerprint → Stotra index for O(1) lookup
    private var fingerprintIndex: Map<String, Stotra>? = null

    /** Load the catalog from assets. Cached after first call. */
    fun getAll(): List<Stotra> {
        catalog?.let { return it }
        return try {
            val json = context.assets.open(CATALOG_FILE).bufferedReader().use { it.readText() }
            val arr = JSONArray(json)
            val list = mutableListOf<Stotra>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                val fpArr = obj.optJSONArray("fingerprints")
                val fps = if (fpArr != null) {
                    (0 until fpArr.length()).map { fpArr.getString(it) }
                } else emptyList()
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
                        description = obj.optString("description", ""),
                        fingerprints = fps
                    )
                )
            }
            catalog = list
            // Build fingerprint index
            val idx = mutableMapOf<String, Stotra>()
            for (s in list) {
                for (fp in s.fingerprints) idx[fp] = s
            }
            fingerprintIndex = idx
            Log.i(TAG, "Loaded ${list.size} stotras from catalog, ${idx.size} fingerprints indexed")
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

    /**
     * FEAT-60: Search inside stotra text content for a phrase.
     * Returns a list of (Stotra, excerpt) pairs where the query appears in the body text.
     * Excerpt shows the matching line with surrounding context.
     */
    data class ContentMatch(val stotra: Stotra, val excerpt: String, val lineNumber: Int)

    fun searchContent(query: String): List<ContentMatch> {
        if (query.isBlank() || query.length < 2) return emptyList()
        val q = query.lowercase()
        val results = mutableListOf<ContentMatch>()
        for (stotra in getAll()) {
            try {
                val text = context.assets.open(stotra.textFile).bufferedReader().use { it.readText() }
                val lines = text.lines()
                for ((idx, line) in lines.withIndex()) {
                    if (line.lowercase().contains(q)) {
                        // Build excerpt: matching line + 1 surrounding line for context
                        val start = maxOf(0, idx - 1)
                        val end = minOf(lines.size - 1, idx + 1)
                        val excerpt = lines.subList(start, end + 1).joinToString("\n")
                        results.add(ContentMatch(stotra, excerpt, idx + 1))
                        break  // one match per stotra is enough
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Content search skip ${stotra.id}: ${e.message}")
            }
        }
        return results
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

    /**
     * Find a stotra by fingerprint-matching the supplied text.
     * Mirrors the desktop _try_stotra_library() / _fingerprint() logic.
     * Returns null if no match found or catalog has no fingerprints.
     */
    fun findByText(inputText: String): Stotra? {
        getAll() // ensure catalog + index are loaded
        val idx = fingerprintIndex ?: return null
        if (idx.isEmpty()) return null
        val fp = computeFingerprint(inputText)
        if (fp.length < MIN_FINGERPRINT_LENGTH) return null
        // Exact match first
        idx[fp]?.let { return it }
        // Prefix match: catalog key starts with fp or fp starts with catalog key
        for ((key, stotra) in idx) {
            if (key.startsWith(fp) || fp.startsWith(key)) return stotra
        }
        return null
    }

    /**
     * Extract a stotra's pre-recorded audio asset to the app's cache directory.
     * Returns the absolute path of the cached file, or null if no audio is available
     * or the asset cannot be read.
     * Synchronized to prevent a race condition when multiple coroutines request
     * the same stotra simultaneously.
     */
    @Synchronized
    fun extractAudioToCache(stotra: Stotra): String? {
        val assetPath = stotra.audioFile ?: return null
        return try {
            val cacheDir = File(context.cacheDir, "stotra_audio").also { it.mkdirs() }
            val outFile = File(cacheDir, "${stotra.id}.mp3")
            // Re-use cached file if already extracted
            if (outFile.exists() && outFile.length() > 0) {
                Log.i(TAG, "Pre-recorded cache hit: ${outFile.absolutePath}")
                return outFile.absolutePath
            }
            // Write to a temp file first, then atomically rename to avoid partial reads
            val tmpFile = File(cacheDir, "${stotra.id}.mp3.tmp")
            context.assets.open(assetPath).use { input ->
                tmpFile.outputStream().use { output -> input.copyTo(output) }
            }
            tmpFile.renameTo(outFile)
            Log.i(TAG, "Pre-recorded audio extracted: ${outFile.absolutePath} (${outFile.length()} bytes)")
            outFile.absolutePath
        } catch (e: Exception) {
            Log.w(TAG, "Failed to extract audio for ${stotra.id}: ${e.message}")
            null
        }
    }
}
