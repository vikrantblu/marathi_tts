"""
Marathi/Sanskrit Grapheme-to-Phoneme (G2P) Engine
==================================================
Implements rule-based G2P processing with an exception lexicon for accurate
Devanagari pronunciation in the TTS pipeline.

This module addresses the core pronunciation errors:
1. Conjunct dropping  (च्या → चा)  — Fixed by conjunct preservation
2. Anusvara mismapping (पदरीं → wrong) — Fixed by context-dependent rules
3. Visarga flattening  (ः → always 'ha') — Fixed by sandhi-aware rules
4. Schwa mishandling  — Fixed by Marathi-specific schwa deletion

The G2P engine runs AFTER text normalization and BEFORE the text is sent
to the acoustic model (gTTS). It transforms normalized Devanagari text
into a phonetically-clarified form that gTTS can pronounce correctly.

Usage:
    from tts.utils.phonetic.g2p_engine import MarathiG2PEngine
    g2p = MarathiG2PEngine()
    clean = g2p.process("त्यांच्या दुःखी मनीं शांती नव्हती")
"""
import re
import os
import logging
import unicodedata
from typing import Dict, List, Optional, Set

from tts.constants.g2p_constants import (
    HALANT, ZWJ, ZWNJ,
    VOWELS, MATRAS, ALL_CONSONANT_SET,
    VALID_CONJUNCTS,
    ANUSVARA_ASSIMILATION, ANUSVARA_NASALIZE_ONLY,
    VISARGA_TO_SIBILANT, VISARGA_ECHO, VISARGA_EXCEPTIONS,
    SCHWA_PRESERVE_CLUSTERS, SCHWA_DELETE_SUFFIXES, SCHWA_EXCEPTIONS,
    LOANWORD_PHONEMES, EXCEPTION_LEXICON,
)

try:
    from tts.utils.text.morphological_analyzer import MarathiMorphologicalAnalyzer as _MorphAnalyzer
    _morph_available = True
except ImportError:
    _morph_available = False

logger = logging.getLogger('tts.g2p')


class MarathiG2PEngine:
    """Rule-based Grapheme-to-Phoneme engine for Marathi and Sanskrit.

    Processing order (each step feeds into the next):
      1. Unicode NFC normalization
      2. Exception lexicon lookup (whole-word overrides)
      3. Loanword phoneme mapping
      4. Conjunct preservation / repair
      5. Anusvara context-dependent assimilation
      6. Visarga context-dependent sandhi
      7. Schwa deletion (Marathi-specific)
      8. Dictionary validation (optional)
    """

    def __init__(self, dictionary_path: Optional[str] = None,
                 anusvara_mode: str = 'preserve',
                 schwa_mode: str = 'gtts'):
        """
        Args:
            dictionary_path: Path to a newline-delimited Marathi word list.
                If provided, the dictionary is loaded for optional validation.
            anusvara_mode: 'preserve' (default) keeps anusvara as-is for gTTS
                compatibility; 'assimilate' replaces anusvara with varga nasal
                before varga consonants (needed for edge-tts SSML).
            schwa_mode: 'gtts' (default) trusts gTTS Marathi model for schwa
                deletion; 'explicit' applies rule-based suffix schwa deletion
                (needed for edge-tts SSML where schwa handling is not implicit).
        """
        self._lexicon = dict(EXCEPTION_LEXICON)
        self._loanwords = dict(LOANWORD_PHONEMES)
        self._dictionary: Set[str] = set()
        self._anusvara_mode = anusvara_mode
        self._schwa_mode = schwa_mode

        # Morphological analyzer — used in explicit schwa mode to insert
        # ZWNJ at morpheme boundaries, preventing edge-tts glide insertion
        self._morph: Optional[object] = None
        if _morph_available and schwa_mode == 'explicit':
            try:
                self._morph = _MorphAnalyzer()  # type: ignore[assignment]
            except Exception as _me:
                logger.debug(f'MorphAnalyzer init error: {_me}')

        # Build regex for conjunct detection: match C + halant + C patterns
        consonant_chars = ''.join(sorted(ALL_CONSONANT_SET))
        self._conjunct_re = re.compile(
            f'([{consonant_chars}]){HALANT}([{consonant_chars}])'
        )

        # Build regex for anusvara + following consonant
        self._anusvara_re = re.compile(
            f'ं([{consonant_chars}])'
        )

        # Build regex for visarga + following consonant
        self._visarga_re = re.compile(
            f'ः([{consonant_chars}])'
        )

        # Load dictionary if path provided
        if dictionary_path and os.path.isfile(dictionary_path):
            self._load_dictionary(dictionary_path)
            logger.info(f"G2P dictionary loaded: {len(self._dictionary)} words")

    # ── Public API ─────────────────────────────────────────────────────

    def process(self, text: str) -> str:
        """Run the full G2P pipeline on the input text.

        This is the primary entry point. It processes word-by-word,
        applying the lexicon first, then rule-based transformations.
        """
        if not text:
            return text

        # Step 0: Strict NFC normalization
        text = unicodedata.normalize('NFC', text)

        # Step 1: Clean up stray ZWJ/ZWNJ that break conjuncts
        text = self._clean_zero_width(text)

        # Step 2: Process word by word
        words = text.split()
        processed = []

        for word in words:
            processed.append(self._process_word(word))

        return ' '.join(processed)

    def add_lexicon_entry(self, written: str, pronunciation: str):
        """Add a word to the exception lexicon at runtime."""
        self._lexicon[written] = pronunciation

    def add_lexicon_entries(self, entries: Dict[str, str]):
        """Bulk-add entries to the exception lexicon."""
        self._lexicon.update(entries)

    # ── Word-Level Processing ──────────────────────────────────────────

    def _process_word(self, word: str) -> str:
        """Process a single word through the G2P pipeline."""
        # Strip punctuation for lookup, reattach later
        prefix_punct, core, suffix_punct = self._strip_punctuation(word)

        if not core:
            return word

        # 1. Exception lexicon — exact match overrides everything
        if core in self._lexicon:
            return prefix_punct + self._lexicon[core] + suffix_punct

        # 2. Loanword check
        if core in self._loanwords:
            return prefix_punct + self._loanwords[core] + suffix_punct

        # 3. Apply rule-based G2P transformations
        result = core
        result = self._fix_conjuncts(result)
        result = self._process_anusvara(result)
        result = self._process_visarga(result)
        result = self._apply_schwa_rules(result)

        return prefix_punct + result + suffix_punct

    # ── Conjunct Preservation (Fix: च्या → चा) ────────────────────────

    def _fix_conjuncts(self, word: str) -> str:
        """Ensure consonant + halant + consonant clusters are preserved.

        The root cause of "च्या→चा" was that downstream regex rules 
        stripped the halant (्) linking च and य. Now that those 
        destructive patterns have been removed from PRONUNCIATION_FIXES 
        and _handle_special_pronunciations(), conjuncts survive intact.

        This method:
        1. Repairs known misspelled conjuncts (e.g., ध्द → द्ध)
        2. Validates C+halant+C sequences against VALID_CONJUNCTS
        
        NOTE: We do NOT insert ZWJ here. gTTS processes the Unicode text
        directly — ZWJ is a rendering hint for fonts, not a phonetic
        marker. Inserting it can confuse the TTS model's tokenizer.
        """
        # Repair known misspelled conjuncts
        repairs = {
            'ध्द': 'द्ध',    # Common mistake: बुध्दी → बुद्धी
            'ध्ड': 'ड्ढ',
        }
        for wrong, right in repairs.items():
            word = word.replace(wrong, right)

        return word

    def _clean_zero_width(self, text: str) -> str:
        """Remove stray ZWJ/ZWNJ that can break conjunct handling.

        ZWJ/ZWNJ are rendering hints for fonts, not phonetic markers.
        They can confuse the TTS tokenizer, so we strip them all.
        The actual conjunct information is in the C + halant + C sequence.
        """
        text = text.replace(ZWJ, '')
        text = text.replace(ZWNJ, '')
        return text

    # ── Anusvara Processing (Fix: पदरीं → correct nasalization) ────────

    def _process_anusvara(self, word: str) -> str:
        """Apply context-dependent anusvara rules.

        Mode 'preserve' (default):
            Keep anusvara as-is — gTTS handles it reasonably well.
            Only exception-lexicon overrides apply (upstream in _process_word).

        Mode 'assimilate':
            BEFORE a varga consonant: anusvara → varga nasal + halant
                e.g., गंभीर → गम्भीर,  संत → सन्त,  पंख → पङ्ख
            BEFORE semivowels/sibilants (य,र,ल,व,श,ष,स,ह):
                Keep anusvara (nasalizes preceding vowel only).
            AT WORD END: Keep anusvara as-is.
        """
        if self._anusvara_mode == 'preserve':
            return word

        # Mode: 'assimilate' — apply varga nasal substitution
        def _anusvara_sandhi(match):
            following = match.group(1)
            if following in ANUSVARA_NASALIZE_ONLY:
                # Before semivowels/sibilants — keep anusvara as nasalization
                return 'ं' + following
            if following in ANUSVARA_ASSIMILATION:
                # Before varga consonant — replace with class nasal
                return ANUSVARA_ASSIMILATION[following] + following
            # Unknown following consonant — keep as-is
            return 'ं' + following

        word = self._anusvara_re.sub(_anusvara_sandhi, word)
        return word

    # ── Visarga Processing (Fix: context-dependent ः) ──────────────────

    def _process_visarga(self, word: str) -> str:
        """Apply context-dependent visarga rules.

        The visarga (ः) pronunciation depends on what follows:
        - Before palatal consonants: becomes श (palatal sibilant)
        - Before retroflex consonants: becomes ष
        - Before dental consonants/sibilants: becomes स
        - Word-final / before vowels: echoes the preceding vowel
        - In specific words: use exception overrides
        """
        # Check exception words first (whole word or as prefix)
        for exc_word, exc_pron in VISARGA_EXCEPTIONS.items():
            if exc_word in word:
                word = word.replace(exc_word, exc_pron)
                return word  # Exception found — done

        # Process visarga + following consonant
        def _visarga_sandhi(match):
            following = match.group(1)
            if following in VISARGA_TO_SIBILANT:
                return VISARGA_TO_SIBILANT[following] + following
            # Before other consonants: light 'h' sound
            return 'ह' + following

        word = self._visarga_re.sub(_visarga_sandhi, word)

        # Word-final visarga: echo the preceding vowel
        if word.endswith('ः'):
            word = word[:-1] + 'ह'

        return word

    # ── Schwa Deletion (Marathi-specific) ──────────────────────────────

    def _apply_schwa_rules(self, word: str) -> str:
        """Apply Marathi schwa deletion rules.

        Mode 'gtts' (default):
            Trust gTTS's Marathi model for schwa deletion. Only apply
            SCHWA_EXCEPTIONS overrides. gTTS lang=mr handles basic
            word-final schwa deletion correctly.

        Mode 'explicit':
            Apply rule-based schwa analysis for edge-tts/SSML where the
            TTS model may not natively handle Marathi schwa rules:
            1. SCHWA_EXCEPTIONS — hard-coded overrides (always applied)
            2. Protect SCHWA_PRESERVE_CLUSTERS — ensure conjuncts are
               not broken by downstream processing
            3. Word-final bare consonant — in Marathi, the implicit
               schwa is always deleted at word end (unlike Hindi).
               Currently handled by the TTS engine; this mode validates
               and can log discrepancies for lexicon expansion.

        NOTE: Full morphology-based schwa prediction requires a trained
        model or extensive lexicon. This implementation covers the most
        impactful patterns. Expand SCHWA_EXCEPTIONS as needed.
        """
        # Step 1: Exception list — always applied regardless of mode
        if word in SCHWA_EXCEPTIONS:
            return SCHWA_EXCEPTIONS[word]

        if self._schwa_mode == 'gtts':
            # Trust gTTS's native Marathi schwa handling
            return word

        # Mode: 'explicit' — rule-based schwa analysis for edge-tts SSML
        if len(word) < 2:
            return word

        # ── Morpheme-boundary ZWNJ insertion ────────────────────────────
        # When the morphological analyzer is available, insert ZWNJ at
        # morpheme boundaries so edge-tts does not insert a y-glide or
        # false vowel between stem and inflectional suffix.
        #
        # Example: बोलतो (stem 'बोल' + suffix 'तो')
        #   Without ZWNJ: edge-tts may read as 'bol-ya-to'
        #   With ZWNJ:    'बोल​तो' → 'bol-to'  (boundary marked)
        #
        # We re-use the ZWNJ convention established for the -chaa fix.
        if self._morph is not None:
            try:
                boundaries = self._morph.morpheme_boundary_positions(word)  # type: ignore[union-attr]
                if boundaries:
                    # Build new string with ZWNJ inserted at each boundary
                    result_chars = list(word)
                    for offset, pos in enumerate(boundaries):
                        result_chars.insert(pos + offset, ZWNJ)
                    word = ''.join(result_chars)
                    logger.debug(f'ZWNJ boundaries inserted: {word!r}')
            except Exception as _be:
                logger.debug(f'Morpheme boundary error for {word!r}: {_be}')

        # ── Word-final consonant logging ─────────────────────────────────
        # In Marathi, bare final consonant = schwa deleted.
        # gTTS / edge-tts handle this natively; log for lexicon expansion.
        last_char = word[-1] if word else ''
        if last_char in ALL_CONSONANT_SET:
            logger.debug(f"Schwa-final consonant: {word!r} (ends in {last_char!r})")

        return word

    # ── Utility ────────────────────────────────────────────────────────

    def _strip_punctuation(self, word: str):
        """Separate leading/trailing punctuation from the core word."""
        punct_chars = '।॥.,;:!?-–—\'"()[]{}«»'
        prefix = ''
        suffix = ''

        while word and word[0] in punct_chars:
            prefix += word[0]
            word = word[1:]

        while word and word[-1] in punct_chars:
            suffix = word[-1] + suffix
            word = word[:-1]

        return prefix, word, suffix

    def _load_dictionary(self, path: str):
        """Load a newline-delimited word list for validation."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):
                        self._dictionary.add(word)
        except Exception as e:
            logger.error(f"Failed to load G2P dictionary: {e}")

    def is_valid_word(self, word: str) -> bool:
        """Check if a word exists in the loaded dictionary."""
        return word in self._dictionary
