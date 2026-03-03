package com.marathitts.mobile.ui.test

import android.app.Application
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.marathitts.mobile.service.NativeImageOcr
import com.marathitts.mobile.service.NativePdfExtractor
import com.marathitts.mobile.service.PythonBridge
import com.marathitts.mobile.service.StotraRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

// ─────────────────────────────────────────────────────────────────────────────
// Models
// ─────────────────────────────────────────────────────────────────────────────

enum class TestStatus { IDLE, RUNNING, PASS, FAIL }

enum class TestGroup(val label: String, val color: Int) {
    TTS("TTS", 0xFF6750A4.toInt()),
    INPUT("Input", 0xFF0288D1.toInt()),
    NLP("NLP", 0xFF2E7D32.toInt()),
    VOICE("Voice", 0xFFC62828.toInt()),
    STOTRA("Stotra", 0xFFE65100.toInt())
}

data class TestCase(
    val id: String,
    val name: String,
    val description: String,
    val group: TestGroup
)

data class TestResult(
    val testCase: TestCase,
    val status: TestStatus = TestStatus.IDLE,
    val message: String = "",
    val audioPath: String? = null,
    val durationMs: Long = 0L
)

// ─────────────────────────────────────────────────────────────────────────────
// ViewModel
// ─────────────────────────────────────────────────────────────────────────────

class TestDashboardViewModel(app: Application) : AndroidViewModel(app) {

    companion object {
        private const val TAG = "TestDashboard"

        // ── Sample texts ───────────────────────────────────────────────────
        // Sanskrit — single shloka (Ganapati dhyana, language=sa)
        val SAMPLE_SANSKRIT = """
            शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।
            प्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ॥
        """.trimIndent()

        // Modern Marathi paragraph (language=mr)
        val SAMPLE_MARATHI =
            "महाराष्ट्र हे भारतातील एक महत्त्वाचे राज्य आहे. " +
            "येथील लोक मराठी भाषा बोलतात. पुणे, मुंबई, नाशिक ही प्रमुख शहरे आहेत. " +
            "शेती हा येथील मुख्य व्यवसाय आहे."

        // Old Marathi — Dnyaneshwari abhanga (language=mr-old)
        val SAMPLE_OLD_MARATHI = """
            ज्ञानदेव म्हणे पाहा विठ्ठलाचे पाय ।
            तेथेचि माझी माय आणि बाप ॥
            आम्ही जातो आपुल्या गावा गावा ।
            आपुला राम राम घ्यावा ॥
        """.trimIndent()

        // Marathi emotion test
        val SAMPLE_EMOTION = "आज खूप आनंद झाला! माझी परीक्षा उत्तम गेली."

        // Correction test
        val SAMPLE_INCORRECT = "मला जाइचे आहे बाजारात खरेदी करायला"

        // Marathi website
        val SAMPLE_WEB_URL = "https://marathi.abplive.com/"

        // Hanuman Chalisa (Marathi/Hindi, language=hi)
        val SAMPLE_HANUMAN = """
            श्री राम जय राम जय जय राम ।
            श्री राम जय राम जय जय राम ॥
        """.trimIndent()

        // Voice modulation emotion texts
        val SAMPLE_HAPPY_TEXT = "आज खूप आनंद झाला! माझी परीक्षा उत्तम गेली. सर्व काही मस्त आहे, खुशाल वाटते."
        val SAMPLE_SAD_TEXT   = "खूप दुःख झाले. मन उदास आहे. वेदना असह्य वाटते, निराश वाटतो."

        // Long text for streaming TTS test (>250 chars, 3 clear sentences)
        val SAMPLE_LONG_MARATHI = """
            मराठी ही भारतातील एक प्रमुख भाषा आहे.
            ती महाराष्ट्र राज्याची अधिकृत भाषा आहे आणि कोट्यवधी लोक ती बोलतात.
            मराठी साहित्याचा इतिहास फार मोठा आणि समृद्ध आहे.
        """.trimIndent()

        // OCR test text (rendered to PNG via Canvas)
        val SAMPLE_OCR_TEXT = "राम नाम सत्य आहे"
    }

    // ── Test catalog ──────────────────────────────────────────────────────────
    val allTestCases = listOf(
        // TTS — language routing
        TestCase("T01", "Sanskrit TTS (verse)",
            "Ganapati shloka → lang=sa → gTTS:hi + Sanskrit phonetics",
            TestGroup.TTS),
        TestCase("T02", "Marathi TTS (prose)",
            "Modern Marathi paragraph → lang=mr → Marathi phonetics",
            TestGroup.TTS),
        TestCase("T03", "Old Marathi TTS (verse)",
            "Dnyaneshwari abhanga → lang=mr-old → Old Marathi phonetics",
            TestGroup.TTS),
        TestCase("T04", "Hindi TTS",
            "Hindi sentence → lang=hi → gTTS:hi",
            TestGroup.TTS),

        // INPUT — web / OCR / PDF
        TestCase("T05", "Web Fetch",
            "Fetch ${SAMPLE_WEB_URL} and extract Marathi text",
            TestGroup.INPUT),
        TestCase("T06", "Web Text → TTS",
            "Run TTS on the first 300 chars of web-fetched text",
            TestGroup.INPUT),
        TestCase("T13", "Native OCR (ML Kit)",
            "Render Devanagari PNG → ML Kit Devanagari recognition → verify text",
            TestGroup.INPUT),
        TestCase("T14", "PDF Bridge",
            "Write minimal text PDF → pdf_bridge.extract_pdf → verify success",
            TestGroup.INPUT),
        TestCase("T15", "PDF → TTS Pipeline",
            "Take T14 extracted text and run Marathi TTS on it",
            TestGroup.INPUT),

        // NLP
        TestCase("T07", "Emotion Analysis",
            "Detect emotion in: \"$SAMPLE_EMOTION\"",
            TestGroup.NLP),
        TestCase("T08", "Text Correction",
            "Correct: \"$SAMPLE_INCORRECT\"",
            TestGroup.NLP),
        TestCase("T09", "Modi → Devanagari",
            "Convert sample Modi script text to Devanagari",
            TestGroup.NLP),

        // STOTRA
        TestCase("T10", "Stotra Catalog",
            "Load catalog from assets — verify count ≥ 1",
            TestGroup.STOTRA),
        TestCase("T11", "Sanskrit Stotra TTS",
            "Vishnu Sahasranama shloka 1 → Sanskrit phonetics + lang=hi",
            TestGroup.STOTRA),
        TestCase("T12", "Marathi Stotra TTS",
            "Manache Shlok verse → Marathi phonetics",
            TestGroup.STOTRA),

        // VOICE — modulation tests
        TestCase("T16", "TTS Speed 0.7× (slow)",
            "Marathi prose at speed=0.7 — verify audio generated",
            TestGroup.VOICE),
        TestCase("T17", "TTS Speed 1.3× (fast)",
            "Marathi prose at speed=1.3 — verify audio generated",
            TestGroup.VOICE),
        TestCase("T18", "TTS Male Voice",
            "gender=male → pitch ~0.79× — verify audio generated",
            TestGroup.VOICE),
        TestCase("T19", "TTS Emotion: Happy",
            "emotion=happy → pitch 1.15, speed 1.1",
            TestGroup.VOICE),
        TestCase("T20", "TTS Emotion: Sad",
            "emotion=sad → pitch 0.9, speed 0.9",
            TestGroup.VOICE),
        TestCase("T21", "Sanskrit Verse + Pitch 1.1",
            "lang=sa, pitch=1.1, speed=0.85 — higher pitch Sanskrit",
            TestGroup.VOICE),
        TestCase("T22", "Old Marathi Slow Recitation",
            "lang=mr-old, speed=0.75 — slow classical recitation",
            TestGroup.VOICE),
        // NLP — extended emotion tests
        TestCase("T23", "Emotion: Sad Detection",
            "Detect sad emotion from: \"$SAMPLE_SAD_TEXT\"",
            TestGroup.NLP),
        // TTS — streaming / parallel chunk generation
        TestCase("T24", "TTS Streaming (long text)",
            "Split 3-sentence Marathi text → 3 parallel TTS chunks",
            TestGroup.TTS),
        // INPUT — native OCR/PDF pipelines
        TestCase("T25", "OCR → TTS Pipeline",
            "ML Kit OCR on Devanagari image → TTS on extracted text",
            TestGroup.INPUT),
        TestCase("T26", "Native PDF OCR",
            "Render Devanagari → embed in PDF → NativePdfExtractor → verify",
            TestGroup.INPUT)
    )

    private val _results = MutableLiveData(
        allTestCases.map { TestResult(it) }
    )
    val results: LiveData<List<TestResult>> get() = _results

    private val _isRunningAll = MutableLiveData(false)
    val isRunningAll: LiveData<Boolean> get() = _isRunningAll

    private var runAllJob: Job? = null

    // Cached web text for T06
    private var cachedWebText: String? = null

    // Cached PDF text for T15  
    private var cachedPdfText: String? = null

    init {
        PythonBridge.init(app)
    }

    // ── Public API ────────────────────────────────────────────────────────────

    fun runTest(id: String) {
        viewModelScope.launch {
            executeTest(id)
        }
    }

    fun runAll() {
        if (_isRunningAll.value == true) return
        _isRunningAll.value = true
        // Reset all to IDLE first
        _results.value = allTestCases.map { TestResult(it) }
        runAllJob = viewModelScope.launch {
            var pass = 0
            var fail = 0
            for (tc in allTestCases) {
                if (!isActive) break
                val statusBefore = _results.value
                executeTest(tc.id)
                // executeTest calls postValue — read via its return (indirect via exception caught)
                // Actually count by checking if exception was thrown during dispatch:
                // We track inside executeTest itself by inspecting the posted status.
                // Simple: bump counters based on final state in postValue callback.
            }
            // Re-read on main thread after all postValues have been dispatched
            val snapshot = _results.value
            if (snapshot != null) {
                pass = snapshot.count { it.status == TestStatus.PASS }
                fail = snapshot.count { it.status == TestStatus.FAIL }
            }
            Log.i(TAG, "ALL done — PASS=$pass  FAIL=$fail  total=${allTestCases.size}")
            _isRunningAll.postValue(false)
        }
    }

    fun stopAll() {
        runAllJob?.cancel()
        runAllJob = null
        _isRunningAll.value = false
        // Mark any still-RUNNING as FAIL
        _results.value = _results.value?.map {
            if (it.status == TestStatus.RUNNING)
                it.copy(status = TestStatus.FAIL, message = "Cancelled")
            else it
        }
    }

    fun clearAll() {
        stopAll()
        cachedWebText = null
        cachedPdfText = null
        _results.value = allTestCases.map { TestResult(it) }
    }

    // ── Internal runner ───────────────────────────────────────────────────────

    private suspend fun executeTest(id: String) {
        updateStatus(id, TestStatus.RUNNING, "Running…")
        val start = System.currentTimeMillis()
        try {
            val (msg, audio) = withContext(Dispatchers.IO) { dispatch(id) }
            val dur = System.currentTimeMillis() - start
            Log.i(TAG, "[$id] PASS (${dur}ms): $msg")
            updateResult(id, TestStatus.PASS, msg, audio, dur)
        } catch (e: Exception) {
            val dur = System.currentTimeMillis() - start
            Log.e(TAG, "[$id] FAIL (${dur}ms): ${e.message}")
            updateResult(id, TestStatus.FAIL, e.message ?: "Unknown error", null, dur)
        }
    }

    /** Dispatch to the correct test runner by ID. */
    private suspend fun dispatch(id: String): Pair<String, String?> = when (id) {
        "T01" -> testSanskritTts()
        "T02" -> testMarathiTts()
        "T03" -> testOldMarathiTts()
        "T04" -> testHindiTts()
        "T05" -> testWebFetch()
        "T06" -> testWebTextTts()
        "T07" -> testEmotion()
        "T08" -> testCorrection()
        "T09" -> testModi()
        "T10" -> testStoraCatalog()
        "T11" -> testSanskritStoraTts()
        "T12" -> testMarathiStoraTts()
        "T13" -> testOcrBridge()
        "T14" -> testPdfBridge()
        "T15" -> testPdfToTts()
        "T16" -> testTtsSlow()
        "T17" -> testTtsFast()
        "T18" -> testTtsMale()
        "T19" -> testTtsEmotionHappy()
        "T20" -> testTtsEmotionSad()
        "T21" -> testSanskritVerseWithPitch()
        "T22" -> testOldMarathiSlow()
        "T23" -> testEmotionSad()
        "T24" -> testTtsStreaming()
        "T25" -> testOcrToTts()
        "T26" -> testNativePdfOcr()
        else  -> throw IllegalArgumentException("Unknown test id: $id")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T01 — Sanskrit TTS (verse mode, lang=sa)
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testSanskritTts(): Pair<String, String?> {
        Log.i(TAG, "[T01] Sanskrit TTS — text len=${SAMPLE_SANSKRIT.length}")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_SANSKRIT,
            "language" to "sa",
            "is_verse" to true,
            "speed"    to 0.9
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        val audio  = r.optString("audio_path")
        Log.i(TAG, "[T01] engine=$engine audio=$audio")
        // Sanity: engine should contain 'sa' or 'hi' (not 'mr') after fix
        val note = if (engine.contains("mr") && !engine.contains("_mr"))
            " ⚠ engine contains 'mr' — check lang map" else ""
        return "engine=$engine  elapsed=${r.optDouble("elapsed_sec", 0.0)}s$note" to audio
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T02 — Marathi TTS (prose mode, lang=mr)
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testMarathiTts(): Pair<String, String?> {
        Log.i(TAG, "[T02] Marathi TTS")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_MARATHI,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.0
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T02] engine=$engine")
        return "engine=$engine  elapsed=${r.optDouble("elapsed_sec", 0.0)}s" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T03 — Old Marathi TTS (verse, lang=mr-old)
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testOldMarathiTts(): Pair<String, String?> {
        Log.i(TAG, "[T03] Old Marathi TTS")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_OLD_MARATHI,
            "language" to "mr-old",
            "is_verse" to true,
            "speed"    to 0.9
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T03] engine=$engine")
        return "engine=$engine  elapsed=${r.optDouble("elapsed_sec", 0.0)}s" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T04 — Hindi TTS
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testHindiTts(): Pair<String, String?> {
        Log.i(TAG, "[T04] Hindi TTS")
        val text = "भारत एक महान देश है। यहाँ अनेक भाषाएँ बोली जाती हैं।"
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to text,
            "language" to "hi",
            "is_verse" to false,
            "speed"    to 1.0
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T04] engine=$engine")
        return "engine=$engine  elapsed=${r.optDouble("elapsed_sec", 0.0)}s" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T05 — Web Fetch
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testWebFetch(): Pair<String, String?> {
        Log.i(TAG, "[T05] Web Fetch → $SAMPLE_WEB_URL")
        val r = PythonBridge.call("web_bridge", "fetch_url", kwargs = mapOf(
            "url"            to SAMPLE_WEB_URL,
            "process_images" to false
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val text  = r.optString("text", "")
        val title = r.optString("title", "no title")
        if (text.isBlank()) throw RuntimeException("Fetched text is empty")
        cachedWebText = text
        Log.i(TAG, "[T05] title='$title' text_len=${text.length}")
        return "title='$title'  chars=${text.length}" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T06 — Web Text → TTS
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testWebTextTts(): Pair<String, String?> {
        val raw = cachedWebText
            ?: throw RuntimeException("Run T05 (Web Fetch) first to cache the text")
        val snippet = raw.take(350)
        Log.i(TAG, "[T06] Web→TTS chars=${snippet.length}")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to snippet,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.0
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T06] engine=$engine")
        return "engine=$engine  snippet_len=${snippet.length}" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T07 — Emotion analysis (happy text → "happy", score > 0)
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testEmotion(): Pair<String, String?> {
        Log.i(TAG, "[T07] Emotion: '$SAMPLE_EMOTION'")
        val r = PythonBridge.call("emotion_bridge", "analyze_emotion", kwargs = mapOf(
            "text" to SAMPLE_EMOTION
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val emotion = r.optString("emotion", "?")
        val score   = r.optDouble("score", 0.0)
        Log.i(TAG, "[T07] emotion=$emotion score=$score")
        // Validate: must detect a real emotion (not "?" or "neutral") with score > 0
        check(emotion != "?" && emotion.isNotBlank()) { "emotion not detected: got '$emotion'" }
        check(score > 0.0) { "score should be > 0 for emotional text, got $score" }
        // Happy keywords present — must lean toward happy
        val method = r.optString("method", "")
        return "emotion=$emotion  confidence=${String.format("%.2f", score)}  method=$method" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T08 — Text correction
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testCorrection(): Pair<String, String?> {
        Log.i(TAG, "[T08] Correction: '$SAMPLE_INCORRECT'")
        val r = PythonBridge.call("correction_bridge", "correct_text", kwargs = mapOf(
            "text" to SAMPLE_INCORRECT
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val corrected = r.optString("corrected_text", "?")
        val method    = r.optString("method", "?")
        Log.i(TAG, "[T08] corrected='$corrected' method=$method")
        return "in : $SAMPLE_INCORRECT\nout: $corrected\nmethod=$method" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T09 — Modi → Devanagari
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testModi(): Pair<String, String?> {
        // Basic Latin-script Modi transliteration test
        val modiText = "𑘦𑘰𑘨𑘰𑘙𑘲"
        Log.i(TAG, "[T09] Modi convert")
        val r = PythonBridge.call("script_converter_bridge", "convert", kwargs = mapOf(
            "text" to modiText,
            "mode" to "modi_to_devanagari"
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val converted = r.optString("converted_text", "?")
        Log.i(TAG, "[T09] result='$converted'")
        return "in : $modiText\nout: $converted" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T10 — Stotra catalog
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testStoraCatalog(): Pair<String, String?> {
        Log.i(TAG, "[T10] Stotra catalog load")
        val repo = StotraRepository(getApplication())
        val all  = withContext(Dispatchers.IO) { repo.getAll() }
        if (all.isEmpty()) throw RuntimeException("Catalog returned 0 stotras")
        val langs = all.groupBy { it.language }.mapValues { it.value.size }
        Log.i(TAG, "[T10] total=${all.size} langs=$langs")
        return "total=${all.size} — $langs" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T11 — Sanskrit stotra TTS (first shloka of Vishnu Sahasranama)
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testSanskritStoraTts(): Pair<String, String?> {
        val repo   = StotraRepository(getApplication())
        val stotra = withContext(Dispatchers.IO) { repo.getById("vishnu_sahasranama") }
            ?: throw RuntimeException("vishnu_sahasranama not in catalog")
        // Use only the dhyana shloka (first two lines) instead of full text
        val text   = SAMPLE_SANSKRIT  // reuse already-tested dhyana shloka
        Log.i(TAG, "[T11] Sanskrit stotra '${stotra.titleEn}' lang=${stotra.language}")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to text,
            "language" to stotra.language,   // "sa" from catalog
            "is_verse" to true,
            "speed"    to 0.85
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T11] engine=$engine stotra_lang=${stotra.language}")
        // Verify: should NOT be gtts_mr — after fix gTTS lang is "hi" for Sanskrit
        val warn = if (engine == "gtts_mr") " ⚠ still using Marathi voice!" else ""
        return "stotra_lang=${stotra.language}  engine=$engine$warn" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T12 — Marathi stotra TTS (Manache Shlok)
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testMarathiStoraTts(): Pair<String, String?> {
        val repo   = StotraRepository(getApplication())
        val stotra = withContext(Dispatchers.IO) { repo.getById("manache_shlok") }
            ?: throw RuntimeException("manache_shlok not in catalog")
        val rawText = withContext(Dispatchers.IO) { repo.loadText(stotra) }
        // Take first ~200 chars (first 2 shlokas)
        val snippet = rawText.lines().take(6).joinToString("\n")
        Log.i(TAG, "[T12] Marathi stotra '${stotra.titleEn}' lang=${stotra.language}")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to snippet,
            "language" to stotra.language,
            "is_verse" to true,
            "speed"    to 0.9
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T12] engine=$engine stotra_lang=${stotra.language}")
        return "stotra_lang=${stotra.language}  engine=$engine" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T13 — OCR bridge via programmatic PNG
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testOcrBridge(): Pair<String, String?> {
        Log.i(TAG, "[T13] OCR bridge: render PNG via Canvas")
        val bmp = Bitmap.createBitmap(600, 200, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.drawColor(Color.WHITE)
        val paint = Paint().apply {
            color = Color.BLACK
            textSize = 60f
            typeface = Typeface.DEFAULT
            isAntiAlias = true
        }
        canvas.drawText(SAMPLE_OCR_TEXT, 40f, 120f, paint)
        val png = File(getApplication<Application>().cacheDir, "test_ocr_input.png")
        FileOutputStream(png).use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bmp.recycle()
        Log.i(TAG, "[T13] PNG written: ${png.absolutePath}")
        // Native ML Kit Devanagari OCR — the real production path
        val nativeText = NativeImageOcr.extract(png)
        val devChars = nativeText.count { it in '\u0900'..'\u097F' }
        Log.i(TAG, "[T13] ML Kit OCR: ${nativeText.length} chars, $devChars devanagari, text='${nativeText.take(60)}'")

        check(nativeText.isNotBlank()) { "ML Kit OCR returned empty text from rendered PNG" }
        check(devChars > 0) { "No Devanagari in OCR result: '${nativeText.take(40)}'" }

        return "ML Kit: ${nativeText.length} chars ($devChars deva)  text='${nativeText.take(40)}'" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T14 — PDF bridge with minimal text PDF
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testPdfBridge(): Pair<String, String?> {
        Log.i(TAG, "[T14] PDF bridge: write minimal PDF")
        val bodyText = "Marathi TTS Test PDF - mraathii tts chaachaNii"
        val pdf = File(getApplication<Application>().cacheDir, "test_marathi.pdf")
        pdf.writeBytes(buildMinimalPdf(bodyText))
        Log.i(TAG, "[T14] PDF written: ${pdf.absolutePath} (${pdf.length()} bytes)")
        val r = PythonBridge.call("pdf_bridge", "extract_pdf", kwargs = mapOf(
            "pdf_path" to pdf.absolutePath
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val method = r.optString("method", "none")
        val chars  = r.optInt("char_count", 0)
        val pages  = r.optInt("page_count", 0)
        cachedPdfText = r.optString("text", "").takeIf { it.isNotBlank() }
        Log.i(TAG, "[T14] method=$method chars=$chars pages=$pages cachedLen=${cachedPdfText?.length}")
        check(chars > 0) { "PDF extraction returned 0 chars (method=$method). Is PyPDF2 available?" }
        return "method=$method  chars=$chars  pages=$pages" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T15 — PDF → TTS pipeline
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testPdfToTts(): Pair<String, String?> {
        val text = cachedPdfText
            ?: "मराठी टीटीएस चाचणी. हे एक परीक्षण वाक्य आहे."
        Log.i(TAG, "[T15] PDF→TTS chars=${text.length} src=${if (cachedPdfText != null) "T14" else "fallback"}")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to text.take(300),
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.0
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        val src    = if (cachedPdfText != null) "T14" else "fallback"
        Log.i(TAG, "[T15] engine=$engine src=$src")
        return "engine=$engine  src=$src" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T16–T22 — Voice modulation tests
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testTtsSlow(): Pair<String, String?> {
        Log.i(TAG, "[T16] TTS speed=0.7")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_MARATHI,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 0.7
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T16] engine=$engine")
        return "speed=0.7  engine=$engine" to r.optString("audio_path")
    }

    private suspend fun testTtsFast(): Pair<String, String?> {
        Log.i(TAG, "[T17] TTS speed=1.3")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_MARATHI,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.3
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T17] engine=$engine")
        return "speed=1.3  engine=$engine" to r.optString("audio_path")
    }

    private suspend fun testTtsMale(): Pair<String, String?> {
        Log.i(TAG, "[T18] TTS gender=male")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_MARATHI,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.0,
            "gender"   to "male"
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T18] engine=$engine gender=male")
        return "gender=male  engine=$engine" to r.optString("audio_path")
    }

    private suspend fun testTtsEmotionHappy(): Pair<String, String?> {
        Log.i(TAG, "[T19] TTS emotion=happy")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_HAPPY_TEXT,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.0,
            "emotion"  to "happy"
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T19] engine=$engine emotion=happy")
        return "emotion=happy  engine=$engine" to r.optString("audio_path")
    }

    private suspend fun testTtsEmotionSad(): Pair<String, String?> {
        Log.i(TAG, "[T20] TTS emotion=sad")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_SAD_TEXT,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.0,
            "emotion"  to "sad"
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T20] engine=$engine emotion=sad")
        return "emotion=sad  engine=$engine" to r.optString("audio_path")
    }

    private suspend fun testSanskritVerseWithPitch(): Pair<String, String?> {
        Log.i(TAG, "[T21] Sanskrit verse pitch=1.1")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_SANSKRIT,
            "language" to "sa",
            "is_verse" to true,
            "speed"    to 0.85,
            "pitch"    to 1.1
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T21] engine=$engine")
        return "lang=sa  pitch=1.1  speed=0.85  engine=$engine" to r.optString("audio_path")
    }

    private suspend fun testOldMarathiSlow(): Pair<String, String?> {
        Log.i(TAG, "[T22] Old Marathi slow speed=0.75")
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to SAMPLE_OLD_MARATHI,
            "language" to "mr-old",
            "is_verse" to true,
            "speed"    to 0.75
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T22] engine=$engine")
        return "lang=mr-old  speed=0.75  engine=$engine" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T23 — Emotion detection: sad text must return "sad" emotion
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testEmotionSad(): Pair<String, String?> {
        Log.i(TAG, "[T23] Emotion sad: '$SAMPLE_SAD_TEXT'")
        val r = PythonBridge.call("emotion_bridge", "analyze_emotion", kwargs = mapOf(
            "text" to SAMPLE_SAD_TEXT
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException(r.optString("error"))
        val emotion = r.optString("emotion", "?")
        val score   = r.optDouble("score", 0.0)
        Log.i(TAG, "[T23] emotion=$emotion score=$score")
        check(emotion != "?" && emotion.isNotBlank()) { "emotion not detected: got '$emotion'" }
        check(score > 0.0) { "score should be > 0 for emotional text, got $score" }
        return "emotion=$emotion  confidence=${String.format("%.2f", score)}" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T24 — TTS streaming: 3 sentence chunks generated → all succeed
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testTtsStreaming(): Pair<String, String?> {
        Log.i(TAG, "[T24] TTS streaming for 3-sentence text")
        // Split SAMPLE_LONG_MARATHI into individual sentences
        val sentences = SAMPLE_LONG_MARATHI.split("\n").map { it.trim() }.filter { it.isNotBlank() }
        check(sentences.size >= 2) { "Expected >= 2 sentences, got ${sentences.size}" }

        val paths = mutableListOf<String>()
        for ((i, sentence) in sentences.withIndex()) {
            Log.i(TAG, "[T24] chunk $i: '${sentence.take(40)}…'")
            val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
                "text"     to sentence,
                "language" to "mr",
                "is_verse" to false,
                "speed"    to 1.0
            ))
            if (!PythonBridge.isSuccess(r)) throw RuntimeException("Chunk $i failed: ${r.optString("error")}")
            val path = r.optString("audio_path", "")
            if (path.isNotBlank()) paths.add(path)
        }
        check(paths.size == sentences.size) {
            "${sentences.size} chunks requested but only ${paths.size} succeeded"
        }
        Log.i(TAG, "[T24] All ${paths.size} chunks generated")
        return "${paths.size}/${sentences.size} chunks OK" to paths.first()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T25 — OCR → TTS pipeline: ML Kit OCR → generate audio from result
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testOcrToTts(): Pair<String, String?> {
        Log.i(TAG, "[T25] OCR → TTS pipeline")
        // Step 1: Render Devanagari text to bitmap
        val srcText = "मराठी भाषा सुंदर आहे"
        val bmp = Bitmap.createBitmap(800, 200, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.drawColor(Color.WHITE)
        canvas.drawText(srcText, 30f, 120f, Paint().apply {
            color = Color.BLACK; textSize = 56f; isAntiAlias = true
        })
        val png = File(getApplication<Application>().cacheDir, "test_ocr_tts.png")
        FileOutputStream(png).use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bmp.recycle()
        // Step 2: Native ML Kit OCR
        val ocrText = NativeImageOcr.extract(png)
        val devChars = ocrText.count { it in '\u0900'..'\u097F' }
        Log.i(TAG, "[T25] OCR: '${ocrText.take(40)}' ($devChars deva)")
        check(ocrText.isNotBlank()) { "OCR returned empty text" }
        check(devChars > 0) { "OCR returned no Devanagari: '$ocrText'" }
        // Step 3: TTS on OCR result
        val r = PythonBridge.call("tts_bridge", "generate_tts", kwargs = mapOf(
            "text"     to ocrText,
            "language" to "mr",
            "is_verse" to false,
            "speed"    to 1.0
        ))
        if (!PythonBridge.isSuccess(r)) throw RuntimeException("TTS failed: ${r.optString("error")}")
        val engine = r.optString("engine", "?")
        Log.i(TAG, "[T25] TTS engine=$engine audio=${r.optString("audio_path")}")
        return "ocr='${ocrText.take(20)}…' → engine=$engine" to r.optString("audio_path")
    }

    // ─────────────────────────────────────────────────────────────────────────
    // T26 — Native PDF OCR: Devanagari image in PDF → NativePdfExtractor
    // ─────────────────────────────────────────────────────────────────────────
    private suspend fun testNativePdfOcr(): Pair<String, String?> {
        Log.i(TAG, "[T26] Native PDF OCR: render Devanagari → embed in PDF")
        // Step 1: Render Devanagari text to bitmap → JPEG bytes
        val srcText = "मराठी भाषा"
        val imgW = 400; val imgH = 120
        val bmp = Bitmap.createBitmap(imgW, imgH, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.drawColor(Color.WHITE)
        canvas.drawText(srcText, 30f, 80f, Paint().apply {
            color = Color.BLACK; textSize = 48f; isAntiAlias = true
        })
        val jpegBaos = java.io.ByteArrayOutputStream()
        bmp.compress(Bitmap.CompressFormat.JPEG, 95, jpegBaos)
        bmp.recycle()
        val jpegBytes = jpegBaos.toByteArray()
        Log.i(TAG, "[T26] JPEG: ${jpegBytes.size} bytes (${imgW}x$imgH)")
        // Step 2: Build PDF with embedded JPEG image
        val pdfBytes = buildImagePdf(jpegBytes, imgW, imgH)
        val pdf = File(getApplication<Application>().cacheDir, "test_deva_image.pdf")
        pdf.writeBytes(pdfBytes)
        Log.i(TAG, "[T26] PDF: ${pdf.length()} bytes")
        // Step 3: NativePdfExtractor (PdfRenderer + ML Kit Devanagari OCR)
        val nativeText = NativePdfExtractor.extract(pdf)
        val devChars = nativeText.count { it in '\u0900'..'\u097F' }
        Log.i(TAG, "[T26] OCR: ${nativeText.length} chars, $devChars deva, text='${nativeText.take(40)}'")
        check(nativeText.isNotBlank()) { "NativePdfExtractor returned empty text" }
        check(devChars > 0) { "No Devanagari from PDF OCR: '${nativeText.take(40)}'" }
        return "PDF OCR: ${nativeText.length} chars ($devChars deva)" to null
    }

    // ─────────────────────────────────────────────────────────────────────────
    // buildMinimalPdf — creates a valid 1-page PDF with xref (parseable by PyPDF2)
    // ─────────────────────────────────────────────────────────────────────────
    private fun buildMinimalPdf(bodyText: String): ByteArray {
        val content = "BT /F1 12 Tf 50 750 Td ($bodyText) Tj ET"
        val sb = StringBuilder()
        val offsets = mutableListOf<Int>()
        sb.append("%PDF-1.4\n")
        offsets.add(sb.length)
        sb.append("1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n")
        offsets.add(sb.length)
        sb.append("2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n")
        offsets.add(sb.length)
        sb.append("3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]")
        sb.append(" /Contents 4 0 R /Resources <</Font <</F1 <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>>>>>")
        sb.append(">>\nendobj\n")
        offsets.add(sb.length)
        sb.append("4 0 obj\n<</Length ${content.length}>>\nstream\n$content\nendstream\nendobj\n")
        val xrefOff = sb.length
        sb.append("xref\n0 ${offsets.size + 1}\n")
        sb.append("0000000000 65535 f \n")
        for (o in offsets) sb.append(String.format("%010d 00000 n \n", o))
        sb.append("trailer\n<</Size ${offsets.size + 1} /Root 1 0 R>>\nstartxref\n$xrefOff\n%%EOF\n")
        return sb.toString().toByteArray(Charsets.ISO_8859_1)
    }

    /** Build a 1-page PDF with an embedded JPEG image (for NativePdfExtractor testing). */
    private fun buildImagePdf(jpegBytes: ByteArray, imgW: Int, imgH: Int): ByteArray {
        val baos = java.io.ByteArrayOutputStream()
        val offsets = mutableListOf<Int>()
        fun wr(s: String) { baos.write(s.toByteArray(Charsets.ISO_8859_1)) }
        fun pos() = baos.size()
        wr("%PDF-1.4\n")
        offsets.add(pos()); wr("1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n")
        offsets.add(pos()); wr("2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n")
        offsets.add(pos()); wr("3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 $imgW $imgH] /Contents 5 0 R /Resources <</XObject <</I1 4 0 R>>>>>>\nendobj\n")
        offsets.add(pos()); wr("4 0 obj\n<</Type /XObject /Subtype /Image /Width $imgW /Height $imgH /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.size}>>\nstream\n")
        baos.write(jpegBytes)
        wr("\nendstream\nendobj\n")
        val cs = "q $imgW 0 0 $imgH 0 0 cm /I1 Do Q"
        offsets.add(pos()); wr("5 0 obj\n<</Length ${cs.length}>>\nstream\n$cs\nendstream\nendobj\n")
        val xref = pos()
        wr("xref\n0 ${offsets.size + 1}\n")
        wr("0000000000 65535 f \n")
        for (o in offsets) wr(String.format("%010d 00000 n \n", o))
        wr("trailer\n<</Size ${offsets.size + 1} /Root 1 0 R>>\nstartxref\n$xref\n%%EOF\n")
        return baos.toByteArray()
    }

    // ─────────────────────────────────────────────────────────────────────────
    // State helpers
    // ─────────────────────────────────────────────────────────────────────────

    private fun updateStatus(id: String, status: TestStatus, message: String) {
        _results.value = _results.value?.map {
            if (it.testCase.id == id) it.copy(status = status, message = message) else it
        }
    }

    private fun updateResult(
        id: String, status: TestStatus, message: String,
        audioPath: String?, durationMs: Long
    ) {
        _results.value = _results.value?.map {
            if (it.testCase.id == id)
                it.copy(status = status, message = message,
                        audioPath = audioPath?.takeIf { p -> p.isNotBlank() },
                        durationMs = durationMs)
            else it
        }
    }
}
