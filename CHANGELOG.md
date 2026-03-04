# Changelog — Marathi TTS

All notable changes to this project are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` / `MAJOR.MINOR.PATCH-hotfix.N`.

---

## [Unreleased]
<!-- Changes staged but not yet released go here -->
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
