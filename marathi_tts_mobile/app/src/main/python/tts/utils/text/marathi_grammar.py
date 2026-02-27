"""
Marathi Grammar & Text Arrangement Engine for TTS
==================================================
Properly extracts, cleans, arranges, and fixes Marathi text according to
Marathi grammar rules before it reaches the TTS engine.

Handles:
 1. Text extraction & cleanup (HTML, OCR artifacts, junk chars)
 2. Spelling corrections (common Marathi misspellings)
 3. Sandhi (संधी) — joining/splitting rules
 4. Vibhakti (विभक्ती) agreement — case marker corrections
 5. Gender/number agreement on verbs & adjectives
 6. Word order (SOV) arrangement — fixing misplaced words
 7. Punctuation restoration (dandas, commas at clause boundaries)
 8. Honorific & postposition normalization
 9. Repetition & stutter removal

This module is purely rule-based (no ML) so it runs fast and offline.
"""
import re
import logging
import unicodedata
from typing import List, Tuple, Optional, Dict
from tts.constants.grammar_constants import (
    SPELLING_CORRECTIONS, SPELLING_PATTERNS,
    SANDHI_SPLITS, VIBHAKTI_FIXES,
    AGREEMENT_FIXES, WORD_ORDER_FIXES,
    SENTENCE_FINAL_VERBS, SENTENCE_STARTERS,
    HONORIFIC_NORMALIZATIONS, COMMA_BEFORE_WORDS,
)

logger = logging.getLogger('tts.grammar')


# All constants (SPELLING_CORRECTIONS, SPELLING_PATTERNS, SANDHI_SPLITS,
# VIBHAKTI_FIXES, AGREEMENT_FIXES, WORD_ORDER_FIXES, SENTENCE_FINAL_VERBS,
# SENTENCE_STARTERS, HONORIFIC_NORMALIZATIONS, COMMA_BEFORE_WORDS)
# are imported from tts.constants.grammar_constants above.


# ═══════════════════════════════════════════════════════════════════════════
# 2. TEXT EXTRACTION & CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

def extract_and_clean(text: str) -> str:
    """Extract clean Marathi text from messy input (OCR, HTML, copy-paste).

    Removes:
     - HTML tags & entities
     - URLs, emails
     - Non-Devanagari junk (stray Latin chars mixed in Marathi)
     - Multiple spaces, weird Unicode
     - Page numbers, headers/footers patterns
    Preserves:
     - Devanagari text, punctuation (।॥,;:?!…—)
     - Numbers (both ०-९ and 0-9) for later conversion
     - Newlines (paragraph structure)
    """
    if not text:
        return ''

    # Strip BOM and normalize line endings
    text = text.lstrip('\uFEFF')
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)     # HTML element tags
    text = re.sub(r'&[a-zA-Z]+;', ' ', text) # HTML entities (&amp; etc.)
    text = re.sub(r'&#\d+;', ' ', text)       # Numeric HTML entities

    # Remove URLs and emails
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', '', text)

    # Remove page/chapter markers like "पृष्ठ ३", "--- Page 5 ---"
    text = re.sub(r'[-–—=_]{3,}.*?[-–—=_]{3,}', '', text)
    text = re.sub(r'^\s*(?:Page|पृष्ठ|पान)\s*[०-९\d]+\s*$', '', text, flags=re.MULTILINE)

    # Remove isolated Latin characters/words mixed into Devanagari text
    # (but keep full English phrases if intentional — heuristic: 3+ Latin chars together)
    # Remove single stray Latin letters/numbers that are OCR noise
    text = re.sub(r'(?<![a-zA-Z0-9])[a-zA-Z](?![a-zA-Z0-9])', '', text)

    # Remove common OCR artifacts
    text = re.sub(r'[¦|¥£€$§¶©®™•·°±×÷]', '', text)
    text = re.sub(r'[_~^`]+', '', text)

    # Collapse multiple blank lines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Collapse multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Unicode NFC normalization (important for Devanagari)
    text = unicodedata.normalize('NFC', text)

    return text.strip()


# Sections 3-10: SANDHI_SPLITS, VIBHAKTI_FIXES, AGREEMENT_FIXES,
# WORD_ORDER_FIXES, SENTENCE_FINAL_VERBS, SENTENCE_STARTERS,
# HONORIFIC_NORMALIZATIONS, COMMA_BEFORE_WORDS
# are all imported from tts.constants.grammar_constants.


# ═══════════════════════════════════════════════════════════════════════════
# 7. PUNCTUATION RESTORATION
# ═══════════════════════════════════════════════════════════════════════════

def restore_punctuation(text: str) -> str:
    """Add missing dandas (।) at sentence boundaries if text lacks punctuation.

    Heuristic: if text has < 1 danda per 80 chars, it likely needs punctuation.
    """
    # Count existing punctuation
    puncts = len(re.findall(r'[।॥.?!]', text))
    char_count = len(text)

    if char_count < 20:
        return text  # too short to analyze

    # If punctuation density is reasonable, don't touch
    if puncts > 0 and char_count / puncts < 120:
        return text

    words = text.split()
    result = []
    i = 0

    while i < len(words):
        word = words[i]
        # Strip any existing trailing punctuation for checking
        clean_word = re.sub(r'[।॥.?!,;]+$', '', word)

        result.append(word)

        # If this word is a sentence-final verb AND not already followed by punct
        if clean_word in SENTENCE_FINAL_VERBS and not re.search(r'[।॥.?!]$', word):
            # Check if next word is a sentence starter or capitalized Marathi
            if i + 1 < len(words):
                next_clean = re.sub(r'^[।॥.?!,;]+', '', words[i + 1])
                if next_clean in SENTENCE_STARTERS:
                    result.append('।')
                # Also add danda if there's a long gap to the next verb
                elif i + 1 < len(words) and _words_until_next_verb(words, i + 1) > 6:
                    result.append('।')
            else:
                # Last word — add final danda
                if not re.search(r'[।॥.?!]$', word):
                    result.append('।')
        i += 1

    return ' '.join(result)


def _words_until_next_verb(words: List[str], start: int) -> int:
    """Count words until the next sentence-final verb."""
    for i in range(start, min(start + 15, len(words))):
        clean = re.sub(r'[।॥.?!,;]+$', '', words[i])
        if clean in SENTENCE_FINAL_VERBS:
            return i - start
    return 15  # large number = no verb found soon


# ═══════════════════════════════════════════════════════════════════════════
# 8. REPETITION & STUTTER REMOVAL
# ═══════════════════════════════════════════════════════════════════════════

def remove_repetitions(text: str) -> str:
    """Remove accidentally repeated words/phrases (common in OCR & copy-paste).

    NOTE: Python's \\b is BROKEN for Devanagari — halant/matras are not \\w,
    so \\b fires inside syllables (e.g., between ं and त in संत). This caused
    false matches like 'श्रीसंत तुकोबारायांच्या' → 'श्रीसंतुकोबारायांच्या'.

    Fix: Use space-delimited word splitting instead of regex word boundaries.
    """
    # Split into words and remove exact consecutive duplicates
    words = text.split()
    if len(words) < 2:
        return text

    result = [words[0]]
    for w in words[1:]:
        if w != result[-1]:
            result.append(w)

    # Also check for repeated 2-word phrases
    cleaned = result[:]
    i = 0
    while i < len(cleaned) - 3:
        phrase = cleaned[i] + ' ' + cleaned[i + 1]
        next_phrase = cleaned[i + 2] + ' ' + (cleaned[i + 3] if i + 3 < len(cleaned) else '')
        if phrase == next_phrase:
            del cleaned[i + 2:i + 4]
        else:
            i += 1

    return ' '.join(cleaned)


# ═══════════════════════════════════════════════════════════════════════════
# COMMA INSERTION AT CLAUSE BOUNDARIES
# ═══════════════════════════════════════════════════════════════════════════

def insert_clause_commas(text: str) -> str:
    """Insert commas before conjunctions/connectives where missing."""
    words = text.split()
    result = []

    for i, word in enumerate(words):
        clean = re.sub(r'^[,;]+', '', word)
        if clean in COMMA_BEFORE_WORDS and i > 0:
            # Check if previous word already has comma
            if result and not re.search(r'[,;।]$', result[-1]):
                result[-1] = result[-1] + ','
        result.append(word)

    return ' '.join(result)


# ═══════════════════════════════════════════════════════════════════════════
# MASTER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

class MarathiGrammarEngine:
    """Complete Marathi grammar & text arrangement engine.

    Usage:
        engine = MarathiGrammarEngine()
        clean_text = engine.process(raw_text)
    """

    def __init__(self):
        # Pre-compile all regex patterns for performance
        self._spelling_patterns = [
            (re.compile(p, re.UNICODE), r) for p, r in SPELLING_PATTERNS
        ]
        self._sandhi_splits = [
            (re.compile(p, re.UNICODE), r) for p, r in SANDHI_SPLITS
        ]
        self._vibhakti_fixes = [
            (re.compile(p, re.UNICODE), r) for p, r in VIBHAKTI_FIXES
        ]
        self._agreement_fixes = [
            (re.compile(p, re.UNICODE), r) for p, r in AGREEMENT_FIXES
        ]
        self._word_order_fixes = [
            (re.compile(p, re.UNICODE), r) for p, r in WORD_ORDER_FIXES
        ]
        self._honorific_norms = [
            (re.compile(p, re.UNICODE), r) for p, r in HONORIFIC_NORMALIZATIONS
        ]

    def process(self, text: str) -> str:
        """Full grammar processing pipeline.

        Order matters — each step builds on the previous:
        1. Extract & clean (remove junk)
        2. Fix spelling
        3. Expand sandhi contractions
        4. Fix vibhakti (case markers)
        5. Fix gender/number agreement
        6. Fix word order
        7. Normalize honorifics & colloquialisms
        8. Remove repetitions
        9. Insert clause commas
        10. Restore missing punctuation
        """
        if not text or not text.strip():
            return text or ''

        original = text
        try:
            # Step 1: Extract & clean
            text = extract_and_clean(text)

            # Step 2: Spelling corrections (dictionary lookup)
            text = self._fix_spelling(text)

            # Step 3: Spelling patterns (regex-based)
            for pattern, repl in self._spelling_patterns:
                text = pattern.sub(repl, text)

            # Step 4: Sandhi expansion
            for pattern, repl in self._sandhi_splits:
                text = pattern.sub(repl, text)

            # Step 5: Vibhakti fixes
            for pattern, repl in self._vibhakti_fixes:
                text = pattern.sub(repl, text)

            # Step 6: Gender/number agreement
            for pattern, repl in self._agreement_fixes:
                text = pattern.sub(repl, text)

            # Step 7: Word order
            for pattern, repl in self._word_order_fixes:
                text = pattern.sub(repl, text)

            # Step 8: Honorifics & colloquial → formal
            for pattern, repl in self._honorific_norms:
                text = pattern.sub(repl, text)

            # Step 9: Remove repeated words
            text = remove_repetitions(text)

            # Step 10: Insert commas at clause boundaries
            text = insert_clause_commas(text)

            # Step 11: Restore missing punctuation
            text = restore_punctuation(text)

            # Final whitespace cleanup
            text = re.sub(r' +', ' ', text)
            text = text.strip()

            logger.debug(f"Grammar engine: {len(original)}→{len(text)} chars, "
                         f"changes={'YES' if text != original else 'NO'}")
            return text

        except Exception as e:
            logger.error(f"Grammar processing error: {e}", exc_info=True)
            return original  # return original on error

    def _fix_spelling(self, text: str) -> str:
        """Apply dictionary-based spelling corrections.

        Uses Devanagari-safe word matching to avoid corrupting substrings.

        NOTE: Python's \\b is BROKEN for Devanagari — the halant (\u094D) and
        matras are not \\w, so \\b fires inside conjuncts/syllables. This caused
        'प्रत्यक्ष' → 'प्रत्येक्ष' because \\b matched between क and ्ष.

        Fix: Use space/punctuation boundaries instead of \\b.
        """
        # Sort by length (longest first) to avoid partial replacements
        sorted_corrections = sorted(
            SPELLING_CORRECTIONS.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        # Devanagari-safe word boundary: space, start/end, or punctuation
        # This avoids matching inside conjuncts where \b would falsely trigger
        _WB_BEFORE = r'(?<=\s)|(?<=^)|(?<=[।॥,;:!?.\-\"\'])|(?<=\()'
        _WB_AFTER = r'(?=\s|$|[।॥,;:!?.\-\"\'\)])'

        for wrong, correct in sorted_corrections:
            if wrong == correct:
                continue  # skip protection entries
            # Space-based word boundary match
            pattern = re.compile(
                r'(?:(?<=\s)|(?<=^)|(?<=[।॥,;:!?.\-\"\'\(]))' +
                re.escape(wrong) +
                r'(?=\s|$|[।॥,;:!?.\-\"\'\)])',
                re.UNICODE | re.MULTILINE
            )
            text = pattern.sub(correct, text)

        return text
