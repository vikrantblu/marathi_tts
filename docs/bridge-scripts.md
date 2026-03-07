# Bridge Scripts Specification

## Overview

Bridge scripts provide the Python ↔ Kotlin interface for desktop and mobile platforms.
They are located at:
- **Mobile:** `marathi_tts_mobile/app/src/main/python/`
- **Desktop:** `marathi_tts_desktop/python_bridge/`

## Contract

Every public bridge function MUST return a `dict` with:
- `"success": True/False`
- `"error": str` (when `success=False`)
- All documented output keys

## TTS Bridge (`tts_bridge.py`)

### `generate_tts(text, speed, pitch, volume, language, gender, is_verse, emotion, emotion_intensity, accent)`

Returns: `{"success": True, "audio_path": "/path/to/output.mp3"}`

**Fallback chain (prose):**
1. Custom voice (fingerprint match)
2. edge-tts prosody-segmented
3. edge-tts single call
4. gTTS prosody-segmented
5. gTTS + pydub effects
6. gTTS bare

**Fallback chain (verse):**
1. Custom voice
2. edge-tts verse prosody
3. edge-tts single
4. gTTS verse (slow=True)
5. gTTS bare

### `analyze_prosody(text, language, is_verse, emotion)`

Returns segment list for prosody preview UI.

### `explain_phonetics(word, language)`

Returns stage-by-stage phonetic transformation trace.

### `regenerate_segment(text, speed, pitch, volume, language, gender, is_verse, emotion)`

Lightweight single-segment TTS for per-sentence regeneration.

## Emotion Bridge (`emotion_bridge.py`)

### `analyze_emotion(text)`

Returns: `{"success": True, "emotion": "devotional", "score": 0.85, "dominant": "devotional", "intensity": 0.85, "voice_params": {...}, "scores": {...}}`

Categories: happy, sad, angry, fear, surprise, disgust, love, devotional, peaceful, neutral.

### `get_scaled_voice_params(emotion, intensity)`

Returns interpolated voice parameters based on emotion intensity slider.

## STT Bridge (`stt_bridge.py`)

### `transcribe(audio_path)`

Returns: `{"success": True, "text": "transcribed text"}`

## OCR Bridge (`ocr_bridge.py`)

### `extract_text(image_path)`

Returns: `{"success": True, "text": "extracted text"}`

## PDF Bridge (`pdf_bridge.py`)

### `extract_pdf(pdf_path)`

Returns: `{"success": True, "text": "combined text", "pages": ["page 1 text", ...]}`

## Web Bridge (`web_bridge.py`)

### `fetch_url(url)`

Returns: `{"success": True, "text": "cleaned web page text"}`

## Correction Bridge (`correction_bridge.py`)

### `correct_text(text)`

Returns: `{"success": True, "corrected": "corrected text"}`

## Script Converter Bridge (`script_converter_bridge.py`)

### `convert(text, direction)`

Direction: `"modi_to_devanagari"` or `"devanagari_to_modi"`
Returns: `{"success": True, "converted": "converted text"}`
