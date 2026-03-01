# मराठी TTS — Desktop App

JavaFX + Kotlin standalone desktop application for **Marathi Text-to-Speech**, with the same
features as the Django web application.  Communication with the Python processing pipeline happens
via subprocess calls to bundled Python bridge scripts — **no server, no Django required**.

---

## Features

| Feature | Description |
|--------|-------------|
| 🔊 **Text to Speech** | Convert Marathi Devanagari text to audio (MP3). Speed, pitch, volume, emotion, verse mode controls. |
| �️ **Verse / Stotra Mode** | Shloka-aware preprocessing with visarga sandhi, danda→pause, verse numbering removal. |
| 📚 **Stotra Library** | Browse the full stotra catalog: deity-based filter chips, live search by name, view complete stotra text with metadata (meter, language, source), send to TTS tab in verse mode for direct playback. |
| 🔤 **Sanskrit Phonetics** | Visarga sandhi, echoing visarga, halant expansion, conjunct aids (ज्ञ→द्न्य). |
| 🔤 **Marathi Phonetics** | Schwa deletion, anusvara cleanup, visarga word lexicon, English vowel fallback. |
| 🗣️ **G2P Engine** | Grapheme-to-phoneme processing for correct conjunct and anusvara pronunciation. |
| 😊 **Emotion Analysis** | Detect the dominant emotion in a Marathi text with score breakdown chart. |
| 📷 **Image OCR** | Extract Marathi text from JPG/PNG/BMP images using Tesseract. |
| ✏️ **AI Text Correction** | Auto-correct Marathi spelling/grammar using the trained `marathi-correction-model`. |
| 📄 **PDF Extract** | Pull Marathi text from PDF files (PyMuPDF → PyPDF2 → OCR fallback). |
| 🌐 **Web Fetch** | Fetch and clean Marathi text from any URL. |
| 🔄 **Modi / IAST / Brahmi Script** | Convert Modi script, IAST, or Brahmi to Devanagari (and Devanagari → IAST). |
| 🗣️ **Speech-to-Text** | Transcribe audio files (WAV/MP3/M4A/OGG/FLAC) or record from microphone. Language selection: Marathi, Hindi, Sanskrit, English. Displays full transcript + per-segment timestamps. Send result directly to TTS tab. |

---

## Prerequisites

### Java / Kotlin
- JDK 17 or later (`java -version`)
- Gradle 8+ (or use the bundled `gradlew` wrapper)

### Python (for the bridge scripts)
- Python 3.9+ (`python --version` or `python3 --version`)
- All packages listed in `python_bridge/setup_bridge.py`

Run once to install:
```bash
python python_bridge/setup_bridge.py
```

### Tesseract OCR (for image / fallback PDF extraction)
| OS | Command |
|----|---------|
| Ubuntu / Debian | `sudo apt install tesseract-ocr tesseract-ocr-mar` |
| macOS | `brew install tesseract tesseract-lang` |
| Windows | Download installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) and select Marathi language pack |

---

## Build & Run

```bash
# Clone / navigate to this directory
cd marathi_tts_desktop

# Build the project
./gradlew build          # Linux / macOS
gradlew.bat build        # Windows

# Run the application
./gradlew run
# or
gradlew.bat run
```

### Set project root (optional but recommended)

The desktop app has a **"Project root"** field at the top.  Set it to the path of the `marathi_tts`
Django project (e.g. `D:\marathi_tts`).  This lets the bridge scripts import the full TTS engine
for highest quality output.  If left blank, the bridges fall back to gTTS + lightweight utilities.

Alternatively set the environment variable before launching:
```bash
set MARATHI_TTS_PROJECT_ROOT=D:\marathi_tts   # Windows
export MARATHI_TTS_PROJECT_ROOT=/path/to/marathi_tts  # Linux/macOS
```

---

## Project Structure

```
marathi_tts_desktop/
├── build.gradle.kts          # Gradle build (Kotlin DSL)
├── settings.gradle.kts
├── python_bridge/            # Python bridge scripts (bundled into JAR)
│   ├── tts_bridge.py
│   ├── emotion_bridge.py
│   ├── ocr_bridge.py
│   ├── correction_bridge.py
│   ├── pdf_bridge.py
│   ├── web_bridge.py
│   ├── stt_bridge.py          # Whisper STT + microphone recording
│   ├── script_converter_bridge.py  # Modi / IAST / Brahmi ↔ Devanagari
│   └── setup_bridge.py       # One-time dependency installer
└── src/main/
    ├── kotlin/com/marathitts/desktop/
    │   ├── MainApp.kt                    # JavaFX entry point
    │   ├── controller/
    │   │   ├── MainController.kt
    │   │   ├── TtsController.kt
    │   │   ├── EmotionController.kt
    │   │   ├── OcrController.kt
    │   │   ├── CorrectionController.kt
    │   │   ├── PdfController.kt
    │   │   ├── WebFetchController.kt
    │   │   ├── SttController.kt
    │   │   ├── ModiController.kt
    │   │   └── StotraController.kt
    │   ├── service/
    │   │   ├── PythonBridge.kt           # Core subprocess runner
    │   │   └── Services.kt               # TTS/Emotion/OCR/… service wrappers
    │   └── util/
    │       └── AudioPlayerUtil.kt
    └── resources/
        ├── fxml/                         # JavaFX FXML layouts
        └── css/style.css                 # Application-wide stylesheet
```

---

## Python bridge architecture

```
JavaFX UI  ──trigger──▶  *Controller  ──submit task──▶  *Service
                                                             │
                                                    (background thread)
                                                             │
                                                    PythonBridge.run()
                                                             │
                                            ProcessBuilder(python, bridge.py, --args)
                                                             │
                                            bridge script prints JSON to stdout
                                                             │
                                    *Controller  ◀─  parsed Map<String, Any?>
```

---

## Adding a custom Python interpreter

If `python3` / `python` are not in your system PATH, set:

```bash
set PYTHON_PATH=C:\Python311\python.exe   # Windows
export PYTHON_PATH=/usr/local/bin/python3  # Linux/macOS
```

---

## License
MIT — same as the parent Marathi TTS project.
