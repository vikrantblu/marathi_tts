# Mobile App Specification

## Overview

**Package:** `com.marathitts.mobile`
**Min SDK:** 26 **Target SDK:** 34
**Build:** Kotlin + Gradle + Chaquopy (Python 3.11)
**Architecture:** MVVM + Navigation Component

## Navigation (v4.0.0)

3-tab bottom navigation:

| Tab | Fragment | Purpose |
|-----|----------|---------|
| Input | InputFragment | Text entry + source chips + Generate |
| Output | OutputFragment | Auto-TTS, playback, prosody preview |
| Me | MeFragment | Stotra, History, Modi, Settings hub |

### Child destinations
- OCR, PDF, Web Fetch, STT, Book Reader (from Input chips)
- Correction (from Input button)
- Emotion, Settings, History, Modi, Stotra, Test Dashboard (from Me/Output)

### Text flow
- Child → Input: `savedStateHandle.set("extracted_text", text)` + `popBackStack()`
- Cross-screen: navigate with `tts_text` argument

## Share-to-App
| Content | Destination | Argument |
|---------|-------------|----------|
| Image | OcrFragment | `shared_image_uri` |
| URL | WebFetchFragment | `shared_url` |
| Plain text | InputFragment | `tts_text` |

## Room Database (v2)

| Entity | Key fields |
|--------|-----------|
| HistoryEntry | category, inputText, outputText, audioPath |
| StotraFavorite | stotraId, title, deity |
| UrlBookmark | url, title |
| RecentTtsInput | text |
| PhoneticCorrection | word, correctedForm |

## Services

| Service | Purpose |
|---------|---------|
| PythonBridge | Singleton Chaquopy caller |
| TtsEngineManager | Engine switching (native/Python) |
| AudioPlayerService | Foreground playback service |
| StotraRepository | Stotra catalog loader |

## Key Utilities

| Utility | Purpose |
|---------|---------|
| OutputActions | Copy, share, save (text/audio) |
| HistoryLogger | Fire-and-forget Room logger |
| AppPreferences | SharedPreferences wrapper |
| PhoneticCorrectionSync | Room → JSON sync for G2P |
