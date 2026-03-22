# Changelog — Marathi TTS

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` / `MAJOR.MINOR.PATCH-hotfix.N`.

---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

---

## [Unreleased]
<!-- Changes staged but not yet released go here -->
### Added
- **FEAT-81**: Persistent mini-player bar — activity-scoped PlaybackViewModel holds
  AudioPlayerService so audio playback survives tab switches. Mini-player bar with title
  marquee, play/pause, and stop buttons appears between NavHostFragment and BottomNav.
- **FEAT-82**: Back-nav dialog — when audio is playing and user presses Back, a dialog
  offers "Stop & Go Back", "Keep Playing", or "Cancel" options.
- **FEAT-77**: Home screen widget with "Speak Clipboard" (reads clipboard → auto-generate TTS)
  and "Open" button. AppWidgetProvider + PendingIntent → MainActivity with auto_generate flag.
- **Audio post-processing** (#19): All prosody-stitched outputs (edge-tts prose/verse, gTTS)
  now get loudness normalization (target -16 dBFS) and leading/trailing silence trimming.
  Applied in both mobile and desktop bridges.
### Fixed
- **BUG-70**: Audio stopped when switching tabs — OutputFragment.onDestroyView() called
  audioPlayer.stop(). Now playback is managed by activity-scoped PlaybackViewModel.
- **BUG-69**: ZWNJ insertions in edge-tts paths caused pronunciation artifacts — created
  apply_edge_tts_fixes() with only chandrabindu + halant rules for neural model paths.
- **Old Marathi pronunciation** (#14): Expanded _OLD_MARATHI_LEXICON from ~40 to ~100 entries
  (archaic pronouns, verb forms, Sant poet names, locative forms). Added trailing anusvara→
  chandrabindu conversion and archaic suffix normalization (-तां→-ता, -णें→-णे). Three new
  test assertions (E5/E6/E7).
- **Accent-specific phonetic rules** (#16): Per-region G2P overrides for 6 Maharashtra
  dialects: Kolhapuri (ळ→ल merging), Vidarbha (ला→ले, ए→ये), Malvani (genitive shift),
  Marathwada (aspiration reduction), Khandeshi (vowel shortening), Konkan (retroflex emphasis).
  `apply_accent_phonetics()` in marathi_phonetics.py, wired into both bridge scripts.
  7 new test assertions (Section L).
- **Adaptive text preprocessing** (#18): Content-type classifier detects news, technical,
  conversational, and address text. Type-specific preprocessors expand units (kg→किलोग्रॅम),
  pronounce pin codes, normalize colloquialisms (बोलतोय→बोलतो आहे), and expand news
  acronyms (BJP→भाजप). New `content_classifier.py` module synced to all 3 platforms.
  9 new test assertions (Section M).
- **BookReader memory safety**: Wrapped bitmap operations in `processBookSpread()` with
  try/catch to ensure bitmap recycle on errors.
- **TextReflow sentence enders**: Added colon, en-dash, and em-dash to sentence-ending
  characters for better Devanagari text reflow.

### Fixed
- **BUG-66 [CRITICAL]**: Streaming produces only 1-2 chunks out of 31 — progressive playback
  (BUG-65 attempt) set `isLoading=false` after the first chunk, triggering autoPlay with a
  single file. When the user switched tabs, the Fragment was recreated causing the remaining
  streaming coroutines to receive `JobCancellationException`. Reverted to wait-for-all approach:
  `isLoading` stays true with live progress status until ALL chunks complete, then a single
  autoPlay fires with the full queue.
- **BUG-67 [CRITICAL]**: Prosody word highlighting broken — `analyze_prosody()` in both bridge
  scripts returned `PauseType` IntEnum objects (e.g. `<PauseType.COMMA: 180>`) that Chaquopy
  couldn't serialize to JSON, causing "Unterminated object" parse failure on the Kotlin side.
  No prosody segments → no highlighting. Fixed by explicitly casting to `int()`/`bool()`/`str()`
  in the result dict.
- **BUG-68 [HIGH]**: Accent/gender chips invisible on Input screen — placed inside collapsed
  `options_card` with `visibility="gone"`. Users had to tap an "Options" toggle to find them.
  Fixed by defaulting options to expanded (`visibility="visible"`, `optionsExpanded=true`).
- **BUG-62 [BLOCKER]**: `fragment_input.xml` had duplicate view IDs (chip_group_sources,
  chip_camera, chip_pdf, chip_web, chip_mic, chip_book, btn_options_toggle, options_card,
  spinner_language, switch_verse) — the Input screen reorder duplicated elements instead of
  moving them, causing a data binding compile error. **This was the actual root cause of
  "streaming not working" — the app could not build, so none of the BUG-57/58/59/60/61
  fixes were ever deployed.** Removed the duplicate XML block.
- **BUG-60 [CRITICAL]**: Streaming UI stuck in loading state forever — `generateStreaming()`
  used `_state.postValue()` for intermediate progress updates and `_state.value` for the
  final success state. Since `postValue` is async, the stale progress update (with
  `isLoading=true` and empty `streamChunks`) could arrive AFTER the final `setValue`,
  overwriting the completed state. The player card disappeared and the progress indicator
  stayed visible even though audio was generated. Fixed by replacing all `postValue()`
  with direct `setValue()` — safe because the streaming coroutine runs on `Dispatchers.Main`.
- **BUG-61 [MEDIUM]**: Silent failure on streaming exceptions — both `generateStreaming()`
  and `generateSingle()` had `try/finally` but no `catch` block. An unexpected exception
  (Chaquopy init failure, coroutine cancellation edge case) would leave the UI stuck on
  the loading state with no error message. Added proper `catch(e: Exception)` that sets
  an error state and logs the exception.
- Added comprehensive logging throughout the mobile streaming pipeline (OutputFragment,
  OutputViewModel) to aid in debugging: generate() entry/routing, chunk success/failure,
  autoPlay trigger, engine selection.
- **BUG-57 [CRITICAL]**: Streaming and single-call TTS generation replaced `_state.value`
  with a new `OutputState()`, wiping all existing UI state — prosody segments, accent,
  gender, emotion intensity, verse detection, and metre info all lost on generation complete.
  Prosody preview disappeared and user-selected accent/gender reset to defaults. Fixed by
  using `.copy()` to preserve existing state in all state assignments.
- **BUG-58 [MEDIUM]**: Desktop streaming progress counter inflated — `completedCount` was
  incremented before checking if TTS succeeded, so failed chunks showed as "✓" in the
  status. Moved counter inside success branch.
- **BUG-59 [MEDIUM]**: Desktop AudioPlayerUtil.playQueueInternal had no error handler — a
  corrupt or missing chunk file caused playback to stall indefinitely. Added `setOnError`
  handler that skips to next chunk, and file existence check before playback.
- Streaming chunk failures now log errors instead of silently swallowing exceptions (both
  mobile and desktop).
- **BUG-53 [CRITICAL]**: Content classifier, prose preprocessing, and grammar engine were all
  skipped when edge-tts succeeded (the common path for users with internet). Preprocessing was
  positioned after edge-tts early return. Moved content classifier, prose preprocessor, and
  grammar engine before the edge-tts block in both mobile and desktop bridges.
- **BUG-54 [HIGH]**: `_normalize_marathi()` (Unicode NFC normalization) was missing for Old
  Marathi in all edge-tts paths (single-call, prose prosody, verse prosody). Added normalization
  before phonetic processing in both mobile and desktop bridges.
- **BUG-55 [HIGH]**: Old Marathi verse + edge-tts combination never called `_preprocess_stotra_text()`.
  Fixed if-elif structure in `_generate_edge_tts()` for both bridges.
- **BUG-56 [MEDIUM]**: Sanskrit anusvara only assimilated before sibilants, not varga stop
  consonants. Added `fix_anusvara_varga()` to SandhiEngine for full class-nasal assimilation
  (velar→ङ्, palatal→ञ्, retroflex→ण्, dental→न्, labial→म्).
- **BUG-51 [HIGH]**: Y-glide persisted on word-final matra+anusvara despite BUG-48 ZWNJ fix.
  Replaced word-final anusvara with chandrabindu (ं→ँ) at word boundaries; applied
  `apply_gtts_mr_fixes()` to ALL edge-tts paths (was previously gTTS-only).
- **BUG-52 [HIGH]**: ज्ञ pronounced as ग्य in verse paths — all verse code paths for default
  "mr" language skipped `apply_marathi_phonetics()`. Added normalize+phonetics to all verse
  and edge-tts code paths in both mobile and desktop bridges.
- **BUG-50 [HIGH]**: Accent profiles produced no audible difference — `needs_fx` threshold
  (>0.05) discarded most accent pitch/speed changes; offsets were 2-8% (imperceptible).
  Lowered all threshold from >0.05 to >0.01; expanded offsets to 10-18% range.
- **BUG-49 [MEDIUM]** (mitigated): Male voice only works via edge-tts. Added `voice_note`
  field so UI shows warning when gTTS pitch-shift approximation is used instead.

### Changed
- **FEAT-57**: Expanded accent profiles from 5 generic to 9 Maharashtra regional accents:
  Standard, Mumbai, Pune, Kolhapuri, Vidarbha, Malvani, Marathwada, Khandeshi, Konkan.
  Updated chip UI in OutputFragment with all 9 profiles.
---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

---

## [4.1.0] — 2026-03-09  (build 18)
### Minor release
### Added
- **FEAT-75**: Segment-level playback highlighting — active segment in prosody preview
  highlights with Material3 secondaryContainer color during audio playback. Tracked via
  `onChunkStart` callback → `activePlayingIndex` in OutputState and ProsodySegmentAdapter.
- **FEAT-76**: Export audio with metadata — `exportAudioWithMetadata()` saves to
  `Music/MarathiTTS/` via `MediaStore.Audio.Media` with TITLE, ARTIST, ALBUM, DURATION
  columns. Export dialog lets user set a custom title. Streaming chunks auto-concatenated
  via `concatenateAudioChunks()` before export.
- **FEAT-78**: Accessibility improvements — `contentDescription` on sliders (Speed,
  Emotion Intensity), language Spinner, prosody segments (mode/metre/instructions),
  export button. Decorative empty-state ImageView marked `importantForAccessibility=no`.

### Fixed
- **BUG-46 [CRITICAL]**: Verse mode crashes app — speed slider `stepSize=0.1` incompatible
  with smart verse speed value `0.85`. Changed `stepSize` to `0.05`.
- **BUG-43 [HIGH]**: TTS generation permanently locks after first attempt — `hasStartedGeneration`
  flag never reset in `generateSingle()`/`generateStreaming()`. Wrapped both in `try/finally`;
  also reset flag in `cancelGeneration()`. Verse mode was the most visible failure path.
- **BUG-44 [MEDIUM]**: Long Marathi prose not streaming — `splitSentences()` regex required
  trailing whitespace after `.`/`;`, causing no splits. Unified regex to `(?<=[।॥?!.;])\s*`;
  added comma/newline fallback for unpunctuated prose.
- **BUG-45 [MEDIUM]**: `text_normalizer.py` eyelash-ra regex used `\u` escapes in raw strings,
  causing `re.error: bad escape \u at position 2` on every normalize call. Replaced with actual
  Devanagari characters across all 3 platforms.

### Security
- **CRITICAL**: Fixed SSRF in web app `website_view.py` — URL validation via DNS resolution
  + IP range blocking before `requests.get()` (both `fetch_website_content` and
  `extract_text_from_image_url`)
- **CRITICAL**: Fixed path traversal in `tts_views.py` `stream_status()` — session_id now
  validated as UUID pattern before use in file paths
- **CRITICAL**: Fixed path traversal in MCP `sync_tts_file()` — rejects `..` components
  and verifies resolved path stays within `tts/` directory
- **CRITICAL**: Fixed SQL injection patterns in `db_id_reset.py`, `db_table_rename.py`,
  `rename_app.py` — added table name validation (regex whitelist)
- **HIGH**: Replaced `@csrf_exempt` with `@csrf_protect` on 6 Django views (OCR, STT,
  script convert, AI correction × 3)
- **HIGH**: Added upload validation with magic byte checks and size limits: images (10MB),
  PDFs (50MB), audio (100MB) via new `tts/utils/security.py` module
- **HIGH**: Fixed SSRF in mobile + desktop `web_bridge.py` — added `_is_safe_url()` with
  DNS resolution and private IP rejection
- **HIGH**: Fixed unsafe `pickle.load()` in `text_processor.py` (all 3 platforms) —
  replaced with `RestrictedUnpickler` allowing only builtin types
- **HIGH**: Restricted Android `FileProvider` scope from `path="/"` to specific subdirs
- **HIGH**: Created `network_security_config.xml` with `cleartextTrafficPermitted="false"`
- **HIGH**: Fixed path traversal in `stotra_view.py` — added `realpath` containment check
  and symlink rejection
- **MEDIUM**: Changed Django `DEBUG` default from `True` to `False` (env var override)
- **MEDIUM**: Enabled `SECURE_CONTENT_TYPE_NOSNIFF` and `SECURE_BROWSER_XSS_FILTER` always
- **MEDIUM**: Removed `urllib3.disable_warnings(InsecureRequestWarning)` from settings.py
  and mobile `web_bridge.py`
- **MEDIUM**: Added `X-Content-Type-Options: nosniff` header in JS middleware
- **MEDIUM**: Set `android:allowBackup="false"` in AndroidManifest.xml
- **MEDIUM**: Added `level` enum validation in MCP `bump_version()` tool
- **MEDIUM**: Removed unsafe runtime `pip install` in `audio_processor.py`
- **MEDIUM**: Fixed symlink-following attack in `_cleanup_output_dir()` (mobile + desktop
  `tts_bridge.py`) — added `os.path.islink()` check and `realpath` containment
- **MEDIUM**: Sanitized error messages in HTTP responses (no `str(e)` exposure)
- Created shared security utility module `tts/utils/security.py` with `is_safe_url()`,
  `is_safe_session_id()`, `validate_image_upload()`, `validate_pdf_upload()`,
  `validate_audio_upload()`, `is_path_within()`

### Added
- FEAT-74: Voice gender selection chips (Female/Male) in Output screen — wires
  existing TtsEngineManager gender support to UI via ChipGroup
- FEAT-80: Per-verse metre detection — MetreEngine.detect_line() + detect_per_line();
  ProsodyEngine applies per-segment tts_rate when mixed metres detected in a stanza

### Changed
- SDLC gaps filled: root requirements.txt, AGENTS.md, Dockerfile + docker-compose.yml,
  .claude/skills/claudeskills/SKILL.md populated
- SDLC maturity (10 gaps): PR template, VS Code tasks (10), validate CI workflow (4 jobs),
  agent prompts (6→12), MCP tools (9→21), VS Code settings enhanced, docs/ folder (16 specs),
  version.json system, pre-commit hooks documented, feature flags pattern

---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

---

## [Unreleased]

<!-- Changes staged but not yet released go here -->
---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

---

## [4.1.0] — 2026-03-09  (build 18)
### Minor release
### Added
- **FEAT-75**: Segment-level playback highlighting — active segment in prosody preview
  highlights with Material3 secondaryContainer color during audio playback. Tracked via
  `onChunkStart` callback → `activePlayingIndex` in OutputState and ProsodySegmentAdapter.
- **FEAT-76**: Export audio with metadata — `exportAudioWithMetadata()` saves to
  `Music/MarathiTTS/` via `MediaStore.Audio.Media` with TITLE, ARTIST, ALBUM, DURATION
  columns. Export dialog lets user set a custom title. Streaming chunks auto-concatenated
  via `concatenateAudioChunks()` before export.
- **FEAT-78**: Accessibility improvements — `contentDescription` on sliders (Speed,
  Emotion Intensity), language Spinner, prosody segments (mode/metre/instructions),
  export button. Decorative empty-state ImageView marked `importantForAccessibility=no`.

### Fixed
- **BUG-46 [CRITICAL]**: Verse mode crashes app — speed slider `stepSize=0.1` incompatible
  with smart verse speed value `0.85`. Changed `stepSize` to `0.05`.
- **BUG-43 [HIGH]**: TTS generation permanently locks after first attempt — `hasStartedGeneration`
  flag never reset in `generateSingle()`/`generateStreaming()`. Wrapped both in `try/finally`;
  also reset flag in `cancelGeneration()`. Verse mode was the most visible failure path.
- **BUG-44 [MEDIUM]**: Long Marathi prose not streaming — `splitSentences()` regex required
  trailing whitespace after `.`/`;`, causing no splits. Unified regex to `(?<=[।॥?!.;])\s*`;
  added comma/newline fallback for unpunctuated prose.
- **BUG-45 [MEDIUM]**: `text_normalizer.py` eyelash-ra regex used `\u` escapes in raw strings,
  causing `re.error: bad escape \u at position 2` on every normalize call. Replaced with actual
  Devanagari characters across all 3 platforms.

### Security
- **CRITICAL**: Fixed SSRF in web app `website_view.py` — URL validation via DNS resolution
  + IP range blocking before `requests.get()` (both `fetch_website_content` and
  `extract_text_from_image_url`)
- **CRITICAL**: Fixed path traversal in `tts_views.py` `stream_status()` — session_id now
  validated as UUID pattern before use in file paths
- **CRITICAL**: Fixed path traversal in MCP `sync_tts_file()` — rejects `..` components
  and verifies resolved path stays within `tts/` directory
- **CRITICAL**: Fixed SQL injection patterns in `db_id_reset.py`, `db_table_rename.py`,
  `rename_app.py` — added table name validation (regex whitelist)
- **HIGH**: Replaced `@csrf_exempt` with `@csrf_protect` on 6 Django views (OCR, STT,
  script convert, AI correction × 3)
- **HIGH**: Added upload validation with magic byte checks and size limits: images (10MB),
  PDFs (50MB), audio (100MB) via new `tts/utils/security.py` module
- **HIGH**: Fixed SSRF in mobile + desktop `web_bridge.py` — added `_is_safe_url()` with
  DNS resolution and private IP rejection
- **HIGH**: Fixed unsafe `pickle.load()` in `text_processor.py` (all 3 platforms) —
  replaced with `RestrictedUnpickler` allowing only builtin types
- **HIGH**: Restricted Android `FileProvider` scope from `path="/"` to specific subdirs
- **HIGH**: Created `network_security_config.xml` with `cleartextTrafficPermitted="false"`
- **HIGH**: Fixed path traversal in `stotra_view.py` — added `realpath` containment check
  and symlink rejection
- **MEDIUM**: Changed Django `DEBUG` default from `True` to `False` (env var override)
- **MEDIUM**: Enabled `SECURE_CONTENT_TYPE_NOSNIFF` and `SECURE_BROWSER_XSS_FILTER` always
- **MEDIUM**: Removed `urllib3.disable_warnings(InsecureRequestWarning)` from settings.py
  and mobile `web_bridge.py`
- **MEDIUM**: Added `X-Content-Type-Options: nosniff` header in JS middleware
- **MEDIUM**: Set `android:allowBackup="false"` in AndroidManifest.xml
- **MEDIUM**: Added `level` enum validation in MCP `bump_version()` tool
- **MEDIUM**: Removed unsafe runtime `pip install` in `audio_processor.py`
- **MEDIUM**: Fixed symlink-following attack in `_cleanup_output_dir()` (mobile + desktop
  `tts_bridge.py`) — added `os.path.islink()` check and `realpath` containment
- **MEDIUM**: Sanitized error messages in HTTP responses (no `str(e)` exposure)
- Created shared security utility module `tts/utils/security.py` with `is_safe_url()`,
  `is_safe_session_id()`, `validate_image_upload()`, `validate_pdf_upload()`,
  `validate_audio_upload()`, `is_path_within()`

### Added
- FEAT-74: Voice gender selection chips (Female/Male) in Output screen — wires
  existing TtsEngineManager gender support to UI via ChipGroup
- FEAT-80: Per-verse metre detection — MetreEngine.detect_line() + detect_per_line();
  ProsodyEngine applies per-segment tts_rate when mixed metres detected in a stanza

### Changed
- SDLC gaps filled: root requirements.txt, AGENTS.md, Dockerfile + docker-compose.yml,
  .claude/skills/claudeskills/SKILL.md populated
- SDLC maturity (10 gaps): PR template, VS Code tasks (10), validate CI workflow (4 jobs),
  agent prompts (6→12), MCP tools (9→21), VS Code settings enhanced, docs/ folder (16 specs),
  version.json system, pre-commit hooks documented, feature flags pattern

---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

---

## [4.0.0] — 2026-03-07

**Tag:** `v4.0.0`  
**Branch:** `feature/ux-redesign-v4` (merged to `main`)

### Added — Phase 1: UX Simplification (FEAT-40 through FEAT-45, FEAT-61)
- FEAT-40 Navigation pivot: 13-item drawer → 3 bottom tabs (INPUT/OUTPUT/ME)
- FEAT-41 INPUT tab: text entry + source chips (Camera/PDF/Web/Mic/Book) + Generate
- FEAT-42 OUTPUT tab: auto-generates on navigate, progress card, auto-play, streaming
- FEAT-43 ME tab: hub cards for Stotra/History/Modi/Settings
- FEAT-44 Developer mode: Test Dashboard hidden, toggled from Settings switch
- FEAT-45 Progressive disclosure: language/verse options collapsed behind expandable toggle
- FEAT-61 Share-to-app: URLs → WebFetch, images → OCR, text → Input

### Added — Phase 2: Intelligent Defaults (FEAT-46 through FEAT-48)
- FEAT-46 Auto-detect language: Sanskrit markers (॥, ॐ, नमः) and Hindi markers analyzed;
  default Marathi. "Auto-detect" is the first spinner option.
- FEAT-47 Emotion auto-suggestion: OutputViewModel auto-detects emotion via emotion_bridge
  before TTS generation; emotion card displays result.
- FEAT-48 Smart verse speed: speed slider defaults to 0.85x in verse mode with hint label.
- FEAT-49 User preference learning: engine success counters in SharedPreferences;
  auto-selects most successful engine after 3+ generations when user is on Auto.
  Engine usage stats visible in Settings under dev mode.

### Planned — Phase 3: Best-in-Class Voice
- Kokoro TTS integration (open-source, offline, Indian voices)

### Added — Phase 3: Prosody Preview + Per-Sentence Regen (FEAT-51, FEAT-52)
- FEAT-51 Real-time prosody preview on Output screen:
  - `analyze_prosody()` bridge function (mobile + desktop) calls ProsodyEngine.segment_text()
    and returns segment list with text, pause_after_ms, emotion, emphasis, pitch_shift,
    is_verse, metre_name, tts_rate
  - `ProsodySegment` Kotlin data class, `ProsodySegmentAdapter` RecyclerView adapter
  - `prosody_preview_card` in fragment_output.xml with segment count, tap-to-regen hint
  - Each segment shows: text content, Verse/Prose badge, metre name, pause duration, TTS rate
  - Runs concurrently with TTS generation (pure text analysis, no network needed)
- FEAT-52 Per-sentence regeneration from prosody preview:
  - `regenerate_segment()` bridge function (mobile + desktop) — lightweight single-segment
    TTS via edge-tts → gTTS fallback chain (skips custom voice for speed)
  - Tap any prosody segment to regenerate just that chunk with current speed setting
  - Replaces corresponding stream chunk audio path in-place
  - Progress indicator on regenerating segment, status update on completion

### Added — Phase 3: Verse Voice Quality (FEAT-VQ)
- `_generate_edge_verse_prosody()` in both mobile + desktop tts_bridge.py:
  - Uses ProsodyEngine metre-aware segmentation (pauses at ।/॥, pitch contour, tts_rate)
  - Edge-tts neural voice generates per-segment audio with SSML rate/pitch/volume per segment
  - pydub stitches with calibrated verse pauses (800ms half, 1200ms full, 1600ms stanza)
  - Previously verse text bypassed prosody and fell to robotic gTTS slow=True
  - Chandrabindu nasalization (FEAT-15) applied per segment
  - Segment cap: 40 (verse segments are shorter than prose)
  - Transparent fallthrough: returns None → single-call edge-tts → gTTS verse

### Added — Phase 3: Custom Stotra Voice (FEAT-50, FEAT-53)
- FEAT-50 Custom Stotra Voice Model training pipeline:
  - `preprocess_audio.py` — Audio normalization + adaptive silence-based segmentation
    (auto-retries at -28/-25/-22/-20 dB thresholds when default -35 dB finds no gaps)
  - `align_transcript.py` — Transcript-to-audio alignment via shloka numbers (॥N॥) or
    double-danda parsing, proportional character-count mapping
  - `validate_dataset.py` — Quality validation (SNR, duration ranges, silence ratio,
    Piper-readiness check)
  - `generate_piper_config.py` — Piper-compatible dataset: wav/ dir, metadata.csv,
    config.json, training_config.json
  - `train_piper.py` — Colab-ready Piper VITS fine-tuning (Hindi base model)
  - `run_pipeline.py` — Master pipeline orchestrator (subprocess-based)
  - `custom_voice_engine.py` deployed to mobile + desktop: Phase A (segment library
    fingerprint matching) + Phase B (ONNX model inference via Sherpa-ONNX)
  - Integrated as highest-priority engine in both mobile + desktop bridge fallback chains
  - Processed 3 recordings: Chandrashekhar (44 segs), Vishnu Sahasranama (143 segs),
    Ram Raksha (42 segs) — total 155 utterances, 36.1 min
- FEAT-53 Dual-engine A/B comparison: `compare_engines()` function in both bridge scripts,
  runs text through gTTS/Edge-TTS/Custom and returns all audio paths for comparison

### Added — Phase 4: Innovation Features (FEAT-54 through FEAT-58)
- FEAT-54 Emotion intensity slider: 0–100% granularity slider in emotion card. Scales
  ProsodyEngine pitch_shift and tts_rate modifiers proportionally. Default 50%. Integrated
  into generate_tts, edge-tts prosody, and verse prosody paths.
- FEAT-55 Phonetic explainer: long-press any prosody segment to see applied rules. Bridge
  function traces 4 stages (G2P lexicon → SandhiEngine → language phonetics → G2P engine)
  and returns rule list. AlertDialog displays stage, rule name, before/after text.
- FEAT-56 Batch stotra playlist: long-press to enter playlist mode with multi-select
  checkboxes. Select All button. Batch TTS generation with progress bar. Sequential
  playback via AudioPlayerService.playQueueAsync(). Cancel during generation.
- FEAT-57 Accent profiles: 5 Marathi regional variants (Standard/Mumbai/Northern/
  Konkanastha/Deccani). Chip group in output screen. Each profile adjusts pitch and rate
  offsets applied in tts_bridge before TTS generation.
- FEAT-58 Smart text clipping: real-time NLP-aware segment preview in InputFragment when
  text exceeds 250 chars. Shows segment count and first 6 segment snippets. Uses same
  sentence-splitting logic as streaming generation (splits at ।/॥/?!/.; merges short runs).

### Added — Backlog Features (FEAT-59, FEAT-60)
- FEAT-59 Community phonetic corrections: long-press phonetic explainer dialog now has
  "Correct" button. Users submit corrected pronunciation via EditText dialog. Corrections
  stored in Room DB (PhoneticCorrection entity, v2 schema), synced to user_corrections.json.
  Python bridge reads corrections via USER_CORRECTIONS_PATH env var and loads into G2P
  lexicon as overrides. Desktop bridge also supports corrections file.
- FEAT-60 Live scripture search with voice: full-text search across all stotra content
  files (not just titles). Voice search button with Android SpeechRecognizer (mr-IN locale).
  Content matches shown with stotra title + ±1 line context excerpt. Tap navigates to
  matching stotra detail. Triggered for queries ≥ 3 characters.

---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

---

## [4.1.0] — 2026-03-09  (build 18)
### Minor release
### Added
- **FEAT-75**: Segment-level playback highlighting — active segment in prosody preview
  highlights with Material3 secondaryContainer color during audio playback. Tracked via
  `onChunkStart` callback → `activePlayingIndex` in OutputState and ProsodySegmentAdapter.
- **FEAT-76**: Export audio with metadata — `exportAudioWithMetadata()` saves to
  `Music/MarathiTTS/` via `MediaStore.Audio.Media` with TITLE, ARTIST, ALBUM, DURATION
  columns. Export dialog lets user set a custom title. Streaming chunks auto-concatenated
  via `concatenateAudioChunks()` before export.
- **FEAT-78**: Accessibility improvements — `contentDescription` on sliders (Speed,
  Emotion Intensity), language Spinner, prosody segments (mode/metre/instructions),
  export button. Decorative empty-state ImageView marked `importantForAccessibility=no`.

### Fixed
- **BUG-46 [CRITICAL]**: Verse mode crashes app — speed slider `stepSize=0.1` incompatible
  with smart verse speed value `0.85`. Changed `stepSize` to `0.05`.
- **BUG-43 [HIGH]**: TTS generation permanently locks after first attempt — `hasStartedGeneration`
  flag never reset in `generateSingle()`/`generateStreaming()`. Wrapped both in `try/finally`;
  also reset flag in `cancelGeneration()`. Verse mode was the most visible failure path.
- **BUG-44 [MEDIUM]**: Long Marathi prose not streaming — `splitSentences()` regex required
  trailing whitespace after `.`/`;`, causing no splits. Unified regex to `(?<=[।॥?!.;])\s*`;
  added comma/newline fallback for unpunctuated prose.
- **BUG-45 [MEDIUM]**: `text_normalizer.py` eyelash-ra regex used `\u` escapes in raw strings,
  causing `re.error: bad escape \u at position 2` on every normalize call. Replaced with actual
  Devanagari characters across all 3 platforms.

### Security
- **CRITICAL**: Fixed SSRF in web app `website_view.py` — URL validation via DNS resolution
  + IP range blocking before `requests.get()` (both `fetch_website_content` and
  `extract_text_from_image_url`)
- **CRITICAL**: Fixed path traversal in `tts_views.py` `stream_status()` — session_id now
  validated as UUID pattern before use in file paths
- **CRITICAL**: Fixed path traversal in MCP `sync_tts_file()` — rejects `..` components
  and verifies resolved path stays within `tts/` directory
- **CRITICAL**: Fixed SQL injection patterns in `db_id_reset.py`, `db_table_rename.py`,
  `rename_app.py` — added table name validation (regex whitelist)
- **HIGH**: Replaced `@csrf_exempt` with `@csrf_protect` on 6 Django views (OCR, STT,
  script convert, AI correction × 3)
- **HIGH**: Added upload validation with magic byte checks and size limits: images (10MB),
  PDFs (50MB), audio (100MB) via new `tts/utils/security.py` module
- **HIGH**: Fixed SSRF in mobile + desktop `web_bridge.py` — added `_is_safe_url()` with
  DNS resolution and private IP rejection
- **HIGH**: Fixed unsafe `pickle.load()` in `text_processor.py` (all 3 platforms) —
  replaced with `RestrictedUnpickler` allowing only builtin types
- **HIGH**: Restricted Android `FileProvider` scope from `path="/"` to specific subdirs
- **HIGH**: Created `network_security_config.xml` with `cleartextTrafficPermitted="false"`
- **HIGH**: Fixed path traversal in `stotra_view.py` — added `realpath` containment check
  and symlink rejection
- **MEDIUM**: Changed Django `DEBUG` default from `True` to `False` (env var override)
- **MEDIUM**: Enabled `SECURE_CONTENT_TYPE_NOSNIFF` and `SECURE_BROWSER_XSS_FILTER` always
- **MEDIUM**: Removed `urllib3.disable_warnings(InsecureRequestWarning)` from settings.py
  and mobile `web_bridge.py`
- **MEDIUM**: Added `X-Content-Type-Options: nosniff` header in JS middleware
- **MEDIUM**: Set `android:allowBackup="false"` in AndroidManifest.xml
- **MEDIUM**: Added `level` enum validation in MCP `bump_version()` tool
- **MEDIUM**: Removed unsafe runtime `pip install` in `audio_processor.py`
- **MEDIUM**: Fixed symlink-following attack in `_cleanup_output_dir()` (mobile + desktop
  `tts_bridge.py`) — added `os.path.islink()` check and `realpath` containment
- **MEDIUM**: Sanitized error messages in HTTP responses (no `str(e)` exposure)
- Created shared security utility module `tts/utils/security.py` with `is_safe_url()`,
  `is_safe_session_id()`, `validate_image_upload()`, `validate_pdf_upload()`,
  `validate_audio_upload()`, `is_path_within()`

### Added
- FEAT-74: Voice gender selection chips (Female/Male) in Output screen — wires
  existing TtsEngineManager gender support to UI via ChipGroup
- FEAT-80: Per-verse metre detection — MetreEngine.detect_line() + detect_per_line();
  ProsodyEngine applies per-segment tts_rate when mixed metres detected in a stanza

### Changed
- SDLC gaps filled: root requirements.txt, AGENTS.md, Dockerfile + docker-compose.yml,
  .claude/skills/claudeskills/SKILL.md populated
- SDLC maturity (10 gaps): PR template, VS Code tasks (10), validate CI workflow (4 jobs),
  agent prompts (6→12), MCP tools (9→21), VS Code settings enhanced, docs/ folder (16 specs),
  version.json system, pre-commit hooks documented, feature flags pattern

---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

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

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

---

## [4.1.0] — 2026-03-09  (build 18)
### Minor release
### Added
- **FEAT-75**: Segment-level playback highlighting — active segment in prosody preview
  highlights with Material3 secondaryContainer color during audio playback. Tracked via
  `onChunkStart` callback → `activePlayingIndex` in OutputState and ProsodySegmentAdapter.
- **FEAT-76**: Export audio with metadata — `exportAudioWithMetadata()` saves to
  `Music/MarathiTTS/` via `MediaStore.Audio.Media` with TITLE, ARTIST, ALBUM, DURATION
  columns. Export dialog lets user set a custom title. Streaming chunks auto-concatenated
  via `concatenateAudioChunks()` before export.
- **FEAT-78**: Accessibility improvements — `contentDescription` on sliders (Speed,
  Emotion Intensity), language Spinner, prosody segments (mode/metre/instructions),
  export button. Decorative empty-state ImageView marked `importantForAccessibility=no`.

### Fixed
- **BUG-46 [CRITICAL]**: Verse mode crashes app — speed slider `stepSize=0.1` incompatible
  with smart verse speed value `0.85`. Changed `stepSize` to `0.05`.
- **BUG-43 [HIGH]**: TTS generation permanently locks after first attempt — `hasStartedGeneration`
  flag never reset in `generateSingle()`/`generateStreaming()`. Wrapped both in `try/finally`;
  also reset flag in `cancelGeneration()`. Verse mode was the most visible failure path.
- **BUG-44 [MEDIUM]**: Long Marathi prose not streaming — `splitSentences()` regex required
  trailing whitespace after `.`/`;`, causing no splits. Unified regex to `(?<=[।॥?!.;])\s*`;
  added comma/newline fallback for unpunctuated prose.
- **BUG-45 [MEDIUM]**: `text_normalizer.py` eyelash-ra regex used `\u` escapes in raw strings,
  causing `re.error: bad escape \u at position 2` on every normalize call. Replaced with actual
  Devanagari characters across all 3 platforms.

### Security
- **CRITICAL**: Fixed SSRF in web app `website_view.py` — URL validation via DNS resolution
  + IP range blocking before `requests.get()` (both `fetch_website_content` and
  `extract_text_from_image_url`)
- **CRITICAL**: Fixed path traversal in `tts_views.py` `stream_status()` — session_id now
  validated as UUID pattern before use in file paths
- **CRITICAL**: Fixed path traversal in MCP `sync_tts_file()` — rejects `..` components
  and verifies resolved path stays within `tts/` directory
- **CRITICAL**: Fixed SQL injection patterns in `db_id_reset.py`, `db_table_rename.py`,
  `rename_app.py` — added table name validation (regex whitelist)
- **HIGH**: Replaced `@csrf_exempt` with `@csrf_protect` on 6 Django views (OCR, STT,
  script convert, AI correction × 3)
- **HIGH**: Added upload validation with magic byte checks and size limits: images (10MB),
  PDFs (50MB), audio (100MB) via new `tts/utils/security.py` module
- **HIGH**: Fixed SSRF in mobile + desktop `web_bridge.py` — added `_is_safe_url()` with
  DNS resolution and private IP rejection
- **HIGH**: Fixed unsafe `pickle.load()` in `text_processor.py` (all 3 platforms) —
  replaced with `RestrictedUnpickler` allowing only builtin types
- **HIGH**: Restricted Android `FileProvider` scope from `path="/"` to specific subdirs
- **HIGH**: Created `network_security_config.xml` with `cleartextTrafficPermitted="false"`
- **HIGH**: Fixed path traversal in `stotra_view.py` — added `realpath` containment check
  and symlink rejection
- **MEDIUM**: Changed Django `DEBUG` default from `True` to `False` (env var override)
- **MEDIUM**: Enabled `SECURE_CONTENT_TYPE_NOSNIFF` and `SECURE_BROWSER_XSS_FILTER` always
- **MEDIUM**: Removed `urllib3.disable_warnings(InsecureRequestWarning)` from settings.py
  and mobile `web_bridge.py`
- **MEDIUM**: Added `X-Content-Type-Options: nosniff` header in JS middleware
- **MEDIUM**: Set `android:allowBackup="false"` in AndroidManifest.xml
- **MEDIUM**: Added `level` enum validation in MCP `bump_version()` tool
- **MEDIUM**: Removed unsafe runtime `pip install` in `audio_processor.py`
- **MEDIUM**: Fixed symlink-following attack in `_cleanup_output_dir()` (mobile + desktop
  `tts_bridge.py`) — added `os.path.islink()` check and `realpath` containment
- **MEDIUM**: Sanitized error messages in HTTP responses (no `str(e)` exposure)
- Created shared security utility module `tts/utils/security.py` with `is_safe_url()`,
  `is_safe_session_id()`, `validate_image_upload()`, `validate_pdf_upload()`,
  `validate_audio_upload()`, `is_path_within()`

### Added
- FEAT-74: Voice gender selection chips (Female/Male) in Output screen — wires
  existing TtsEngineManager gender support to UI via ChipGroup
- FEAT-80: Per-verse metre detection — MetreEngine.detect_line() + detect_per_line();
  ProsodyEngine applies per-segment tts_rate when mixed metres detected in a stanza

### Changed
- SDLC gaps filled: root requirements.txt, AGENTS.md, Dockerfile + docker-compose.yml,
  .claude/skills/claudeskills/SKILL.md populated
- SDLC maturity (10 gaps): PR template, VS Code tasks (10), validate CI workflow (4 jobs),
  agent prompts (6→12), MCP tools (9→21), VS Code settings enhanced, docs/ folder (16 specs),
  version.json system, pre-commit hooks documented, feature flags pattern

---

## [4.1.1] — 2026-03-10  (build 19)
### Hotfix / patch
- fix ZWNJ
### Fixed
- **BUG-47 [HIGH]**: Schwa deletion lexicon never matched Devanagari words — Python `re \b`
  word boundary treats matras (ा ी ू etc.) as `\W`, so `\bमुलगा\b` never matched. Replaced
  regex-based lexicon lookup with token-splitting approach. Expanded `_SCHWA_DELETION_LEXICON`
  from ~20 to ~200 entries covering common verbs, nouns, adjectives, pronouns, and adverbs.
  Added rule-based medial schwa deletion for unlisted words (conservative: only fires when
  a consonant with inherent schwa sits between two syllables with explicit matras).
  Sanskrit/tatsama prefixes excluded from rule-based deletion to avoid incorrect changes.

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
