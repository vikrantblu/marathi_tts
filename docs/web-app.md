# Web App Specification

## Overview

**Framework:** Django 4.x
**Python:** 3.11
**Database:** SQLite (`db.sqlite3`)
**Venv:** `marathi_tts_web/.venv`

## Start

```powershell
cd marathi_tts_web
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Or `.\start_server.ps1` from the web directory.

## Django Apps

| App / Path | Purpose |
|-----------|---------|
| `tts/` | Core TTS engine (canonical source for all platforms) |
| `marathi_tts/` | Django project settings, URLs, middleware |
| `utils/` | Shared web utilities |
| `models/` | ML correction models |
| `static/`, `staticfiles/` | Frontend assets |
| `media/tts/` | Generated audio output |
| `data/stotras/` | Stotra text source files |

## TTS Engine (Canonical Source)

The `tts/` package is the canonical source. Desktop and mobile platforms
mirror this directory under their respective bridge paths.

```
tts/
├── constants/          # audio_constants, g2p_constants, tts_config
├── utils/
│   ├── audio/          # prosody_engine.py
│   ├── core/           # tts_engine.py
│   ├── emotion/        # emotion_analyzer.py
│   ├── phonetic/       # marathi_phonetics, sandhi_engine, metre_engine, g2p_engine
│   ├── text/           # text_normalizer, text_processor, marathi_grammar, morphological_analyzer
│   └── voice/          # voice_modulator.py (web only)
└── morph/
    └── morfessor/      # mr.model (statistical morphology)
```

## Docker

```bash
docker compose up -d    # Uses Dockerfile + docker-compose.yml at repo root
```
