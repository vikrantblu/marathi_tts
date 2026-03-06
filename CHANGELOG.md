# Changelog — Marathi TTS

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` / `MAJOR.MINOR.PATCH-hotfix.N`.

---

## [Unreleased]
### Added
- Long-audio STT (FEAT-38): `stt_bridge.py` gains `_ensure_wav`, `_audio_duration_sec`,
  `_split_wav_chunks`, `transcribe_long_audio` on both desktop and mobile. Desktop uses
  Whisper (full-file) or chunked project-STT fallback with `transcribe-long` CLI subcommand.
  Mobile Android path splits to 55-second WAV chunks and returns paths to Kotlin for
  sequential playback-loopback transcription. `SttFragment` fully rewritten: URI-to-cache
  copy, chunked loopback (`startChunkedPlaybackTranscription`), continuous recognizer
  restart, history logging. `SttViewModel` adds `nativeChunks`/`nativeAudioPath` fields,
  `clearNativeSttFlag()`, and switches to `transcribe_long_audio`. Desktop `SttService`
  adds `transcribeLong()`; `SttController.onTranscribe` shows chunk count and engine.
  Supported input formats: WAV, MP3, M4A, AAC, OGG, FLAC, MP4, WMA.
- GitHub Actions CI workflow (`.github/workflows/test.yml`) — runs
  `test_all_platforms.py` automatically on every push/PR to main/master/develop
  using `ubuntu-latest` Python 3.11; only `Morfessor` needed as CI dep.
- `.github/ci-requirements.txt` — slim dependency list for CI (no torch/TF/pydub).
- `.github/SETUP_GITHUB.md` — step-by-step guide to push repo to GitHub, enable
  Copilot coding agent, and use `gh copilot` CLI.
- `test_all_platforms.py` now uses `_ROOT = os.path.dirname(os.path.abspath(__file__))`
  for cross-platform path resolution; works on Windows dev machine and Linux CI runner.

---

## [1.0.0] — 2026-03 (initial release)
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
