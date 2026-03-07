# TTS Features Documentation

## Overview
This document outlines the feature set for both Normal and Advanced Text-to-Speech (TTS) modes for the Marathi TTS application.

## Normal TTS (Basic Mode)

### Basic Text Processing
- Text normalization with basic pronunciation fixes
- Marathi script validation (Devanagari/Modi support)
- Simple punctuation handling

### Voice Controls
- **Speed Control**: 0.5x to 1.5x playback rate adjustment
- **Pitch Control**: -12 to +12 semitones
- **Volume Control**: -20dB to +20dB range

> **Note (BUG-26):** Current pydub-based pitch/speed uses frame-rate manipulation,
> not proper pitch shifting. This couples pitch and duration. Safe operating ranges
> are **speed ∈ [0.75, 1.25]** and **pitch ∈ [0.79, 1.26]** (~-4 to +4 semitones).
> Values outside this range are clamped automatically. This limitation will be
> superseded by edge-tts SSML `<prosody rate/pitch>` (FEAT-8).

### Audio Output
- WAV format generation
- Built-in audio playback functionality
- Download capabilities with player controls
- **Prosody-segmented generation (FEAT-1/FEAT-8):** Mobile and desktop bridges segment
  prose text at clause/sentence boundaries via ProsodyEngine, generate per-segment TTS
  audio, and stitch with calibrated silence pauses (180-900ms). Works for both gTTS
  (FEAT-1, up to 25 segments) and edge-tts (FEAT-8, up to 15 segments with per-segment
  pitch emphasis). Falls through to single-call generation on failure.

## Advanced TTS Features

### Enhanced Text Analysis
- Emotion detection from text content
- Sentiment analysis capabilities
- Phonetic analysis for accurate pronunciation
- Natural pause detection
- Contextual linguistic analysis

### Voice Modulation
- Emotion-based voice adaptation
- Dynamic intensity control (0-1 range)
- Natural intonation pattern application
- Breathing effect simulation
- Voice quality adjustments:
    - Breathiness control
    - Richness enhancement
    - Clarity optimization

### Advanced Audio Processing
- Professional audio effects application
- EQ adjustments based on detected emotions
- Enhanced audio quality output
- Improved pronunciation handling
- Word-level synchronization
- Natural pause insertion

### User Preferences Management
- User-specific voice profile settings
- Customizable voice parameters
- Preference persistence
- User feedback system integration

### Performance Optimization
- Streaming support for large content
- Caching for emotion analysis
- Rate limiting implementation
- Real-time progress tracking
- Chunk-based processing for efficiency

### Text Input Methods
- Direct text input support
- URL content extraction and processing
- OCR for Marathi text in images (मराठी मजकुराचे छायाचित्र)
- PDF text extraction (मराठी पीडीएफ)
- Text correction features

### User Interface Features
- Word highlighting synchronized with playback
- Emotion visualization display
- Progress indicators
- Real-time emotion analysis visualization
- Interactive playback controls