# Marathi/Sanskrit TTS — Enhancement & Improvement Recommendations

> **Scope**: Simple text TTS and Verse/Stotra TTS across all three platforms
> **Reviewed**: Web (Django), Desktop (JavaFX+Kotlin), Mobile (Android+Chaquopy)
> **Date**: 2026-03-03

---

## Current State Summary

Your project is **remarkably well-built**. You have:

- A shared Python phonetic core ([marathi_phonetics.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/marathi_phonetics.py), [sandhi_engine.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/sandhi_engine.py), [metre_engine.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py), [prosody_engine.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py)) across all 3 platforms
- Three distinct phonetic modes: **Modern Marathi**, **Sanskrit/Stotra**, and **Old Marathi** (Dnyaneshwari/Sant literature)
- Metre-aware prosody (12 metres in catalogue) with per-metre rate, pauses, and pitch contour
- Grammar engine with 90+ spelling fixes, sandhi, vibhakti, word order
- G2P engine with exception lexicon
- Stotra library with pre-recorded audio matching

The suggestions below are **enhancements on top of an already solid foundation**.

---

## 🔴 HIGH PRIORITY — Simple Text TTS

### 1. ✅ SHIPPED — Prosody Engine on Desktop & Mobile

| Feature                               | Web |  Desktop  | Mobile |
| ------------------------------------- | :-: | :--------: | :-----: |
| Prosody Engine (segment-level pauses) | ✅ |    ✅     |   ✅   |
| Metre-aware recitation speed          | ✅ |    ✅     |   ✅   |

**Fix applied (FEAT-1 / FEAT-8)**: Both `_generate_prosody_audio()` (gTTS) and `_generate_edge_prosody()` (edge-tts) in the mobile and desktop `tts_bridge.py` now invoke `MarathiProsodyEngine.segment_text()` to split prose into clause/sentence segments with calibrated silence pauses (180–900 ms). Metre-aware recitation speed (rate < 1.0 for verse) is propagated through the same prosody path. Prose > 250 chars also routes through the streaming/chunking path (FEAT-2) which chains per-sentence audio with sequential playback.

### 2. ✅ SHIPPED — Desktop Streaming/Chunking for Long Simple Text

**Problem**: Desktop's `tts_bridge.py` sent the full text to gTTS in one shot. For texts > 250 chars, mobile has streaming, web has DRF streaming views, but desktop did not.

**Fix applied**: `TtsController.dispatchGeneration()` routes Marathi prose >250 chars (non-verse) to `runStreamingGeneration()`. `splitSentences()` splits at ।, ॥, ?, !, ., ; with 20-char minimum fragment merging. Chunks generated via 3-thread pool + Semaphore(3) concurrency limit. `AudioPlayerUtil.playQueue()` chains sequential multi-file playback. `onSaveAudio()` concatenates chunk MP3s. Status: "Streaming: N of M ✓".

### 3. ✅ SHIPPED — Grammar Engine Now Applied in All Bridges

**Problem**: The `MarathiGrammarEngine.process()` pipeline ran fully on Web but the bridges on Desktop/Mobile only called `_normalize_marathi()`. If the import failed, grammar was silently skipped.

**Fix applied**: Added `_apply_grammar()` lazy singleton to both mobile and desktop `tts_bridge.py`. Wraps `MarathiGrammarEngine` with try/except safety (returns original text on failure). Applied in `generate_tts()` after prose preprocessing, before all TTS stages. Excluded for verse, Sanskrit, and English text. Idempotent — safe to double-apply when TTSEngine Stage 1 also runs grammar internally.

---

## 🟠 HIGH PRIORITY — Verse/Stotra TTS

### 4. ✅ SHIPPED — MetreEngine Gaṇa Pattern Matching + New Metres

**Problem**: The syllabic metre matching ([_match_syllabic_metre](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#496-527)) uses average syllable count across all lines with ±2 tolerance. This works for homogeneous texts but **misidentifies mixed-metre stotras** (e.g., a stotra that opens with Anushtubh and switches to Shardula-vikridita). It also can't distinguish:

- **Indravajra** (11 syllables, pattern: ¯¯⌣¯¯⌣⌣¯⌣¯¯) from **Trishtubh** (also 11 syllables but different gaṇa pattern)
- **Upajati** (mixed Indravajra + Vamshastha) from Trishtubh

**Recommendation**:

- Add **gaṇa (metrical foot) pattern matching** — classify each syllable as laghu (⌣) or guru (¯) and match against known gaṇa sequences
- Support **per-verse metre detection** (not just per-paragraph) so mixed-metre works like Meghaduta or Shivanandalahari get correct prosody per shloka
- Add these missing but common metres: **Upajati, Indravajra, Vamshastha, Rathoddhatā, Sragdharā** (21 syllables — the longest classical metre)

### 5. ✅ SHIPPED — Sandhi Engine Missing Key Rules

**Problem**: The [SandhiEngine](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/sandhi_engine.py#254-408) handles avagraha, visarga+vowel, and anusvara+sibilant, but misses:

| Missing Rule                              | Example                                                       | Impact                                     |
| ----------------------------------------- | ------------------------------------------------------------- | ------------------------------------------ |
| **Visarga + voiced consonant** → r | `पुनः + दर्शनम्` → `पुनर्दर्शनम्` | Common in stotras                          |
| **Vowel sandhi** (a+i→e, a+u→o)   | `महा + ईश्वर` → `महेश्वर`                 | Already written in text, but TTS may split |
| **Pada-final m→anusvara**          | In verse recitation, final म् often nasalizes               | Recitation quality                         |

**Recommendation**: Add `fix_visarga_voiced_consonant()` step to the pipeline. This is the second most impactful sandhi rule after visarga+vowel.

### 6. ✅ SHIPPED — Yati (Caesura) Pauses Implemented

**Problem**: [MetreDefinition](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#153-170) has a [pause_yati_ms](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#325-328) field (e.g., 200ms for Anushtubh, 280ms for Mandakranta), and the [apply_to_segments()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#419-448) method references it, but **no code actually inserts yati pauses within a pāda**. The pause is only applied at danda (।) and double-danda (॥) boundaries.

**Recommendation**: In [_segment_verse_block()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#194-261), detect the yati position within each pāda based on the detected metre:

- **Anushtubh**: yati after syllable 4 (the pāda's rhythmic pivot)
- **Mandākrāntā**: yati after syllables 4, 6, 7 (three caesurae!)
- **Shārdūlavikrīḍita**: yati after syllables 12, 7

Insert [TextSegment](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#43-54) splits at yati points with [pause_yati_ms](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#325-328) silence. This is what makes human recitation sound musical vs. robotic.

### 7. ✅ SHIPPED — Old Marathi Ovi: Rhythmic Pulse

**Problem**: Ovi metre has a specific rhythmic pulse — lines 1-3 should be read at the same tempo with matching cadence, and line 4 (the shorter cadence line) should slow down. Currently, all 4 lines get identical `tts_rate` and `pause_after_ms`.

**Recommendation**:

- Lines 1-3: `tts_rate=0.82`, `pause_after_ms=400ms` (flowing, musical)
- Line 4 (cadence): `tts_rate=0.75`, `pause_after_ms=800ms` (slow, conclusive)
- Between stanzas: `pause_after_ms=1200ms` with pitch reset
- The rhyme group detection ([_find_rhyme_groups](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#532-555)) already finds lines 1-3 — use this to identify the cadence line

---

## 🟡 MEDIUM PRIORITY — Both Simple & Verse

### 8. ✅ SHIPPED — Edge-TTS Per-Segment SSML Prosody

**Problem**: Both bridges use `edge-tts` (Microsoft Neural voices — `mr-IN-AarohiNeural`, `mr-IN-ManoharNeural`), which **supports SSML** including `<break>`, `<prosody rate/pitch>`, and `<emphasis>`. But the current code sends plain text only, relying on audio-level post-processing (pydub speed/pitch) which degrades quality.

**Recommendation**: Generate SSML for edge-tts calls:

```xml
<speak version="1.0" xmlns="..." xml:lang="mr-IN">
  <prosody rate="0.85" pitch="-2st">
    नमस्ते सर्वेभ्यः
  </prosody>
  <break time="650ms"/>
  <prosody rate="0.80">
    ॐ नमः शिवाय
  </prosody>
</speak>
```

This would give **native neural-quality** prosody instead of pydub resampling artifacts. The [TextSegment](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#43-54) dataclass already has all the fields needed (`pause_after_ms`, `tts_rate`, `pitch_shift`, [emphasis](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#409-428)).

### 9. ✅ SHIPPED — Emotion-Adaptive Voice Connected to Verse Mode

**Problem**: The emotion analyzer detects `devotional` and `peaceful` emotions (ideal for stotras), but verse mode (`is_verse=True`) doesn't use emotion parameters to adjust voice. A stotra detected as `devotional` should have different prosody than one detected as `peaceful` or `neutral`.

**Recommendation**: Map emotions to prosody modifiers for verse mode:

| Emotion                         | Rate   | Pitch                   | Pause Scale           |
| ------------------------------- | ------ | ----------------------- | --------------------- |
| `devotional`                  | ×0.90 | -1st (deeper, reverent) | ×1.2 (longer pauses) |
| `peaceful`                    | ×0.85 | 0 (neutral)             | ×1.3                 |
| `neutral`                     | ×1.0  | 0                       | ×1.0                 |
| `happy` (celebration stotras) | ×1.05 | +1st                    | ×0.9                 |

### 10. ⏭️ DEFERRED — Stotra Library: Pre-Recorded Audio on Mobile

**Problem**: The feature matrix shows `Stotra library: ✅ Desktop, ✅ (text) Mobile`. Desktop has pre-recorded audio files in `stotras/` directory that the bridge matches via fingerprinting. Mobile only has the text catalog — no pre-recorded playback.

**Recommendation**: Bundle the same pre-recorded stotra audio files into the mobile APK's `assets/stotras/` directory. The fingerprint matching logic already exists in [tts_bridge.py](file:///d:/marathi_tts/marathi_tts_desktop/python_bridge/tts_bridge.py) — it just needs the audio files.

### 11. ✅ SHIPPED — Pitch Contour Implemented

**Problem**: [MetreDefinition](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#153-170) has `pitch_contour` field (`'rising'`, `'falling'`, `'wave'`, `'level'`) and [TextSegment](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#43-54) has `pitch_shift`, but nothing connects them. The pitch contour is **documented but not applied** — all segments get `pitch_shift=0.0`.

**Recommendation**: Implement pitch contour application in [_apply_metre_prosody()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#148-182):

- `'wave'`: Segments 1,3,5... get `+0.5st`, segments 2,4,6... get `-0.5st` (gentle wave)
- `'falling'`: Progressive `-0.3st` per segment within a stanza (natural verse descent)
- `'rising'`: Progressive `+0.3st` (for celebratory/invocatory passages)
- `'level'`: No change (prose-like)

This is what makes human recitation sound musical. Combined with SSML (recommendation #8), this would be transformative.

---

## 🟢 LOWER PRIORITY — Polish & Quality of Life

### 12. ✅ SHIPPED — Schwa Deletion Lexicon Expanded to 220+ Entries

**Problem**: The current `_SCHWA_DELETION_LEXICON` has only ~20 words. Schwa deletion is the **#1 pronunciation difference** between Hindi and Marathi. gTTS `lang=mr` handles many cases, but there are systematic gaps — especially for:

- Compound words: `शेतकरी` (shet-kri, not she-ta-ka-ri)
- Verb forms: `बोलतो` (bol-to), `करतो` (kar-to)
- Place names: `पुणेकर` (pu-ṇe-kar), `मुंबईकर` (mum-bai-kar)

**Recommendation**: Expand the lexicon to 200+ entries, sourced from:

- Marathi pronunciation dictionaries (मराठी उच्चार कोश)
- Common mispronunciation reports from user feedback
- Systematic suffix-based patterns (e.g., all `-कर` suffix words delete middle schwa)

### 13. ✅ SHIPPED — Abhanga Rhythmic Refrain Detection

**Problem**: Abhangas often have a **refrain (धृवपद)** — a repeated line/phrase that appears at fixed intervals. Currently this is not detected. The refrain should have slightly different prosody (familiar, call-like) vs. new stanza lines (declarative).

**Recommendation**: Detect repeated text segments across stanzas and mark them with `emphasis=1.1` and a slight pitch boost. This makes the TTS recitation sound like actual kirtan/bhajan singing.

### 14. ✅ SHIPPED — Morphological Analysis / Dictionary Lookup

| Feature                            | Web | Desktop | Mobile |
| ---------------------------------- | :-: | :-----: | :----: |
| Morphological analysis (Morfessor) | ✅ |   ✅   |   ✅   |
| Rule-based suffix stripping        | ✅ |   ✅   |   ✅   |

**Shipped**: New `tts/utils/text/morphological_analyzer.py` — `MarathiMorphologicalAnalyzer`
with ~70 rule-based suffix rules (all platforms) + optional Morfessor model for web/desktop
(`tts/morph/morfessor/mr.model`). Integrated into:
- **G2P engine** explicit schwa mode: ZWNJ inserted at morpheme boundaries → prevents
  edge-tts glide insertion between stem/suffix.
- **Grammar engine** `remove_repetitions()`: stem-aware Pass 2 collapses inflectional
  duplicate pairs (e.g., `बोलतो बोलते` → `बोलतो`). All 3 platforms (FEAT-33).

### 15. ✅ SHIPPED — Chandrabindu Nasalization via Edge-TTS Volume

**Problem**: In [apply_old_marathi_phonetics()](file:///d:/marathi_tts/marathi_tts_desktop/python_bridge/tts_bridge.py#76-77), chandrabindu (ँ) and anusvara (ं) are both preserved — which is correct. But the **documentation notes** that chandrabindu is "lighter nasalization" without any actual TTS difference. gTTS treats them identically.

**Recommendation**: For edge-tts (which supports SSML), chandrabindu syllables could get a `<prosody volume="-3dB">` wrapper to simulate lighter nasalization. Minor but adds authenticity for Old Marathi poetry.

### 16. Dead Code in [_segment_verse_block()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#194-261)

**Problem**: In [prosody_engine.py:251-260](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#L251-L260), there is unreachable code after `return segments` on line 249. Steps 4 and 5 (speaking rate scaling, emphasis marking) are dead code inside [_segment_verse_block()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#194-261) — they already run in the parent [segment_text()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#69-143) method.

**Recommendation**: Remove lines 251-260 to clean up the dead code.

---

## � BUG FIXES — Discovered During Code Audit

> Items #17-33 were discovered during a deep code audit on 2026-03-03.
> Items marked ✅ FIXED have already been resolved.

### 17. ✅ FIXED — SPECIAL_CHARS Destroys Double-Danda (॥)

**Problem**: `text_constants.py` `SPECIAL_CHARS` dict mapped `'॥': '।'`, converting all double-dandas to single-dandas before `ProsodyEngine._is_verse_block()` could count `॥` markers. This broke verse-vs-prose detection for **all stotra recitation** — the engine could no longer distinguish full-verse (॥) from half-verse (।) boundaries, losing calibrated pause differences.

**Fix applied**: Removed `'॥': '।'` from `SPECIAL_CHARS` in all 3 platforms. Added explanatory comment about why `॥` must be preserved.

### 18. G2P `_process_anusvara()` Is a No-Op

**Severity**: 🔴 HIGH

**Problem**: In [g2p_engine.py](marathi_tts_web/tts/utils/phonetic/g2p_engine.py), `_process_anusvara()` (line ~188) has extensive docstring documenting anusvara assimilation rules, but the method body is simply `return word`. The `ANUSVARA_ASSIMILATION` dict in [g2p_constants.py](marathi_tts_web/tts/constants/g2p_constants.py) maps following consonants to their varga nasals (e.g., `क→ङ्`, `च→ञ्`, `ट→ण्`, `त→न्`, `प→म्`), but this dict is **never used**.

Currently gTTS handles anusvara reasonably, but when moving to edge-tts SSML (#8), explicit anusvara processing will be essential. The safe approach: implement the logic now but gate it behind a flag so it's ready when needed.

**Recommendation**: Implement the anusvara assimilation using `ANUSVARA_ASSIMILATION` and `ANUSVARA_NASALIZE_ONLY` from `g2p_constants.py`. Add a constructor parameter `anusvara_mode='preserve'` (default safe) with option `'assimilate'` for when edge-tts SSML is enabled.

### 19. G2P `_apply_schwa_rules()` Is Essentially a No-Op

**Severity**: 🔴 HIGH

**Problem**: `_apply_schwa_rules()` in [g2p_engine.py](marathi_tts_web/tts/utils/phonetic/g2p_engine.py) (line ~256) only checks the `SCHWA_EXCEPTIONS` dict (8 entries) and returns the word unchanged. No rule-based schwa deletion is implemented. `SCHWA_DELETE_SUFFIXES` and `SCHWA_PRESERVE_CLUSTERS` are defined in `g2p_constants.py` but never used.

Like #18, gTTS's `lang=mr` model handles basic schwa deletion, but the engine claims to do it and doesn't. The constants are there, the infrastructure is there — the logic just needs to be connected.

**Recommendation**: Implement suffix-based schwa prediction using `SCHWA_DELETE_SUFFIXES` and `SCHWA_PRESERVE_CLUSTERS`. Gate behind `schwa_mode='gtts'` (trust gTTS) vs `'explicit'` (apply rules). This prepares for edge-tts migration where schwa handling must be explicit.

### 20. No Audio Caching

**Severity**: 🟡 MEDIUM

**Problem**: Every call to `generate_tts()` in both mobile and desktop bridges performs a full gTTS/edge-tts API call, even for identical text. Stotras that users recite repeatedly pay the full network + generation cost each time.

**Recommendation**: Implement hash-based audio caching in the bridges: `SHA256(text + engine + voice + params)` → cached audio file path. Check existence before generating. Add cache size limit (50 MB default) with LRU eviction. This is especially impactful for the stotra library.

### 21. No Network Connectivity Pre-Check

**Severity**: 🟡 MEDIUM

**Problem**: Both gTTS and edge-tts require network access, but neither bridge checks connectivity before making API calls. On mobile with flaky networks, the user waits for a long timeout before getting a generic error.

**Recommendation**: Add a lightweight connectivity check (socket connect to `translate.google.com:443` or `speech.platform.bing.com:443` with 3-second timeout) before TTS generation. Return a structured error immediately if offline: `{"success": false, "error_code": "NO_NETWORK", "message": "..."}`.

### 22. ✅ FIXED — Abbreviation Lists Duplicated

**Problem**: Mobile `tts_bridge.py` had its own `_MARATHI_ABBREV` regex list, duplicating abbreviations already in `text_constants.py` but missing several entries.

**Fix applied**: Added 5 missing abbreviations to shared `text_constants.py ABBREVIATIONS` in all 3 platforms: `स्व.→स्वर्गीय`, `कि.मी.→किलोमीटर`, `नं.→नंबर`, `पृ.→पृष्ठ`, `मु.पो.→मुक्काम पोस्ट`.

### 23. English-to-Devanagari Transliteration Is Mobile-Only

**Severity**: 🟠 HIGH

**Problem**: Mobile's `tts_bridge.py` has `_ENGLISH_TO_DEVNAGARI` (~80 common English words → Devanagari) plus `_transliterate_english_char_level()` for unknown words. Desktop and Web lack this entirely — raw ASCII English words get sent to gTTS/edge-tts which either mangles them or speaks English mid-Marathi-sentence.

**Recommendation**: Move the transliteration dict and functions to a shared module (`tts/utils/text/english_transliterator.py`) and wire it into all 3 platforms. This is the single most impactful code-sharing improvement.

### 24. ✅ FIXED — MarathiTextNormalizer Re-Instantiated Per Call

**Problem**: `_normalize_marathi()` in mobile and desktop bridges created a new `MarathiTextNormalizer()` on every call, paying the `IndicNormalizerFactory` init cost repeatedly.

**Fix applied**: Changed to `hasattr`-based lazy singleton pattern in both bridges.

### 25. No Timeout or Retry on gTTS/edge-tts

**Severity**: 🟠 HIGH

**Problem**: gTTS `save()` and edge-tts `Communicate().save()` make HTTP calls with no explicit timeout. A single slow or hung request blocks the entire TTS pipeline indefinitely. Mobile streaming (3 concurrent calls) is especially vulnerable — one hung call can stall the whole batch.

**Recommendation**: Wrap gTTS/edge-tts calls with:

1. Timeout: 30 seconds for gTTS, 45 seconds for edge-tts (neural generation is slower)
2. Retry: Up to 2 retries with exponential backoff (2s, 4s)
3. On final failure: return structured error, don't hang

### 26. Pydub Pitch/Speed Is Naive

**Severity**: 🟢 LOW (will be superseded by SSML — see #8)

**Problem**: Both bridges use `pydub`'s `speedup()` and manual sample-rate manipulation for pitch shifting. `pydub.speedup()` uses a naive overlap-add that introduces artifacts at extreme values. Sample-rate pitch shifting also changes duration.

**Recommendation**: Document this as a known limitation. The real fix is to move to edge-tts SSML (#8) where `<prosody rate="X" pitch="Yst">` is applied at the neural model level with no quality loss. In the meantime, clamp values: speed ∈ [0.75, 1.25], pitch ∈ [-3st, +3st].

### 27. No Temp File Cleanup on Mobile

**Severity**: 🟡 MEDIUM

**Problem**: Mobile's `tts_bridge.py` generates audio files in the `output/` directory but never cleans up old files. On storage-limited Android devices, stale audio files accumulate indefinitely.

**Recommendation**: Add cleanup at bridge initialization: delete files in `output/` older than 24 hours. Also add a total size cap (default 100 MB) — if exceeded, delete oldest files first.

### 28. ✅ FIXED — Desktop indicnlp Bare Import Crash

**Problem**: Desktop's `text_normalizer.py` imported `from indicnlp.normalize...` without a try/except guard. If `indicnlp` was not installed, the entire normalizer module failed to load.

**Fix applied**: Added try/except guard matching mobile's pattern. Falls back to `IndicNormalizerFactory = None`.

### 29. ✅ FIXED — Inconsistent NFC Normalization

**Problem**: Unicode NFC normalization was applied inconsistently — `g2p_engine.py` did NFC but the bridges didn't, so lexicon lookups could miss entries due to different Unicode representations of the same Devanagari text.

**Fix applied**: Added `unicodedata.normalize('NFC', text)` at the start of `_normalize_marathi()` in both bridges.

### 30. ✅ FIXED — Visarga Double-Processing

**Problem**: `text_normalizer.py` applied `VISARGA_WORDS` substitutions, then `g2p_engine._process_visarga()` ran on the same text — causing words like दुःख, नमः, स्वतः to be double-processed. The normalizer's generic `'ः'→'हा'` fallback was especially destructive.

**Fix applied**: Removed `VISARGA_WORDS` application from `text_normalizer.normalize_text()` in all 3 platforms. The G2P engine is now the sole visarga handler.

### 31. No Structured Error Codes in Bridges

**Severity**: 🟢 LOW

**Problem**: Bridge error responses use free-text messages like `"Error occurred: ..."`. Kotlin/JavaFX callers must string-match to determine failure type (network error vs. invalid input vs. engine error). This makes error handling fragile and locale-dependent.

**Recommendation**: Define error code constants:

```python
ERR_NO_NETWORK = "NO_NETWORK"
ERR_TTS_TIMEOUT = "TTS_TIMEOUT"
ERR_INVALID_INPUT = "INVALID_INPUT"
ERR_ENGINE_INIT = "ENGINE_INIT_FAILED"
ERR_AUDIO_SAVE = "AUDIO_SAVE_FAILED"
```

Return these in `result["error_code"]` alongside the human-readable message.

### 32. ✅ SHIPPED — Test Coverage: Sections I/J/K Added

**Severity**: 🟡 MEDIUM

**Problem**: `test_all_platforms.py` covers Sandhi, MetreEngine, ProsodyEngine, and phonetics, but does **not** test:

- `TextNormalizer.normalize_text()` — abbreviation expansion, number conversion, normalization pipeline
- `MarathiGrammarEngine.process()` — spelling fixes, sandhi, vibhakti
- `number_to_words` — edge cases in `convert_time()`, `convert_date()`, large numbers
- Bridge preprocessing — `_normalize_marathi()`, English transliteration pipeline

**Recommendation**: Add Section H (Normalizer), Section I (Grammar), Section J (Number conversion) to `test_all_platforms.py`. This would catch regressions in the most frequently-changed modules.

### 33. `convert_time()` :45 Edge Case

**Severity**: 🟡 MEDIUM

**Problem**: In [number_to_words.py](marathi_tts_web/tts/utils/text/number_to_words.py) `convert_time()`, the `:45` (quarter-to) path does:

```python
elif minute == 45:
    parts.append('पावणे ' + number_to_marathi_words(hour + 1))
    return ' '.join(parts[:1] + parts[-1:])  # skip hour word
```

When **no AM/PM period** is present, `parts` has only `[hour_word, 'पावणे X']`, so `parts[:1]` grabs the current hour word (wrong) and `parts[-1:]` grabs the पावणे phrase. Result: `"तीन पावणे चार"` instead of `"पावणे चार"`.

When AM/PM **is** present, `parts[:1]` correctly grabs the period text (e.g., `'दुपारचे'`) and the hour word in the middle is skipped.

**Recommendation**: Fix the :45 path to explicitly construct the result based on whether period text exists, rather than using fragile index slicing.

---

## 🀽� Prioritized Implementation Roadmap

| Priority | #  | Enhancement                                     | Impact | Effort  | Platforms       | Status     |
| -------- | -- | ----------------------------------------------- | ------ | ------- | --------------- | ---------- |
| 🔴       | 1  | Wire prosody engine into Mobile/Desktop bridges | 🔥🔥🔥 | Medium  | Mobile, Desktop | ✅ SHIPPED |
| 🔴       | 2  | Desktop streaming/chunking for long text        | 🔥🔥   | Medium  | Desktop         | ✅ SHIPPED |
| 🔴       | 3  | Grammar engine as hard dependency               | 🔥     | Low     | Desktop, Mobile | ✅ SHIPPED |
| 🔴       | 17 | SPECIAL_CHARS destroys double-danda (॥)        | 🔥🔥🔥 | Trivial | All             | ✅ FIXED   |
| 🔴       | 18 | G2P `_process_anusvara()` is a no-op          | 🔥🔥   | Medium  | All             | ✅ FIXED   |
| 🔴       | 19 | G2P `_apply_schwa_rules()` is a no-op         | 🔥🔥   | Medium  | All             | ✅ FIXED   |
| 🟠       | 4  | Add gaṇa matching + missing metres to MetreEngine | 🔥🔥 | High   | All             | ✅ SHIPPED |
| 🟠       | 5  | Visarga + voiced consonant sandhi rule          | 🔥     | Low     | All             | ✅ SHIPPED |
| 🟠       | 6  | Implement yati (caesura) pauses in verse mode   | 🔥🔥🔥 | Medium  | All             | ✅ SHIPPED |
| 🟠       | 7  | Ovi rhythmic pulse (line 4 cadence slowdown)    | 🔥🔥   | Low     | All             | ✅ SHIPPED |
| 🟠       | 23 | English transliteration is mobile-only          | 🔥🔥   | Medium  | All             | ✅ FIXED   |
| 🟠       | 25 | No timeout/retry on gTTS/edge-tts               | 🔥🔥   | Medium  | All             | ✅ FIXED   |
| 🟡       | 8  | Use edge-tts SSML for native prosody            | 🔥🔥🔥 | Medium  | Desktop, Mobile | ✅ SHIPPED |
| 🟡       | 9  | Emotion → verse prosody mapping                | 🔥     | Low     | All             | ✅ SHIPPED |
| 🟡       | 10 | Pre-recorded stotra audio on Mobile             | 🔥     | Low     | Mobile          | ⏭️ DEFERRED |
| 🟡       | 11 | Implement pitch contour from MetreDefinition    | 🔥🔥   | Low     | All             | ✅ SHIPPED |
| 🟡       | 12 | Expand schwa deletion lexicon                   | 🔥     | Medium  | All             | ✅ SHIPPED |
| 🟡       | 20 | No audio caching                                | 🔥     | Medium  | All             | ✅ FIXED   |
| 🟡       | 21 | No network connectivity pre-check               | 🔥     | Low     | Mobile, Desktop | ✅ FIXED   |
| 🟡       | 22 | Abbreviation lists duplicated                   | 🔥     | Trivial | All             | ✅ FIXED   |
| 🟡       | 24 | Normalizer re-instantiated per call             | 🔥     | Trivial | Mobile, Desktop | ✅ FIXED   |
| 🟡       | 27 | No temp file cleanup on mobile                  | 🔥     | Low     | Mobile, Desktop | ✅ FIXED   |
| 🟡       | 28 | Desktop indicnlp bare import crash              | 🔥     | Trivial | Desktop         | ✅ FIXED   |
| 🟡       | 29 | Inconsistent NFC normalization                  | 🔥     | Trivial | Mobile, Desktop | ✅ FIXED   |
| 🟡       | 30 | Visarga double-processing                       | 🔥🔥   | Low     | All             | ✅ FIXED   |
| 🟡       | 32 | Test coverage gaps                              | 🔥     | High    | All             | ✅ SHIPPED |
| 🟡       | 33 | `convert_time()` :45 edge case                | 🔥     | Trivial | All             | ✅ FIXED   |
| 🟢       | 13 | Abhanga refrain detection                       | ⭐     | Medium  | All             | ✅ SHIPPED |
| 🟢       | 14 | Morphological analysis on Mobile/Desktop        | ⭐     | High    | Mobile, Desktop | ✅ SHIPPED |
| 🟢       | 15 | Chandrabindu lighter nasalization via SSML      | ⭐     | Low     | Mobile, Desktop | ✅ SHIPPED |
| 🟢       | 16 | Dead code in prosody_engine.py                  | 🧹     | Trivial | All             | ✅ FIXED   |
| 🟢       | 26 | Pydub pitch/speed is naive                      | ⭐     | N/A     | Mobile, Desktop | ✅ FIXED   |
| 🟢       | 31 | No structured error codes                       | ⭐     | Medium  | Mobile, Desktop | ✅ FIXED   |

---

> [!TIP]
> The single highest-impact change is **#1 + #8 together**: wiring the prosody engine into all platforms AND using SSML with edge-tts. This would give each platform natural breathing pauses + neural-quality pitch/rate control — no pydub artifacts.
> **Both are now SHIPPED.** _generate_prosody_audio() handles gTTS path; _generate_edge_prosody() handles edge-tts path.

> [!IMPORTANT]
> Since the Python phonetic modules are shared across all 3 platforms (identical source files), improvements to [marathi_phonetics.py](marathi_tts_web/tts/utils/phonetic/marathi_phonetics.py), [sandhi_engine.py](marathi_tts_web/tts/utils/phonetic/sandhi_engine.py), [metre_engine.py](marathi_tts_web/tts/utils/phonetic/metre_engine.py), and [prosody_engine.py](marathi_tts_web/tts/utils/audio/prosody_engine.py) automatically benefit **all platforms** once the bridges properly invoke them.
>
> **All 17 bug-fix items are resolved** (#17-33 plus #16 dead code). **All feature enhancements are shipped** (#1-15, #32, and #33 — morphological analyzer). The only deferred item is #10 (mobile pre-recorded stotra audio — requires APK asset bundling). The roadmap is otherwise complete.
