/**
 * API Endpoints - Centralized URL constants for all API calls.
 * 
 * IMPORTANT: Check this file first before adding new API endpoints.
 * All API URLs should be defined here to ensure consistency.
 */

// Base URL prefix for all TTS endpoints
export const BASE_URL = '/marathi_tts/tts';

// Audio generation
export const GENERATE_AUDIO_URL = `${BASE_URL}/generate-audio/`;

// Text correction & formatting
export const CORRECT_TEXT_URL = `${BASE_URL}/api/correct-text-para/`;
export const FORMAT_TEXT_URL = `${BASE_URL}/api/format-text/`;
export const SUGGEST_CORRECTION_URL = `${BASE_URL}/api/suggest-correction/`;

// Emotion analysis
export const ANALYZE_EMOTION_URL = `${BASE_URL}/analyze-emotion/`;

// OCR / image text extraction
export const EXTRACT_TEXT_URL = `${BASE_URL}/extract-text/`;

// Speech-to-Text
export const TRANSCRIBE_AUDIO_URL = `${BASE_URL}/api/transcribe-audio/`;

// Script Converter (Modi / IAST / Brahmi ↔ Devanagari)
export const CONVERT_SCRIPT_URL = `${BASE_URL}/api/convert-script/`;
