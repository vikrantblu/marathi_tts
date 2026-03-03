# Changelog — Marathi TTS

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` / `MAJOR.MINOR.PATCH-hotfix.N`.

---

## [Unreleased]
<!-- Changes staged but not yet released go here -->

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
