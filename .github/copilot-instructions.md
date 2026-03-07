# GitHub Copilot Instructions — Marathi TTS

---

## RULE 0 — DOCS-FIRST (read before exploring)

**Before using any file-search, directory-listing, or codebase-exploration tool,
read this file in full.**  It contains the complete structure of all three platforms.
Only reach for `file_search` / `list_dir` / `grep_search` when this file does not
answer the question.

> _Rationale: exploring the workspace with tools is slow and wastes context.
> Every structural fact that has been discovered must be recorded here._

---

## RULE 0B — DOCS-UPDATE (write after every structural change)

**Any time a file, class, fragment, screen, service, route, or bridge is added,
removed, or renamed in any platform, update the matching section of this file in
the same turn — before reporting the task done.**

Checklist after every structural change:
- [ ] Updated the relevant platform map below (Mobile / Desktop / Web)
- [ ] Updated the Python `tts/` tree if a TTS engine file changed
- [ ] Confirmed `test_all_platforms.py` still passes

---

## RULE 0D — GIT PULL FIRST (before any code change)

**Before making any edit to any file in the workspace, run `git pull` in the
project root to ensure you are working on the latest code.**

```powershell
cd d:\marathi_tts
git pull
```

If the pull fails (no network, merge conflict, etc.) report the issue to the
user before proceeding — do not edit files on a potentially stale checkout.

---

## CI / GitHub Setup

**Workflow file:** `.github/workflows/test.yml`  
**CI requirements:** `.github/ci-requirements.txt`  
**Setup guide:** `.github/SETUP_GITHUB.md`

The GitHub Actions workflow runs `test_all_platforms.py` automatically on every push
and pull request against `main`/`master`/`develop`.

- **Runner:** `ubuntu-latest` (Python 3.11)
- **Dependencies:** Only `Morfessor` (lightweight); all heavy ML deps are skipped by
  the test's `except ModuleNotFoundError` guards.
- **Sections I/J/K** (TextNormalizer, GrammarEngine, number_to_words) skip gracefully
  without `indicnlp` — they do NOT fail CI.

**`test_all_platforms.py` path handling:** The script now uses `_ROOT = os.path.dirname(
os.path.abspath(__file__))` to compute all platform paths dynamically — works on both
Windows (`d:\marathi_tts\`) and the CI Linux runner.

**Copilot coding agent:** Once the repo is on GitHub, create Issues for planned features
(from `FEATURES.txt`), assign them to Copilot, and it will open a PR. CI auto-runs on
the PR and Copilot self-corrects on test failures.

---

## RULE 0C — CHECK BUGS & FEATURES (read before every task)

**Before starting any coding task, read these four files:**

1. `CHANGELOG.md` (project root) — full version history: what changed, when, and why
2. `BUGS.txt` (project root) — known bugs and regressions
3. `FEATURES.txt` (project root) — planned and shipped features
4. `marathi_tts_web/tts_features.md` — detailed TTS feature documentation

**Why:** These files track what is broken and what is planned.  When fixing a
bug or adding a feature, check whether it is already listed.  After completing
work, update the relevant file:

- **Bug fixed** → move the entry from Open to Fixed in `BUGS.txt` with the version.
- **New bug discovered** → add it to the Open section of `BUGS.txt`.
- **Feature shipped** → move the entry from Planned to Shipped in `FEATURES.txt`.
- **New feature planned** → add it to the Planned section of `FEATURES.txt`.
- **TTS capability changed** → update `marathi_tts_web/tts_features.md`.
- **Any release** → the deploy script (`deploy_mobile.ps1`) auto-appends to `CHANGELOG.md`;
  for non-deploy changes, manually add an entry under `## [Unreleased]` in `CHANGELOG.md`.

The deploy script copies these files to `C:\My_Drive_Backup\builds\marathi_tts\`
on every build, so the backup folder always has the latest snapshot.

---

## Project Structure

This workspace has **three platforms** that share the same Python TTS engine code:

| Platform | Python root |
|----------|-------------|
| **Web** (Django) | `marathi_tts_web/tts/` |
| **Desktop** (JavaFX + Chaquopy bridge) | `marathi_tts_desktop/python_bridge/tts/` |
| **Mobile** (Android + Chaquopy) | `marathi_tts_mobile/app/src/main/python/tts/` |

All three platforms mirror the same package layout:

```
tts/
  constants/          # audio_constants, g2p_constants, tts_config, …
  utils/
    audio/            # prosody_engine.py
    core/             # tts_engine.py
    emotion/          # emotion_analyzer.py
    phonetic/         # marathi_phonetics, sandhi_engine, metre_engine, g2p_engine, …
    text/             # text_normalizer, text_processor, marathi_grammar, …
    voice/            # voice_modulator.py  (web only — desktop/mobile use try/except)
```

---

## Mobile App Map  (`marathi_tts_mobile/`)

**Language:** Kotlin  **Min SDK:** 26  **Target SDK:** 34  
**Package:** `com.marathitts.mobile`  
**Build:** Gradle + Chaquopy plugin (embeds Python 3.11)  
**Python bridge location:** `app/src/main/python/` (Chaquopy copies at build time)

### Navigation (v4.0.0 — 3-tab bottom navigation)

Pattern: `BottomNavigationView` (3 tabs) + `NavHostFragment`  
Top-level tabs show bottom bar; child destinations show Up arrow in toolbar.

**Bottom tabs:**

| Tab | Nav ID | Fragment class | Purpose |
|-----|--------|---------------|---------|
| Input ★ | `inputFragment` | `ui/input/InputFragment` | Text entry, source chips, Generate |
| Output | `outputFragment` | `ui/output/OutputFragment` | Auto-generates TTS, playback, emotion, copy/share/save |
| Me | `meFragment` | `ui/me/MeFragment` | Stotra, History, Modi, Settings hub |

★ = start destination

**Child destinations (navigable from tabs via actions):**

| Nav ID | Fragment class | Accessed from | Purpose |
|--------|---------------|---------------|---------|
| `ocrFragment` | `ui/ocr/OcrFragment` | Input → chip_camera | Camera OCR → text |
| `pdfFragment` | `ui/pdf/PdfFragment` | Input → chip_pdf | PDF → text |
| `webFetchFragment` | `ui/web/WebFetchFragment` | Input → chip_web | Web page → text |
| `sttFragment` | `ui/stt/SttFragment` | Input → chip_mic | Speech-to-text |
| `bookReaderFragment` | `ui/bookreader/BookReaderFragment` | Input → chip_book | Book camera + reader |
| `correctionFragment` | `ui/correction/CorrectionFragment` | Input → btn_correction | Spell/grammar correction |
| `emotionFragment` | `ui/emotion/EmotionFragment` | Output | Emotion analysis |
| `stotraFragment` | `ui/stotra/StotraFragment` | Me → card | Stotra library |
| `historyFragment` | `ui/history/HistoryFragment` | Me → card | Generation history |
| `modiFragment` | `ui/modi/ModiFragment` | Me → card | Modi script converter |
| `settingsFragment` | `ui/settings/SettingsFragment` | Me → card | App settings |
| `testDashboardFragment` | `ui/test/TestDashboardFragment` | Me (dev) | Feature test dashboard |
| `ttsFragment` | `ui/tts/TtsFragment` | Legacy deep link | Original TTS screen (kept for compat) |

**Text flow:** Child screens (OCR/PDF/Web/STT) return text to InputFragment via
`savedStateHandle.set("extracted_text", text)` + `popBackStack()`. Other screens
(Correction/Emotion/History/Modi/Stotra) navigate to `inputFragment` with `tts_text` arg.

Bottom tab menu: `res/menu/bottom_tabs_menu.xml`  
Nav graph: `res/navigation/nav_graph.xml`  
Old drawer menu (deprecated): `res/menu/bottom_nav_menu.xml`

### Layout files

| File | Used by |
|------|---------|
| `activity_main.xml` | `MainActivity` — Toolbar + NavHostFragment + BottomNavigationView |
| `fragment_input.xml` | InputFragment — text entry + source chips + generate |
| `fragment_output.xml` | OutputFragment — playback + emotion + actions |
| `fragment_me.xml` | MeFragment — hub cards for stotra/history/modi/settings |
| `fragment_tts.xml` | TtsFragment (legacy, kept for deep links) |
| `nav_header.xml` | Drawer header (deprecated) |
| `fragment_emotion.xml` | EmotionFragment |
| `fragment_stt.xml` | SttFragment |
| `fragment_ocr.xml` | OcrFragment |
| `fragment_pdf.xml` | PdfFragment |
| `fragment_web_fetch.xml` | WebFetchFragment |
| `fragment_correction.xml` | CorrectionFragment |
| `fragment_modi.xml` | ModiFragment |
| `fragment_stotra.xml` | StotraFragment + `item_stotra.xml` (RecyclerView row) |
| `fragment_book_reader.xml` | BookReaderFragment |
| `activity_book_camera.xml` | BookCameraActivity |
| `fragment_history.xml` | HistoryFragment |
| `item_history.xml` | HistoryAdapter — history entry row |
| `fragment_settings.xml` | SettingsFragment |
| `fragment_test_dashboard.xml` | TestDashboardFragment |
| `item_test_row.xml` | TestDashboardAdapter — result row |
| `item_test_group_header.xml` | TestDashboardAdapter — group section header |

### Share-to-App (FEAT-61)

The app is registered as a share target for URLs and images via `AndroidManifest.xml`
intent filters. When a user shares content from another app (browser, gallery, etc.),
`MainActivity.handleShareIntent()` routes by MIME type:

| Shared content | MIME type | Destination | Behavior |
|----------------|-----------|-------------|----------|
| Image from gallery | `image/*` | OcrFragment | Auto-loads image via `shared_image_uri` arg |
| URL from browser | `text/plain` (http/https) | WebFetchFragment | Auto-fills URL + auto-fetches via `shared_url` arg |
| Plain text | `text/plain` (non-URL) | InputFragment | Fills text input via `tts_text` arg |

**Intent filters** (in `AndroidManifest.xml` on `MainActivity`):
- `ACTION_SEND` + `text/plain` — URLs and plain text
- `ACTION_SEND` + `image/*` — images from gallery/camera/browser

### Services & helpers (`service/` package)

| Class | Purpose |
|-------|---------|
| `PythonBridge` | Singleton; calls Chaquopy Python bridge scripts |
| `TtsEngineManager` | Switches between native Android TTS and Python TTS |
| `AudioPlayerService` | Foreground service — plays generated audio queue; `playQueueAsync(List<String>)` for streaming |
| `StotraRepository` | Loads stotra catalog JSON from assets |
| `SystemTtsEngine` | Wraps Android `TextToSpeech` API |
| `NativePdfExtractor` | Extracts text from PDF via Android APIs |
| `NativeImageOcr` | OCR via ML Kit |
| `BookPageProcessor` | Handles book-photo pipeline |
| `TextReflow` | Cleans/reflows extracted text |

### Utilities (`util/` package)

| Class | Purpose |
|-------|---------|
| `OutputActions` | Static helpers: copyText, shareText, shareAudio (FileProvider), saveTextToDownloads, saveAudioToDownloads (MediaStore for API 29+) |
| `HistoryLogger` | Fire-and-forget Room DB logger; IO dispatcher; truncates to 2000 chars |
| `AppPreferences` | SharedPreferences wrapper: theme, TTS defaults, draft text, dev mode toggle |

### Python bridge scripts (called via `PythonBridge`)

All located at `app/src/main/python/` (flat, not under `tts/`):

| Script | Function |
|--------|---------|
| `tts_bridge.py` | Text → audio file path (includes `_generate_prosody_audio` for gTTS prosody and `_generate_edge_prosody` for edge-tts prosody) |
| `emotion_bridge.py` | Text → emotion label + score |
| `stt_bridge.py` | Audio → Marathi transcript |
| `ocr_bridge.py` | Image path → text |
| `pdf_bridge.py` | PDF path → text |
| `web_bridge.py` | URL → cleaned text |
| `correction_bridge.py` | Text → corrected text |
| `script_converter_bridge.py` | Modi ↔ Devanagari |
| `setup_bridge.py` | One-time model init |

### Static assets

| Path | Contents |
|------|---------|
| `app/src/main/assets/stotras/` | `.txt` stotra files (Vishnu Sahasranama, Ram Raksha, etc.) |
| `app/src/main/assets/stotra_catalog.json` | Index of stotra files |

---

## Desktop App Map  (`marathi_tts_desktop/`)

**Language:** Kotlin + JavaFX  **Build:** Gradle  
**Python bridge:** Chaquopy; bridge scripts at `python_bridge/`

### Python bridge scripts (`python_bridge/`)

Same set as mobile (above). `tts/` subtree mirrors web exactly.

### Stotra assets

`stotras/` directory at project root (same `.txt` files as mobile assets).

---

## Web App Map  (`marathi_tts_web/`)

**Framework:** Django 4.x  **Python:** 3.11  **DB:** SQLite (`db.sqlite3`)  
**Venv:** `marathi_tts_web/.venv`  **Start:** `python manage.py runserver` or `.\start_server.ps1`

### Django apps / URL routes

| App / path | Purpose |
|-----------|---------|
| `tts/` | Core TTS engine package (Python, canonical source) |
| `marathi_tts/` | Django project settings, ASGI/WSGI, middleware, URLs |
| `utils/` | Shared web utilities |
| `models/` | ML correction models |
| `static/`, `staticfiles/` | Frontend assets |
| `media/tts/` | Generated audio output |
| `data/stotras/` | Stotra `.txt` source files (web copy) |

---

## TTS Engine Sync Rule

**Any time you create, edit, or delete a file under any one platform's `tts/` tree,
you MUST apply the identical change to the same relative path in all three platforms.**

### How to sync after editing the web platform (the canonical source):

```python
import shutil, os

WEB  = r'd:\marathi_tts\marathi_tts_web\tts'
DESK = r'd:\marathi_tts\marathi_tts_desktop\python_bridge\tts'
MOB  = r'd:\marathi_tts\marathi_tts_mobile\app\src\main\python\tts'

def sync(relative_path: str):
    src = os.path.join(WEB, relative_path)
    for root in [DESK, MOB]:
        dst = os.path.join(root, relative_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f'Synced -> {dst}')
```

Run this after every file edit. For new directories (e.g. `utils/audio/`) also
create the corresponding `__init__.py` in desktop and mobile.

### Platform-specific differences to preserve

The **desktop** and **mobile** `tts_engine.py` use `try/except ImportError` guards
around Django-only imports (`from django.conf import settings`, `VoiceModulator`,
etc.).  When editing `tts_engine.py`, make sure these guards are retained in the
desktop/mobile copies — they are intentional.

---

## Phonetic Engine Architecture

```
Input text
  │
  ├─ Sanskrit (lang=sa or auto-detected)
  │    └─ SandhiEngine → apply_sanskrit_phonetics → G2P → prosody
  │
  ├─ Old Marathi (classical markers detected)
  │    └─ apply_old_marathi_phonetics → G2P → prosody (no schwa deletion)
  │
  └─ Modern Marathi (default)
       └─ GrammarEngine → TextNormalizer → G2P → apply_marathi_phonetics → prosody
```

Key modules (same in all three platforms):

- `phonetic/sandhi_engine.py` — Sanskrit sandhi: avagraha, r-sandhi, visarga+voiced→r, anusvara+sibilant
- `phonetic/metre_engine.py` — Verse metre detection (12-metre catalogue); sets pause timings
- `phonetic/marathi_phonetics.py` — Language-mode phonetic preprocessors
- `audio/prosody_engine.py` — Segment-level pause engine; calls MetreEngine for verse; emotion modifiers; pitch contour; Ovi pulse
- `constants/g2p_constants.py` — Exception lexicon (Sanskrit, Old Marathi, Sant literature)

---

## Custom Stotra Voice Pipeline (FEAT-50, FEAT-53)

### Training Pipeline (`custom-tts-voice-model/scripts/`)

| Script | Purpose |
|--------|---------|
| `preprocess_audio.py` | Normalize audio (22050Hz mono 16-bit), adaptive silence detection, segment at verse boundaries |
| `align_transcript.py` | Map transcript verses to audio segments (numbered ॥N॥ or double-danda parsing) |
| `validate_dataset.py` | Quality checks (SNR, duration ranges, silence ratio, Piper-readiness) |
| `generate_piper_config.py` | Create Piper-compatible dataset (wav/ dir, metadata.csv, config.json) |
| `train_piper.py` | Colab-ready Piper VITS fine-tuning (Hindi base model) |
| `run_pipeline.py` | Master orchestrator (subprocess-based, runs all 4 steps) |

### Adaptive Silence Detection

`preprocess_audio.py` auto-retries with progressively sensitive thresholds if no
silence gaps found at the default -35dB/400ms:

```
-35dB/400ms → -28dB/300ms → -25dB/250ms → -22dB/200ms → -20dB/150ms
```

Stops when at least 3 gaps are found. Segments exceeding MAX_SEGMENT_SEC (15s) are
force-split evenly. CLI overrides: `--silence-thresh-db`, `--min-silence-ms`.

### Custom Voice Engine

**Files:**
- Mobile: `marathi_tts_mobile/app/src/main/python/custom_voice_engine.py`
- Desktop: `marathi_tts_desktop/python_bridge/custom_voice_engine.py`

**Phase A — Segment Library:** Fingerprint-matches input text against pre-recorded
segments (first 80 Devanagari chars, prefix overlap scoring, 0.7 threshold).

**Phase B — ONNX Model:** Loads Piper VITS model via onnxruntime, generates audio
from text input (activated when `stotra_voice.onnx` is present).

### Bridge Integration

Custom voice is the **highest-priority engine** in both fallback chains:

**Mobile (verse):** Custom → Network check → edge-tts verse prosody → edge-tts single → gTTS verse (slow) → gTTS bare

**Mobile (prose):** Custom → Network check → edge-tts prosody → edge-tts single → gTTS prosody → gTTS+pydub → gTTS bare

**Desktop (verse):** Custom → Stage 0 stotra library → Stage 1 TTSEngine → Network check → edge-tts verse prosody → edge-tts single → gTTS verse → gTTS bare

**Desktop (prose):** Custom → Stage 0 stotra library → Stage 1 TTSEngine → Network check → edge-tts prosody → edge-tts single → gTTS prosody → gTTS+pydub → gTTS bare

### A/B Comparison (FEAT-53)

`compare_engines()` in both bridge scripts: runs text through gTTS, Edge-TTS, and
custom voice; returns dict with all audio paths for side-by-side quality comparison.

### Processed Data

| Recording | Segments | Duration | Status |
|-----------|----------|----------|--------|
| ShreeChandrashekharAshtakam | 44 | 7.7 min | Aligned (10 verses) |
| ShreeVishnuSahatranam | 143 | 18.6 min | Piper-ready ✓ |
| ShriRamRakshaStotra | 42 | 9.9 min | Piper-ready ✓ |

Total: 155 utterances, 36.1 min. Piper dataset at `data/piper_dataset/`.

---

## Prosody Preview + Per-Sentence Regen (FEAT-51, FEAT-52)

### Prosody Preview (FEAT-51)

**Bridge function:** `analyze_prosody(text, language, is_verse, emotion)` in both
mobile and desktop `tts_bridge.py`. Returns segment list:

```json
{
  "success": true,
  "segments": [
    {"index": 0, "text": "...", "pause_after_ms": 600, "emotion": "neutral",
     "emphasis": 1.0, "pitch_shift": 0.0, "is_verse": false, "metre_name": "",
     "tts_rate": 1.0}
  ],
  "segment_count": N,
  "is_verse_detected": false,
  "metre": ""
}
```

**Kotlin classes:**
- `ProsodySegment` data class — mirrors bridge JSON fields + `audioPath`
- `ProsodySegmentAdapter` — RecyclerView adapter with DiffUtil, shows text + badges
- `OutputState.prosodySegments` — list of segments, updated by `analyzeProsody()`

**UI flow:** `OutputViewModel.generate()` launches `analyzeProsody()` concurrently
with TTS generation. The prosody preview card shows segments immediately (pure text
analysis, no network). Each segment displays: text, Verse/Prose badge, metre name
(when detected), pause duration, TTS rate.

**Layout:** `prosody_preview_card` in `fragment_output.xml` between emotion_card
and text_preview_card. Contains segment count header, tap hint, and RecyclerView.

### Per-Sentence Regeneration (FEAT-52)

**Bridge function:** `regenerate_segment(text, speed, pitch, volume, language, gender,
is_verse, emotion)` — lightweight single-segment TTS. Skips custom voice for speed.
Fallback: edge-tts → gTTS.

**UI:** Tap any segment in the prosody preview → `OutputViewModel.regenerateSegment()`
calls the bridge, replaces the corresponding `streamChunks[index]` and updates the
segment's `audioPath`. Linear progress indicator shown on the regenerating segment.

**State tracking:** `OutputState.regeneratingIndex` (-1 = none). Adapter highlights
the regenerating item with a progress bar.

---

## MANDATORY — Offline test before finishing any task

**Every task that touches any `tts/` file MUST end by running the offline test
script and confirming ALL checks pass.  Do not report the task as done until
the output shows `RESULT: ALL PASS`.**

### Run the test

```powershell
cd d:\marathi_tts
python test_all_platforms.py
```

### What the test covers

**Step 0 — Syntax (18 files):** Every engine file in all 3 platforms parses cleanly.

**Step 1 — Section A: SandhiEngine**

| Check | What it verifies |
|-------|-----------------|
| Vedic accent strip | U+0951 udātta removed from Sanskrit output |
| Avagraha expand | ऽ resolved; not passed raw to gTTS |
| Anusvara + श | संशय → सन्शय (palatal assimilation) |
| Anusvara + ष | Anusvara before ष assimilated |
| Visarga + vowel | र्-sandhi applied before voiced vowel |
| Visarga + voiced consonant | पुनः दर्शनम् → पुनर् दर्शनम् |
| Visarga + voiceless no change | दुःख visarga unchanged before voiceless |

**Section B: Sanskrit phonetics**

| Check | What it verifies |
|-------|-----------------|
| Sanskrit detect (true) | stotra text → `is_predominantly_sanskrit()` True |
| Sanskrit detect (false) | modern Marathi prose → False |
| OM symbol | ॐ → ओम् |
| Full shloka | `apply_sanskrit_phonetics()` non-empty on 2-line shloka |

**Section C: MetreEngine**

| Check | What it verifies |
|-------|-----------------|
| Metre detect | Anushtubh/Shloka detected for 4-pada text |
| Rate ≤ 0.95 | Verse is recited slower than prose |
| Half-pause ≥ 400 ms | Minimum pause at ।  |
| `apply_to_segments` full | pause_full_ms applied to ॥ segment |
| `apply_to_segments` half | pause_half_ms applied to । segment |
| count_syllables | Returns 3–8 for शुक्लांबरधरं |
| Prose metre | Plain prose returns Prose metre, rate == 0.92 |

**Section D: ProsodyEngine (integration)**

| Check | What it verifies |
|-------|-----------------|
| is_verse_block True | ॥ × 2 → verse block detected |
| is_verse_block False | Prose paragraph → not a verse block |
| segment_text → is_verse | All segments in verse block have `is_verse=True` |
| tts_rate propagated | Verse segments get `tts_rate < 1.0` from MetreEngine |
| segment_text prose | Prose segments have `is_verse=False` |
| Pitch contour applied | At least one verse segment has non-zero pitch_shift |
| Emotion devotional slower | Devotional emotion → lower avg tts_rate than neutral |

**Section E: Old Marathi phonetics**

| Check | What it verifies |
|-------|-----------------|
| Non-empty output | `apply_old_marathi_phonetics()` returns text |
| विठ्ठल retained | Sant lit. retroflex survives |
| ज्ञ → द्न्य | ज्ञानदेव rendered in Marathi way |
| Schwa guard | Classical verse runs without crash or empty return |

**Section F: Modern Marathi phonetics**

| Check | What it verifies |
|-------|-----------------|
| ज्ञ → द्न्य | ज्ञान → द्न्यान |
| Visarga gemination | दुःख not passed raw through |
| Retroflex ळ | ळ preserved in output |
| ॠ → री | Rare vocalic R converted |
| Visarga + sibilant | निःशब्द resolved |

**Section G: G2P exception lexicon keys**

| Check | What it verifies |
|-------|-----------------|
| मुळे | Retroflex ळ word in lexicon |
| गणेश | Sanskrit deity name block present |
| ज्ञानदेव | Sant literature entry present |
| स्तोत्र | Stotra-genre word present |
| नमस्कार | Common greeting/stotra word present |

### If a test fails

1. Fix the failure in the **web** platform first (canonical source).
2. Re-sync the fixed file to desktop and mobile (see sync script above).
3. Re-run `python test_all_platforms.py` and confirm all pass.
4. Only then report the task complete.

### Adding new tests

When adding a new pronunciation rule or new language feature, add a
corresponding assertion to `test_all_platforms.py` **in the same commit**
so regressions are caught immediately.

---

## Coding Standards

- All source files: UTF-8 with BOM-free encoding.
- Devanagari string literals: always use actual Unicode characters, NOT escape sequences
  (i.e. `'राम'` not `'\u0930\u093e\u092e'`) except in comments.
- After any change, run the syntax check:
  ```
  python -c "import ast; [ast.parse(open(f).read()) for f in [...]]"
  ```
- Exception lexicon entries (`g2p_constants.py`) must be added as identical word → correct-form
  pairs;  do NOT transliterate to Latin.
- Never apply schwa deletion inside `apply_old_marathi_phonetics()` — it breaks metre.


---

## TTS Streaming (Mobile)

**Trigger:** TtsViewModel.generateAudio() auto-routes Marathi prose > 250 chars to generateAudioStreaming().

**Algorithm:** splitSentences() -> Semaphore(3) concurrency-limited parallel async(IO) per chunk -> TtsState.streamChunks list -> TtsFragment calls AudioPlayerService.playQueueAsync().

**Concurrency:** Max 3 parallel TTS API calls (Semaphore). Prevents Google TTS rate-limiting and device overload.

**Cancel:** currentJob: Job? stored in TtsViewModel. cancelGeneration() cancels the coroutine. TtsFragment toggles Generate button to "Cancel" during isLoading.

**Status messages:** "Streaming: N of M ✓" (AtomicInteger counter). No "engine locked" wording.

**TtsState** now has: streamChunks: List<String>. When size > 1, use playQueueAsync; else use playAsync(audioPath).

---

## TTS Streaming (Desktop) — FEAT-2

**Trigger:** TtsController.dispatchGeneration() routes Marathi prose > STREAMING_THRESHOLD (250 chars), non-verse to runStreamingGeneration().

**Algorithm:** splitSentences() splits at ।, ॥, ?, !, ., ; with 20-char minimum fragment merging → submit chunks to 3-thread streamingPool with Semaphore(3) → AtomicInteger progress counter → "Streaming: N of M ✓" status → AudioPlayerUtil.playQueue() chains sequential playback.

**Concurrency:** 3-thread fixed pool (`tts-stream`) + Semaphore(3). Each chunk spawns a full PythonBridge subprocess.

**Playback:** AudioPlayerUtil.playQueue(paths, onAllFinished) → recursive playQueueInternal() using setOnEndOfMedia to chain files. Live speed/volume control via JavaFX MediaPlayer.

**Save:** onSaveAudio() concatenates chunk MP3 files via byte-level concatenation (MP3 frames are independently decodable).

**Key classes:**
- TtsController.splitSentences() — sentence-level chunking
- TtsController.runStreamingGeneration() — chunked generation with progress
- TtsController.dispatchGeneration() — threshold-based routing
- AudioPlayerUtil.playQueue() — sequential multi-file playback

---

## Grammar Engine in Bridges — FEAT-3

Both mobile and desktop `tts_bridge.py` now run `MarathiGrammarEngine` on prose text
before passing to any TTS engine. The `_apply_grammar()` function is a lazy singleton
(created once per process) with try/except protection — returns original text on failure.

**When applied:** In `generate_tts()` after `_preprocess_prose_text()`, only for:
- Prose text (not verse mode)
- Language not Sanskrit (`sa`) or English (`en`)

**What it does:** Spelling corrections, sandhi splits, vibhakti/agreement fixes, word
order (SOV enforcement), punctuation restoration, repetition removal, comma insertion
at clause boundaries. Pure rule-based, no ML dependencies.

**Idempotency:** Safe to double-apply — web TTSEngine's `preprocess_marathi_text()` also
runs grammar internally, but the second pass is a no-op on already-corrected text.

---

## BookReader Camera Flow (Mobile)

**Google Lens-like auto-save:** Point camera at book → tap shutter → auto-crop + perspective correct → return to reader. No manual crop step.

**Algorithm:** takePhoto() → loadAndShowCrop():
1. Load JPEG with EXIF rotation
2. Pre-crop to overlay guide frame (getFrameFractions())
3. Run PageEdgeDetector.detect() on pre-cropped bitmap
4. If confidence ≥ 0.30 → apply PerspectiveCropView.perspectiveCropDirect() for de-warp
5. Save JPEG → setResult(RESULT_OK) → finish()

**Fallback:** Confirm (✓) and Retake (↩) buttons are wired for the manual crop editor (Phase 2), but the default flow bypasses it entirely via auto-save.

---

## Emotion Detection (Mobile/Desktop Bridges)

analyze_emotion() always returns: emotion (str), score (float alias of intensity), dominant, intensity, voice_params, scores, success.
_normalize_result() helper ensures these keys are always present.
Categories: happy, sad, angry, fear, surprise, disgust, love, devotional, peaceful, neutral.
Web emotion_constants.py now has devotional + peaceful in all dicts.

---

## ZWNJ chaa Fix

gTTS lang=mr adds y-glide to word-internal -cha suffix. Fix: insert ZWNJ after G2P in marathi_phonetics.py (all 3 platforms) and in tts_bridge.py verse + prose Stage3b paths (mobile + desktop).

---

## Mobile Test Cases T23-T26

T23 (NLP): Sad emotion detection: sad text -> emotion=sad, score>0
T24 (TTS): Streaming 3-sentence Marathi -> 3 chunks all succeed
T25 (INPUT): OCR → TTS pipeline: render Devanagari PNG → NativeImageOcr → TTS → verify audio
T26 (INPUT): Native PDF OCR: Devanagari bitmap embedded in PDF → NativePdfExtractor → verify Devanagari text

### Improved tests (T13/T14)
T13: Now uses NativeImageOcr (ML Kit Devanagari) instead of Python ocr_bridge (which requires Tesseract).
T14: buildMinimalPdf now includes proper xref table → PyPDF2 extracts text (method=pypdf2, chars>0).
T15: Now uses real T14 text (src=T14) instead of fallback.

---

## Emotion Detection (Mobile/Desktop Bridges)

analyze_emotion() always returns: emotion, score (alias of intensity), dominant, voice_params, scores, success.
_normalize_result() helper ensures keys always present.
Categories: happy, sad, angry, fear, surprise, disgust, love, devotional, peaceful, neutral.
Web emotion_constants.py now has devotional + peaceful in all dicts.

---

## ZWNJ cha Fix (word-internal genitive suffix)

gTTS lang=mr adds y-glide to word-internal -cha. Fix: ZWNJ after G2P in apply_marathi_phonetics() (synced all 3 platforms) and tts_bridge.py verse + Stage3b paths (mobile + desktop).

---

## Prosody-Segmented Generation (FEAT-1 + FEAT-8)

Both mobile and desktop bridges now have two prosody functions that segment prose text
at natural clause/sentence boundaries and generate per-segment TTS audio with calibrated
silence pauses.

### Functions

| Function | Engine | Max segments | Pause source |
|----------|--------|-------------|-------------|
| `_generate_prosody_audio()` | gTTS | 25 | pydub silence |
| `_generate_edge_prosody()` | edge-tts | 15 | pydub silence |

### Fallback chain (mobile)

1. `_generate_edge_prosody()` — prosody-segmented edge-tts (FEAT-8)
2. `_generate_edge_tts()` — single-call edge-tts
3. `_generate_prosody_audio()` — prosody-segmented gTTS (FEAT-1)
4. Stage 1: single-call gTTS + pydub effects
5. Stage 2: bare gTTS fallback

### Fallback chain (desktop)

1. Stage 0: stotra library (pre-recorded)
2. Stage 1: TTSEngine (web app engine)
3. `_generate_edge_prosody()` — prosody-segmented edge-tts (FEAT-8)
4. `_generate_edge_tts()` — single-call edge-tts
5. `_generate_prosody_audio()` — prosody-segmented gTTS (FEAT-1)
6. Stage 3b: single-call gTTS + pydub effects
7. Stage 4: bare gTTS fallback

### Design

- ProsodyEngine gets `speaking_rate=1.0` → natural pause calibration
- User speed/pitch/volume: edge-tts uses native SSML params; gTTS uses pydub post-processing
- Per-segment pitch_shift from ProsodyEngine emphasis (questions +0.05, exclamations -0.05) applied to edge-tts only
- Verse text bypasses prosody (has its own segmentation path)
- All prosody functions return `None` on failure → transparent fallthrough
- Temp segment files cleaned up in `finally` block

---

## Gaṇa Pattern Matching + New Metres (FEAT-4 + FEAT-12)

**`classify_syllable_weights(pada: str) -> str`** (module-level in `metre_engine.py`):
Returns a string of `'L'`/`'G'` characters, one per syllable. Guru conditions: long
vowel mātrā, anusvara/chandrabindu/visarga following syllable, saṃyoga (consonant
cluster closing syllable). Laghu: short open syllable.

**`MetreDefinition`** new fields:
- `gana_pattern: str` — expected L/G weight string (empty = no pattern check)
- `yati_syllables: List[int]` — syllable positions for caesura pauses (0-indexed)

**Six new metres** added to `METRE_CATALOGUE`:

| Metre | Syllables | Yati positions |
|-------|-----------|---------------|
| Sragdharā | 21 | [7, 14] |
| Indravajra | 11 | [6] |
| Upendravajra | 11 | [6] |
| Rathoddhatā | 11 | [5] |
| Upajati | 11 | [6] |
| Vamshastha | 12 | [6] |

Existing metres updated with `yati_syllables`: Shardula([12]), Vasanta-tilaka([8]),
Mandakranta([4,10]), Malini([8]), Anushtubh([4]), Trishtubh([5]), Jagati([4,8]).

`_match_syllabic_metre()` now accepts `lines` param; computes `actual_pattern` from
first usable line and adds `gana_bonus * 0.20` to confidence when patterns overlap.
New `_gana_match_score(observed, expected) -> float` returns proportion of matching positions.

---

## Yati Caesura Pauses (FEAT-6)

**`_split_pada_at_yati(text, yati_positions) -> List[str]`** in `MarathiProsodyEngine`:
Word-boundary approximation — accumulates `count_syllables()` per word, splits at the
nearest word boundary once target syllable count is reached or exceeded. Returns `[text]`
(unsplit) if split cannot be resolved. Never splits mid-word.

**`_apply_yati_splits(segments, prosody) -> None`**:
Iterates verse segments; splits each at all yati positions (in order); inserts a
sub-segment with `pause_yati_ms` duration between parts; replaces `segments[:]` in-place.
Triggered when `prosody.metre.yati_syllables` is non-empty.

---

## Abhanga Refrain Detection (FEAT-13)

**`_detect_abhanga_refrain(segments) -> None`** in `MarathiProsodyEngine`:
- Counts exact text repetitions across all verse segments
- Counts rhyme suffix repetitions (last 2 Devanagari characters)
- Marks segments with 2+ exact repeats OR 3+ rhyme matches: `emphasis = max(existing, 1.1)`,
  `pitch_shift += 0.5`
- Triggered when `metre.name == 'Abhanga'`

---

## Schwa Deletion Lexicon (FEAT-10)

`SCHWA_EXCEPTIONS` in `g2p_constants.py` expanded from 8 to 220+ entries grouped as:
- Verb forms ending in `-तो`, `-ते`, `-णे` (common present tense and infinitives)
- `-कर` suffix compounds (demonyms: पुणेकर, मुंबईकर, शेतकरी)
- Common adjectives, nouns, adverbs, postpositions
- Maharashtra place names
- Bhakti/devotional vocabulary (विठोबा, वारकरी, एकादशी, etc.)

Words in this dict bypass rule-based schwa processing (identity map = gTTS handles correctly).

---

## Chandrabindu Nasalization (FEAT-15)

`_generate_edge_prosody()` and `_generate_edge_verse_prosody()` in **both** mobile and
desktop `tts_bridge.py`:
- For each segment, checks if `'\u0901'` (chandrabindu ँ) appears in the processed text
- When present: applies `-25 pp` volume reduction (≈ -3 dB nasal softening):
  ```python
  seg_vol_str = f"{max(int((volume - 1.0) * 100) - 25, -50):+d}%"
  ```
- Otherwise: uses the flat `vol_str`
- The per-segment volume string `sv` is passed as a default arg to the `_run_seg()` closure

---

## Edge-TTS Verse Prosody (FEAT-VQ)

**Function:** `_generate_edge_verse_prosody()` in both mobile and desktop `tts_bridge.py`

**Problem solved:** Verse/stotra text previously bypassed the prosody-segmented edge-tts
pipeline (which was prose-only), falling to single-call edge-tts or robotic gTTS slow=True.

**How it works:**
1. ProsodyEngine segments verse text at natural boundaries (। and ॥ markers)
2. Metre detected: Anushtubh, Sragdhara, Stotra, etc. — sets per-segment tts_rate
3. Pitch contour: wave/falling/rising pattern from MetreDefinition applied per segment
4. Per-segment preprocessing: stotra-specific + G2P (language-aware: Sanskrit/Old Marathi/Marathi)
5. Edge-tts neural voice generates each segment with per-segment SSML: rate, pitch, volume
6. pydub stitches segments with calibrated verse pauses (800ms half, 1200ms full, 1600ms stanza)
7. Chandrabindu nasalization (FEAT-15) applied per segment

**Segment cap:** 40 (higher than prose's 15 since verse segments are shorter)

**Fallback:** Returns None on failure → falls to single-call edge-tts → gTTS verse

---

## Marathi Morphological Analyzer (FEAT-33)

**File:** `tts/utils/text/morphological_analyzer.py` — synced to all 3 platforms.

**Class:** `MarathiMorphologicalAnalyzer`  
**Singleton:** `get_analyzer()` module-level function

### Design

| Component | Web | Desktop | Mobile |
|-----------|-----|---------|--------|
| Rule-based suffix stripping (~70 rules) | ✅ | ✅ | ✅ |
| Morfessor statistical model (`mr.model`) | ✅ | ✅ | ❌ (no APK bloat) |

Desktop has `mr.model` copied to `python_bridge/tts/morph/morfessor/mr.model`.  
Mobile gets rule-based only — Morfessor `ImportError` is caught and ignored silently.

### Public API

```python
m = MarathiMorphologicalAnalyzer()
m.stem('बोलतो')                   # → 'बोल'
m.segment('रामाचा')               # → ['राम', 'चा']
m.is_same_stem('बोलतो', 'बोलते') # → True
m.morpheme_boundary_positions('बोलतो')  # → [5] (char index where suffix starts)
m.is_morfessor_available()         # → True / False
```

### Integrations

1. **`g2p_engine.py` explicit schwa mode** — `_apply_schwa_rules()` uses
   `morpheme_boundary_positions()` to insert `ZWNJ` at stem/suffix boundaries,
   preventing edge-tts from inserting y-glide between morpheme components.

2. **`marathi_grammar.py` `remove_repetitions()`** — Pass 2 stem-aware deduplication:
   consecutive words sharing the same stem (e.g., `बोलतो बोलते`) are collapsed to the
   first occurrence. Uses `is_same_stem()` with minimum stem length ≥ 4 chars to avoid
   false positives from short words.

### Suffix categories covered

Genitive clusters (`च्यांना`, `च्या`, `चा`, `ची`, `चे`), verbal inflections (`णे`, `तो`,
`ते`, `तात`, `ला`, `ली`, `ले`), case markers (`ने`, `शी`, `त`), plural/honorific clusters
(`ांना`, `ांनी`, `ांचा`), postpositions (`साठी`, `मध्ये`, `पासून`, `मुळे`, `बद्दल`),
participles (`णारा`, `णारी`, `णारे`), abstract suffixes (`पणा`, `पण`), emphatics (`ही`, `च`).

---

## Test Coverage (FEAT-32)

`test_all_platforms.py` gains three new check sections (run for all 3 platforms):

| Section | Module | Checks |
|---------|--------|--------|
| I | `MarathiTextNormalizer` | Non-empty output, verse number strip, इ. expansion, empty input |
| J | `MarathiGrammarEngine` | `process()` returns str, `remove_repetitions()` deduplicates, empty input |
| K | `number_to_words` | `number_to_marathi_words(1)=एक`, `10=दहा`, `convert_time` 9:00 AM/12:45, ordinal, percentage |

Sections **skip** (not fail) via `except ModuleNotFoundError` when optional `indicnlp`
production dep is absent in the offline CI environment.

`tts/utils/text/__init__.py` now has a `try/except ImportError` guard around
`from .text_normalizer import MarathiTextNormalizer` — prevents package import failures
when `indicnlp` is not installed (e.g. desktop/mobile build environments).

---

## Mobile Test Cases T23-T26

T23 (NLP): Sad emotion detection - sad text must return emotion=sad, score>0
T24 (TTS): 3-sentence streaming - 3 chunks all succeed
T25 (INPUT): OCR → TTS end-to-end pipeline
T26 (INPUT): Native PDF OCR via embedded Devanagari image

---

## STT Playback Loopback Transcription (BUG-42)

Android's `SpeechRecognizer` is mic-only — it cannot process audio files.
Instead of showing an error, the mobile app uses **playback loopback**:

1. User browses an audio file and taps **Transcribe**
2. Fragment requests mic permission (if not already granted)
3. `MediaPlayer` plays the audio through the phone speaker (volume auto-boosted to ~80%)
4. `SpeechRecognizer` listens via mic simultaneously with `EXTRA_PARTIAL_RESULTS`
5. On each `onResults` callback: text is appended to `accumulatedTranscript`, recognizer
   auto-restarts (200 ms delay) if `MediaPlayer` is still playing — this gives continuous
   recognition over long audio
6. On `onError` (silence timeout, no match): recognizer also auto-restarts if playback continues
7. When `MediaPlayer.OnCompletionListener` fires: 2 s grace period, then final transcript shown
8. Transcribe button toggles to **Cancel** during playback loopback; tapping again stops
   both `MediaPlayer` and `SpeechRecognizer`, keeping any partial transcript

**Limitations:**
- Accuracy depends on speaker volume and ambient noise
- Works best with clear Marathi/Hindi speech recordings
- Long files (>5 min) may have gaps due to recognizer restart latency
- Not as accurate as Whisper (which runs on desktop/web)

**Key fields in `SttFragment`:**
- `mediaPlayer: MediaPlayer?` — plays the audio file
- `isPlaybackTranscribing: Boolean` — loopback mode active flag
- `accumulatedTranscript: StringBuilder` — progressive transcript accumulator
- `handler: Handler` — for delayed restart / cleanup callbacks

---

## Versioning & Release Workflow

### Version scheme

The project uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`) plus an optional
hotfix suffix:

| Format | Example | When to use |
|--------|---------|-------------|
| `MAJOR.MINOR.PATCH` | `2.0.0` | Normal releases |
| `MAJOR.MINOR.PATCH-hotfix.N` | `1.3.2-hotfix.1` | Urgent fix on a released version |

- **MAJOR** — Breaking changes, large rewrites, major new platform features.
- **MINOR** — New screens, new TTS features, new bridge capabilities.
- **PATCH** — Bug fixes, phonetic rule tweaks, dependency bumps.
- **Hotfix** — Emergency fix applied on top of an already-released version
  without rolling the patch number. Hotfix counter auto-increments.

### Source of truth

The canonical version lives in **`marathi_tts_mobile/app/build.gradle.kts`**:

```kotlin
versionCode = 12        // monotonically increasing integer (Google Play requirement)
versionName = "1.3.2"   // human-readable SemVer string
```

`deploy_mobile.ps1` reads and writes these values automatically when a bump
flag is passed.

### Interactive confirmation

Every run of `deploy_mobile.ps1` shows a version menu **before** building:

```
--------------------------------------------
  Current version: v1.2.3 (build 7)

  Version this build?
    [1] Major release  (v2.0.0) -- breaking changes, new major feature
    [2] Minor release  (v1.3.0) -- new features, backward compatible
    [3] Hotfix/patch   (v1.2.4) -- bug fixes
    [4] Build only     (v1.2.3 build 8) -- no version bump, just increment build
    [n] Skip           -- no versioning

  Choice [1/2/3/4/n]:
--------------------------------------------
```

- Choosing **1/2/3** bumps the version, increments `versionCode`, writes back to
  `build.gradle.kts`, prompts for one-line release notes, and builds a **release APK**.
- Choosing **4** just increments `versionCode` (build counter) and builds **debug**.
- Choosing **n** builds the current version without any changes (debug).

The script also lists connected ADB devices at startup before showing the menu.

### How to run

```powershell
# Normal interactive deploy
.\deploy_mobile.ps1

# Build only, no device install
.\deploy_mobile.ps1 -NoDeploy

# Target a specific device
.\deploy_mobile.ps1 -DeviceSerial <serial>
```

### APK backup

Every deploy copies docs to `C:\My_Drive_Backup\builds\marathi_tts\`. APK is only copied for release builds.

| What | When |
|------|------|
| `marathi-tts-v<VERSION>-release-<YYYYMMDD-HHmmss>.apk` | Release builds only |
| `marathi-tts-v<VERSION>-release-<YYYYMMDD-HHmmss>.txt` | Release builds only (one-line release notes) |
| `CHANGELOG.md` | Every deploy |
| `bugs.txt` | Every deploy |
| `features.txt` | Every deploy |
| `tts_features.txt` | Every deploy |

**Note:** The signing key is stored in `marathi_tts_mobile/marathi_tts_release.jks` and
credentials in `marathi_tts_mobile/keystore.properties`. Both are excluded from git via
`.gitignore`. The signing config is wired into `app/build.gradle.kts` — release builds
are automatically signed and installable on device via ADB.

The deploy script also copies these docs to the backup folder as `.txt` files
(if they exist):

| Source | Backup copy |
|--------|-------------|
| `marathi_tts_web/tts_features.md` | `tts_features.txt` |
| `BUGS.txt` (project root) | `bugs.txt` |
| `FEATURES.txt` (project root) | `features.txt` |

This keeps a snapshot of known bugs and planned features alongside each build.

### Tracking bugs and features

Before each release, review the txt files in the backup folder
(`C:\My_Drive_Backup\builds\marathi_tts\`) to check for reported bugs and
planned features:

- **bugs.txt** — Known bugs and regressions. Verify each is fixed or documented
  in the release notes before shipping.
- **features.txt** / **tts_features.txt** — Planned and implemented features.
  Confirm new features are listed and tested.

Maintain the source files (`BUGS.txt`, `FEATURES.txt`,
`marathi_tts_web/tts_features.md`) as you discover bugs or plan features.
The deploy script will always push the latest copies to the backup folder.

### Release checklist

1. Ensure all tests pass: `python test_all_platforms.py` → `RESULT: ALL PASS`
2. Stage notable unreleased changes under `## [Unreleased]` in `CHANGELOG.md`
3. Run deploy: `.\deploy_mobile.ps1`
4. At the menu, choose the appropriate bump level (1/2/3).
5. Enter a one-line release note when prompted (deploy script auto-updates `CHANGELOG.md`).
6. Confirm APK copied to `C:\My_Drive_Backup\builds\marathi_tts\`.
7. Commit the updated `build.gradle.kts` + `CHANGELOG.md` with message: `release: v<VERSION>`
8. Tag the commit: `git tag v<VERSION>` and push.

### Hotfix workflow

```
main ──●──●──●── v1.3.0 ──●── v1.3.1 ──●── ...
                     \
                      └─ hotfix/1.3.0 ── v1.3.0-hotfix.1  (cherry-pick fix)
```

1. Create a branch from the release commit: `git checkout -b hotfix/<base-version>`
2. Apply the minimal fix.
3. Deploy: `.\deploy_mobile.ps1` → choose **[3] Hotfix/patch** at the menu.
4. Commit + tag: `release: v1.3.0-hotfix.1`
5. Cherry-pick the fix back to `main` branch.

---

## Copy / Share / Save UX (FEAT-34)

All 10 mobile screens now have unified Copy/Share output actions via `OutputActions` utility.

| Screen | Copy | Share | Save | Send to TTS |
|--------|------|-------|------|-------------|
| TTS | ✅ text | ✅ audio | ✅ audio→Downloads | — |
| STT | ✅ transcript | ✅ transcript | — | — |
| OCR | ✅ text | ✅ text | — | ✅ (existing) |
| PDF | ✅ text | ✅ text | — | ✅ (existing) |
| Web Fetch | ✅ text | ✅ text | — | ✅ (existing) |
| Correction | ✅ corrected | ✅ corrected | — | ✅ (existing) |
| Modi | ✅ converted | ✅ converted | — | — |
| Emotion | ✅ analysis | ✅ analysis | — | ✅ (existing) |
| Stotra | ✅ stotra text | ✅ stotra text | — | ✅ (existing) |
| BookReader | ✅ text | ✅ text | — | ✅ (NEW) |

**FileProvider paths:** `file_paths.xml` includes `cache-path`, `files-path`, and
`external-files-path` to cover all possible audio output locations (including
Chaquopy-generated files under `getFilesDir()`).

**Icons:** `ic_content_copy_24.xml`, `ic_share_24.xml`, `ic_download_24.xml` (Material
vector drawables, `?attr/colorOnSurface` tint).

---

## PDF Page Selection (FEAT-35)

**Problem:** Large PDFs (100+ pages) are not feasible for full TTS. Users need to choose
which pages to listen to.

**Flow:**
1. Browse PDF → Extract → all pages extracted with per-page text
2. Page selection card appears showing "{N} Pages" with a range input field
3. Pre-filled with all pages for small PDFs (≤12), prompts selection for larger ones
4. User types ranges like "1-5, 8, 10-12" — extracted text preview updates live
5. "Send to TTS" only sends selected pages' text

**Architecture:**

- `pdf_bridge.py`: `extract_pdf()` returns `pages: List[str]` (per-page text) alongside `text`
- `NativePdfExtractor.kt`: `extractPages()` returns `ExtractionResult(combinedText, pageTexts, pageCount)`
- `PdfState`: `pageTexts: List<String>`, `selectedPages: Set<Int>` (1-indexed), `pageCount: Int`
- `PdfViewModel`: `setPageRange(rangeText)`, `selectAllPages()`, `getSelectedText()`,
  `parsePageRange()` / `formatPageRange()` (companion object, static)
- `fragment_pdf.xml`: page selection card with `page_range_input`, `select_all_btn`,
  `selected_pages_label`, `page_count_label`

---

## Tier 2 UX — Room DB + History + Favorites + Bookmarks + Batch OCR (FEAT-36)

### Room Database

**File:** `data/AppDatabase.kt` — singleton "marathi_tts.db", version 1  
**Plugin:** KSP 1.9.22-1.0.17 + Room 2.6.1

| Entity | PK | Fields |
|--------|-----|--------|
| `HistoryEntry` | id (autoGenerate) | category, inputText, outputText, audioPath?, engine?, timestamp |
| `StotraFavorite` | stotraId (String) | title, titleEn, deity, timestamp |
| `UrlBookmark` | id (autoGenerate) | url, title?, timestamp |
| `RecentTtsInput` | id (autoGenerate) | text, timestamp |

| DAO | Key methods |
|-----|-------------|
| `HistoryDao` | getAll(), getByCategory(), insert(), delete(), deleteAll(), trimOld(keep 200) |
| `StotraFavoriteDao` | getAll(), getAllIds(), isFavorite(), insert(), delete() |
| `UrlBookmarkDao` | getRecent(limit 20), insert(REPLACE), deleteByUrl(), trimOld() |
| `RecentTtsInputDao` | getRecent(limit 5), insert(), deleteByText(), trimOld() |

### History Screen

- `ui/history/HistoryFragment` → nav ID `historyFragment` in drawer
- Filter chips: All / TTS / STT / OCR / Stotra / Other (groups PDF/WEB/CORRECTION/MODI/EMOTION/BOOK_READER)
- Tap entry → options dialog (copy / share / send to TTS)
- Clear All button with confirmation dialog

### HistoryLogger

`util/HistoryLogger.kt` — fire-and-forget singleton, IO dispatcher, truncates to 2000 chars.
Wired to all 10 screens with hash-based dedup (each fragment stores `lastLoggedXxxHash`).

### Stotra Favorites

Heart icon toggle on each stotra in list + detail view. `StotraFavoriteDao` persists.
"★ Favorites" chip in StotraFragment filters to favorites only.

### URL Bookmarks (WebFetch)

Recent fetched URLs shown as chips (up to 8). Tap to fill URL field, close icon to delete.
Saved on successful fetch via `UrlBookmarkDao`.

### Quick Re-generate Chips (TTS)

Last 5 TTS inputs shown as Material chips below text input. Tap to fill, close to delete.
Saved on generate via `RecentTtsInputDao`.

### Batch OCR

`batch_btn` in fragment_ocr.xml launches `GetMultipleContents("image/*")`.
`OcrViewModel.extractBatch()` processes images sequentially with progress status
("Batch: N / M"). Results concatenated with "--- Image N ---" separators.

---

## Tier 3 UX — Settings + Dark Mode + Draft Persistence (FEAT-37)

### Settings Screen

**Fragment:** `ui/settings/SettingsFragment` → nav ID `settingsFragment` in drawer  
**Layout:** `fragment_settings.xml`  
**Prefs helper:** `util/AppPreferences.kt` — SharedPreferences wrapper (`marathi_tts_prefs`)

| Section | Controls |
|---------|----------|
| Appearance | Theme spinner (System/Light/Dark) — applies via `AppCompatDelegate.setDefaultNightMode()` |
| TTS Defaults | Engine spinner (Auto/Edge-TTS/gTTS/Native), Speed/Pitch/Volume sliders |
| Data Management | Clear History (Room), Clear Cache (cacheDir + output/), Reset to Defaults |
| About | App icon, name, version from `BuildConfig`, feature summary |

### AppPreferences keys

| Key | Type | Default | Used by |
|-----|------|---------|---------|
| `theme_mode` | String | `"system"` | MainActivity (onCreate), SettingsFragment |
| `default_engine` | String | `"auto"` | SettingsFragment, TtsFragment (future) |
| `default_speed` | Float | `1.0` | TtsFragment (slider init) |
| `default_pitch` | Float | `1.0` | TtsFragment (slider init) |
| `default_volume` | Float | `1.0` | TtsFragment (slider init) |
| `tts_draft_text` | String | `""` | TtsFragment (onPause save / onViewCreated restore) |

### Dark Mode

- Theme parent: `Theme.Material3.DayNight.NoActionBar`
- Light colors: `values/colors.xml` (Saffron #E65C00 primary)
- Dark colors: `values-night/colors.xml` (auto-generated M3 dark scheme)
- Applied in `MainActivity.onCreate()` before `super.onCreate()`

### Dynamic Version

Nav drawer header (`nav_header.xml`) has `nav_version_text` TextView.
`MainActivity` sets it to `"v${BuildConfig.VERSION_NAME}"` after view creation.
`buildConfig = true` enabled in `build.gradle.kts` buildFeatures.

### TTS Draft Persistence

- `TtsFragment.onPause()` saves current text to `AppPreferences.setTtsDraft()`
- `TtsFragment.onViewCreated()` restores draft if no `tts_text` argument was passed
- Slider defaults (speed/pitch/volume) loaded from AppPreferences on fragment creation

### Icons

| File | Purpose |
|------|---------|
| `ic_settings.xml` | Material gear icon for drawer menu |
| `ic_clear_cache.xml` | Calendar/clear icon for Clear Cache button |
| `ic_reset.xml` | Circular arrow icon for Reset to Defaults |

---

## Phase 4: Innovation Features (FEAT-54 through FEAT-58)

### Emotion Intensity Slider (FEAT-54)

**UI:** `slider_emotion_intensity` (Slider, 0.0–1.0, stepSize=0.05) inside `emotion_card`
in `fragment_output.xml`. Default 0.5 (50%).

**Python:** `emotion_bridge.py` → `get_scaled_voice_params(emotion, intensity)` linearly
interpolates between neutral `{pitch:1.0, speed:1.0, volume:0.0}` and full emotion params.
`tts_bridge.py` → `generate_tts()` accepts `emotion_intensity` parameter; prosody functions
scale `seg.pitch_shift * emotion_intensity` and `1.0 + (seg.tts_rate - 1.0) * emotion_intensity`.

**Kotlin:** `OutputState.emotionIntensity`, `OutputViewModel.setEmotionIntensity()`,
`TtsEngineManager.generate()` and `tryGtts()` pass `emotion_intensity` kwarg to bridge.

### Phonetic Explainer (FEAT-55)

**Trigger:** Long-press any segment in the prosody preview RecyclerView.

**Python:** `tts_bridge.py` → `explain_phonetics(word, language)` traces 4 stages:
1. G2P exception lexicon lookup
2. SandhiEngine rules (Sanskrit text)
3. Language-specific phonetics (marathi_phonetics / old_marathi / sanskrit)
4. G2P engine transformations

Returns `{original, final, rules: [{stage, rule, before, after, description}]}`.

**Kotlin:** `OutputViewModel.PhoneticRule` / `PhoneticExplanation` data classes,
`explainPhonetics()` calls bridge. `ProsodySegmentAdapter` has `onSegmentLongClick` callback.
`OutputFragment.observePhoneticExplanation()` shows AlertDialog with formatted rules.

### Batch Stotra Playlist (FEAT-56)

**Activation:** Long-press any stotra in the list → enters playlist mode.

**State:** `StotraListState` gains `isPlaylistMode`, `playlistSelection: Set<String>` (IDs),
`playlistPaths`, `playlistProgress/Total`, `isPlaylistPlaying`, `playlistCurrentIndex`.

**Adapter:** `StotraAdapter` shows `playlist_check` indicator (circle + ✓) in playlist mode.
`MaterialCardView.isChecked` highlights selected cards.

**Generation:** `StotraViewModel.generatePlaylist()` loops through selected stotras,
tries pre-recorded audio first (Stage 0), falls back to TTS (Stage 1), collects paths.
Progress bar updates during generation.

**Playback:** `StotraFragment.startPlaylistPlayback()` calls `AudioPlayerService.playQueueAsync()`
with `onChunkStart/onAllComplete/onError` callbacks for sequential playback.

**Controls:** Playlist button, Select All, Play All, Stop, Cancel during generation.

### Accent Profiles (FEAT-57)

**Python:** `ACCENT_PROFILES` dict in `tts_bridge.py` with 5 profiles:

| Profile | Pitch offset | Rate offset |
|---------|-------------|-------------|
| Standard (प्रमाण) | 0.0 | 0.0 |
| Mumbai (मुंबई) | +0.03 | +0.08 |
| Northern (उत्तर) | -0.02 | -0.05 |
| Konkanastha (कोकणस्थ) | +0.05 | -0.03 |
| Deccani (दख्खनी) | -0.04 | 0.0 |

`_apply_accent(speed, pitch, accent)` adjusts params at the start of `generate_tts()`.
`get_accent_profiles()` returns profile list for UI.

**UI:** `accent_card` with `ChipGroup` (filter chips, singleSelection=true) in
`fragment_output.xml`. `OutputFragment.setupAccentChips()` maps chip IDs to accent keys
and updates description label. `OutputState.accent`, `OutputViewModel.setAccent()`.

### Smart Text Clipping (FEAT-58)

**UI:** `clip_preview_card` in `fragment_input.xml` — appears when text exceeds 250 chars.
Shows segment count header and first 6 segment snippets.

**Logic:** `InputFragment.setupSmartClipPreview()` adds a text watcher. `smartSplit(text)`
uses NLP-aware sentence splitting (same algorithm as `OutputViewModel.splitSentences()`):
splits at ।/॥/?!/.; merges fragments under 40 chars. `updateClipPreview()` shows/hides
the card and formats the preview text.
