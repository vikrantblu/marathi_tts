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

## RULE 0C — CHECK BUGS & FEATURES (read before every task)

**Before starting any coding task, read these three files:**

1. `BUGS.txt` (project root) — known bugs and regressions
2. `FEATURES.txt` (project root) — planned and shipped features
3. `marathi_tts_web/tts_features.md` — detailed TTS feature documentation

**Why:** These files track what is broken and what is planned.  When fixing a
bug or adding a feature, check whether it is already listed.  After completing
work, update the relevant file:

- **Bug fixed** → move the entry from Open to Fixed in `BUGS.txt` with the version.
- **New bug discovered** → add it to the Open section of `BUGS.txt`.
- **Feature shipped** → move the entry from Planned to Shipped in `FEATURES.txt`.
- **New feature planned** → add it to the Planned section of `FEATURES.txt`.
- **TTS capability changed** → update `marathi_tts_web/tts_features.md`.

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

### Navigation

Pattern: `DrawerLayout` (hamburger) + `NavigationView` sidebar + `NavHostFragment`  
All fragments are top-level destinations (no Back arrow — drawer shows on every screen).

| Nav ID | Fragment class | Screen |
|--------|---------------|--------|
| `ttsFragment` ★ | `ui/tts/TtsFragment` | Marathi TTS — enter text, speak |
| `emotionFragment` | `ui/emotion/EmotionFragment` | Emotion analysis |
| `sttFragment` | `ui/stt/SttFragment` | Speech-to-text |
| `ocrFragment` | `ui/ocr/OcrFragment` | Camera OCR → text |
| `pdfFragment` | `ui/pdf/PdfFragment` | PDF → read aloud |
| `webFetchFragment` | `ui/web/WebFetchFragment` | Fetch web page → TTS |
| `correctionFragment` | `ui/correction/CorrectionFragment` | Spell / grammar correction |
| `modiFragment` | `ui/modi/ModiFragment` | Modi script converter |
| `stotraFragment` | `ui/stotra/StotraFragment` | Stotra library browser |
| `bookReaderFragment` | `ui/bookreader/BookReaderFragment` | Book camera + page reader |
| `testDashboardFragment` | `ui/test/TestDashboardFragment` | Feature test dashboard |

★ = start destination

Drawer menu file: `res/menu/bottom_nav_menu.xml`  
Nav graph file: `res/navigation/nav_graph.xml`

### Layout files

| File | Used by |
|------|---------|
| `activity_main.xml` | `MainActivity` — DrawerLayout + Toolbar + NavHostFragment |
| `nav_header.xml` | Drawer header |
| `fragment_tts.xml` | TtsFragment |
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
| `fragment_test_dashboard.xml` | TestDashboardFragment |
| `item_test_row.xml` | TestDashboardAdapter — result row |
| `item_test_group_header.xml` | TestDashboardAdapter — group section header |

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

### Python bridge scripts (called via `PythonBridge`)

All located at `app/src/main/python/` (flat, not under `tts/`):

| Script | Function |
|--------|---------|
| `tts_bridge.py` | Text → audio file path |
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

- `phonetic/sandhi_engine.py` — Sanskrit sandhi: avagraha, r-sandhi, anusvara+sibilant
- `phonetic/metre_engine.py` — Verse metre detection (12-metre catalogue); sets pause timings
- `phonetic/marathi_phonetics.py` — Language-mode phonetic preprocessors
- `audio/prosody_engine.py` — Segment-level pause engine; calls MetreEngine for verse
- `constants/g2p_constants.py` — Exception lexicon (Sanskrit, Old Marathi, Sant literature)

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

**Algorithm:** splitSentences() -> parallel async(IO) per chunk -> TtsState.streamChunks list -> TtsFragment calls AudioPlayerService.playQueueAsync().

**TtsState** now has: streamChunks: List<String>. When size > 1, use playQueueAsync; else use playAsync(audioPath).

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

**Trigger:** TtsViewModel.generateAudio() auto-routes Marathi prose > 250 chars to generateAudioStreaming().

**Algorithm:** splitSentences() -> parallel async(IO) per chunk -> TtsState.streamChunks list -> TtsFragment calls AudioPlayerService.playQueueAsync().

**TtsState** now has: streamChunks: List<String>. When size > 1, use playQueueAsync; else use playAsync(audioPath).

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

## Mobile Test Cases T23-T26

T23 (NLP): Sad emotion detection - sad text must return emotion=sad, score>0
T24 (TTS): 3-sentence streaming - 3 chunks all succeed
T25 (INPUT): OCR → TTS end-to-end pipeline
T26 (INPUT): Native PDF OCR via embedded Devanagari image

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

The deploy script **always asks for confirmation** before changing the version:

- **With a bump flag** (`-BumpMinor`, `-BumpPatch`, etc.) — shows the proposed
  new version and asks `Proceed with version bump? (Y/n)`.  Press Enter or `Y`
  to accept; anything else skips the bump and builds with the current version.
- **Without a bump flag** — shows the current version and asks
  `Bump version before building? (major/minor/patch/hotfix/N)`.  Type the level
  to bump, or press Enter / `N` to build without changing the version.

This ensures you never accidentally bump or forget to bump.

### How to bump (deploy script flags)

```powershell
# Regular feature release (minor bump)
.\deploy_mobile.ps1 -Release -BumpMinor

# Bug-fix release
.\deploy_mobile.ps1 -Release -BumpPatch

# Emergency hotfix on current release
.\deploy_mobile.ps1 -Release -Hotfix

# Major version bump
.\deploy_mobile.ps1 -Release -BumpMajor

# Build WITHOUT bumping (re-deploy same version)
.\deploy_mobile.ps1 -Release
```

Each bump flag:
1. Reads current `versionName` and `versionCode` from `build.gradle.kts`.
2. Shows the proposed version and asks for confirmation.
3. On `Y`: increments `versionCode` by 1 and writes both values back.
4. On `n`: skips the bump and proceeds with the current version.

### APK backup

Every deploy (debug or release) copies the built APK to:

```
C:\My_Drive_Backup\builds\marathi_tts\marathi-tts-v<VERSION>-<variant>-<YYYYMMDD-HHmmss>.apk
```

Example filenames:
- `marathi-tts-v1.3.2-release-20260303-143022.apk`
- `marathi-tts-v1.3.2-hotfix.1-debug-20260303-150511.apk`

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
2. Decide bump level (major / minor / patch / hotfix).
3. Run deploy: `.\deploy_mobile.ps1 -Release -Bump<Level>`
4. Verify the version printed in the script output.
5. Confirm APK copied to `C:\My_Drive_Backup\builds\marathi_tts\`.
6. Commit the updated `build.gradle.kts` with message: `release: v<VERSION>`
7. Tag the commit: `git tag v<VERSION>` and push.

### Hotfix workflow

```
main ──●──●──●── v1.3.0 ──●── v1.3.1 ──●── ...
                     \
                      └─ hotfix/1.3.0 ── v1.3.0-hotfix.1  (cherry-pick fix)
```

1. Create a branch from the release commit: `git checkout -b hotfix/<base-version>`
2. Apply the minimal fix.
3. Deploy with `-Hotfix`: `.\deploy_mobile.ps1 -Release -Hotfix`
4. Commit + tag: `release: v1.3.0-hotfix.1`
5. Cherry-pick the fix back to `main` branch.

---