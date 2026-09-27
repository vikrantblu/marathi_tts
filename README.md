# मराठी TTS — Marathi Text-to-Speech Platform

[![CI - TTS Engine Tests](https://github.com/vikrantblu/marathi_tts/actions/workflows/test.yml/badge.svg)](https://github.com/vikrantblu/marathi_tts/actions/workflows/test.yml)
[![CI - Validate](https://github.com/vikrantblu/marathi_tts/actions/workflows/validate.yml/badge.svg)](https://github.com/vikrantblu/marathi_tts/actions/workflows/validate.yml)
[![CodeQL Analysis](https://github.com/vikrantblu/marathi_tts/actions/workflows/codeql.yml/badge.svg)](https://github.com/vikrantblu/marathi_tts/actions/workflows/codeql.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python: 3.10 | 3.11](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Android: API 26+](https://img.shields.io/badge/Android-API%2026%2B-3DDC84?logo=android&logoColor=white)](https://developer.android.com)

A full-featured, open-source **Marathi Text-to-Speech** ecosystem spanning three platforms:
**Web** (Django), **Desktop** (JavaFX + Kotlin), and **Mobile** (Android + Chaquopy).


---

## Platform Overview

| Platform | Stack | Status |
|----------|-------|--------|
| [**Web**](marathi_tts_web/) | Django 5.2 · DRF · gTTS · Coqui TTS · Whisper | Production |
| [**Desktop**](marathi_tts_desktop/) | JavaFX · Kotlin · Python bridge (subprocess) | Production |
| [**Mobile**](marathi_tts_mobile/) | Android (API 26+) · Kotlin · Chaquopy Python 3.11 | Production |

---

## Feature Matrix

| # | Feature | Web | Desktop | Mobile |
|---|---------|:---:|:-------:|:------:|
| 1 | **Basic TTS** (Marathi text → speech) | ✅ | ✅ | ✅ |
| 2 | **Verse / Stotra mode** (shloka-aware pauses) | ✅ | ✅ | ✅ |
| 3 | **Stotra library** (pre-recorded catalog) | — | ✅ | ✅ (text) |
| 4 | **Sanskrit phonetics** (visarga sandhi, echoing, halant) | ✅ | ✅ | ✅ |
| 5 | **Marathi phonetics** (schwa deletion, anusvara, conjuncts) | ✅ | ✅ | ✅ |
| 6 | **G2P engine** (grapheme-to-phoneme) | ✅ | ✅ | ✅ |
| 7 | **Text correction** (ML-powered) | ✅ | ✅ | ✅ |
| 8 | **Emotion analysis** (8-class) | ✅ | ✅ | ✅ |
| 9 | **Image OCR** (Devanagari) | ✅ | ✅ | ✅ |
| 10 | **PDF extraction** (PyMuPDF → PyPDF2 → OCR) | ✅ | ✅ | ✅ |
| 11 | **Web scraping** (URL → Marathi text) | ✅ | ✅ | ✅ |
| 12 | **Speech-to-Text** (Whisper / Android SpeechRecognizer) | ✅ API | ✅ Tab | ✅ Tab |
| 13 | **Script conversion** (Modi / IAST / Brahmi ↔ Devanagari) | ✅ | ✅ | ✅ |
| 14 | **Multi-engine TTS** (gTTS / System / Sherpa AI) | Partial | Partial | ✅ |
| 15 | **Prosody engine** (natural pauses) | ✅ | Partial | — |
| 16 | **Grammar engine** (90+ spelling fixes, sandhi, vibhakti) | ✅ | ✅ | ✅ |
| 17 | **Number-to-words** (currency, dates, ordinals) | ✅ | ✅ | ✅ |
| 18 | **Morphological analysis** (Morfessor) | ✅ | — | — |
| 19 | **Dictionary lookup** | ✅ | — | — |
| 20 | **Streaming TTS** | ✅ | — | — |
| 21 | **Custom voice model** (VITS / XTTS v2) | ✅ | — | — |
| 22 | **User system / feedback** | ✅ | — | — |
| 23 | **Theme support** (Material3 DayNight) | — | — | ✅ |
| 24 | **Book Reader** (CameraX + perspective crop + sentence TTS) | — | — | ✅ |
| 25 | **Stotra Library** (full text + API) | ✅ API | ✅ Tab | ✅ Tab |

---

## Phonetic Engine

A shared Python module (`marathi_phonetics.py`) provides comprehensive pronunciation rules
for both Sanskrit and Marathi text across all three platforms:

### Sanskrit Rules (`apply_sanskrit_phonetics`)
- Terminal halant expansion (म् → म before space/punct/end)
- Visarga sandhi: before palatals → श, retroflexes → ष, dentals → स, velars/labials → ह
- Echoing terminal visarga: after इ → हि, उ → हु, ए → हे, default → हा
- Conjuncts: ज्ञ → द्न्य, ॠ → री
- OM symbol → ओम

### Marathi Rules (`apply_marathi_phonetics`)
- Visarga word lexicon (दुःख → दुख्ख, निःशब्द → निश्शब्द, etc.)
- Classical trailing anusvara cleanup
- Schwa deletion lexicon (~20 known problem words)
- English vowel normalization (ॲ → ए for System TTS)
- Conjuncts and OM handling

---

## Text Processing Pipeline

```
Raw text
 → MarathiGrammarEngine    — spelling/grammar/word-order fixes
 → MarathiTextNormalizer    — visarga, abbreviations, numbers → words
 → apply_marathi_phonetics  — phonetic rules (schwa, anusvara, conjuncts)
 → MarathiG2PEngine         — grapheme-to-phoneme processing
 → EmotionAnalyzer          — detect emotion → voice parameters
 → TTS Engine               — generate audio segments
 → Audio post-processing    — speed/pitch/volume/EQ
 → Output (MP3/WAV)
```

---

## Quick Start

### Web App
```bash
cd marathi_tts_web
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Desktop App
```powershell
.\start_desktop.ps1          # Windows
# or
cd marathi_tts_desktop && ./gradlew run
```

### Mobile App
```powershell
.\deploy_mobile.ps1          # Build + deploy to connected device
# or
cd marathi_tts_mobile && ./gradlew assembleDebug
```

---

## Security

All Python dependencies are scanned with `pip-audit` and `bandit`.

| Category | Status |
|----------|--------|
| Django | 5.2.11 (all CVEs patched) |
| pip | 26.0.1 |
| setuptools | 82.0.0 |
| SSL verification | `verify=True` on all HTTP requests |
| File permissions | 0o755 (not 0o777) |
| Hash functions | SHA-256 (not MD5) for cache keys |
| HuggingFace | Local model loading (no unpinned downloads in prod) |

---

## Project Structure

```
marathi_tts/
├── marathi_tts_web/         # Django web application
├── marathi_tts_desktop/     # JavaFX + Kotlin desktop app
├── marathi_tts_mobile/      # Android + Chaquopy mobile app
├── deploy_mobile.ps1        # Mobile build & deploy script
├── start_desktop.ps1        # Desktop launch script
├── check_runtime_logs.ps1   # Android logcat viewer
└── README.md                # This file
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, phonetic rules, engine synchronization, and the pull request process.

## Security

Please review our [Security Policy](SECURITY.md) to report any security vulnerabilities.

---

## License

[GNU General Public License v3.0](LICENSE)

---

## Acknowledgements

- [Coqui TTS](https://github.com/coqui-ai/TTS) — open-source TTS framework
- [OpenAI Whisper](https://github.com/openai/whisper) — speech recognition
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — OCR engine
- [AI4Bharat](https://ai4bharat.org/) — Indic NLP resources
- [Chaquopy](https://chaquo.com/chaquopy/) — Python on Android
- [Google ML Kit](https://developers.google.com/ml-kit) — on-device text recognition
