# Changelog — Marathi TTS

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` / `MAJOR.MINOR.PATCH-hotfix.N`.

---

## [Unreleased]
<!-- Changes staged but not yet released go here -->

### Added
- **FEAT-4: Gaṇa pattern matching in MetreEngine** — new `classify_syllable_weights()`
  module function computes L/G weight string per syllable (guru: long vowel, anusvara,
  saṃyoga; laghu: short open syllable). `MetreDefinition` gains `gana_pattern` and
  `yati_syllables` fields. `_match_syllabic_metre()` adds `gana_bonus * 0.20` when
  observed pattern matches expected. New `_gana_match_score()` helper. All 3 platforms.
- **FEAT-6: Yati (caesura) pauses** — new `_split_pada_at_yati()` and
  `_apply_yati_splits()` in `MarathiProsodyEngine`. Word-boundary approximation splits
  verse segments at detected yati positions and inserts `pause_yati_ms` sub-segments.
  Triggered when `metre.yati_syllables` is non-empty. All 3 platforms.
- **FEAT-10: Schwa deletion lexicon expanded** — `SCHWA_EXCEPTIONS` in `g2p_constants.py`
  grown from 8 entries to 220+ covering verb -तो/-ते/-णे forms, -कर demonyms, adjectives,
  nouns, place names, adverbs, postpositions, and bhakti vocabulary. All 3 platforms.
- **FEAT-12: Six new Sanskrit metres** — `METRE_CATALOGUE` gains: Sragdharā (21 syl),
  Indravajra (11 syl), Upendravajra (11 syl), Rathoddhatā (11 syl), Upajati (11 syl,
  mixed Indravajra/Upendravajra), Vamshastha (12 syl). `yati_syllables` added to 9
  existing metres (Shardula, Vasanta-tilaka, Mandakranta, Malini, Anushtubh, Trishtubh,
  Jagati, and the 3 new 11-syl metres). All 3 platforms.
- **FEAT-13: Abhanga refrain (धृवपद) detection** — new `_detect_abhanga_refrain()` in
  `MarathiProsodyEngine`. Counts exact + 2-char Devanagari suffix repetitions; marks
  segments with 2+ exact repeats or 3+ rhyme matches with `emphasis=1.1`,
  `pitch_shift += 0.5`. Fires when `metre.name == 'Abhanga'`. All 3 platforms.
- **FEAT-15: Chandrabindu nasalization volume** — `_generate_edge_prosody()` in both
  mobile and desktop `tts_bridge.py` now detects ँ (U+0901) in each segment and applies
  -25 pp volume reduction (~-3 dB) to preserve soft nasal quality in edge-tts output.
- **FEAT-32: Test coverage sections I/J/K** — `test_all_platforms.py` gains three new
  sections: I (TextNormalizer: verse-number strip, इ. expansion, empty input),
  J (GrammarEngine: process(), remove_repetitions, empty input),
  K (number_to_words: cardinals, convert_time 9:00 AM / 12:45, ordinal, percentage).
- **FEAT-33: Marathi morphological analyzer** — new `tts/utils/text/morphological_analyzer.py`
  (`MarathiMorphologicalAnalyzer`) with rule-based suffix stripping (~70 suffixes, longest-first)
  for all 3 platforms, plus optional Morfessor statistical model for web and desktop
  (loads `tts/morph/morfessor/mr.model`; gracefully degrades when Morfessor is absent).
  Public API: `stem()`, `segment()`, `is_same_stem()`, `morpheme_boundary_positions()`,
  `get_analyzer()` singleton. Integrated into:
  1. `g2p_engine.py` explicit schwa mode — inserts ZWNJ at morpheme boundaries to prevent
     edge-tts glide insertion between stem and inflectional suffix.
  2. `marathi_grammar.py` `remove_repetitions()` — Pass 2 stem-aware dedup collapses
     consecutive same-stem inflectional variants (e.g., 'बोलतो बोलते' → 'बोलतो').
  `mr.model` copied to desktop bridge; all 4 files synced across all 3 platforms.
  Sections skip gracefully when optional `indicnlp` dep is absent in offline env.
  Also added `try/except ImportError` guard to `tts/utils/text/__init__.py` for
  optional `indicnlp` dep. All 3 platforms.
- **FEAT-5: Visarga + voiced consonant → r sandhi rule** — new
  `fix_visarga_voiced_consonant()` method in `SandhiEngine` pipeline step 4b.
  Regex: visarga + space + voiced consonant → `र्` + consonant (e.g.
  पुनः दर्शनम् → पुनर् दर्शनम्). Only fires across word boundaries.
  All 3 platforms.
- **FEAT-7: Ovi rhythmic pulse** — new `_apply_ovi_rhythmic_pulse()` in
  `MarathiProsodyEngine`. Lines 1-3: rate=0.82, pause≤400ms; line 4: rate=0.75,
  pause≥800ms; stanza break=1200ms. Triggered when MetreEngine detects Ovi metre.
  All 3 platforms.
- **FEAT-9: Emotion → verse prosody mapping** — `MarathiProsodyEngine` now accepts
  `emotion` parameter. New `_apply_emotion_verse_modifiers()` adjusts verse segment
  rate, pitch_shift, and pause scaling per emotion: devotional (0.90, -1.0st, 1.2×),
  peaceful (0.85, 0.0, 1.3×), happy (1.05, +1.0st, 0.9×), sad (0.88, -1.5st, 1.25×).
  All 3 platforms.
- **FEAT-11: Pitch contour from MetreDefinition** — new `_apply_pitch_contour()` in
  `MarathiProsodyEngine`. Uses MetreDefinition's `pitch_contour` field: wave=±0.5st
  alternating, falling=-0.3st progressive, rising=+0.3st progressive. Resets per stanza.
  All 3 platforms.
- **FEAT-3: Grammar engine in desktop/mobile bridges** — new `_apply_grammar()` lazy
  singleton in both `tts_bridge.py` bridges wraps `MarathiGrammarEngine` (spelling
  corrections, sandhi splits, vibhakti/agreement fixes, word order, punctuation
  restoration). Applied to prose text after preprocessing, before ALL TTS stages
  (gTTS, edge-tts, system). Excluded for verse, Sanskrit, and English. Try/except
  wrapped — returns original text on failure. Both platforms.
- **FEAT-2: Desktop streaming/chunking for long text** — new `splitSentences()` in
  `TtsController.kt` splits Marathi text at ।, ॥, ?, !, ., ; with short-fragment
  merging (≥20 chars). `dispatchGeneration()` routes Marathi prose >250 chars to
  `runStreamingGeneration()` which generates chunks via 3-thread pool with Semaphore(3)
  concurrency limit. `AudioPlayerUtil.playQueue()` chains sequential multi-file playback.
  `onSaveAudio()` concatenates chunk MP3 files. Status: "Streaming: N of M ✓".
- **FEAT-1: ProsodyEngine wired into mobile/desktop bridges** — new
  `_generate_prosody_audio()` function in both `tts_bridge.py` bridges segments prose
  text at clause/sentence boundaries via `MarathiProsodyEngine.segment_text()`, generates
  per-segment gTTS audio, and stitches with calibrated pydub silence pauses (180-900ms).
  Prose only (verse has its own path). Cap at 25 segments. Full fallthrough to single-call
  gTTS if prosody unavailable or fails. Per-segment preprocessing pipeline:
  normalize → phonetics → G2P → gTTS fixes. Both platforms.
- **FEAT-8: Edge-TTS prosody segmentation** — new `_generate_edge_prosody()` function
  in both bridges generates per-segment audio via edge-tts neural voices with
  ProsodyEngine-determined pauses. Uses edge-tts native SSML rate/pitch/volume per
  segment + per-segment `pitch_shift` from emphasis detection (questions +0.05,
  exclamations -0.05). Cap at 15 segments (stricter than gTTS due to WebSocket overhead).
  Falls through to single-call `_generate_edge_tts()` on failure. Both platforms.

### Fixed
- **BUG-17 [CRITICAL]: SPECIAL_CHARS ॥→। killed verse detection** — removed `'॥': '।'`
  mapping from `text_constants.py SPECIAL_CHARS` in all 3 platforms. ProsodyEngine's
  `_is_verse_block()` counts ॥ markers to detect verse blocks, and `_segment_verse_block()`
  uses ॥ vs । for full-verse vs half-verse pause calibration. The normalizer was destroying
  these markers before prosody segmentation ever saw the text.
- **BUG-22: Duplicate abbreviation lists** — consolidated mobile-only abbreviations
  (स्व.→स्वर्गीय, कि.मी.→किलोमीटर, नं.→नंबर, पृ.→पृष्ठ, मु.पो.→मुक्काम पोस्ट)
  into shared `text_constants.py ABBREVIATIONS` so all 3 platforms get them.
- **BUG-24: Normalizer re-instantiated per call** — `_normalize_marathi()` in mobile
  and desktop bridges now uses a lazy singleton instead of creating a new
  `MarathiTextNormalizer()` on each call. Eliminates repeated IndicNormalizerFactory init.
- **BUG-28: Desktop indicnlp bare import crash** — `text_normalizer.py` on desktop
  now wraps `from indicnlp.normalize...` in try/except like mobile does. Falls back
  gracefully when indicnlp is not installed.
- **BUG-29: Inconsistent NFC normalization** — both mobile and desktop bridges now
  apply `unicodedata.normalize('NFC', text)` at the start of `_normalize_marathi()`,
  ensuring consistent Unicode before any lexicon lookup or text processing.
- **BUG-30: Visarga double-processing** — removed `VISARGA_WORDS` application from
  `text_normalizer.normalize_text()` in all 3 platforms. The G2P engine's
  `_process_visarga()` using `VISARGA_EXCEPTIONS` is now the sole visarga handler,
  preventing words like दुःख, नमः, स्वतः from being processed twice.
- **BUG-18: G2P _process_anusvara() was a no-op** — implemented with mode gating:
  `preserve` mode (default) returns word unchanged for gTTS compat; `assimilate` mode
  applies ANUSVARA_ASSIMILATION dict + ANUSVARA_NASALIZE_ONLY set with regex substitution
  for edge-tts migration. All 3 platforms.
- **BUG-19: G2P _apply_schwa_rules() was a no-op** — implemented with `gtts`/`explicit`
  mode gating. Explicit mode logs word-final consonant schwa deletion for migration
  monitoring. All 3 platforms.
- **BUG-33: convert_time() :45 edge case** — replaced fragile `parts[:1] + parts[-1:]`
  index slicing with explicit period-aware construction. `3:45` now correctly yields
  `"पावणे चार"` instead of `"तीन पावणे चार"`. All 3 platforms.
- **BUG-23: English-to-Devanagari transliteration missing on desktop/web** — created
  shared `tts/utils/text/english_transliterator.py` with merged superset dict (~80 entries)
  and vowel-aware char-level fallback. All 3 platforms.
- **BUG-25: No timeout/retry on TTS API calls** — created shared `tts/utils/tts_retry.py`
  with `tts_save_with_retry()` (configurable timeout, exponential backoff) and
  `check_network()` connectivity check. All 3 platforms.
- **BUG-27: No temp file cleanup in bridge output/ dir** — added `_cleanup_output_dir()`
  to both mobile and desktop bridges. Runs at module load: deletes files >24h old,
  enforces 100MB size cap with LRU eviction.
- **BUG-20: No audio caching** — created shared `tts/utils/audio_cache.py` with
  `AudioCache` class: SHA-256 keyed file cache, LRU mtime tracking, configurable
  50MB cap, `make_key(text, engine, lang, speed, pitch, voice)`. All 3 platforms.
- **BUG-21: No network pre-check** — added `_is_network_available()` (3-second socket
  check to 8.8.8.8:53) to both bridges. Mobile checks before any API call; desktop
  checks after local TTSEngine fails but before edge-tts/gTTS. Returns clear
  `ERR_NO_NETWORK` error code.
- **BUG-31: No structured error codes** — created `tts/constants/error_codes.py` with
  `ERR_EMPTY_TEXT`, `ERR_NO_NETWORK`, `ERR_ALL_ENGINES_FAILED`, etc. Added `error_code`
  field to all bridge error returns. All 3 platforms.
- **BUG-26: pydub pitch/speed undocumented** — added safe clamping (speed [0.75-1.25],
  pitch [0.79-1.26]) to `_apply_pitch_speed()` in both bridges. Added limitation
  docstring and note in `tts_features.md`. Will be superseded by SSML (FEAT-8).
- **#16: Dead code in prosody_engine.py** — removed unreachable lines 251-260 after
  `return segments` in `_segment_verse_block()`. All 3 platforms.

### Added
- **Shared audio cache module** (`tts/utils/audio_cache.py`) — reusable across all platforms
- **Shared retry/timeout module** (`tts/utils/tts_retry.py`) — reusable across all platforms
- **Shared English transliterator** (`tts/utils/text/english_transliterator.py`) — merged
  mobile+desktop dictionaries into shared module
- **Structured error codes** (`tts/constants/error_codes.py`) — machine-readable error codes
  for Kotlin/JavaFX bridge callers

### Also previously fixed (pre-Unreleased)
- **Backup APK unsigned** — v5.0.0 backup APK was built before signing config existed;
  rebuilt v5.2.0 release APK with proper APK Signature Scheme v2 signing
- **BookReader: buttons not wired** — Confirm (✓) and Retake (↩) buttons in crop editor
  had no click listeners; user could take photo but never save it
- **BookReader: forced manual crop** — replaced two-phase capture→crop flow with Google
  Lens-like auto-save: point camera → tap shutter → auto-crop via guide frame +
  PageEdgeDetector perspective correction → return immediately to reader
- **TTS Streaming: "engine locked" error** — confusing status message
  "Streaming: chunk 1/41 ready (engine locked)…" replaced with clear progress
  "Streaming: N of M ✓"
- **TTS Streaming: parallel overload** — all remaining chunks (40+) launched simultaneously,
  overwhelming Google TTS API and causing hangs; now limited to 3 concurrent calls via Semaphore

### Added
- **TTS Cancel button** — Generate Audio button becomes "Cancel" during streaming generation;
  `cancelGeneration()` on TtsViewModel cancels the coroutine Job
- **BookReader auto-perspective** — PageEdgeDetector runs after guide-frame pre-crop;
  if confidence ≥ 0.30 applies perspective de-warp automatically

---

## [5.2.0] — 2026-03-03  (build 10)
### Added
- Interactive version menu in deploy script: shows all connected ADB devices before build
- Version menu choices: Major / Minor / Hotfix-patch / Build-only / Skip
- Release notes prompt on every release build; saved as `.txt` alongside APK in backup
- Git pull step at start of every deploy run

### Changed
- Deploy script fully rewritten; release APK is now signed automatically
- APK backup now only runs for release builds (not debug)
- Bug/feature docs (`bugs.txt`, `features.txt`, `tts_features.txt`) copied to backup on every deploy

---

## [5.0.0] — 2026-03  (build 8)
### Added
- Android signing config wired into `app/build.gradle.kts` via `keystore.properties`
- Keystore excluded from git (`.jks`, `keystore.properties` in `.gitignore`)
- `BUGS.txt` and `FEATURES.txt` created for project-level tracking
- RULE 0C: AI must read tracking files before every task and update after

### Fixed
- `INSTALL_PARSE_FAILED_NO_CERTIFICATES` — release APK was unsigned; signing config added
- Deploy script syntax error (stray `}` at line 302) — script fully rewritten

---

## [1.3.x] — (earlier builds)
### Added
- **TTS Streaming**: Marathi prose > 250 chars auto-routes to `generateAudioStreaming()`;
  sentences chunked in parallel; `AudioPlayerService.playQueueAsync()` plays queue
- **Emotion Detection** (`emotion_bridge.py`): returns `emotion`, `score`, `dominant`,
  `intensity`, `voice_params`, `scores`, `success`; 10 categories including `devotional`
  and `peaceful`
- **ZWNJ cha fix**: gTTS y-glide on word-internal `-cha` suffix fixed by inserting ZWNJ
  after G2P stage in `marathi_phonetics.py` (all 3 platforms) and `tts_bridge.py`
- **OCR → TTS pipeline** (T25): Devanagari image → ML Kit OCR → TTS → audio
- **Native PDF OCR** (T26): Devanagari bitmap in PDF → `NativePdfExtractor` → text
- **Mobile test T23**: sad emotion detection (`emotion=sad`, `score>0`)
- **Mobile test T24**: 3-sentence streaming → 3 chunks all succeed

---

## [1.0.0] — (initial release)
### Added
- Marathi TTS engine (3 platforms: Web/Django, Desktop/JavaFX, Mobile/Android)
- Phonetic engine: Modern Marathi, Old Marathi (Sant literature), Sanskrit modes
- `SandhiEngine`: avagraha expand, anusvara assimilation, visarga sandhi
- `MetreEngine`: 12-metre catalogue; verse recitation rate ≤ 0.95, half-pause ≥ 400 ms
- `ProsodyEngine`: segment-level pause engine; verse block detection
- `G2PEngine` + exception lexicon (Sanskrit deities, Sant literature, Stotra genre)
- Text input: direct text, URL fetch, OCR (image), PDF extraction
- Voice modulation: speed (0.5×–1.5×), pitch (±12 st), volume (±20 dB)
- Emotion-based voice adaptation (happy/sad/angry/fear/surprise/disgust/love/devotional/peaceful/neutral)
- Stotra library browser with catalog JSON
- Modi script converter (Modi ↔ Devanagari)
- Speech-to-text (Marathi)
- Spelling / grammar correction bridge
- Book page camera reader
- Web fetch → TTS pipeline
- `test_all_platforms.py`: 30+ checks across Sections A–G (Sandhi, Sanskrit phonetics,
  MetreEngine, ProsodyEngine, Old Marathi, Modern Marathi, G2P lexicon)

---

_This file is auto-updated by `deploy_mobile.ps1` on every release build._
