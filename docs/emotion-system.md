# Emotion Detection System

## Overview

All three platforms detect emotion in Marathi/Sanskrit text and apply voice
modulation parameters to TTS output.

## Categories

| Emotion | Voice pitch | Voice speed | Volume |
|---------|------------|------------|--------|
| happy | +0.10 | +0.05 | +10% |
| sad | -0.10 | -0.10 | -10% |
| angry | +0.15 | +0.10 | +20% |
| fear | +0.05 | +0.15 | -5% |
| surprise | +0.20 | +0.05 | +10% |
| disgust | -0.05 | -0.05 | 0% |
| love | +0.05 | -0.10 | -5% |
| devotional | -0.05 | -0.15 | -10% |
| peaceful | -0.05 | -0.10 | -5% |
| neutral | 0.0 | 0.0 | 0% |

## Architecture

### Bridge layer

`emotion_bridge.py` in both mobile and desktop:

```python
def analyze_emotion(text: str) -> dict:
    """Returns: emotion, score, dominant, intensity, voice_params, scores, success"""
```

`_normalize_result()` ensures all keys are always present regardless of backend.

### Engine layer

`tts/utils/emotion/emotion_analyzer.py` — keyword + pattern matching for Marathi text.
`tts/constants/emotion_constants.py` — category definitions, keyword lists, voice params.

### Prosody integration

`ProsodyEngine.segment_text(emotion=...)` applies emotion modifiers:
- `devotional` → slower tts_rate (−0.15)
- `happy` → faster tts_rate (+0.05)
- All emotions adjust pitch contour and pause durations

### Emotion Intensity Slider (FEAT-54)

`get_scaled_voice_params(emotion, intensity)` linearly interpolates between
neutral and full emotion parameters based on user-controlled intensity (0.0–1.0).

## Mobile UI

`EmotionFragment` shows detected emotion label, score, and bar chart of all
category scores. Copy/share actions via `OutputActions`.

## Desktop UI

`EmotionController` tab — bar chart visualization with copy button.
