"""
Content-type classifier and adaptive preprocessor for Marathi TTS.

Detects the content type of input text (news, conversational, technical,
address, verse, or general prose) and applies type-specific preprocessing
to improve TTS pronunciation accuracy.

Usage (from bridge scripts)::

    from tts.utils.text.content_classifier import classify_content, preprocess_by_content_type

    content_type = classify_content(text, is_verse=False)
    text = preprocess_by_content_type(text, content_type)
"""
import re


# ── Content type constants ──────────────────────────────────────────────
VERSE = "verse"
NEWS = "news"
CONVERSATIONAL = "conversational"
TECHNICAL = "technical"
ADDRESS = "address"
GENERAL = "general"


# ═══════════════════════════════════════════════════════════════════════
# PART 1 — CLASSIFICATION HEURISTICS
# ═══════════════════════════════════════════════════════════════════════

_RE_VERSE = re.compile(r'[।॥]')
_RE_NEWS = re.compile(
    r'(?:वार्ताहर|संवाददाता|बातमी|प्रतिनिधी|मुख्यमंत्री|उपमुख्यमंत्री'
    r'|पंतप्रधान|राष्ट्रपती|आयुक्त|पोलीस|न्यायालय|सरकार|विधानसभा'
    r'|लोकसभा|निवडणूक|जाहीर|प्रसिद्धी|वृत्तसंस्था)'
)
_RE_TECHNICAL = re.compile(
    r'(?:kg|km|mg|ml|cm|mm|gm|°C|°F|Hz|kHz|MHz|GHz|MB|GB|TB|KB'
    r'|km/h|m/s|sq\.?\s*(?:m|ft|km)|cu\.?\s*(?:m|ft))\b',
    re.IGNORECASE,
)
_RE_ADDRESS = re.compile(
    r'(?:पिन\s*कोड|पत्ता|रहिवासी|सोसायटी|अपार्टमेंट|फ्लॅट\s*नं'
    r'|मजला|इमारत|गल्ली|रस्ता|चौक|नगर|वाडी|पेठ|गाव|वस्ती)'
    r'|\b\d{6}\b'
)
_RE_CONVERSATIONAL = re.compile(
    r'(?:\bना\b|\bरे\b|\bये\b|\bअरे\b|\bयार\b|\bबरं\b'
    r'|\bहॅलो\b|\bबाय\b|\bओके\b|\bहं\b|\bअच्छा\b|\bचल\b)'
)
_RE_ENGLISH_WORD = re.compile(r'[a-zA-Z]{2,}')


def classify_content(text: str, is_verse: bool = False) -> str:
    """Classify text into a content type for adaptive preprocessing.

    Parameters
    ----------
    text : str
        Input Marathi text.
    is_verse : bool
        If the caller already knows this is verse/stotra text.

    Returns
    -------
    str
        One of: ``'verse'``, ``'news'``, ``'conversational'``,
        ``'technical'``, ``'address'``, ``'general'``.
    """
    if is_verse:
        return VERSE

    verse_count = len(_RE_VERSE.findall(text))
    news_count = len(_RE_NEWS.findall(text))
    tech_count = len(_RE_TECHNICAL.findall(text))
    addr_count = len(_RE_ADDRESS.findall(text))
    conv_count = len(_RE_CONVERSATIONAL.findall(text))
    english_count = len(_RE_ENGLISH_WORD.findall(text))
    word_count = max(len(text.split()), 1)
    english_ratio = english_count / word_count

    # Verse auto-detection (may not have is_verse flag)
    if verse_count >= 2 and verse_count > news_count:
        return VERSE

    # Weighted scoring — higher weight for more distinctive markers
    scores = {
        NEWS: news_count * 2,
        TECHNICAL: tech_count * 3,
        ADDRESS: addr_count * 3,
        CONVERSATIONAL: conv_count * 2 + (3 if english_ratio > 0.25 else 0),
    }

    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best
    return GENERAL


# ═══════════════════════════════════════════════════════════════════════
# PART 2 — TYPE-SPECIFIC PREPROCESSORS
# ═══════════════════════════════════════════════════════════════════════

# ── Technical: unit and measurement expansion ────────────────────────

_UNIT_PRONUNCIATIONS = {
    'km/h': 'किलोमीटर प्रति तास',
    'm/s': 'मीटर प्रति सेकंद',
    'sq km': 'चौरस किलोमीटर',
    'sq m': 'चौरस मीटर',
    'sq ft': 'चौरस फूट',
    'cu m': 'घनमीटर',
    'cu ft': 'घनफूट',
    'kg': 'किलोग्रॅम',
    'km': 'किलोमीटर',
    'cm': 'सेंटीमीटर',
    'mm': 'मिलिमीटर',
    'mg': 'मिलिग्रॅम',
    'ml': 'मिलिलीटर',
    'gm': 'ग्रॅम',
    'kHz': 'किलोहर्ट्झ',
    'MHz': 'मेगाहर्ट्झ',
    'GHz': 'गिगाहर्ट्झ',
    'Hz': 'हर्ट्झ',
    'MB': 'मेगाबाइट',
    'GB': 'गिगाबाइट',
    'TB': 'टेराबाइट',
    'KB': 'किलोबाइट',
    '°C': 'अंश सेल्सियस',
    '°F': 'अंश फॅरनहाइट',
    'm': 'मीटर',
    'g': 'ग्रॅम',
    'L': 'लीटर',
    'l': 'लीटर',
}

# Build regex: longest units first to avoid partial matches
_RE_UNIT = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*(' +
    '|'.join(re.escape(u) for u in sorted(
        _UNIT_PRONUNCIATIONS, key=len, reverse=True
    )) +
    r')(?=\s|[,.)।॥]|$)',
)

# Percentage: ५०% or 50%
_RE_PERCENT = re.compile(r'(\d+(?:[.,]\d+)?)\s*%')


def _preprocess_technical(text: str) -> str:
    """Expand technical units and measurements to spoken Marathi."""
    # Expand units: "5 kg" → "5 किलोग्रॅम"
    def _replace_unit(m):
        num, unit = m.group(1), m.group(2)
        spoken = _UNIT_PRONUNCIATIONS.get(unit, unit)
        return f'{num} {spoken}'

    text = _RE_UNIT.sub(_replace_unit, text)

    # Expand percentage: "50%" → "50 टक्के"
    text = _RE_PERCENT.sub(r'\1 टक्के', text)

    return text


# ── Address: pin codes + structured address patterns ─────────────────

_RE_PINCODE = re.compile(r'\b(\d{6})\b')


def _expand_pincode(m):
    """Read 6-digit pin code as three pairs: 411001 → "41 10 01"."""
    digits = m.group(1)
    return ' '.join(digits[i:i + 2] for i in range(0, 6, 2))


_ADDRESS_ABBREV = [
    (re.compile(r'\bमु\.\s*पो\.\s*'), 'मुक्काम पोस्ट '),
    (re.compile(r'\bता\.\s*जि\.\s*'), 'तालुका जिल्हा '),
    (re.compile(r'\bफ्लॅट\s*नं\.\s*'), 'फ्लॅट नंबर '),
]


def _preprocess_address(text: str) -> str:
    """Expand address abbreviations and pronounce pin codes."""
    for pat, repl in _ADDRESS_ABBREV:
        text = pat.sub(repl, text)
    text = _RE_PINCODE.sub(_expand_pincode, text)
    return text


# ── Conversational: colloquial → standard Marathi ───────────────────

# Progressive-tense contractions: बोलतोय → बोलतो आहे
_CONVERSATIONAL_NORMS = [
    (re.compile(r'\bबोलतोय\b'), 'बोलतो आहे'),
    (re.compile(r'\bकरतोय\b'), 'करतो आहे'),
    (re.compile(r'\bजातोय\b'), 'जातो आहे'),
    (re.compile(r'\bयेतोय\b'), 'येतो आहे'),
    (re.compile(r'\bखातोय\b'), 'खातो आहे'),
    (re.compile(r'\bबसतोय\b'), 'बसतो आहे'),
    (re.compile(r'\bपितोय\b'), 'पितो आहे'),
    (re.compile(r'\bहसतोय\b'), 'हसतो आहे'),
    (re.compile(r'\bरडतोय\b'), 'रडतो आहे'),
    (re.compile(r'\bधावतोय\b'), 'धावतो आहे'),
    (re.compile(r'\bबोलतेय\b'), 'बोलते आहे'),
    (re.compile(r'\bकरतेय\b'), 'करते आहे'),
    (re.compile(r'\bजातेय\b'), 'जाते आहे'),
    (re.compile(r'\bयेतेय\b'), 'येते आहे'),
    # Contracted neuter forms: कसं → कसे, तसं → तसे
    (re.compile(r'\bकसं\b'), 'कसे'),
    (re.compile(r'\bतसं\b'), 'तसे'),
    (re.compile(r'\bकुठं\b'), 'कुठे'),
    (re.compile(r'\bइथं\b'), 'इथे'),
    (re.compile(r'\bतिथं\b'), 'तिथे'),
    (re.compile(r'\bकधीतरी\b'), 'कधी तरी'),
    (re.compile(r'\bकुठेतरी\b'), 'कुठे तरी'),
]


def _preprocess_conversational(text: str) -> str:
    """Normalize conversational Marathi to standard forms for clearer TTS."""
    for pat, repl in _CONVERSATIONAL_NORMS:
        text = pat.sub(repl, text)
    return text


# ── News: formal title and institution expansion ──────────────────

_NEWS_NORMS = [
    (re.compile(r'\bमुं\.'), 'मुंबई'),
    (re.compile(r'\bपुणे\.'), 'पुणे'),
    (re.compile(r'\bनवी दिल्ली\.'), 'नवी दिल्ली'),
    (re.compile(r'\bANI\b'), 'एएनआय'),
    (re.compile(r'\bPTI\b'), 'पीटीआय'),
    (re.compile(r'\bIMD\b'), 'भारतीय हवामान विभाग'),
    (re.compile(r'\bRBI\b'), 'रिझर्व्ह बँक'),
    (re.compile(r'\bGST\b'), 'जीएसटी'),
    (re.compile(r'\bGDP\b'), 'जीडीपी'),
    (re.compile(r'\bCOVID\b', re.IGNORECASE), 'कोविड'),
    (re.compile(r'\bFIR\b'), 'एफआयआर'),
    (re.compile(r'\bIPC\b'), 'आयपीसी'),
    (re.compile(r'\bBNS\b'), 'भारतीय न्याय संहिता'),
    (re.compile(r'\bNDA\b'), 'एनडीए'),
    (re.compile(r'\bUPA\b'), 'यूपीए'),
    (re.compile(r'\bBJP\b'), 'भाजप'),
    (re.compile(r'\bMVA\b'), 'महाविकास आघाडी'),
    # Lakh/crore in mixed script: "5 lakh" or "2 crore"
    (re.compile(r'\blakh\b', re.IGNORECASE), 'लाख'),
    (re.compile(r'\bcrore\b', re.IGNORECASE), 'कोटी'),
]


def _preprocess_news(text: str) -> str:
    """Expand news-specific abbreviations and acronyms."""
    for pat, repl in _NEWS_NORMS:
        text = pat.sub(repl, text)
    return text


# ═══════════════════════════════════════════════════════════════════════
# PART 3 — MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════════

def preprocess_by_content_type(text: str, content_type: str) -> str:
    """Apply type-specific preprocessing to *text*.

    This is called **before** the existing prose/verse preprocessing
    pipeline (abbreviation expansion, grammar engine, phonetics, etc.).
    It only adds type-specific expansions; it does not replace any
    existing pipeline step.

    Parameters
    ----------
    text : str
        Input text (may contain Devanagari, digits, English fragments).
    content_type : str
        As returned by :func:`classify_content`.

    Returns
    -------
    str
        Preprocessed text — possibly with units expanded, colloquialisms
        normalized, acronyms expanded, or pin codes readied for TTS.
    """
    if content_type == TECHNICAL:
        return _preprocess_technical(text)
    if content_type == ADDRESS:
        return _preprocess_address(text)
    if content_type == CONVERSATIONAL:
        return _preprocess_conversational(text)
    if content_type == NEWS:
        return _preprocess_news(text)
    # VERSE and GENERAL: no extra preprocessing needed
    return text
