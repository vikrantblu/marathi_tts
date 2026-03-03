"""
English → Devanagari Transliterator
=====================================
Converts embedded ASCII English words in Devanagari text into approximate
Marathi phonetic equivalents so the TTS voice reads them naturally without
switching to an English accent.

Two strategies:
  1. Dictionary lookup — common English words with curated Devanagari forms
  2. Character-level fallback — best-effort letter-by-letter mapping

Usage:
    from tts.utils.text.english_transliterator import transliterate_english_words
    result = transliterate_english_words("त्यांना heart attack आला")
    # → "त्यांना हार्ट अटॅक आला"
"""
import re
from typing import Dict

# ═══════════════════════════════════════════════════════════════════════════
# ENGLISH → DEVANAGARI WORD DICTIONARY
# Curated transliterations for common English words found in Marathi text.
# Merged superset from mobile and desktop bridges.
# ═══════════════════════════════════════════════════════════════════════════

ENGLISH_TO_DEVANAGARI: Dict[str, str] = {
    # ── Medical ──────────────────────────────────────────────────────────
    'heart':        'हार्ट',
    'attack':       'अटॅक',
    'blood':        'ब्लड',
    'pressure':     'प्रेशर',
    'sugar':        'शुगर',
    'diabetes':     'डायबिटीस',
    'hospital':     'हॉस्पिटल',
    'doctor':       'डॉक्टर',
    'doctors':      'डॉक्टर्स',
    'medicine':     'मेडिसिन',
    'tablet':       'टॅब्लेट',
    'tablets':      'टॅब्लेट्स',
    'capsule':      'कॅप्सूल',
    'injection':    'इंजेक्शन',
    'injections':   'इंजेक्शन्स',
    'dose':         'डोस',
    'fever':        'फीव्हर',
    'pain':         'पेन',
    'test':         'टेस्ट',
    'report':       'रिपोर्ट',
    'delivery':     'डिलिव्हरी',
    'normal':       'नॉर्मल',
    'abnormal':     'अबनॉर्मल',
    'cesarean':     'सिझेरियन',
    'caesarean':    'सिझेरियन',
    'operation':    'ऑपरेशन',
    'emergency':    'इमर्जन्सी',
    'ambulance':    'अँब्युलन्स',
    'oxygen':       'ऑक्सिजन',
    'icu':          'आयसीयू',
    'ward':         'वॉर्ड',
    'convulsion':   'कन्व्हल्शन',
    'convulsions':  'कन्व्हल्शन्स',
    'infection':    'इन्फेक्शन',
    'virus':        'व्हायरस',
    'vaccine':      'व्हॅक्सिन',
    'protein':      'प्रोटीन',
    'calcium':      'कॅल्शियम',
    'vitamin':      'व्हिटॅमिन',
    'hemoglobin':   'हिमोग्लोबिन',
    'anemia':       'अॅनिमिया',
    'ultrasound':   'अल्ट्रासाउंड',
    'xray':         'एक्सरे',
    'scan':         'स्कॅन',
    'patient':      'पेशंट',
    'misoprost':    'मिसोप्रोस्ट',
    'expand':       'एक्सपँड',
    'expanding':    'एक्सपँडिंग',

    # ── Education ────────────────────────────────────────────────────────
    'school':       'स्कूल',
    'college':      'कॉलेज',
    'class':        'क्लास',
    'exam':         'एक्झाम',
    'result':       'रिझल्ट',
    'pass':         'पास',
    'fail':         'फेल',
    'marks':        'मार्क्स',
    'percent':      'पर्सेंट',
    'fee':          'फी',
    'form':         'फॉर्म',

    # ── Technology ───────────────────────────────────────────────────────
    'mobile':       'मोबाईल',
    'phone':        'फोन',
    'internet':     'इंटरनेट',
    'computer':     'कॉम्प्युटर',
    'software':     'सॉफ्टवेअर',
    'app':          'अॅप',
    'online':       'ऑनलाईन',
    'offline':      'ऑफलाईन',
    'download':     'डाऊनलोड',
    'upload':       'अपलोड',
    'account':      'अकाऊंट',
    'password':     'पासवर्ड',
    'video':        'व्हिडिओ',
    'photo':        'फोटो',
    'camera':       'कॅमेरा',
    'news':         'न्यूज',

    # ── Transport ────────────────────────────────────────────────────────
    'bus':          'बस',
    'train':        'ट्रेन',
    'car':          'कार',
    'bike':         'बाईक',
    'ticket':       'तिकीट',
    'station':      'स्टेशन',
    'platform':     'प्लॅटफॉर्म',

    # ── General ──────────────────────────────────────────────────────────
    'office':       'ऑफिस',
    'file':         'फाईल',
    'copy':         'कॉपी',
    'post':         'पोस्ट',
    'call':         'कॉल',
    'god':          'गॉड',
    'sir':          'सर',
    'madam':        'मॅडम',
}


# ═══════════════════════════════════════════════════════════════════════════
# CHARACTER-LEVEL TRANSLITERATION (fallback for unknown words)
# ═══════════════════════════════════════════════════════════════════════════

# Vowels: standalone form (word-initial or after vowel) vs matra (after consonant)
_VOWEL_STANDALONE = {
    'a': 'अ', 'e': 'ए', 'i': 'इ', 'o': 'ओ', 'u': 'उ',
}
_VOWEL_MATRA = {
    'a': 'ा', 'e': 'े', 'i': 'ि', 'o': 'ो', 'u': 'ु',
}

# Consonant map
_CONSONANT = {
    'b': 'ब', 'c': 'क', 'd': 'ड', 'f': 'फ', 'g': 'ग', 'h': 'ह',
    'j': 'ज', 'k': 'क', 'l': 'ल', 'm': 'म', 'n': 'न', 'p': 'प',
    'q': 'क', 'r': 'र', 's': 'स', 't': 'ट', 'v': 'व', 'w': 'व',
    'x': 'क्स', 'y': 'य', 'z': 'झ',
}

# ASCII English word detection pattern (3+ alphabetic chars)
_ENGLISH_WORD_RE = re.compile(r'[A-Za-z]{3,}')


def transliterate_char_level(word: str) -> str:
    """Letter-by-letter English → Devanagari fallback for unknown words.

    Uses vowel standalone vs matra forms based on context:
    - After a consonant → matra form (ा, े, ि, ो, ु)
    - Word-initial or after another vowel → standalone (अ, ए, इ, ओ, उ)
    - Silent final 'e' after a consonant is skipped.
    """
    w = word.lower()
    out = []
    prev_was_consonant = False

    for i, ch in enumerate(w):
        # Skip silent final 'e' after consonant
        if ch == 'e' and i == len(w) - 1 and prev_was_consonant:
            continue

        if ch in _VOWEL_STANDALONE:
            if prev_was_consonant:
                out.append(_VOWEL_MATRA[ch])
            else:
                out.append(_VOWEL_STANDALONE[ch])
            prev_was_consonant = False
        elif ch in _CONSONANT:
            out.append(_CONSONANT[ch])
            prev_was_consonant = True
        else:
            # Unknown character (digit, punct) — keep as-is
            prev_was_consonant = False

    return ''.join(out) if out else word


def transliterate_english_words(text: str) -> str:
    """Replace ASCII English words (3+ chars) embedded in Devanagari text
    with Devanagari phonetic equivalents.

    Short words (≤2 chars like 'a', 'of', 'in') are left as-is — gTTS
    usually reads them acceptably and they're often OCR artifacts.
    """
    def _replace(match):
        word = match.group(0)
        key = word.lower()
        if key in ENGLISH_TO_DEVANAGARI:
            return ENGLISH_TO_DEVANAGARI[key]
        return transliterate_char_level(word)

    return _ENGLISH_WORD_RE.sub(_replace, text)
