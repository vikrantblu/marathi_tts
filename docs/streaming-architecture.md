# TTS Streaming Architecture

## Overview

Both mobile and desktop platforms split long prose text into sentence-level
chunks and generate TTS audio in parallel, enabling progressive playback.

## Trigger

Text is routed to the streaming path when **all** conditions are met:
- Language is Marathi (not English/Sanskrit)
- Text length > **250 characters** (`STREAMING_THRESHOLD`)
- Not verse mode (verse has its own segmentation)

## Sentence Splitting

`splitSentences()` breaks text at:
- Devanagari danda `।` and double danda `॥`
- Punctuation: `?`, `!`, `.`, `;`
- Minimum fragment length: **20 characters** (short fragments merge with next)

## Concurrency

| Parameter | Mobile | Desktop |
|-----------|--------|---------|
| Max parallel calls | 3 (Semaphore) | 3 (Semaphore + FixedThreadPool) |
| Dispatcher | `Dispatchers.IO` | `tts-stream` 3-thread pool |
| Progress tracking | `AtomicInteger` counter | `AtomicInteger` counter |
| Status message | `"Streaming: N of M ✓"` | `"Streaming: N of M ✓"` |

## Fallback Chain (per chunk)

Each chunk tries the full TTS engine fallback:

**Mobile (prose):**
1. Custom voice engine (segment library / ONNX)
2. Network check
3. edge-tts prosody-segmented (`_generate_edge_prosody`)
4. edge-tts single call
5. gTTS prosody-segmented (`_generate_prosody_audio`)
6. gTTS + pydub effects
7. gTTS bare

**Desktop (prose):**
1. Custom voice engine
2. Stage 0: stotra library (pre-recorded)
3. Stage 1: TTSEngine (web engine)
4. edge-tts prosody-segmented
5. edge-tts single call
6. gTTS prosody-segmented
7. gTTS + pydub effects
8. gTTS bare

## Playback

### Mobile
`AudioPlayerService.playQueueAsync(List<String>)` — foreground service chains
audio files sequentially. Callbacks: `onChunkStart`, `onAllComplete`, `onError`.

### Desktop
`AudioPlayerUtil.playQueue(paths, onAllFinished)` — recursive `playQueueInternal()`
using JavaFX `MediaPlayer.setOnEndOfMedia` to chain files. Live speed/volume
control available during playback.

## Cancellation

- **Mobile:** `currentJob: Job?` in ViewModel — `cancelGeneration()` cancels
  the coroutine. UI toggles Generate → Cancel button during `isLoading`.
- **Desktop:** `streamingPool.shutdownNow()` + new pool on cancel.

## Save / Export

- **Mobile:** Save button writes generated audio to Downloads via `MediaStore`.
- **Desktop:** `onSaveAudio()` concatenates chunk MP3 files via byte-level
  concatenation (MP3 frames are independently decodable).
