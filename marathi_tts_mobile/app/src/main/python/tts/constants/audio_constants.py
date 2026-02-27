"""
Audio & Prosody Constants
=========================
Pause types, prosody patterns (conjunctions, clause starters, vocatives),
emphasis markers, and sentence/internal punctuation maps.

Imports:
    from tts.constants.audio_constants import (
        PauseType, CONJUNCTIONS, CLAUSE_STARTERS, VOCATIVES,
        QUOTE_VERBS, EMPHASIS_WORDS, SENTENCE_ENDINGS,
        INTERNAL_PUNCTUATION,
    )
"""
from enum import IntEnum
from typing import Dict, Set


# ═══════════════════════════════════════════════════════════════════════════
# PAUSE TYPES — calibrated for natural Marathi speech
# ═══════════════════════════════════════════════════════════════════════════

class PauseType(IntEnum):
    """Pause durations in milliseconds."""
    NONE         = 0
    MICRO        = 80       # Between closely connected words
    COMMA        = 180      # Comma or light enumeration
    CONJUNCTION  = 250      # आणि, किंवा, पण
    CLAUSE       = 350      # Subordinate clause boundary
    SEMICOLON    = 400      # ;  :
    SENTENCE     = 550      # ।  .
    QUESTION     = 600      # ?
    EXCLAMATION  = 500      # !
    DOUBLE_DANDA = 700      # ॥  (verse/stanza end)
    VERSE_HALF   = 500      # ।  within a verse (half-verse breath)
    VERSE_FULL   = 900      # ॥  at verse end (full verse pause)
    VERSE_STANZA = 1400     # Between stanzas/sections of verses
    PARAGRAPH    = 900      # Paragraph break
    SECTION      = 1200     # Section/heading transition


# Minimum number of ॥-terminated lines to trigger verse/recitation mode
VERSE_MIN_LINES = 2


# ═══════════════════════════════════════════════════════════════════════════
# CONJUNCTIONS — pause BEFORE these words
# ═══════════════════════════════════════════════════════════════════════════

CONJUNCTIONS: Dict[str, PauseType] = {
    'आणि': PauseType.CONJUNCTION,
    'व': PauseType.COMMA,
    'तसेच': PauseType.CONJUNCTION,
    'पण': PauseType.CONJUNCTION,
    'परंतु': PauseType.CLAUSE,
    'मात्र': PauseType.CONJUNCTION,
    'तथापि': PauseType.CLAUSE,
    'किंवा': PauseType.CONJUNCTION,
    'अथवा': PauseType.CONJUNCTION,
    'म्हणून': PauseType.CONJUNCTION,
    'त्यामुळे': PauseType.CONJUNCTION,
    'कारण': PauseType.CONJUNCTION,
    'जेणेकरून': PauseType.CONJUNCTION,
    'तरीही': PauseType.CONJUNCTION,
    'तरीसुद्धा': PauseType.CONJUNCTION,
    'शिवाय': PauseType.CONJUNCTION,
    'याशिवाय': PauseType.CONJUNCTION,
    'अर्थात': PauseType.CONJUNCTION,
    'उलट': PauseType.CONJUNCTION,
}


# ═══════════════════════════════════════════════════════════════════════════
# CLAUSE STARTERS — pause before and slightly after
# ═══════════════════════════════════════════════════════════════════════════

CLAUSE_STARTERS: Dict[str, PauseType] = {
    'जर': PauseType.CLAUSE,
    'तर': PauseType.CLAUSE,
    'जेव्हा': PauseType.CLAUSE,
    'तेव्हा': PauseType.CLAUSE,
    'जसे': PauseType.COMMA,
    'तसे': PauseType.COMMA,
    'जरी': PauseType.CLAUSE,
    'कारण': PauseType.CLAUSE,
    'म्हणजे': PauseType.CONJUNCTION,
    'ज्यावेळी': PauseType.CLAUSE,
    'त्यावेळी': PauseType.CLAUSE,
    'जोपर्यंत': PauseType.CLAUSE,
    'तोपर्यंत': PauseType.CLAUSE,
    'जिथे': PauseType.CLAUSE,
    'तिथे': PauseType.CLAUSE,
    'जसजसे': PauseType.CLAUSE,
    'तसतसे': PauseType.CLAUSE,
}


# ═══════════════════════════════════════════════════════════════════════════
# VOCATIVES — pause after address markers
# ═══════════════════════════════════════════════════════════════════════════

VOCATIVES: Set[str] = {
    'हे', 'अहो', 'अरे', 'बाबा', 'आई', 'देवा', 'भगवंता',
    'गुरुदेवा', 'महाराज', 'साहेब', 'मित्रांनो', 'बंधूंनो',
    'भाविकांनो', 'श्रोत्यांनो', 'वाचकांनो',
}


# ═══════════════════════════════════════════════════════════════════════════
# QUOTE VERBS — pause before quotation
# ═══════════════════════════════════════════════════════════════════════════

QUOTE_VERBS: Set[str] = {
    'म्हणाला', 'म्हणाली', 'म्हणाले', 'बोलला', 'बोलली',
    'सांगितले', 'विचारले', 'उत्तरले', 'ओरडला', 'ओरडली',
}


# ═══════════════════════════════════════════════════════════════════════════
# EMPHASIS WORDS — slow down & increase volume
# ═══════════════════════════════════════════════════════════════════════════

EMPHASIS_WORDS: Set[str] = {
    'अत्यंत', 'अतिशय', 'खरोखर', 'खूपच', 'नक्कीच', 'निश्चितच',
    'अगदी', 'मुळीच', 'कधीच', 'केवळ', 'फक्त', 'सर्वात',
    'अतिप्रचंड', 'महत्त्वाचे', 'विशेष',
}


# ═══════════════════════════════════════════════════════════════════════════
# PUNCTUATION → PAUSE MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════

SENTENCE_ENDINGS: Dict[str, PauseType] = {
    '।': PauseType.SENTENCE,
    '॥': PauseType.DOUBLE_DANDA,
    '.': PauseType.SENTENCE,
    '?': PauseType.QUESTION,
    '!': PauseType.EXCLAMATION,
    '…': PauseType.SENTENCE,
}

INTERNAL_PUNCTUATION: Dict[str, PauseType] = {
    ',': PauseType.COMMA,
    ';': PauseType.SEMICOLON,
    ':': PauseType.SEMICOLON,
    '—': PauseType.CLAUSE,
    '–': PauseType.CLAUSE,
    '-': PauseType.MICRO,
}
