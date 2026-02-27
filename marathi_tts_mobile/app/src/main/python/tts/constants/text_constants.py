"""
Text Processing Constants
=========================
Abbreviations, special character replacements, and pronunciation fix
patterns used across multiple text-processing modules.

Imports:
    from tts.constants.text_constants import (
        ABBREVIATIONS, SPECIAL_CHARS, PRONUNCIATION_FIXES,
        MARATHI_CHAR_REPLACEMENTS, HINDI_NUKTA_REPLACEMENTS,
        CONJUNCT_FIXES, VISARGA_WORDS
    )
"""
from typing import Dict, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# ABBREVIATIONS — Maps short forms to full Marathi expansions
# Used by: TextProcessor, clean_text(), PhoneticAnalyzer, MarathiTextNormalizer
# ═══════════════════════════════════════════════════════════════════════════

ABBREVIATIONS: Dict[str, str] = {
    # Honorifics & titles
    'प.पू.': 'परमपूज्य',
    'डॉ.': 'डॉक्टर',
    'श्री.': 'श्री',
    'श्रीमती': 'श्रीमती',
    'सौ.': 'सौभाग्यवती',
    'प्रा.': 'प्राध्यापक',
    'कु.': 'कुमारी',
    'पं.': 'पंडित',

    # Government & institutions
    'उ.म.': 'उत्तर महाराष्ट्र',
    'का.स.': 'कार्यकारी सदस्य',
    'म.स.': 'महाराष्ट्र सरकार',
    'वि.स.': 'विधान सभा',
    'वि.प.': 'विधान परिषद',
    'रा.स.': 'राज्य सभा',
    'अ.भा.': 'अखिल भारतीय',
    'म.टा.': 'महाराष्ट्र टाईम्स',
    'वि.वि.': 'विद्यापीठ',

    # Time & dates
    'इ.स.': 'इसवी सन',
    'इ.स.पू.': 'इसवी सन पूर्वी',
    'स.का.': 'सकाळी',
    'स.': 'सकाळी',
    'दु.': 'दुपारी',

    # Units & references
    'रु.': 'रुपये',
    'पा.क्र.': 'पान क्रमांक',
    'पृ.क्र.': 'पृष्ठ क्रमांक',
    'क्र.': 'क्रमांक',
    'उदा.': 'उदाहरण',

    # Publishing & organization
    'आ.': 'आवृत्ती',
    'सं.': 'संपादक',
    'लि.': 'लिमिटेड',
    'नि.': 'निर्माता',
    'अ.': 'अध्याय',
    'मु.': 'मुख्य',
    'वि.': 'विभाग',
    'इ.': 'इत्यादी',

    # Additional honorifics
    'वे.': 'वेदमूर्ती',
    'प.': 'पूज्य',

    # Geographic
    'जि.': 'जिल्हा',
    'ता.': 'तालुका',
    'गा.': 'गाव',
    'म.': 'महाराष्ट्र',
    'दि.': 'दिनांक',

    # Honorific titles (normalizer)
    'प. पू.': 'परमपूज्य',
    'वै.': 'वैकुंठवासी',
    'पू.': 'पूज्य',

    # English-derived abbreviations
    'एल.सी.पी.एस.': 'एल सी पी एस',
    'एल. सी.पी. एस.': 'एल सी पी एस',
    'एल. ': 'एल',
    'बी. जे.': 'बी जे',
}


# ═══════════════════════════════════════════════════════════════════════════
# SPECIAL CHARACTER REPLACEMENTS
# Used by: TextProcessor, clean_text(), MarathiTextNormalizer
# ═══════════════════════════════════════════════════════════════════════════

SPECIAL_CHARS: Dict[str, str] = {
    # Sacred symbols
    'ॐ': 'ओम्',

    # Typographic normalization
    '॥': '।',
    '–': '-',
    '\u201c': '"',   # left double quote
    '\u201d': '"',   # right double quote
    '\u2018': "'",   # left single quote
    '\u2019': "'",   # right single quote

    # Symbols
    '&': 'आणि',
    '@': 'अॅट',
    '॰': '',         # abbreviation dot — remove
}


# ═══════════════════════════════════════════════════════════════════════════
# VISARGA WORD REPLACEMENTS — specific words before generic visarga rule
# Used by: clean_text(), MarathiTextNormalizer
# ═══════════════════════════════════════════════════════════════════════════

VISARGA_WORDS: Dict[str, str] = {
    'स्वतः': 'स्वतह',
    'स्वत:': 'स्वतह',
    'यः': 'याहा',
    'नमः': 'नमहा',
    'रामः': 'रामहा',
    'कृष्णः': 'कृष्णहा',
    'दुःख': 'दुख्ख',
    'मनःपूर्वक': 'मनःपूर्वक',
}

# Generic visarga & conjunct fixes (applied AFTER specific words above)
VISARGA_GENERIC: Dict[str, str] = {
    'ऱ्य': 'र्य',
    'ः': 'हा',       # generic visarga → 'ha' sound (must be last)
}


# ═══════════════════════════════════════════════════════════════════════════
# MARATHI CHARACTER REPLACEMENTS — used in _process_marathi()
# ═══════════════════════════════════════════════════════════════════════════

MARATHI_CHAR_REPLACEMENTS: Dict[str, str] = {
    'ॅ': 'अॅ',
    'ऎ': 'ए',
    'ऒ': 'ओ',
    '॰': '.',
    '–': '-',
}


# ═══════════════════════════════════════════════════════════════════════════
# CONJUNCT PRONUNCIATION FIXES — used in _process_marathi()
# ═══════════════════════════════════════════════════════════════════════════

CONJUNCT_FIXES: Dict[str, str] = {
    'ध्द': 'द्ध',
    'द्ध्य': 'द्ध्य',
    'ष्ट': 'ष्ट',
    'न्न': 'न्न',
    'त्त': 'त्त',
    'त्र': 'त्र',
}

# Direct word replacements for -या patterns
RAYA_DIRECT_REPLACEMENTS: Dict[str, str] = {
    'भासणा-या': 'भासणाऱ्या',
    'दिसणा-या': 'दिसणाऱ्या',
    'करणा-या': 'करणाऱ्या',
    'असणा-या': 'असणाऱ्या',
}


# ═══════════════════════════════════════════════════════════════════════════
# HINDI NUKTA REPLACEMENTS — used in _process_hindi()
# ═══════════════════════════════════════════════════════════════════════════

HINDI_NUKTA_REPLACEMENTS: Dict[str, str] = {
    'क़': 'क',
    'ख़': 'ख',
    'ग़': 'ग',
    'ज़': 'ज',
    'ड़': 'ड',
    'ढ़': 'ढ',
    'फ़': 'फ',
}


# ═══════════════════════════════════════════════════════════════════════════
# PRONUNCIATION FIXES — regex pattern → replacement
# Used by: TextProcessor._fix_pronunciation()
# ═══════════════════════════════════════════════════════════════════════════

PRONUNCIATION_FIXES: Dict[str, str] = {
    # Nasalized ending fixes
    r'\bश्रीचरणीं\b': 'श्रीचरणी',
    r'\bस्मरणीं\b': 'स्मरणी',
    r'\bमनीं\b': 'मनी',
    r'\bध्यानीं\b': 'ध्यानी',
    r'\bकानीं\b': 'कानी',
    r'\bहातीं\b': 'हाती',
    r'\bपायीं\b': 'पायी',
    r'\bकीर्तनीं\b': 'कीर्तनी',
    r'\bशरणीं\b': 'शरणी',

    # Conjunct mispronunciations
    r'\bडोळ्यांत\b': 'डोळ्यात',
    r'\bअंतःकरण\b': 'अंतकरण',
    r'\bबुध्दी\b': 'बुद्धी',
    r'\bशुध्द\b': 'शुद्ध',
    r'\bवृध्द\b': 'वृद्ध',

    # Colloquial contractions
    r'वाटतंय\b': 'वाटतय',
    r'तंय\b': 'तय',
    r'आजारी\b': 'आजारी',

    # Duhkha-specific fix (kept for backward compat; G2P handles generically)
    r'दुःख([ीेाु])': r'दुख\1',

    # Nasalization fixes — REMOVED blanket anusvara stripping on णीं.
    # The G2P exception lexicon handles specific words (पदरीं→पदरी etc.)
    # Blanket rules corrupted verse/literary words like चरणीं, श्रीचरणीं.

    # Common pronunciation shifts
    # NOTE: 'मध्ये' is standard Marathi postposition — do NOT simplify.
    # gTTS pronounces 'मध्ये' correctly as 'madhye'.
    # r'मध्ये\b': 'मधे',  # REMOVED — was corrupting standard text
    r'मधील\b': 'मधल',
    r'(र्\u200dय)\b': 'रय',
    r'(त्\u200dय)\b': 'त्य',

    # Pronoun preservation — keep conjuncts intact
    r'त्या(वर|मध्ये|साठी)': r'त्या\1',
    r'त्य(ा|ां|ाने|ास|ाला|ामध्ये|ावर|ामुळे|ासाठी)': r'त्य\1',
    r'([ाेोिीुूैौ])तंय\b': r'\1तय',

    # NOTE: Conjunct+य, anusvara, and visarga rules have been moved to
    # the G2P engine (tts.utils.phonetic.g2p_engine) for context-aware
    # processing. Do NOT add conjunct-stripping patterns here.
}


# ═══════════════════════════════════════════════════════════════════════════
# MARATHI SUFFIX LIST — used by multiple -या pattern fixes
# ═══════════════════════════════════════════════════════════════════════════

MARATHI_SUFFIXES = (
    'ं|ना|च्या|ची|चे|ला|त|स|शी|हून|कडे|साठी|नी|पैकी|ंना|ंनी|ंच्या'
    '|नीच|ंनाच|ने|मध्ये|बरोबर|वर|तून|मुळे|पर्यंत|विना|पासून|द्वारे'
    '|सह|वाचून|समोर|मागे|खाली|वरून|खालून|बाहेर|आत|पलीकडे|सोबत'
    '|विषयी|मार्फत|पाशी'
)

# All Marathi consonant characters (used in regex character classes)
ALL_CONSONANTS = 'कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळक्षज्ञ'
