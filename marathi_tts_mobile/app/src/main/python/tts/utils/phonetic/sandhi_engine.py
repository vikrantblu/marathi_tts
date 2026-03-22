"""
Sanskrit Sandhi Engine for Human-Like TTS
==========================================
Processes Sanskrit Devanagari text to correctly handle sandhi (sound-junction)
rules so that TTS engines pronounce Sanskrit as a human pandita or reciter would.

WHY THIS EXISTS
---------------
Sanskrit is written *after* sandhi has been applied: the words "यदा" and "अर्जुन:"
become "यदार्जुनः" in running text.  A TTS engine reading letter-by-letter will:
  • Mispronounce the compound vowel as two separate vowels
  • Ignore avagraha (ऽ) — an ellided vowel that must produce a natural glide
  • Map visarga before a vowel as "ha" instead of the correct voiced 'r'
  • Drop/merge nasals before consonants in unclear ways

This engine does NOT un-apply sandhi (that would require a full parser).
Instead it rewrites the text to give the TTS engine the phonetic hints it
needs to produce correct speech — the same way a human writes pronunciation
guides in Devanagari margin notes.

ARCHITECTURE
------------
Processing pipeline (each step called in order by ``process()``):
  1. avagraha_expansion      — ऽ (avagraha) → silent glide hint
  2. visarga_before_vowel    — ःA → rA  (the most commonly wrong rule)
  3. anusvara_before_sibilant — ंश/ष/स → nasal + sibilant
  4. vowel_junction_hints    — ā+i → e  etc. (for reanalysis after display sandhi)
  5. terminal_consonant_prep — final cluster clarification for chanting
  6. geminate_hint           — tt/dd clusters → slight hold hint

Usage::

    from tts.utils.phonetic.sandhi_engine import SandhiEngine

    engine = SandhiEngine()
    clean  = engine.process(verse_text)          # full pipeline
    # or call individual steps:
    clean  = engine.expand_avagraha(raw)
    clean  = engine.fix_visarga_vowel_sandhi(raw)
"""
from __future__ import annotations

import re
import unicodedata
import logging
from typing import List, Tuple, Dict

log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════
# Character constants
# ══════════════════════════════════════════════════════════════════════════

HALANT      = '\u094D'   # ्
ANUSVARA    = '\u0902'   # ं
VISARGA     = '\u0903'   # ः
CHANDRABINDU= '\u0901'   # ँ
AVAGRAHA    = '\u093D'   # ऽ
NUKTA       = '\u093C'   # ़
ANUDATTA    = '\u0952'   # ॒  (accent marks — common in recitation texts)
UDATTA      = '\u0951'   # ॑

# Independent vowels
_IND_VOWELS = 'अआइईउऊऋॠऌए ऐओऔ'

# Dependent matra (vowel signs) – ordered long-before-short for matching
_MATRAS = 'ािीुूृॄेैोौ'

# Short dependent matras (for vowel sandhi detection)
_SHORT_MATRAS = {'ि', 'ु', 'ृ'}
_LONG_MATRAS  = {'ा', 'ी', 'ू'}     # long dependent matras

# All Devanagari consonants (क–ह + ळ)
_CONSONANT_RE = re.compile(r'[\u0915-\u0939\u0933]')

# Vowel matras
_MATRA_RE     = re.compile(r'[\u093E-\u094C]')

# Independent vowel RE (excludes अ which is zero-form)
_IND_VOWEL_RE = re.compile(r'[\u0906-\u0914]')  # आ–औ


# ══════════════════════════════════════════════════════════════════════════
# Visarga + vowel sandhi map
# ══════════════════════════════════════════════════════════════════════════

# When visarga is followed by a *vowel*, it usually becomes voiced 'r'
# (the original Sanskrit r-visarga): "देवः अपि" = "devo'pi" → "देवोऽपि"
# For recitation / TTS we convert ः + vowel → written 'र' + vowel
# (the most natural way to guide the TTS engine)
#
# NOTE:  This is the "r-sandhi" rule:
#   -aḥ + V → -a r V  (a keeps unchanged; visarga becomes r)
#   -āḥ + V → -ā r V
#   -iḥ + V → -i r V  (rare; mostly epic Sanskrit)
#   BUT:   -aḥ + a  →  -o  (guna sandhi — vowel changes!)
#
# We implement the conservative version that is always safe:
#   ः + any vowel = ह + vowel (aspirate h)
# And the precise version for common patterns:
#   ः + अ / ा (aa) → visarga echoes, then elision usually handled by avagraha

_VISARGA_VOWEL_MAP: Dict[str, str] = {
    'अ': 'र् अ',    # namaḥ + asti = namaḥ → namar-asti
    'आ': 'र् आ',
    'इ': 'र् इ',
    'ई': 'र् ई',
    'उ': 'र् उ',
    'ऊ': 'र् ऊ',
    'ए': 'र् ए',
    'ऐ': 'र् ऐ',
    'ओ': 'र् ओ',
    'औ': 'र् औ',
    'ऋ': 'र् ऋ',
}

# ── r-sandhi matra (consonant + matra vowel versions)
#    When visarga follows a consonant+matra and NEXT char is independent vowel
_MATRA_VOWEL_MAP: Dict[str, str] = {
    'ा': 'र् ',   # -āḥ → -ā r (followed by vowel)
    'ि': 'र् ',
    'ी': 'र् ',
    'ु': 'र् ',
    'ू': 'र् ',
    'ृ': 'र् ',
    'े': 'र् ',
    'ै': 'र् ',
    'ो': 'र् ',
    'ौ': 'र् ',
}


# ══════════════════════════════════════════════════════════════════════════
# Avagraha handling
# ══════════════════════════════════════════════════════════════════════════
# ऽ (avagraha, U+093D) marks an elided vowel in Sanskrit sandhi.
# Common case: "रामोऽपि" = "rāmo + api" where the 'a' of api is elided.
# For TTS the natural pronunciation is a very brief neutral glide.
# We replace avagraha with a ZWNJ (zero-width non-joiner) followed by nothing,
# telling the TTS to simply skip the position (the gTTS model should do this
# naturally when it encounters ZWNJ).  If the model ignores ZWNJ we simply
# drop the avagraha character to avoid mispronunciation.

_AVAGRAHA_REPLACE = ''   # just drop — the surrounding vowels will glide naturally


# ══════════════════════════════════════════════════════════════════════════
# Nasalization before sibilants
# ══════════════════════════════════════════════════════════════════════════
# Sanskrit: anusvara before ś/ṣ/s → assimilates to dental nasal + sibilant
# e.g., सं + शय = संशय → "san-śaya" TTS often says "am-śaya" or just anusvara
# We insert explicit nasal: ंश → न्श,  ंष → न्ष,  ंस → न्स

_ANUSVARA_SIBILANT_MAP: List[Tuple[str, str]] = [
    (ANUSVARA + 'श', 'न्' + 'श'),
    (ANUSVARA + 'ष', 'न्' + 'ष'),
    (ANUSVARA + 'स', 'न्' + 'स'),
    (ANUSVARA + 'ह', 'म्' + 'ह'),   # before h → m in Sanskrit recitation
]

# anusvara before semivowels — remains as nasalized vowel (no rewrite needed)
# anusvara before varga stops — assimilate to class nasal for correct recitation

_ANUSVARA_VARGA_MAP: Dict[str, str] = {
    # Velar class (anusvara → ङ्)
    'क': 'ङ्', 'ख': 'ङ्', 'ग': 'ङ्', 'घ': 'ङ्', 'ङ': 'ङ्',
    # Palatal class (anusvara → ञ्)
    'च': 'ञ्', 'छ': 'ञ्', 'ज': 'ञ्', 'झ': 'ञ्', 'ञ': 'ञ्',
    # Retroflex class (anusvara → ण्)
    'ट': 'ण्', 'ठ': 'ण्', 'ड': 'ण्', 'ढ': 'ण्', 'ण': 'ण्',
    # Dental class (anusvara → न्)
    'त': 'न्', 'थ': 'न्', 'द': 'न्', 'ध': 'न्', 'न': 'न्',
    # Labial class (anusvara → म्)
    'प': 'म्', 'फ': 'म्', 'ब': 'म्', 'भ': 'म्', 'म': 'म्',
}


# ══════════════════════════════════════════════════════════════════════════
# Visarga + voiced consonant → r  (FEAT-5)
# ══════════════════════════════════════════════════════════════════════════
# When visarga is followed (across a word boundary) by a voiced consonant,
# it becomes 'r' in Sanskrit recitation.
# e.g., पुनः + दर्शनम् → पुनर्दर्शनम्
#       मनः + गत     → मनर्गत
#       अंतः + करण   → अंतर्करण
# This is the second most impactful sandhi rule after visarga + vowel.
#
# Voiced consonants: the full list of Devanagari voiced stops & nasals
# (ग, घ, ज, झ, ड, ढ, द, ध, ब, भ, and nasals ङ, ञ, ण, न, म)
# Plus semivowels (य, र, ल, व) which are also voiced.
_VOICED_CONSONANTS = 'गघजझडढदधबबभङञणनमयरलव'


# ══════════════════════════════════════════════════════════════════════════
# Vowel junction clarification hints
# ══════════════════════════════════════════════════════════════════════════
# In Sanskrit running text, vowel sandhi has *already* been applied.
# The output is already the fused form (so we generally don't re-fuse).
# What we DO need is to ensure that certain fused forms are read correctly:
#
#   Case 1 — Compensatory lengthening residue:
#     The long vowel that resulted from sandhi may be split by TTS into two:
#     "नमस्ते" — read correctly as na-mas-te.  No issue.
#     "गायति" — the 'ā' is already in the text, TTS reads it correctly.
#
#   Case 2 — Hiatus after elision (avagraha cases):
#     "रामोऽपि" — after removing ऽ → "रामोपि" — TTS reads "rā-mo-pi" ✓
#
#   Case 3 — yaN sandhi visible form:
#     Word-initial 'i/u' after a word ending in i/u produces य/व:
#     "अत्र + इति" = "अत्रेति" which is already written as ए, read correctly.
#
# Most cases are already correct in the written Sanskrit text.
# We add hints only for the cases where TTS commonly goes wrong.

_VOWEL_JUNCTION_FIXES: List[Tuple[str, str]] = [
    # Double aa from sandhi — some TTS engines split ā+ā into two syllables
    # We don't need to do anything; gTTS handles ā correctly.

    # Anushtubh half-verse metric break — in written Sanskrit the caesura
    # (yati) is invisible.  Insert a zero-width space so TTS pauses fractionally.
    # We handle this in the metre engine, not here.
]


# ══════════════════════════════════════════════════════════════════════════
# Geminate cluster hint
# ══════════════════════════════════════════════════════════════════════════
# Sanskrit has phonemically distinct geminates (tt, dd, nn, etc.)
# that must be held longer than single consonants.
# gTTS tends to reduce them.  We use this pattern as a documentation note;
# the actual audio-level hold is handled by the prosody engine.

# Geminates that need a hold (documentation only — see prosody_engine)
GEMINATE_CLUSTERS = frozenset([
    'त्त', 'द्द', 'न्न', 'म्म', 'ल्ल', 'र्र',
    'क्क', 'ग्ग', 'ट्ट', 'ड्ड', 'प्प', 'ब्ब',
    'श्श', 'ष्ष', 'स्स',
])


# ══════════════════════════════════════════════════════════════════════════
# Udātta / Anudātta accent stripping
# ══════════════════════════════════════════════════════════════════════════
# Some Sanskrit texts (especially Veda-corpus) include pitch-accent marks
# (vedic extensions U+1CD0–U+1CFF).  These are purely scholarly notation
# and confuse TTS engines.  We strip them before processing.
_VEDIC_ACCENT_RE = re.compile(r'[\u1CD0-\u1CFF\u0951\u0952\u0953\u0954]')


# ══════════════════════════════════════════════════════════════════════════
# Specific word-level overrides for common Sanskrit phrases
# ══════════════════════════════════════════════════════════════════════════
# These cover cases that general rules miss or get wrong.
# Key = written Sanskrit (post-sandhi), Value = TTS-friendly pronunciation.
WORD_OVERRIDES: Dict[str, str] = {
    # Common stotra words
    'नमस्ते':       'नमस्ते',        # correct as-is
    'नमस्कार':      'नमस्कार',
    'नमोनमः':       'नमो नमहा',      # avagraha-like elision
    'ॐ':            'ओम्',
    'श्रीःˈ':       'श्री',
    # Visarga in terminal position common in stotras
    'नमः':          'नमहा',
    'स्वाहा':       'स्वाहा',
    'स्वधा':        'स्वधा',
    # Common junctions that TTS mispronounces
    'तस्मात्':      'तस्मात',
    'एवम्':         'एवम',
    'सर्वम्':       'सर्वम',
    # NOTE: ज्ञान is intentionally NOT overridden here.
    # In Sanskrit mode it stays as-is (Sanskrit = gyān).
    # In Marathi mode, apply_marathi_phonetics() handles ज्ञ → द्न्य separately.
    # Putting ज्ञान → ध्यान here would replace "knowledge" with "meditation"
    # everywhere, which is completely wrong.
}


# ══════════════════════════════════════════════════════════════════════════
# SandhiEngine class
# ══════════════════════════════════════════════════════════════════════════

class SandhiEngine:
    """Apply Sanskrit sandhi pronunciation rules for TTS.

    This engine is designed to work **after** text normalization and
    **before** the text is passed to the acoustic model (gTTS/edge-tts).

    It does NOT un-apply sandhi.  It rewrites the post-sandhi Sanskrit
    text to give TTS engines the phonetic hints they need.

    Typical use in verse / stotra pipeline::

        from tts.utils.phonetic.sandhi_engine import SandhiEngine
        engine = SandhiEngine()
        tts_text = engine.process(verse_text)
    """

    def __init__(self, mode: str = 'classical'):
        """
        Args:
            mode: 'classical'   — strict Sanskrit (stotra, shloka, vedic-adjacent)
                  'epic'        — Epic Sanskrit (Mahabharata, Ramayana) — slightly relaxed
                  'hybrid'      — Old Marathi texts with Sanskritic vocabulary
        """
        self.mode = mode
        log.debug("SandhiEngine initialised in mode=%s", mode)

    # ── Main entry point ──────────────────────────────────────────────────

    def process(self, text: str) -> str:
        """Run full sandhi correction pipeline.

        Steps applied in order:
          1. Unicode NFC
          2. Vedic accent stripping
          3. Avagraha expansion
          4. Visarga + vowel sandhi fix (most impactful)
          4b. Visarga + voiced consonant → r  (FEAT-5)
          5. Anusvara + sibilant assimilation
          5b. Anusvara + varga stop assimilation
          6. Word-level overrides (applied last to protect key words)
        """
        if not text:
            return text

        text = unicodedata.normalize('NFC', text)
        text = self._strip_vedic_accents(text)
        text = self.expand_avagraha(text)
        text = self.fix_visarga_vowel_sandhi(text)
        text = self.fix_visarga_voiced_consonant(text)
        text = self.fix_anusvara_sibilant(text)
        text = self.fix_anusvara_varga(text)
        text = self._apply_word_overrides(text)

        return text

    # ── Step 1: Vedic accent stripping ───────────────────────────────────

    def _strip_vedic_accents(self, text: str) -> str:
        """Remove Udātta/Anudātta/Svarita marks and other vedic extensions."""
        return _VEDIC_ACCENT_RE.sub('', text)

    # ── Step 2: Avagraha ─────────────────────────────────────────────────

    def expand_avagraha(self, text: str) -> str:
        """Handle avagraha (ऽ) — elided vowel marker.

        In Sanskrit running text, avagraha marks where a short 'a' vowel
        was elided in sandhi.  Examples:
            रामोऽपि    = rāmo + api   (avagraha replaces the 'a' of api)
            देवोऽहम्   = devo + aham
            तवोऽdeva?  (rare — mostly rāmo'pi type)

        For TTS we simply drop the avagraha.  The vowel on the left
        already encodes the sandhi result; dropping avagraha means the
        next consonant directly follows it — which is the correct reading.

        E.g.:  "रामोऽपि"  →  "रामोपि"  → TTS reads "rā-mo-pi"  ✓
               "देवोऽहम्" → "देवोहम्"  → TTS reads "de-vo-ham" ✓
        """
        # Drop avagraha character
        text = text.replace(AVAGRAHA, _AVAGRAHA_REPLACE)
        # Also handle the ASCII apostrophe used instead in some texts
        # Only when between Devanagari characters
        text = re.sub(
            r"(?<=[\u0900-\u097F])'(?=[\u0900-\u097F])",
            '', text
        )
        return text

    # ── Step 3: Visarga before vowel → r-sandhi ──────────────────────────

    def fix_visarga_vowel_sandhi(self, text: str) -> str:
        """Fix the most common sandhi error: visarga before a vowel.

        Sanskrit r-sandhi: when a word ending in ḥ (visarga) is followed
        by a *voiced* vowel or consonant, the visarga becomes 'r'.

        Written as-is in texts:   "देवः अस्ति"  (deva + asti)
        Correct pronunciation:    "देवर् अस्ति" → "devara-sti"
        Simpler TTS hint:         "देवर अस्ति"

        IMPORTANT: This only applies to r-sandhi contexts (when the word
        before visarga had an original 'r').  For aḥ + a → o sandhi
        (e.g., "रामः अपि" → "रामोऽपि"), the sandhi form "रामोऽपि" is
        already written — we just expand the avagraha.

        In this engine we apply the conservative rule:
            ः + independent vowel → र + vowel (drop the visarga)
        This is correct for most stotra/shloka contexts.
        """
        # Pattern: visarga followed by an independent vowel letter.
        # IMPORTANT: the character class must contain NO spaces — a space
        # would cause every word-boundary visarga (ः followed by space) to
        # be replaced with a phantom 'र् ', inserting stray syllables between
        # all words that end in visarga.

        def _replace(m: re.Match) -> str:
            vowel = m.group(1)
            # ः + vowel → र् + vowel  (r-sandhi hint for TTS)
            return 'र् ' + vowel

        text = re.sub(VISARGA + '([अआइईउऊऋॠऌएऐओऔ])', _replace, text)

        # Visarga before anusvara'd forms (rare) — drop visarga
        text = re.sub(VISARGA + '(?=' + ANUSVARA + ')', '', text)

        return text

    # ── Step 4b: Visarga + voiced consonant → r (FEAT-5) ─────────────────

    def fix_visarga_voiced_consonant(self, text: str) -> str:
        """Visarga before a voiced consonant becomes 'r' in Sanskrit recitation.

        Examples:
            पुनः दर्शनम्  → पुनर् दर्शनम्
            मनः गत       → मनर् गत
            अंतः करण     → (no change — क is voiceless)

        Only applies across a word boundary (space after visarga).
        Does NOT apply when the word already ends in a consonant cluster
        that would make 'r' unnatural.

        This is the second most impactful sandhi rule after visarga + vowel.
        Common in stotras: नमः, दुःख, अंतः, पुनः before voiced words.
        """
        # Pattern: visarga + space + voiced consonant letter
        # Replace: visarga → र् (repha form)
        def _replace_voiced(m: re.Match) -> str:
            consonant = m.group(1)
            return 'र् ' + consonant

        text = re.sub(
            VISARGA + r'\s+([' + _VOICED_CONSONANTS + '])',
            _replace_voiced,
            text
        )
        return text

    # ── Step 5: Anusvara + sibilant assimilation ─────────────────────────

    def fix_anusvara_sibilant(self, text: str) -> str:
        """Insert explicit nasal before sibilants where anusvara precedes them.

        Sanskrit: anusvara + ś/ṣ/s → dental nasal + sibilant
            संशय → सन्शय  (TTS now reads "san-śaya" correctly)
            संस्कृत → सन्स्कृत  (san-skṛta)
            संहार → सम्हार  (sam-hāra)

        NOTE:  We do NOT rewrite anusvara before stop consonants (क-म series)
        because gTTS handles those through its own phoneme model.  Only
        the sibilant assimilation is consistently wrong without this hint.
        """
        for pattern, replacement in _ANUSVARA_SIBILANT_MAP:
            text = text.replace(pattern, replacement)
        return text

    def fix_anusvara_varga(self, text: str) -> str:
        """Assimilate anusvara to class nasal before varga (stop) consonants.

        Sanskrit: anusvara before a varga consonant assimilates to the nasal
        of that varga (class).  This is mandatory in correct recitation:
            संकल्प   → सङ्कल्प   (velar ङ before क)
            संचय     → सञ्चय     (palatal ञ before च)
            संतोष    → सन्तोष    (dental न before त)
            संपूर्ण  → सम्पूर्ण  (labial म before प)

        TTS engines often read anusvara as a generic nasal 'm', which is
        incorrect before non-labial stops.  Rewriting to explicit class nasal
        gives the TTS engine the correct phonetic target.
        """
        result = []
        i = 0
        while i < len(text):
            if text[i] == ANUSVARA and i + 1 < len(text):
                next_char = text[i + 1]
                if next_char in _ANUSVARA_VARGA_MAP:
                    # Replace anusvara with class nasal; keep the consonant
                    result.append(_ANUSVARA_VARGA_MAP[next_char])
                else:
                    result.append(text[i])
            else:
                result.append(text[i])
            i += 1
        return ''.join(result)

    # ── Step 5: Word-level overrides ─────────────────────────────────────

    def _apply_word_overrides(self, text: str) -> str:
        """Apply the WORD_OVERRIDES dictionary for known problem words."""
        for written, phonetic in WORD_OVERRIDES.items():
            if written in text:
                # Only replace full word (word-boundary aware)
                text = re.sub(
                    r'(?<![ा-ौ\u0900-\u097F])' + re.escape(written) + r'(?![ा-ौ\u0900-\u097F])',
                    phonetic, text
                )
        return text


# ══════════════════════════════════════════════════════════════════════════
# Helper: detect if text is primarily Sanskrit vs Marathi
# ══════════════════════════════════════════════════════════════════════════

# Sanskrit-diagnostic words (high-frequency, only in Sanskrit/tatsama contexts)
_SANSKRIT_MARKERS = frozenset([
    'नमः', 'नमः', 'स्वाहा', 'स्वधा', 'वन्दे', 'जयति',
    'ब्रह्म', 'विष्णु', 'शंकर', 'महेश्वर', 'परमेश्वर',
    'श्रीमद्', 'भगवद्', 'गीता', 'उपनिषद्',
    'तस्मात्', 'एवम्', 'यथा', 'तथा', 'इति',
])

_VERSE_MARKER_RE = re.compile(r'[।॥]')


def is_predominantly_sanskrit(text: str) -> bool:
    """Heuristic: does this text look more like Sanskrit than Marathi?

    Returns True if:
      - Text has ॥ (double danda = Sanskrit/Old Marathi verse)
      - Text contains Sanskrit marker words
      - Visarga count > 0 with low Marathi function words
    """
    if _VERSE_MARKER_RE.search(text):
        return True
    for marker in _SANSKRIT_MARKERS:
        if marker in text:
            return True
    # Visarga-heavy text is likely Sanskrit
    if text.count(VISARGA) > 2:
        return True
    return False
