"""
Script Constants
================
Unicode script ranges, Modi-to-Devanagari mappings, and phonetic/IPA maps.

Imports:
    from tts.constants.script_constants import (
        SCRIPT_RANGES, MODI_RANGE, MODI_DEVANAGARI_MAP,
        MODI_TO_DEVANAGARI_MAP, PHONETIC_MAP, MATRA_MAP,
    )
"""
from typing import Dict, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# SCRIPT UNICODE RANGES
# Used by: tts_settings.py, ScriptConverter
# ═══════════════════════════════════════════════════════════════════════════

SCRIPT_RANGES: Dict[str, List[Tuple[int, int]]] = {
    'MODI': [(0x11600, 0x11644), (0x11645, 0x11649)],
    'DEVANAGARI': [(0x0900, 0x097F), (0xA8E0, 0xA8FF)],
}

# ScriptConverter class-level range
MODI_RANGE: Tuple[int, int] = (0x11600, 0x1165F)


# ═══════════════════════════════════════════════════════════════════════════
# MODI TO DEVANAGARI — ScriptConverter class mapping (short form)
# Used by: ScriptConverter.MODI_DEVANAGARI_MAP
# ═══════════════════════════════════════════════════════════════════════════

MODI_DEVANAGARI_MAP: Dict[str, str] = {
    '\U00011600': '\u0905',  # MODI LETTER A -> DEVANAGARI LETTER A
    '\U00011601': '\u0906',  # MODI LETTER AA -> DEVANAGARI LETTER AA
    '\U00011602': '\u0907',  # MODI LETTER I -> DEVANAGARI LETTER I
    '\U00011603': '\u0908',  # MODI LETTER II -> DEVANAGARI LETTER II
    '\U00011604': '\u0909',  # MODI LETTER U -> DEVANAGARI LETTER U
    '\U00011605': '\u090A',  # MODI LETTER UU -> DEVANAGARI LETTER UU
    '\U00011606': '\u090B',  # MODI LETTER VOCALIC R -> DEVANAGARI LETTER VOCALIC R
    '\U00011607': '\u090C',  # MODI LETTER VOCALIC RR -> DEVANAGARI LETTER VOCALIC RR
    '\U00011608': '\u090F',  # MODI LETTER E -> DEVANAGARI LETTER E
    '\U00011609': '\u0910',  # MODI LETTER AI -> DEVANAGARI LETTER AI
    '\U0001160A': '\u0913',  # MODI LETTER O -> DEVANAGARI LETTER O
    '\U0001160B': '\u0914',  # MODI LETTER AU -> DEVANAGARI LETTER AU
    '\U0001160C': '\u0915',  # MODI LETTER KA -> DEVANAGARI LETTER KA
    '\U0001160D': '\u0916',  # MODI LETTER KHA -> DEVANAGARI LETTER KHA
    '\U0001160E': '\u0917',  # MODI LETTER GA -> DEVANAGARI LETTER GA
    '\U0001160F': '\u0918',  # MODI LETTER GHA -> DEVANAGARI LETTER GHA
}


# ═══════════════════════════════════════════════════════════════════════════
# MODI TO DEVANAGARI — Full standalone mapping (module-level)
# Used by: script_converter.modi_to_devanagari() standalone function
# ═══════════════════════════════════════════════════════════════════════════

MODI_TO_DEVANAGARI_MAP: Dict[str, str] = {
    # Vowels
    '\u11600': '\u0905',  # अ
    '\u11601': '\u0906',  # आ
    '\u11602': '\u0907',  # इ
    '\u11603': '\u0908',  # ई
    '\u11604': '\u0909',  # उ
    '\u11605': '\u090A',  # ऊ
    '\u11606': '\u090B',  # ऋ
    '\u11607': '\u0960',  # ॠ
    '\u11608': '\u090C',  # ऌ
    '\u11609': '\u0961',  # ॡ
    '\u1160A': '\u090F',  # ए
    '\u1160B': '\u0910',  # ऐ
    '\u1160C': '\u0913',  # ओ
    '\u1160D': '\u0914',  # औ

    # Consonants
    '\u11610': '\u0915',  # क
    '\u11611': '\u0916',  # ख
    '\u11612': '\u0917',  # ग
    '\u11613': '\u0918',  # घ
    '\u11614': '\u0919',  # ङ
    '\u11615': '\u091A',  # च
    '\u11616': '\u091B',  # छ
    '\u11617': '\u091C',  # ज
    '\u11618': '\u091D',  # झ
    '\u11619': '\u091E',  # ञ
    '\u1161A': '\u091F',  # ट
    '\u1161B': '\u0920',  # ठ
    '\u1161C': '\u0921',  # ड
    '\u1161D': '\u0922',  # ढ
    '\u1161E': '\u0923',  # ण
    '\u1161F': '\u0924',  # त
    '\u11620': '\u0925',  # थ
    '\u11621': '\u0926',  # द
    '\u11622': '\u0927',  # ध
    '\u11623': '\u0928',  # न
    '\u11624': '\u092A',  # प
    '\u11625': '\u092B',  # फ
    '\u11626': '\u092C',  # ब
    '\u11627': '\u092D',  # भ
    '\u11628': '\u092E',  # म
    '\u11629': '\u092F',  # य
    '\u1162A': '\u0930',  # र
    '\u1162B': '\u0932',  # ल
    '\u1162C': '\u0935',  # व
    '\u1162D': '\u0936',  # श
    '\u1162E': '\u0937',  # ष
    '\u1162F': '\u0938',  # स
    '\u11630': '\u0939',  # ह
    '\u11631': '\u0933',  # ळ

    # Matras (vowel signs)
    '\u11633': '\u093E',  # ा
    '\u11634': '\u093F',  # ि
    '\u11635': '\u0940',  # ी
    '\u11636': '\u0941',  # ु
    '\u11637': '\u0942',  # ू
    '\u11638': '\u0943',  # ृ
    '\u11639': '\u0944',  # ॄ
    '\u1163A': '\u0962',  # ॢ
    '\u1163B': '\u0963',  # ॣ
    '\u1163C': '\u0947',  # े
    '\u1163D': '\u0948',  # ै
    '\u1163E': '\u094B',  # ो
    '\u1163F': '\u094C',  # ौ

    # Special signs
    '\u11640': '\u094D',  # ् (virama)
    '\u11641': '\u0902',  # ं (anusvara)
    '\u11642': '\u0903',  # ः (visarga)
    '\u11643': '\u093D',  # ऽ (avagraha)
    '\u11644': '\u0901',  # ँ (candrabindu)

    # Punctuation and digits
    '\u11646': '\u0964',  # । (danda)
    '\u11647': '\u0965',  # ॥ (double danda)
    '\u11650': '\u0966',  # ०
    '\u11651': '\u0967',  # १
    '\u11652': '\u0968',  # २
    '\u11653': '\u0969',  # ३
    '\u11654': '\u096A',  # ४
    '\u11655': '\u096B',  # ५
    '\u11656': '\u096C',  # ६
    '\u11657': '\u096D',  # ७
    '\u11658': '\u096E',  # ८
    '\u11659': '\u096F',  # ९
}


# ═══════════════════════════════════════════════════════════════════════════
# PHONETIC MAP — Devanagari character to Latin/IPA transliteration
# Used by: PhoneticAnalyzer
# ═══════════════════════════════════════════════════════════════════════════

PHONETIC_MAP: Dict[str, str] = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u',
    'ऊ': 'oo', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'क': 'ka', 'ख': 'kha', 'ग': 'ga', 'घ': 'gha', 'ङ': 'na',
    'च': 'cha', 'छ': 'chha', 'ज': 'ja', 'झ': 'jha', 'ञ': 'nya',
    'ट': 'ta', 'ठ': 'tha', 'ड': 'da', 'ढ': 'dha', 'ण': 'Na',
    'त': 'ta', 'थ': 'tha', 'द': 'da', 'ध': 'dha', 'न': 'na',
    'प': 'pa', 'फ': 'pha', 'ब': 'ba', 'भ': 'bha', 'म': 'ma',
    'य': 'ya', 'र': 'ra', 'ल': 'la', 'व': 'va',
    'श': 'sha', 'ष': 'sha', 'स': 'sa', 'ह': 'ha',
    'ळ': 'La', 'क्ष': 'ksha', 'ज्ञ': 'dnya',
}


# ═══════════════════════════════════════════════════════════════════════════
# MATRA MAP — Devanagari vowel signs (matras) to Latin/IPA
# Used by: PhoneticAnalyzer
# ═══════════════════════════════════════════════════════════════════════════

MATRA_MAP: Dict[str, str] = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n',
    'ः': 'h', '्': '',
}
