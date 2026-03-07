# Architecture Overview — Marathi TTS

## Three-Platform Design

The project runs one TTS engine on three platforms:

```
                    ┌─────────────┐
                    │  Python TTS │
                    │   Engine    │
                    │  (tts/)     │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   Web       │ │  Desktop    │ │  Mobile     │
    │  (Django)   │ │ (JavaFX)    │ │ (Android)   │
    │  Python 3.11│ │ Kotlin+     │ │ Kotlin+     │
    │  SQLite     │ │ Chaquopy    │ │ Chaquopy    │
    └─────────────┘ └─────────────┘ └─────────────┘
```

## TTS Engine Pipeline

```
Input Text
  │
  ├─ Language Detection (Sanskrit / Old Marathi / Modern Marathi)
  │
  ├─ Text Preprocessing
  │   ├─ MarathiTextNormalizer (number→word, abbreviation expansion)
  │   ├─ MarathiGrammarEngine (spelling, sandhi, punctuation)
  │   └─ MorphologicalAnalyzer (stem/suffix boundary detection)
  │
  ├─ Phonetic Processing
  │   ├─ G2P Engine (grapheme-to-phoneme with exception lexicon)
  │   ├─ SandhiEngine (Sanskrit sandhi rules)
  │   ├─ MarathiPhonetics (ज्ञ→द्न्य, visarga gemination, ZWNJ)
  │   └─ SchwaEngine (schwa deletion with 220+ exceptions)
  │
  ├─ Prosody Analysis
  │   ├─ MetreEngine (18 metre catalogue, gaṇa pattern matching)
  │   ├─ ProsodyEngine (segment pauses, pitch contour, emotion)
  │   └─ AbhangaRefrain (refrain detection for Abhanga metre)
  │
  └─ Audio Generation
      ├─ edge-tts (Microsoft neural voices, primary)
      ├─ gTTS (Google TTS, fallback)
      ├─ Custom Voice (Piper VITS ONNX, offline)
      └─ Android native TTS (system fallback)
```

## Bridge Architecture (Mobile + Desktop)

Each platform feature maps to a bridge script:

| Bridge | Input | Output |
|--------|-------|--------|
| `tts_bridge.py` | text + params | audio file path |
| `emotion_bridge.py` | text | emotion label + scores |
| `stt_bridge.py` | audio file | transcript |
| `ocr_bridge.py` | image path | extracted text |
| `pdf_bridge.py` | PDF path | text + per-page list |
| `web_bridge.py` | URL | cleaned text |
| `correction_bridge.py` | text | corrected text |
| `script_converter_bridge.py` | text | Modi ↔ Devanagari |

## Directory Layout

```
marathi_tts/
├── .github/
│   ├── instructions/     # Scoped Copilot instructions
│   ├── mcp/              # MCP server tools
│   ├── prompts/          # Agent prompt files
│   └── workflows/        # CI/CD workflows
├── docs/                 # Structured documentation
├── marathi_tts_web/      # Django web app (canonical TTS source)
├── marathi_tts_desktop/  # JavaFX desktop app
├── marathi_tts_mobile/   # Android mobile app
├── test_all_platforms.py # Cross-platform test suite
├── version.json          # Version source of truth
├── BUGS.txt              # Bug tracker
├── FEATURES.txt          # Feature backlog
└── CHANGELOG.md          # Release history
```
