# Marathi TTS — मराठी Text-to-Speech Platform

A full-featured, open-source Marathi Text-to-Speech web application built with Django.  
It converts Marathi/Devanagari text into **human-like speech** with natural pauses, grammar-aware text fixing, emotion-responsive voice modulation, and support for multiple input sources.

---

## Features

| Category | Feature |
|---|---|
| **Natural Prosody** | Segment-based audio with calibrated silence at sentence, clause, and conjunction boundaries — mimics real Marathi breathing patterns |
| **Grammar Engine** | Automatic spelling correction (90+ words), sandhi expansion, vibhakti fixes, gender/number agreement, SOV word-order correction, punctuation restoration |
| **Number-to-Words** | Full Marathi number system — currency (₹/$), dates, times, phone numbers, ordinals, percentages — all spoken as Marathi words |
| **Emotion Detection** | 8-class keyword-based emotion analyzer auto-adjusts pitch, speed, volume, and EQ per utterance |
| **Text Cleanup** | Extracts clean Devanagari from HTML, OCR, URLs; removes junk, normalizes colloquial → formal Marathi |
| **TTS Engine** | Google TTS with optimized language validation, soothing voice profile, 8-band EQ |
| **Input Sources** | Direct text, Image OCR, PDF (text + scanned), Website scraping |
| **NLP** | Text normalization, script conversion (Modi / IAST / Brahmi ↔ Devanagari), pronunciation fixes |
| **Phonetics** | Sanskrit phonetics (visarga sandhi, echoing, halant), Marathi phonetics (schwa deletion, anusvara, conjuncts), G2P engine |
| **Streaming** | Chunked audio streaming with real-time session status |
| **Speech-to-Text** | Whisper-based Marathi transcription — REST API (`POST /api/transcribe-audio/`) + standalone scripts |
| **Custom Voice** | VITS voice model training pipeline for custom Marathi voices |
| **XTTS v2** | Voice cloning from reference audio via Coqui XTTS v2 |
| **User System** | Auth, per-user voice preferences, TTS feedback/ratings |
| **Stotra Library** | REST API for the stotra catalog: list with deity / keyword filters, fetch full text by ID |
| **Admin** | Django admin panel with configurable URL slug |

---

## Tech Stack

- **Backend**: Python 3.10+, Django 5.2, Django REST Framework
- **TTS**: gTTS, Coqui TTS (VITS, XTTS v2)
- **OCR**: Tesseract (Marathi + Sanskrit + English), pdf2image, PyPDF2
- **NLP**: Transformers (mT5, MuRIL, IndicBERT), Morfessor
- **Audio**: pydub, librosa, scipy, pedalboard (EQ, compression, modulation)
- **ML**: PyTorch, TensorFlow (correction model)
- **Web scraping**: BeautifulSoup, Requests
- **Database**: SQLite (development) / PostgreSQL (production)

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) with Marathi language pack:
  ```bash
  # Ubuntu / Debian
  sudo apt-get install tesseract-ocr tesseract-ocr-mar
  
  # macOS
  brew install tesseract
  # Then install Marathi tessdata from https://github.com/tesseract-ocr/tessdata
  ```
- (Optional) CUDA-capable GPU for offline voice synthesis and Whisper STT

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/marathi-tts.git
cd marathi-tts

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env — at minimum set DJANGO_SECRET_KEY

# 5. Apply database migrations
python manage.py migrate

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Run the development server
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Windows + WSL2 Quick Start

If you run Django inside WSL2, use the included startup script:

```powershell
# From PowerShell on Windows:
.\start_server.ps1              # Starts Django + TCP proxy, opens browser
.\start_server.ps1 -Port 9000   # Custom Windows port (default: 9000)
```

This launches Django in WSL2 on port 8888, bridges it to Windows port 9000
via a TCP proxy, and opens your browser automatically.

---

## Configuration

All configuration is done via environment variables (see [`.env.example`](.env.example)).  
Copy `.env.example` to `.env` and adjust values for your environment.

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | *(auto-generated)* | Django secret key — **must be set in production** |
| `DJANGO_DEBUG` | `True` | `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DJANGO_ADMIN_URL` | `admin/` | Admin panel URL prefix — change in production |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8001` | Comma-separated CORS origins |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8001` | Comma-separated CSRF origins |
| `TESSERACT_LANGUAGE` | `mar` | Tesseract language code |
| `INDIC_NLP_RESOURCES` | `<BASE_DIR>/indic_nlp_resources` | Path to Indic NLP resources |
| `INDIC_NLP_LIB` | `<BASE_DIR>/indic_nlp_library` | Path to Indic NLP library |

---

## Project Structure

```
marathi-tts/
├── marathi_tts/          # Django project config (settings, URLs, middleware)
├── tts/                  # Core Django app
│   ├── views/
│   │   ├── tts_views.py        # TTS generation, emotion analysis, streaming
│   │   ├── ai_view.py          # Text correction & formatting API
│   │   ├── ocr_image_view.py   # Image → text extraction
│   │   ├── ocr_pdf_view.py     # PDF → text extraction
│   │   └── website_view.py     # URL → text scraping
│   ├── utils/
│   │   ├── core/               # TTS engine (segment-based), services, settings
│   │   ├── text/               # Grammar engine, normalizer, number-to-words,
│   │   │                       #   text processor, script converter
│   │   ├── audio/              # Prosody engine (pause injection), audio processor
│   │   ├── voice/              # Voice modulator (pitch, speed, EQ, soothing profile)
│   │   ├── emotion/            # 8-class emotion analyzer
│   │   ├── phonetic/           # Phoneme analyzer, pronunciation resolver
│   │   ├── nlp/                # Morphological analyzer
│   │   └── ai/                 # Dictionary, local LLM hook
│   ├── models/                 # UserProfile, TTSFeedback
│   └── templates/              # HTML templates
├── models/               # Trained ML model files (not committed — see .gitignore)
├── data/                 # Training data (not committed — see .gitignore)
├── scripts/              # Data preprocessing and model training scripts
├── mytts/                # Coqui TTS integration (VITS training, XTTS v2)
├── custom-tts-voice-model/ # Custom voice model pipeline
├── speech_to_text.py     # Standalone Whisper STT script
├── start_server.ps1      # Windows+WSL2 one-click server startup
├── tcp_proxy.py          # TCP proxy for WSL2 → Windows browser bridge
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
└── manage.py
```

---

## API Endpoints

All endpoints are prefixed with `/marathi_tts/tts/`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | TTS home page |
| `POST` | `generate-audio/` | Generate audio from Marathi text |
| `GET` | `generate-audio/stream/` | Chunked streaming audio generation |
| `GET` | `stream-status/<session_id>/` | Poll streaming session status |
| `POST` | `fetch-website-content/` | Scrape and extract text from a URL |
| `POST` | `extract-text/` | OCR text from an uploaded image |
| `POST` | `extract-pdf-text/` | Extract text from an uploaded PDF |
| `POST` | `analyze-emotion/` | Detect emotion in Marathi text |
| `POST` | `api/correct-text-para/` | AI-powered Marathi text correction |
| `POST` | `api/format-text/` | Format/normalize Marathi text |
| `POST` | `tts/suggest-correction/` | Submit an incorrect→correct pair for model retraining |
| `POST` | `api/transcribe-audio/` | Transcribe audio file to Marathi text (Whisper) |
| `POST` | `api/convert-script/` | Script conversion: `modi_to_devanagari`, `devanagari_to_iast`, `iast_to_devanagari`, `brahmi_to_devanagari` |
| `GET` | `api/stotras/` | List stotra catalog (optional `?deity=` / `?q=` filters) |
| `GET` | `api/stotras/<id>/` | Retrieve full text of a stotra by catalog index |
| `GET` | `cleanup/` | Remove temporary audio files older than 24 h |

---

## Voice Model Training

To train a custom Marathi voice:

```bash
# 1. Prepare raw audio + transcription data in data/raw/

# 2. Preprocess
python scripts/preprocess_data.py

# 3. Train correction model
python scripts/train_model.py

# 4. Train VITS voice model
python mytts/train_vits.py

# 5. Synthesize test audio
python custom-tts-voice-model/scripts/synthesize.py
```

See [`custom-tts-voice-model/README.md`](custom-tts-voice-model/README.md) and [`tts_features.md`](tts_features.md) for detailed guidance.

---

## Speech-to-Text

Standalone Marathi transcription using Whisper:

```bash
# Small model (fast, default)
python speech_to_text.py path/to/audio.wav

# Large model (slower, more accurate)
python speech_to_text.py path/to/audio.wav --model large-v2

# Save to a specific output file
python speech_to_text.py path/to/audio.wav --model medium --output result.txt
```

GPU is used automatically if available. Falls back to CPU.  
Available models: `tiny`, `base`, `small` (default), `medium`, `large`, `large-v2`, `large-v3`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT License](LICENSE)

---

## Text Processing Pipeline

Input text goes through a multi-stage pipeline before reaching the TTS engine:

```
Raw text
 → MarathiGrammarEngine   — extract, clean, fix spelling/grammar/word-order
 → MarathiTextNormalizer   — visarga, abbreviations, numbers → Marathi words
 → TextProcessor           — pronunciation fixes, conjunct corrections
 → EmotionAnalyzer         — detect emotion → set voice parameters
 → MarathiProsodyEngine    — split into segments with calibrated pauses
 → gTTS per segment        — generate audio for each clause/sentence
 → Silence injection       — stitch segments with natural pause gaps
 → VoiceModulator          — pitch, speed, EQ, soothing profile
 → WAV output
```

### Grammar Engine

The grammar engine (`tts/utils/text/marathi_grammar.py`) fixes:

- **Spelling** — 90+ common misspellings (`बुध्दी` → `बुद्धी`, `आशिर्वाद` → `आशीर्वाद`)
- **Sandhi** — colloquial contractions expanded (`केलंय` → `केलं आहे`, `बोलतोय` → `बोलतो आहे`)
- **Vibhakti** — case marker corrections (`मधे` → `मध्ये`, doubled postpositions removed)
- **Gender agreement** — subject-verb agreement (`ती ... केला` → `ती ... केली`)
- **Word order** — SOV correction (`आहे माझे नाव` → `माझे नाव आहे`)
- **Colloquial → formal** — (`कोन` → `कोण`, `कुठं` → `कुठे`, `नाय` → `नाही`)
- **Punctuation** — auto-inserts dandas `।` and commas at clause boundaries
- **Repetition removal** — `माझे माझे नाव` → `माझे नाव`

### Prosody Engine

The prosody engine (`tts/utils/audio/prosody_engine.py`) splits text at:

- Sentence boundaries (danda / period / question mark) — 550–700ms pause
- Clause boundaries (subordinate clauses) — 350ms pause
- Conjunctions (आणि, परंतु, म्हणून) — 250ms pause
- Commas — 180ms pause
- Paragraph breaks — 900ms pause

---

## Acknowledgements

- [Coqui TTS](https://github.com/coqui-ai/TTS) — open-source TTS framework
- [OpenAI Whisper](https://github.com/openai/whisper) — speech recognition
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — OCR engine
- [AI4Bharat](https://ai4bharat.org/) — Indic NLP resources and pre-trained models
- [IndicNLP Library](https://github.com/anoopkunchukuttan/indic_nlp_library)
