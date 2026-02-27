# मराठी TTS — Android Mobile App

Kotlin-based Android application that brings the full Marathi TTS feature-set to mobile devices.
Python processing is powered by **[Chaquopy](https://chaquo.com/chaquopy/)** — a Gradle plugin that
bundles a complete Python 3.11 runtime inside the APK.

---

## Features

| Tab | Feature |
|-----|---------|
| 🔊 **TTS** | Convert Marathi text to speech. Control speed, pitch, volume, emotion, verse mode. |
| 😊 **Emotion** | Detect dominant emotion with score breakdown. |
| 📷 **OCR** | Extract Marathi text from camera photos or gallery images. |
| ✏️ **Correction** | AI-powered Marathi text spell/grammar correction. |
| 📄 **PDF** | Extract text from PDF files. |
| 🌐 **Web** | Fetch and clean Marathi text from any URL. |

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
        │   │   ├── PythonBridge.kt   # Chaquopy wrapper
        │   │   └── AudioPlayerService.kt
        │   └── ui/
        │       ├── tts/   TtsFragment + TtsViewModel
        │       ├── emotion/   EmotionFragment + EmotionViewModel
        │       ├── ocr/   OcrFragment + OcrViewModel
        │       ├── correction/   CorrectionFragment + CorrectionViewModel
        │       ├── pdf/   PdfFragment + PdfViewModel
        │       └── web/   WebFetchFragment + WebFetchViewModel
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
| `CAMERA` | (optional) Take a photo for OCR |
| `READ_MEDIA_IMAGES` | Select gallery images for OCR |
| `READ_EXTERNAL_STORAGE` | Legacy storage access (≤ Android 12) |

---

## License
MIT — same as the parent Marathi TTS project.
