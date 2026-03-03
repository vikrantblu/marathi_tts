# Changelog — Marathi TTS

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` / `MAJOR.MINOR.PATCH-hotfix.N`.

---

## [Unreleased]
<!-- Changes staged but not yet released go here -->

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
