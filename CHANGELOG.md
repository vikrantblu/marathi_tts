# Changelog — Marathi TTS

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` / `MAJOR.MINOR.PATCH-hotfix.N`.

---

## [Unreleased] — v4.0.0 UX Redesign

**Branch:** `feature/ux-redesign-v4`  
**Baseline:** `v3.0.0-stable` tag

### Planned — Phase 1: UX Simplification
- Navigation: 13-item drawer → 3 bottom tabs (INPUT / OUTPUT / ME)
- Consolidate OCR/PDF/Web/STT into INPUT tab as inline chip actions
- OUTPUT tab: unified playback + emotion selector + speed/pitch controls
- ME tab: history + favorites + stotra library + settings
- Hide TestDashboard behind developer mode
- Progressive disclosure: advanced options collapsed by default

### Planned — Phase 2: Intelligent Defaults
- Auto-detect language (Marathi/Hindi/Sanskrit/English)
- Sentiment-driven emotion auto-suggestion
- Optimal playback speed recommendation (verse vs prose)
- Smart engine fallback based on user preferences

### Planned — Phase 3: Best-in-Class Voice
- Kokoro TTS integration (open-source, offline, Indian voices)
- Real-time waveform/prosody preview before generation
- Per-sentence regeneration from preview
- Dual-engine A/B comparison

---

## [3.0.0] — 2026-03

**Tag:** `v3.0.0` → `v3.0.0-stable` (baseline for v4 pivot)

### Added — Mobile UX (FEAT-34 through FEAT-37)
- FEAT-37 Settings screen: theme toggle (system/light/dark), default TTS engine/speed/
  pitch/volume, Clear History, Clear Cache, Reset to Defaults, About with BuildConfig
  version. Nav drawer header shows version. TTS draft persistence on navigate away.
- FEAT-36 Room database (4 entities: HistoryEntry, StotraFavorite, UrlBookmark,
  RecentTtsInput). History screen with category filter chips. HistoryLogger singleton
  wired to all 10 screens with hash-based dedup. Stotra favorites with heart toggle.
  WebFetch URL bookmark chips. TTS recent input chips (last 5). Batch OCR.
- FEAT-35 PDF page selection: per-page text extraction, range input ("1-5, 8, 10-12"),
  Select All, live preview, Send to TTS only sends selected pages.
- FEAT-34 Copy/Share/Save across all 10 mobile screens via OutputActions utility.
  BookReader gains Send to TTS. FileProvider paths extended for Chaquopy audio.

### Added — TTS Engine (FEAT-1 through FEAT-15)
- FEAT-1 ProsodyEngine wired into mobile/desktop bridges: clause-level gTTS segmentation
  with calibrated pydub silence pauses (180–900 ms).
- FEAT-2 Desktop streaming/chunking: Semaphore(3) concurrency, sequential playback chain.
- FEAT-3 Grammar engine in bridges: lazy singleton, prose-only, pre-TTS text correction.
- FEAT-4 Gaṇa pattern matching: syllable weight classification (L/G), gana_bonus scoring.
- FEAT-5 Visarga + voiced consonant → r-sandhi rule in SandhiEngine.
- FEAT-6 Yati caesura pauses: word-boundary-aware pāda splits at gaṇa positions.
- FEAT-7 Ovi rhythmic pulse: lines 1–3 rate=0.82, line 4 rate=0.75, stanza break=1200 ms.
- FEAT-8 Edge-TTS prosody segmentation: per-segment SSML with ProsodyEngine pitch_shift.
- FEAT-9 Emotion → verse prosody mapping: devotional/peaceful/happy/sad/angry modifiers.
- FEAT-10 Schwa deletion lexicon expanded from 8 to 220+ entries.
- FEAT-11 Pitch contour from MetreDefinition: wave/falling/rising patterns, stanza reset.
- FEAT-12 Six new Sanskrit metres (Sragdharā, Indravajra, Upendravajra, Rathoddhatā,
  Upajati, Vamshastha) + yati_syllables on 9 existing metres.
- FEAT-13 Abhanga refrain detection: exact + rhyme repetition → emphasis=1.1, pitch_shift+=0.5.
- FEAT-15 Chandrabindu nasalization: -25 pp volume reduction for ँ segments in edge-tts.

### Added — Shared Infrastructure
- FEAT-14 Pre-recorded stotra audio playback on mobile.
- FEAT-20 Hash-based audio caching (SHA-256, 50 MB LRU cap).
- FEAT-23 Shared English-to-Devanagari transliteration module.
- FEAT-32 Test sections I/J/K: TextNormalizer, GrammarEngine, number_to_words.
- FEAT-33 Marathi morphological analyzer: 70+ suffix rules, optional Morfessor model.
- Shared retry/timeout utility with configurable backoff + network pre-check.
- Structured error codes (ERR_NO_NETWORK, ERR_EMPTY_TEXT, ERR_ALL_ENGINES_FAILED, etc.).
- Temp file cleanup: 24 h age + 100 MB size cap in bridge output directories.
- pydub safe clamping: speed [0.75–1.25], pitch [0.79–1.26].

### Fixed — All 42 Bugs Closed
- BUG-42 STT playback loopback transcription (mic-only SpeechRecognizer workaround).
- BUG-40/41 STT Whisper fallback on Android + 32-bit ARM ABI support.
- BUG-34–39 STT content URI, stop toggle, key mismatch, reobserve loop, locale, error messages.
- BUG-17 SPECIAL_CHARS ॥→। mapping destroyed verse detection.
- BUG-19 G2P schwa rules re-enabled with gtts/explicit mode gating.
- BUG-20–31 Audio caching, network pre-check, timeout/retry, error codes, indicnlp guard,
  NFC normalization, visarga double-processing, temp cleanup, pydub clamping, dead code.
- BookReader auto-save, TTS Streaming cancel/concurrency/status (v5.3.0).

### Changed
- GitHub Actions CI workflow added (`test_all_platforms.py` on ubuntu-latest).
- Cross-platform path resolution with `_ROOT` in test script.

---

## [1.0.0] — 2026-02 (initial release)
### Added
- Marathi TTS engine (3 platforms: Web/Django, Desktop/JavaFX, Mobile/Android)
- Phonetic engine: Modern Marathi, Old Marathi (Sant literature), Sanskrit modes
- `SandhiEngine`: avagraha expand, anusvara assimilation, visarga sandhi
- `MetreEngine`: 12-metre catalogue; verse recitation rate ≤ 0.95, half-pause ≥ 400 ms
- `ProsodyEngine`: segment-level pause engine; verse block detection
- `G2PEngine` + exception lexicon (Sanskrit deities, Sant literature, Stotra genre)
- Text input: direct text, URL fetch, OCR (image), PDF extraction
- Voice modulation: speed (0.5×–1.5×), pitch (±12 st), volume (±20 dB)
- Emotion-based voice adaptation (10 categories)
- Stotra library browser with catalog JSON
- Modi script converter (Modi ↔ Devanagari)
- Speech-to-text (Marathi)
- Spelling / grammar correction bridge
- Book page camera reader
- Web fetch → TTS pipeline
- `test_all_platforms.py`: 30+ checks across Sections A–G

---

_This file is auto-updated by `deploy_mobile.ps1` on every release build._
