# मराठी TTS — Android Mobile App

Kotlin-based Android application that brings the full Marathi TTS feature-set to mobile devices.
Python processing is powered by **[Chaquopy](https://chaquo.com/chaquopy/)** — a Gradle plugin that
bundles a complete Python 3.11 runtime inside the APK.

---

## Features

| Tab | Feature |
|-----|---------|
| 🔊 **TTS** | Convert Marathi text to speech. Multi-engine: Auto / gTTS / System TTS / Sherpa AI. |
| 🕉️ **Stotra** | Browse 15+ stotras, verse-mode TTS with Sanskrit phonetics. |
| 🔤 **Phonetics** | Sanskrit + Marathi phonetic preprocessing (visarga, schwa, anusvara, conjuncts). |
| 🗣️ **G2P** | Grapheme-to-phoneme engine for accurate pronunciation. |
| 😊 **Emotion** | Detect dominant emotion with score breakdown. |
| 📷 **OCR** | Extract Marathi text from camera photos or gallery images (ML Kit + Tesseract). |
| ✏️ **Correction** | AI-powered Marathi text spell/grammar correction. |
| 📄 **PDF** | Extract text from PDF files. |
| 🌐 **Web** | Fetch and clean Marathi text from any URL. |
| 🔄 **Modi** | Convert Modi script to Devanagari. |
| 🎤 **Speech-to-Text** | Record via Android SpeechRecognizer or upload an audio file; language selection: Marathi / Hindi / English / Auto-detect. Result can be sent to TTS. |
| 📖 **Book Reader** | Capture open-book photos with CameraX (CONTINUOUS_PICTURE AF, MAXIMIZE_QUALITY). Interactive perspective-correction crop (4 corner handles). Dual-page spread or single-page mode. ML Kit / Tesseract OCR on de-warped image. Sentence-by-sentence TTS playback with soft-yellow sentence highlight and a persistent foreground notification (Stop button). Append mode to accumulate multi-page text. |
---

## Prerequisites

### Development machine
- **Android Studio Hedgehog (2023.1)** or later
- JDK 17
- Android SDK 34 (API level 34)
- Chaquopy license: free tier available at https://chaquo.com/chaquopy/

### Device / emulator
- Android 8.0 (API 26) or later
- arm64-v8a or x86_64 ABI (Chaquopy requirement)

---

## Build & Install

```bash
# Navigate to the project
cd marathi_tts_mobile

# Debug build
./gradlew assembleDebug

# Install on connected device
./gradlew installDebug

# Release build (requires signing config in app/build.gradle.kts)
./gradlew assembleRelease
```

### Open in Android Studio

1. **File → Open** → select `marathi_tts_mobile/`
2. Let Gradle sync (Chaquopy will download Python 3.11 ~20 MB and pip packages ~50 MB)
3. Build & Run on device or emulator

---

## Python packages (Chaquopy pip)

Defined in `app/build.gradle.kts` under `chaquopy { defaultConfig { pip { ... } } }`:

| Package | Used for |
|---------|---------|
| `gtts` | Text-to-speech audio generation |
| `requests` | Web URL fetching |
| `beautifulsoup4` | HTML parsing / web fetch |
| `Pillow` | Image processing for OCR |
| `pytesseract` | Marathi OCR (requires Tesseract) |
| `PyPDF2` | PDF text extraction |
| `pydub` | Audio speed/pitch post-processing |

> **Note:** Tesseract is a C library. On Android, pytesseract cannot use a system-installed
> Tesseract. For production, replace `pytesseract` with
> [Tess4J](https://github.com/nguyenq/tess4j) or Google ML Kit's text recognition.

---

## Project Structure

```
marathi_tts_mobile/
├── build.gradle.kts                 # Top-level (Chaquopy plugin)
├── settings.gradle.kts
└── app/
    ├── build.gradle.kts             # App module (Chaquopy config, dependencies)
    └── src/main/
        ├── AndroidManifest.xml
        ├── python/                  # Python bridge modules (loaded by Chaquopy)
        │   ├── tts_bridge.py
        │   ├── emotion_bridge.py
        │   ├── ocr_bridge.py
        │   ├── correction_bridge.py
        │   ├── pdf_bridge.py
        │   └── web_bridge.py
        ├── kotlin/com/marathitts/mobile/
        │   ├── MainActivity.kt
        │   ├── service/
        │   │   ├── PythonBridge.kt     # Chaquopy wrapper
        │   │   └── AudioPlayerService.kt
        │   └── ui/
        │       ├── tts/      TtsFragment + TtsViewModel
        │       ├── emotion/  EmotionFragment + EmotionViewModel
        │       ├── ocr/      OcrFragment + OcrViewModel
        │       ├── correction/  CorrectionFragment + CorrectionViewModel
        │       ├── pdf/      PdfFragment + PdfViewModel
        │       ├── web/      WebFetchFragment + WebFetchViewModel
        │       ├── stt/      SttFragment + SttViewModel
        │       ├── stotra/   StotraFragment + StotraViewModel + StotraAdapter
        │       ├── modi/     ModiFragment + ModiViewModel
        │       └── bookreader/
        │           ├── BookReaderFragment.kt     # Main UI: OCR + sentence TTS
        │           ├── BookReaderViewModel.kt    # State mgmt + AudioPlayerService
        │           ├── BookCameraActivity.kt     # CameraX capture + PerspectiveCropView
        │           ├── BookCameraOverlayView.kt   # Alignment guide overlay
        │           ├── BookReaderForegroundService.kt  # Persistent notification
        │           ├── PageEdgeDetector.kt       # Book-spine / page edge detection
        │           └── PerspectiveCropView.kt    # 4-corner drag handles for de-warp
        └── res/
            ├── layout/              # Material 3 XML layouts
            ├── navigation/nav_graph.xml
            ├── menu/bottom_nav_menu.xml
            ├── values/              # strings, colors, themes
            └── font/                # Place NotoSansDevanagari-Regular.ttf here
```

---

## Architecture

```
Fragment  ──observe──▶  ViewModel  ──launch coroutine──▶  PythonBridge.call()
                                                                   │
                                                        Python.getInstance().getModule(...)
                                                                   │
                                                         bridge function executes
                                                                   │
                                                         returns JSONObject
                                                                   │
                        ViewModel  ◀── LiveData.postValue(state) ──┘
```

---

## Devanagari font

Download **[Noto Sans Devanagari](https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari)**
and save the `.ttf` file to:

```
app/src/main/res/font/noto_sans_devanagari.ttf
```

The layouts reference `android:fontFamily="@font/noto_sans_devanagari"` for proper rendering.

---

## Permissions

| Permission | Why |
|-----------|-----|
| `INTERNET` | Web URL fetching |
| `CAMERA` | Book Reader camera capture + (optional) OCR photo |
| `RECORD_AUDIO` | Speech-to-Text microphone recording |
| `READ_MEDIA_IMAGES` | Select gallery images for OCR / Book Reader |
| `READ_EXTERNAL_STORAGE` | Legacy storage access (≤ Android 12) |
| `FOREGROUND_SERVICE` | Book Reader foreground service (persistent notification) |

---

## License
MIT — same as the parent Marathi TTS project.
