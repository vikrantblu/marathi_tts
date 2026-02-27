"""
Sanskrit & Marathi Phonetic Preprocessing Engine
=================================================

Rewrites Devanagari text to improve pronunciation quality when read by
TTS engines (gTTS, Android System TTS, etc.) that don't natively
implement the full phonological rules of these languages.

Sanskrit rules (for stotra/verse mode):
  - Terminal halant expansion (म् → म at word boundary)
  - Visarga context-sensitive sandhi (ः → श/ष/स/ह depending on next consonant)
  - Echoing terminal visarga (ः copies preceding vowel colour: -iḥ → -ihi)
  - Upadhmaniya / Jihvamuliya (ः before प/क → sharp breath)
  - Conjunct pronunciation aids (ज्ञ → द्न्य)
  - OM symbol expansion

Marathi rules (for conversational/modern text):
  - Schwa deletion awareness (अकार लोप) — documented, lightly applied
  - Visarga simplification in Marathi words (दुःख → दुख्ख)
  - Conjunct pronunciation (ज्ञ → द्न्य)
  - Classical trailing anusvara cleanup (नाहीं → नाही)
  - English loan-word vowels (ॲ/ॅ fallback for engines that lack them)
  - Common mispronunciation patterns
  - Retroflex ळ preservation documentation

Affricate dual-nature (च/ज palatal vs dental) is documented but
cannot be fixed via text rewriting — it depends on the TTS model's
phoneme inventory.

Usage::

    from tts.utils.phonetic.marathi_phonetics import (
        apply_sanskrit_phonetics,
        apply_marathi_phonetics,
    )

    # For stotra / verse / Sanskrit text:
    text = apply_sanskrit_phonetics(text)

    # For general Marathi text:
    text = apply_marathi_phonetics(text)
"""

import re
import unicodedata
import logging

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Unicode Constants
# ═══════════════════════════════════════════════════════════════════════════

HALANT = '\u094D'        # ्  (virama)
ANUSVARA = '\u0902'      # ं
VISARGA = '\u0903'       # ः
CHANDRABINDU = '\u0901'  # ँ
NUKTA = '\u093C'         # ़

_CON_START = '\u0915'    # क
_CON_END   = '\u0939'    # ह


def _is_consonant(ch: str) -> bool:
    """True for Devanagari consonants (क-ह)."""
    return _CON_START <= ch <= _CON_END


def _is_matra(ch: str) -> bool:
    """True for dependent vowel signs (ा-ौ)."""
    return '\u093E' <= ch <= '\u094C'


def _is_vowel(ch: str) -> bool:
    """True for independent vowel letters (अ-औ, ॠ, ऌ)."""
    return '\u0904' <= ch <= '\u0914' or ch in ('\u0960', '\u0961')


def _is_devanagari(ch: str) -> bool:
    """True for any Devanagari codepoint."""
    return '\u0900' <= ch <= '\u097F'


# ═══════════════════════════════════════════════════════════════════════════
# PART 1 – SANSKRIT PHONETIC RULES
# ═══════════════════════════════════════════════════════════════════════════

def apply_sanskrit_phonetics(text: str) -> str:
    """Apply strict Sanskrit pronunciation rules to Devanagari text.

    Designed to be called AFTER structural preprocessing (dandas→punctuation,
    verse numbers stripped etc.) and BEFORE handing to the TTS engine.

    Implements rules from Pāṇinian phonology:
      1. Terminal halant expansion
      2. Visarga sandhi (context-dependent)
      3. Echoing terminal visarga
      4. Conjunct pronunciation aids
      5. OM symbol
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # Remove ZWJ / ZWNJ that confuse tokenizers
    text = text.replace('\u200D', '').replace('\u200C', '')

    # ── 1. Terminal Halant Expansion ──────────────────────────────────
    # Sanskrit words ending in halant make the final consonant inaudible
    # for gTTS.  Remove the halant so gTTS adds implicit schwa.
    #   म् → म,  न् → न,  त् → त   (before space/punct/end)
    text = re.sub(HALANT + r'(?=[\s.,;!?\n]|$)', '', text)

    # ── 2. Visarga (ः) Sandhi — before consonants ────────────────────
    # Before palatal consonants (च,छ,ज,झ,श) → श (palatal sibilant)
    text = re.sub(r'ः(?=[चछजझश])', 'श', text)
    # Before retroflex consonants (ट,ठ,ड,ढ,ष) → ष (retroflex sibilant)
    text = re.sub(r'ः(?=[टठडढष])', 'ष', text)
    # Before dental consonants (त,थ,द,ध,स,न) → स (dental sibilant)
    text = re.sub(r'ः(?=[तथदधसन])', 'स', text)
    # Before velar consonants (क,ख) → jihvamuliya (sharp breath, approx ह)
    text = re.sub(r'ः(?=[कख])', 'ह', text)
    # Before labial consonants (प,फ) → upadhmaniya (sharp breath, approx ह)
    text = re.sub(r'ः(?=[पफ])', 'ह', text)

    # ── 3. Echoing Terminal Visarga ──────────────────────────────────
    # At end of line/verse, visarga echoes the preceding short vowel:
    #   -aḥ → -aha,  -iḥ → -ihi,  -uḥ → -uhu
    # After इ-class vowel (ि,ी) → हि
    text = re.sub(r'([\u093F\u0940])ः(?=[\s.,\n]|$)', r'\1हि', text)
    # After उ-class vowel (ु,ू) → हु
    text = re.sub(r'([\u0941\u0942])ः(?=[\s.,\n]|$)', r'\1हु', text)
    # After ए-matra (े) → हे
    text = re.sub(r'(\u0947)ः(?=[\s.,\n]|$)', r'\1हे', text)
    # After ऐ-matra (ै) → हि (ai echoes i)
    text = re.sub(r'(\u0948)ः(?=[\s.,\n]|$)', r'\1हि', text)
    # After ओ-matra (ो) → हो
    text = re.sub(r'(\u094B)ः(?=[\s.,\n]|$)', r'\1हो', text)
    # After औ-matra (ौ) → हु (au echoes u)
    text = re.sub(r'(\u094C)ः(?=[\s.,\n]|$)', r'\1हु', text)
    # Default (after अ / bare consonant) → हा
    text = re.sub(r'ः(?=[\s.,\n]|$)', 'हा', text)

    # ── 4. Remaining Mid-Word Visarga → ह ────────────────────────────
    text = text.replace('ः', 'ह')

    # ── 5. Conjunct Pronunciation Aids ────────────────────────────────
    # ज्ञ → द्न्य  (Marathi/Maharashtra standard, not Hindi "gya")
    text = text.replace('ज्ञ', 'द्न्य')
    # Long ॠ (rare) → री
    text = text.replace('ॠ', 'री')

    # ── 6. Special Symbols ────────────────────────────────────────────
    text = text.replace('ॐ', 'ओम')

    return text


# ═══════════════════════════════════════════════════════════════════════════
# PART 2 – MARATHI PHONETIC RULES
# ═══════════════════════════════════════════════════════════════════════════

# ── Affricate Dual Nature (Documentary) ──────────────────────────────────
# In Marathi, च/ज/झ have TWO pronunciations:
#
#   PALATAL (English-like ch/j/jh):
#     Before front vowels (इ,ई,ए,ऐ) and semi-vowel य:
#       चिमणी = chimṇī,  जीवन = jīvan,  झील = jhīl
#
#   DENTAL (like ts/dz/dzh):
#     Before back vowels (अ,आ,उ,ऊ,ओ,औ):
#       चमचा = tsamtsā,  जमीन = dzamīn,  झाड = dzhāḍ
#
#   Exception: Sanskrit loan-words (tatsama) retain palatal pronunciation
#   regardless of vowel:  जल = jal (NOT dzal),  चक्र = chakra (NOT tsakra)
#
# This distinction CANNOT be enforced via text rewriting.  It depends on
# the TTS model's phoneme inventory.  gTTS lang=mr handles the common
# cases; Android System TTS often does not.
#
# ── Retroflex ळ (Lla) ────────────────────────────────────────────────────
# ळ (\u0933) is a retroflex lateral flap unique to Marathi.  It MUST NOT
# be merged with ल (dental lateral).  No text rewrite needed — but the
# character must be preserved intact in all text processing.
#   मंगळ  (Mars)  = Man-gaḷ
#   वेळ   (Time)  = Veḷ
#   काळ   (Era)   = Kāḷ

# ── Visarga in common Marathi words ──────────────────────────────────────
_MARATHI_VISARGA_WORDS = {
    'दुःख':       'दुख्ख',       # duḥkha → dukh-kha (gemination)
    'दुःखी':      'दुख्खी',
    'दुःखद':      'दुख्खद',
    'निःशब्द':    'निश्शब्द',    # nihśabda → niśśabda
    'निःस्वार्थ': 'निस्स्वार्थ',
    'निःसंशय':    'निस्संशय',
    'प्रातःकाल':  'प्रातकाल',
    'अंतःकरण':    'अंतकरण',
    'मनःशांती':   'मनशांती',
    'मनःस्थिती':  'मनस्थिती',
    'पुनःश्च':    'पुनश्च',
    'नमः':        'नमहा',         # terminal visarga in Marathi loans
    'स्वतः':      'स्वतहा',
    'अतः':        'अतहा',
    'ततः':        'ततहा',
    'यतः':        'यतहा',
    'प्रायः':     'प्रायहा',
}

# ── Common mispronunciation fixes ────────────────────────────────────────
_MARATHI_PRONUNCIATION_FIXES = [
    # ज्ञ in Marathi is always द्न्य (NOT Hindi "gya")
    ('ज्ञ', 'द्न्य'),
    # Long ॠ → री
    ('ॠ', 'री'),
]

# ── Classical Marathi trailing anusvara ──────────────────────────────────
# In classical texts (Sant literature, older compositions), words like
# नाहीं, करतीं, तीं use anusvara to indicate nasalized vowel — NOT a
# consonantal nasal.  Modern Marathi drops this trailing anusvara.
# We only strip anusvara after long vowel matras at word boundaries.
_CLASSICAL_ANUSVARA_RE = re.compile(
    r'([ीेैोौ])'   # long vowel matra
    r'ं'            # anusvara
    r'(?=[\s.,;!?\n]|$)'  # word boundary
)

# ── Schwa Deletion Patterns ─────────────────────────────────────────────
# Marathi deletes inherent schwa in specific positions.  gTTS lang=mr
# handles the common cases.  We apply targeted fixes for patterns that
# gTTS frequently gets wrong.
#
# Rule A: End-of-word — always delete (gTTS handles this for lang=mr)
# Rule B: Three-syllable words with trailing matra → delete middle schwa
#         मालकी → माल्की  (gTTS sometimes says mā-la-kī instead of māl-kī)
# Rule C: Four-syllable words → delete 2nd & 4th schwa
#         करवत → कर्वत  (gTTS sometimes says ka-ra-vat instead of kar-vat)
#
# We apply Rule B and C conservatively via known word patterns.

# Words where gTTS gets schwa deletion wrong (add explicit halant)
_SCHWA_DELETION_LEXICON = {
    # Three-syllable Rule B: middle schwa deleted before trailing matra
    'मालकी': 'माल्की',
    'सरकी': 'सर्की',
    'चमकी': 'चम्की',
    'कमकी': 'कम्की',
    'बरकी': 'बर्की',
    'ढमकी': 'ढम्की',
    # Four-syllable Rule C: 2nd and 4th schwa deleted
    'करवत': 'कर्वत',
    'सरपट': 'सर्पट',
    'अलमट': 'अल्मट',
    'बडबड': 'बड्बड',
    'चटपट': 'चट्पट',
    'गटपट': 'गट्पट',
    'पटपट': 'पट्पट',
    'कटकट': 'कट्कट',
    'खटपट': 'खट्पट',
    'गडबड': 'गड्बड',
    # Common words where gTTS retains incorrect schwa
    'सरकार': 'सर्कार',     # sarkār not sarakār
    'अरवट': 'अर्वट',
}

# ── English Vowel Integration ────────────────────────────────────────────
# Modern Marathi has two vowels for English loanwords:
#   ॲ (U+0972) — short æ as in "bat"  (ॲप = App, बॅट = Bat)
#   ऑ (U+0911) — short ɒ as in "cot"  (डॉक्टर = Doctor, ऑफिस = Office)
#   ॅ (U+0945) — candra-e matra (dependent form of ॲ)
#   ॉ (U+0949) — candra-o matra (dependent form of ऑ)
#
# gTTS lang=mr supports these natively.  Android System TTS may not,
# especially if configured for Hindi.  Fallback mappings:
_ENGLISH_VOWEL_FALLBACK = {
    'ॲ': 'ए',      # ॲ → ए (closest standard Devanagari vowel)
    '\u0945': '\u0947',  # ॅ → े (matra)
    # ऑ and ॉ map to ओ/ो but gTTS handles them — only apply if needed
}


def apply_marathi_phonetics(text: str, for_system_tts: bool = False) -> str:
    """Apply Marathi-specific pronunciation rules.

    Parameters
    ----------
    text : str
        Devanagari text to preprocess.
    for_system_tts : bool
        If True, apply more aggressive normalization suitable for
        Android System TTS (which may lack native Marathi support).
        If False, apply conservative fixes suitable for gTTS lang=mr.

    Returns
    -------
    str
        Phonetically normalized text.
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # Remove ZWJ / ZWNJ that confuse tokenizers
    text = text.replace('\u200D', '').replace('\u200C', '')

    # ── 1. Visarga in Common Marathi Words ────────────────────────────
    for original, replacement in _MARATHI_VISARGA_WORDS.items():
        text = text.replace(original, replacement)

    # General Marathi visarga handling (remaining cases):
    # Before sibilants → matching sibilant
    text = re.sub(r'ः(?=[श])', 'श', text)
    text = re.sub(r'ः(?=[ष])', 'ष', text)
    text = re.sub(r'ः(?=[स])', 'स', text)
    # Before other consonants → mostly silent in modern Marathi (drop)
    text = re.sub(r'ः(?=[\u0915-\u0939])', '', text)
    # Terminal visarga in Marathi → light aspiration
    text = re.sub(r'ः(?=[\s.,;!?\n]|$)', 'हा', text)
    # Any remaining
    text = text.replace('ः', '')

    # ── 2. Conjunct Pronunciation ─────────────────────────────────────
    for old, new in _MARATHI_PRONUNCIATION_FIXES:
        text = text.replace(old, new)

    # ── 3. Classical Trailing Anusvara Cleanup ────────────────────────
    # नाहीं → नाही,  करतीं → करती,  गेलीं → गेली
    text = _CLASSICAL_ANUSVARA_RE.sub(r'\1', text)

    # ── 4. Schwa Deletion Lexicon ─────────────────────────────────────
    for original, replacement in _SCHWA_DELETION_LEXICON.items():
        text = re.sub(r'\b' + re.escape(original) + r'\b', replacement, text)

    # ── 5. English Vowel Fallback (System TTS only) ──────────────────
    if for_system_tts:
        for old, new in _ENGLISH_VOWEL_FALLBACK.items():
            text = text.replace(old, new)

    # ── 6. OM Symbol ──────────────────────────────────────────────────
    text = text.replace('ॐ', 'ओम')

    return text


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE: Combined Sanskrit Verse Preprocessing
# ═══════════════════════════════════════════════════════════════════════════

def preprocess_stotra_text(text: str) -> str:
    """Full preprocessing pipeline for stotra/shloka/verse text.

    Applies structural cleanup (dandas, verse numbers) followed by
    Sanskrit phonetic rules.  This is a drop-in replacement for
    the simpler ``_preprocess_stotra_text()`` in bridge files.
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # ── Structural Cleanup ────────────────────────────────────────────
    # Remove hyphens inside compound words
    text = re.sub(r'(?<=[\u0900-\u097F])-(?=[\u0900-\u097F])', '', text)
    # Remove ZWJ/ZWNJ
    text = text.replace('\u200D', '').replace('\u200C', '')
    # ASCII colon after Devanagari → visarga
    text = re.sub(r'([\u0900-\u097F]):', r'\1ः', text)
    # Verse numbers:  ॥ ३ ॥  or  ॥3॥ → period
    text = re.sub(r'॥\s*[\d०-९]+\s*॥', '.', text)
    # Double danda → period (long pause)
    text = text.replace('॥', '.')
    # Single danda → comma (half-line pause)
    text = text.replace('।', ',')
    # Stanza breaks
    text = re.sub(r'\n\s*\n+', '\n.\n', text)

    # ── Sanskrit Phonetics ────────────────────────────────────────────
    text = apply_sanskrit_phonetics(text)

    # ── Final Cleanup ─────────────────────────────────────────────────
    text = re.sub(r'[.,]{2,}', '.', text)
    text = re.sub(r'^\s*[.,]\s*', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
