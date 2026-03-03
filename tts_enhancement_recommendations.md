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

### 1. Prosody Engine Missing on Desktop & Mobile

| Feature | Web | Desktop | Mobile |
|---------|:---:|:-------:|:------:|
| Prosody Engine (segment-level pauses) | ✅ | ❌ Partial | ❌ None |
| Metre-aware recitation speed | ✅ | ❌ Partial | ❌ None |

**Problem**: The [MarathiProsodyEngine](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#59-446) exists in all three [tts/utils/audio/prosody_engine.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py) files, but looking at the mobile [tts_bridge.py](file:///d:/marathi_tts/marathi_tts_desktop/python_bridge/tts_bridge.py) (592 lines) vs desktop [tts_bridge.py](file:///d:/marathi_tts/marathi_tts_desktop/python_bridge/tts_bridge.py) (952 lines), the mobile bridge does **not** invoke the prosody engine's [segment_text()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#69-143) to split prose into natural clause/sentence segments with calibrated pauses. It sends the entire text as one chunk to gTTS.

**Recommendation**: Wire `MarathiProsodyEngine.segment_text()` into the mobile and desktop [generate_tts()](file:///d:/marathi_tts/marathi_tts_mobile/app/src/main/python/tts_bridge.py#424-573) flows. This alone will make simple prose sound dramatically more natural — with breathing pauses at commas, conjunctions (आणि, परंतु, म्हणून), and sentence breaks.

### 2. No Streaming/Chunking for Long Simple Text on Desktop

**Problem**: Desktop's [tts_bridge.py](file:///d:/marathi_tts/marathi_tts_desktop/python_bridge/tts_bridge.py) sends the full text to gTTS in one shot. For texts > 250 chars, mobile has streaming (`generateAudioStreaming()`), web has DRF streaming views, but desktop does not.

**Recommendation**: Implement segment-based generation on Desktop:
1. Use `MarathiProsodyEngine.segment_text()` to split
2. Generate audio per segment (parallel with `ThreadPoolExecutor(max_workers=3)`)
3. Stitch with calibrated silence gaps from `TextSegment.pause_after_ms`
4. This also enables a progress indicator and cancel button (like mobile v5.3.0)

### 3. Grammar Engine Not Applied Consistently

**Problem**: The `MarathiGrammarEngine.process()` pipeline (spelling → sandhi → vibhakti → word order → commas → punctuation) runs fully on Web but the bridges on Desktop/Mobile only call [_normalize_marathi()](file:///d:/marathi_tts/marathi_tts_mobile/app/src/main/python/tts_bridge.py#252-262) which is a thin wrapper. If the import fails, grammar is silently skipped.

**Recommendation**: Make grammar processing a hard dependency on all platforms. The grammar engine is pure Python with no heavy deps — it should never fail to import.

---

## 🟠 HIGH PRIORITY — Verse/Stotra TTS

### 4. MetreEngine Detection Confidence Is Too Coarse

**Problem**: The syllabic metre matching ([_match_syllabic_metre](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#496-527)) uses average syllable count across all lines with ±2 tolerance. This works for homogeneous texts but **misidentifies mixed-metre stotras** (e.g., a stotra that opens with Anushtubh and switches to Shardula-vikridita). It also can't distinguish:
- **Indravajra** (11 syllables, pattern: ¯¯⌣¯¯⌣⌣¯⌣¯¯) from **Trishtubh** (also 11 syllables but different gaṇa pattern)
- **Upajati** (mixed Indravajra + Vamshastha) from Trishtubh

**Recommendation**:
- Add **gaṇa (metrical foot) pattern matching** — classify each syllable as laghu (⌣) or guru (¯) and match against known gaṇa sequences
- Support **per-verse metre detection** (not just per-paragraph) so mixed-metre works like Meghaduta or Shivanandalahari get correct prosody per shloka
- Add these missing but common metres: **Upajati, Indravajra, Vamshastha, Rathoddhatā, Sragdharā** (21 syllables — the longest classical metre)

### 5. Sandhi Engine Missing Key Rules

**Problem**: The [SandhiEngine](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/sandhi_engine.py#254-408) handles avagraha, visarga+vowel, and anusvara+sibilant, but misses:

| Missing Rule | Example | Impact |
|---|---|---|
| **Visarga + voiced consonant** → r | `पुनः + दर्शनम्` → `पुनर्दर्शनम्` | Common in stotras |
| **Vowel sandhi** (a+i→e, a+u→o) | `महा + ईश्वर` → `महेश्वर` | Already written in text, but TTS may split |
| **Pada-final m→anusvara** | In verse recitation, final म् often nasalizes | Recitation quality |

**Recommendation**: Add `fix_visarga_voiced_consonant()` step to the pipeline. This is the second most impactful sandhi rule after visarga+vowel.

### 6. No Yati (Caesura) Pause Implementation

**Problem**: [MetreDefinition](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#153-170) has a [pause_yati_ms](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#325-328) field (e.g., 200ms for Anushtubh, 280ms for Mandakranta), and the [apply_to_segments()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#419-448) method references it, but **no code actually inserts yati pauses within a pāda**. The pause is only applied at danda (।) and double-danda (॥) boundaries.

**Recommendation**: In [_segment_verse_block()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#194-261), detect the yati position within each pāda based on the detected metre:
- **Anushtubh**: yati after syllable 4 (the pāda's rhythmic pivot)
- **Mandākrāntā**: yati after syllables 4, 6, 7 (three caesurae!)
- **Shārdūlavikrīḍita**: yati after syllables 12, 7

Insert [TextSegment](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#43-54) splits at yati points with [pause_yati_ms](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#325-328) silence. This is what makes human recitation sound musical vs. robotic.

### 7. Old Marathi Ovi: No Rhythmic Pulse

**Problem**: Ovi metre has a specific rhythmic pulse — lines 1-3 should be read at the same tempo with matching cadence, and line 4 (the shorter cadence line) should slow down. Currently, all 4 lines get identical `tts_rate` and `pause_after_ms`.

**Recommendation**:
- Lines 1-3: `tts_rate=0.82`, `pause_after_ms=400ms` (flowing, musical)
- Line 4 (cadence): `tts_rate=0.75`, `pause_after_ms=800ms` (slow, conclusive)
- Between stanzas: `pause_after_ms=1200ms` with pitch reset
- The rhyme group detection ([_find_rhyme_groups](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#532-555)) already finds lines 1-3 — use this to identify the cadence line

---

## 🟡 MEDIUM PRIORITY — Both Simple & Verse

### 8. Edge-TTS SSML Not Utilized

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

### 9. Emotion-Adaptive Voice Not Connected to Verse Mode

**Problem**: The emotion analyzer detects `devotional` and `peaceful` emotions (ideal for stotras), but verse mode (`is_verse=True`) doesn't use emotion parameters to adjust voice. A stotra detected as `devotional` should have different prosody than one detected as `peaceful` or `neutral`.

**Recommendation**: Map emotions to prosody modifiers for verse mode:
| Emotion | Rate | Pitch | Pause Scale |
|---------|------|-------|-------------|
| `devotional` | ×0.90 | -1st (deeper, reverent) | ×1.2 (longer pauses) |
| `peaceful` | ×0.85 | 0 (neutral) | ×1.3 |
| `neutral` | ×1.0 | 0 | ×1.0 |
| `happy` (celebration stotras) | ×1.05 | +1st | ×0.9 |

### 10. Stotra Library: Text-Only on Mobile, No Pre-Recorded Audio

**Problem**: The feature matrix shows `Stotra library: ✅ Desktop, ✅ (text) Mobile`. Desktop has pre-recorded audio files in `stotras/` directory that the bridge matches via fingerprinting. Mobile only has the text catalog — no pre-recorded playback.

**Recommendation**: Bundle the same pre-recorded stotra audio files into the mobile APK's `assets/stotras/` directory. The fingerprint matching logic already exists in [tts_bridge.py](file:///d:/marathi_tts/marathi_tts_desktop/python_bridge/tts_bridge.py) — it just needs the audio files.

### 11. Pitch Contour Not Actually Implemented

**Problem**: [MetreDefinition](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py#153-170) has `pitch_contour` field (`'rising'`, `'falling'`, `'wave'`, `'level'`) and [TextSegment](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#43-54) has `pitch_shift`, but nothing connects them. The pitch contour is **documented but not applied** — all segments get `pitch_shift=0.0`.

**Recommendation**: Implement pitch contour application in [_apply_metre_prosody()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#148-182):
- `'wave'`: Segments 1,3,5... get `+0.5st`, segments 2,4,6... get `-0.5st` (gentle wave)
- `'falling'`: Progressive `-0.3st` per segment within a stanza (natural verse descent)
- `'rising'`: Progressive `+0.3st` (for celebratory/invocatory passages)
- `'level'`: No change (prose-like)

This is what makes human recitation sound musical. Combined with SSML (recommendation #8), this would be transformative.

---

## 🟢 LOWER PRIORITY — Polish & Quality of Life

### 12. Expand Schwa Deletion Lexicon

**Problem**: The current `_SCHWA_DELETION_LEXICON` has only ~20 words. Schwa deletion is the **#1 pronunciation difference** between Hindi and Marathi. gTTS `lang=mr` handles many cases, but there are systematic gaps — especially for:
- Compound words: `शेतकरी` (shet-kri, not she-ta-ka-ri)
- Verb forms: `बोलतो` (bol-to), `करतो` (kar-to)
- Place names: `पुणेकर` (pu-ṇe-kar), `मुंबईकर` (mum-bai-kar)

**Recommendation**: Expand the lexicon to 200+ entries, sourced from:
- Marathi pronunciation dictionaries (मराठी उच्चार कोश)
- Common mispronunciation reports from user feedback
- Systematic suffix-based patterns (e.g., all `-कर` suffix words delete middle schwa)

### 13. Add Abhanga Rhythmic Refrain Detection

**Problem**: Abhangas often have a **refrain (धृवपद)** — a repeated line/phrase that appears at fixed intervals. Currently this is not detected. The refrain should have slightly different prosody (familiar, call-like) vs. new stanza lines (declarative).

**Recommendation**: Detect repeated text segments across stanzas and mark them with `emphasis=1.1` and a slight pitch boost. This makes the TTS recitation sound like actual kirtan/bhajan singing.

### 14. Mobile: No Morphological Analysis or Dictionary Lookup

| Feature | Web | Desktop | Mobile |
|---------|:---:|:-------:|:------:|
| Morphological analysis (Morfessor) | ✅ | ❌ | ❌ |
| Dictionary lookup | ✅ | ❌ | ❌ |

**Recommendation**: These are web-only Python deps. Consider:
- Porting a lightweight Morfessor model to run on Chaquopy
- Or: expose these as an optional API call from mobile → web server (when online)

### 15. Chandrabindu vs Anusvara Distinction

**Problem**: In [apply_old_marathi_phonetics()](file:///d:/marathi_tts/marathi_tts_desktop/python_bridge/tts_bridge.py#76-77), chandrabindu (ँ) and anusvara (ं) are both preserved — which is correct. But the **documentation notes** that chandrabindu is "lighter nasalization" without any actual TTS difference. gTTS treats them identically.

**Recommendation**: For edge-tts (which supports SSML), chandrabindu syllables could get a `<prosody volume="-3dB">` wrapper to simulate lighter nasalization. Minor but adds authenticity for Old Marathi poetry.

### 16. Dead Code in [_segment_verse_block()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#194-261)

**Problem**: In [prosody_engine.py:251-260](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#L251-L260), there is unreachable code after `return segments` on line 249. Steps 4 and 5 (speaking rate scaling, emphasis marking) are dead code inside [_segment_verse_block()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#194-261) — they already run in the parent [segment_text()](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py#69-143) method.

**Recommendation**: Remove lines 251-260 to clean up the dead code.

---

## 📋 Prioritized Implementation Roadmap

| Priority | Enhancement | Impact | Effort | Platforms |
|----------|------------|--------|--------|-----------|
| 🔴 1 | Wire prosody engine into Mobile/Desktop bridges | 🔥🔥🔥 | Medium | Mobile, Desktop |
| 🔴 2 | Desktop streaming/chunking for long text | 🔥🔥 | Medium | Desktop |
| 🟠 3 | Implement yati (caesura) pauses in verse mode | 🔥🔥🔥 | Medium | All |
| 🟠 4 | Use edge-tts SSML for native prosody | 🔥🔥🔥 | Medium | Desktop, Mobile |
| 🟠 5 | Implement pitch contour from MetreDefinition | 🔥🔥 | Low | All |
| 🟠 6 | Add gaṇa pattern matching to MetreEngine | 🔥🔥 | High | All |
| 🟠 7 | Ovi rhythmic pulse (line 4 cadence slowdown) | 🔥🔥 | Low | All |
| 🟡 8 | Emotion → verse prosody mapping | 🔥 | Low | All |
| 🟡 9 | Pre-recorded stotra audio on Mobile | 🔥 | Low | Mobile |
| 🟡 10 | Expand schwa deletion lexicon | 🔥 | Medium | All |
| 🟡 11 | Add missing Sanskrit metres | 🔥 | Medium | All |
| 🟡 12 | Visarga + voiced consonant sandhi rule | 🔥 | Low | All |
| 🟡 13 | Grammar engine as hard dependency | 🔥 | Low | Desktop, Mobile |
| 🟢 14 | Abhanga refrain detection | ⭐ | Medium | All |
| 🟢 15 | Remove dead code in prosody engine | 🧹 | Trivial | Web |

---

> [!TIP]
> The single highest-impact change is **#1 + #4 together**: wiring the prosody engine into all platforms AND using SSML with edge-tts. This would give each platform natural breathing pauses + neural-quality pitch/rate control — no pydub artifacts.

> [!IMPORTANT]  
> Since the Python phonetic modules are shared across all 3 platforms (identical source files), improvements to [marathi_phonetics.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/marathi_phonetics.py), [sandhi_engine.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/sandhi_engine.py), [metre_engine.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/phonetic/metre_engine.py), and [prosody_engine.py](file:///d:/marathi_tts/marathi_tts_web/tts/utils/audio/prosody_engine.py) automatically benefit **all platforms** once the bridges properly invoke them.
