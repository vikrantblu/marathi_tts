# Desktop App Specification

## Overview

**Language:** Kotlin + JavaFX
**Build:** Gradle
**Python bridge:** Chaquopy subprocess
**Bridge scripts:** `python_bridge/`

## Tabs

| Tab | Controller | Features |
|-----|-----------|----------|
| TTS | TtsController | Streaming (>250 chars), draft persistence, recent chips |
| Emotion | EmotionController | Bar chart, copy |
| Image OCR | OcrController | Single + batch |
| Correction | CorrectionController | Grammar/spell |
| PDF | PdfController | Page selection |
| Web Fetch | WebFetchController | URL bookmarks |
| STT | SttController | Whisper-based |
| Script Converter | ModiController | Modi ↔ Devanagari |
| Stotra Library | StotraController | Pre-recorded catalog |
| History | HistoryController | In-memory, filterable |
| Settings | SettingsController | Defaults, data, about |

## Key Classes

| Class | Purpose |
|-------|---------|
| AudioPlayerUtil | JavaFX MediaPlayer, `playQueue()` for streaming |
| HistoryManager | Thread-safe in-memory singleton, 200 cap |
| ClipboardUtil | Shared clipboard helper |

## TTS Streaming

Threshold: 250 chars prose
- `splitSentences()` at sentence boundaries
- 3-thread pool + Semaphore(3)
- AtomicInteger progress counter
- Sequential playback via `playQueue()`

## Stotra Assets

`stotras/` directory at project root with `.txt` files and `stotra_catalog.json`.
