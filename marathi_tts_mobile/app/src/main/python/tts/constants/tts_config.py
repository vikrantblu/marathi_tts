"""
TTS Configuration Constants
============================
Supported languages, engine defaults, morphological data,
and pronunciation resolution data.

Imports:
    from tts.constants.tts_config import (
        SUPPORTED_LANGUAGES, TTS_DEFAULTS,
        MORPH_SUFFIXES, MORPH_VERB_FORMS,
        PRONUNCIATION_RULES, CONTEXT_MARKERS,
    )
"""
from typing import Dict, Set, List, Any


# ═══════════════════════════════════════════════════════════════════════════
# SUPPORTED LANGUAGES — merged from OptimizedTTS, CachedGTTS
# Used by: tts_engine.py, google_service.py
# ═══════════════════════════════════════════════════════════════════════════

SUPPORTED_LANGUAGES: Dict[str, str] = {
    'mr': 'Marathi',
    'hi': 'Hindi',
    'sa': 'Sanskrit',
    'en': 'English',
}


# ═══════════════════════════════════════════════════════════════════════════
# TTS ENGINE DEFAULTS — from TTSSettings._config
# Used by: tts_settings.py
# ═══════════════════════════════════════════════════════════════════════════

TTS_DEFAULTS: Dict[str, Any] = {
    'DEFAULT_VOICE': 'google',
    'SUPPORTED_VOICES': ['google', 'azure', 'local'],
    'MAX_TEXT_LENGTH': 25000,
    'MIN_TEXT_LENGTH': 1,
    'AUDIO_FORMAT': 'wav',
    'SAMPLE_RATE': 22050,
    'CHANNELS': 1,
    'FRAME_RATE': 24000,
    'CHUNK_SIZE': 1000,
    'RATE_LIMIT': 10,
    'CACHE_TIMEOUT': 3600,
    'FILE_TTL': 3600,
    'CLEANUP_INTERVAL': 300,
    'MAX_FILE_AGE': 86400,
}


# ═══════════════════════════════════════════════════════════════════════════
# MORPHOLOGICAL DATA — common suffixes and verb forms
# Used by: MarathiMorphAnalyzer
# ═══════════════════════════════════════════════════════════════════════════

MORPH_SUFFIXES: Set[str] = {
    'ला', 'ना', 'मध्ये', 'वर', 'खाली', 'मुळे',
    'चा', 'ची', 'चे', 'च्या', 'शी', 'हून', 'तून',
    'पासून', 'कडे', 'कडून', 'सोबत', 'साठी',
}

MORPH_VERB_FORMS: Set[str] = {
    'णे', 'ने', 'णार', 'त', 'ला', 'ली', 'ले',
    'तो', 'ते', 'ती', 'तात', 'तील', 'तीस',
}


# ═══════════════════════════════════════════════════════════════════════════
# PRONUNCIATION RULES — context-dependent word pronunciations
# Used by: PronunciationResolver
# ═══════════════════════════════════════════════════════════════════════════

PRONUNCIATION_RULES: Dict[str, Dict[str, str]] = {
    'पाणी': {'water': 'पाणी', 'money': 'पैणी'},
    'कर': {'tax': 'कर', 'do': 'कर्'},
    'वाट': {'path': 'वाट', 'wait': 'वाट्'},
    'मान': {'respect': 'मान', 'neck': 'मान्'},
    'पाने': {'leaves': 'पाने', 'pages': 'पाणे'},
    'साला': {'year': 'साला', 'brother': 'साळा'},
    'कडा': {'edge': 'कडा', 'strict': 'कड्डा'},
    'चाल': {'walk': 'चाल', 'behavior': 'चाळ'},
    'मारा': {'hit': 'मारा', 'intensity': 'मार्रा'},
    'काळ': {'time': 'काळ', 'black': 'काळा'},
    'पार': {'completely': 'पार', 'platform': 'पार्'},
    'वार': {'day': 'वार', 'hit': 'वार्'},
    'कर्म': {'deed': 'कर्म', 'fate': 'कर्मा'},
    'वेळ': {'time': 'वेळ', 'occasion': 'वेळा'},
    'पान': {'leaf': 'पान', 'page': 'पान्'},
    'कळा': {'art': 'कळा', 'pain': 'कळ'},
    'मळा': {'farm': 'मळा', 'garden': 'मळ्या'},
    'तारा': {'star': 'तारा', 'wire': 'तार'},
    'हार': {'defeat': 'हार', 'necklace': 'हार्'},
    'वार्या': {'wind': 'वार्या', 'time': 'वार्‍या'},
    # Pronunciation rules for special cases
    'यांच्या': {'default': 'yaanchyaa'},
    'च्या': {'default': 'chyaa'},
    'चा': {'default': 'chaa'},
    'ज्या': {'default': 'jyaa'},
    'जा': {'default': 'jaa'},
    'झ्या': {'default': 'jhyaa'},
    'झा': {'default': 'jhaa'},
}


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT MARKERS — words that disambiguate pronunciation
# Used by: PronunciationResolver
# ═══════════════════════════════════════════════════════════════════════════

CONTEXT_MARKERS: Dict[str, List[str]] = {
    'water': ['पिणे', 'प्यायला', 'तहान'],
    'money': ['पैसे', 'रक्कम', 'पगार'],
    'tax': ['टॅक्स', 'महसूल', 'कर'],
    'do': ['करणे', 'कार्य', 'काम'],
    'path': ['रस्ता', 'मार्ग', 'पथ'],
    'wait': ['थांबणे', 'प्रतीक्षा', 'वाट पाहणे'],
    'default': [''],  # Default case that will always match
}


# ═══════════════════════════════════════════════════════════════════════════
# PHONETIC ABBREVIATIONS — shared by PhoneticAnalyzer
# (Main ABBREVIATIONS dict is in text_constants.py — this is for
# the phonetic-specific subset if needed)
# ═══════════════════════════════════════════════════════════════════════════

PHONETIC_ABBREVIATIONS: Dict[str, str] = {
    'प.पू.': 'परमपूज्य',
    'श्री.': 'श्रीमान',
    'डॉ.': 'डॉक्टर',
    'इ.स.': 'इसवी सन',
    'रु.': 'रुपये',
    'प्रा.': 'प्राध्यापक',
    'कु.': 'कुमारी',
    'सौ.': 'सौभाग्यवती',
    'म.': 'महाराष्ट्र',
    'वि.': 'विभाग',
    'दि.': 'दिनांक',
    'क्र.': 'क्रमांक',
}
