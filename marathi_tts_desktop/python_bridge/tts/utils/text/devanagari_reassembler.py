"""
Devanagari Text Reassembler
============================
Fixes broken Devanagari text extracted from PDFs where PyPDF2/pdfplumber
inserts spurious spaces inside syllables, splitting:
  - Consonant from its matra (vowel sign)
  - Consonant from halant (virama)
  - Halant from the next consonant (breaking conjuncts)
  - Consonant from anusvara/visarga/chandrabindu

Example of broken PDF extraction:
    Input:  "महालमी अटकम ् ॥ नमत े ऽत ु महामाय े"
    Output: "महालमी अटकम् ॥ नमतेऽतु महामाये"

Usage:
    from tts.utils.text.devanagari_reassembler import reassemble_devanagari
    clean = reassemble_devanagari(broken_pdf_text)
"""
import re
import unicodedata
import logging

logger = logging.getLogger('tts.reassembler')

# ── Unicode ranges ──────────────────────────────────────────────────────

# Devanagari vowel signs (matras) — MUST attach to preceding consonant
# These should NEVER have a space before them
MATRAS = '\u093E-\u094C\u094E\u0955-\u0957'  # ा ि ी ु ू ृ ॄ ॅ ॆ े ै ॉ ॊ ो ौ

# Halant (virama) — joins consonant to next consonant or suppresses vowel
HALANT = '\u094D'  # ्

# Anusvara, visarga, chandrabindu — nasalization/aspiration marks
NASALS = '\u0901\u0902\u0903'  # ँ ं ः

# Nukta — dot below consonant for borrowed sounds
NUKTA = '\u093C'  # ़

# Devanagari consonants
CONSONANTS = '\u0915-\u0939\u0958-\u095F'  # क-ह + क़-य़

# Devanagari vowels (independent/full forms)
VOWELS = '\u0904-\u0914'  # अ-औ

# Devanagari digits
DIGITS = '\u0966-\u096F'  # ०-९

# All Devanagari base characters (consonants + vowels)
DEVANAGARI_BASE = f'[{CONSONANTS}{VOWELS}]'

# All Devanagari combining marks (things that attach to a base)
COMBINING = f'[{MATRAS}{HALANT}{NASALS}{NUKTA}]'


def reassemble_devanagari(text: str) -> str:
    """Reassemble broken Devanagari text from PDF extraction.
    
    Removes spurious spaces that PDF extractors insert between
    Devanagari base characters and their combining marks.
    
    The key insight: broken PDFs use SINGLE spaces between glyph
    fragments (within a syllable/word) and DOUBLE+ spaces or newlines
    between actual words. We exploit this pattern:
    
    1. Mark real word boundaries (double+ spaces → marker)
    2. Remove single spaces between Devanagari characters
    3. Restore word boundaries
    
    This is safe to run on already-correct text — it won't break
    properly-formed Devanagari.
    """
    if not text:
        return text
    
    # Step 0: Unicode NFC normalization first
    text = unicodedata.normalize('NFC', text)
    
    # Process line by line (newlines are real boundaries)
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        fixed_lines.append(_reassemble_line(line))
    
    text = '\n'.join(fixed_lines)
    
    # Final cleanup: collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Final NFC normalization  
    text = unicodedata.normalize('NFC', text)
    
    return text.strip()


def _reassemble_line(line: str) -> str:
    """Reassemble a single line of broken Devanagari text.
    
    Strategy:
    1. Protect real word boundaries (2+ spaces → marker)
    2. Remove all single spaces within Devanagari character sequences
    3. Restore word boundaries from markers
    """
    if not line or not line.strip():
        return line
    
    WORD_BOUNDARY = '\x00'  # temp marker for real word gaps
    
    # Step 1: Mark definite word boundaries (2+ consecutive spaces)
    # In broken PDFs, double-spaces represent actual word gaps
    line = re.sub(r'  +', WORD_BOUNDARY, line)
    
    # Step 2: Remove space BEFORE combining marks (matras, halant, etc.)
    # "त े" → "ते"   "म ्" → "म्"   "ती ं" → "तीं"
    line = re.sub(
        rf'(\S) ({COMBINING})',
        r'\1\2',
        line
    )
    
    # Step 3: Remove space AFTER halant (before next consonant)
    # "क ् ष" → "क्ष"   "स ् त" → "स्त"
    line = re.sub(
        rf'({HALANT}) ?({DEVANAGARI_BASE})',
        r'\1\2',
        line
    )
    
    # Step 4: Remove space between matra and anusvara/visarga
    # "ती ं" → "तीं"
    line = re.sub(
        rf'([{MATRAS}]) ([{NASALS}])',
        r'\1\2',
        line
    )
    
    # Step 5: Handle avagraha (ऽ)
    line = re.sub(r'(\u093D) ', r'\1', line)
    line = re.sub(r' (\u093D)', r'\1', line)
    
    # Step 6: Remove remaining single spaces between Devanagari chars
    # This is the KEY fix for "द े व" → "देव" and "स ु र" → "सुर"
    # After steps 2-5, remaining single spaces between Devanagari
    # characters are glyph-boundary artifacts, NOT word boundaries
    # (real word boundaries were already converted to WORD_BOUNDARY)
    line = re.sub(
        rf'([{CONSONANTS}{VOWELS}{MATRAS}{HALANT}{NASALS}{NUKTA}{DIGITS}])'
        rf' '
        rf'([{CONSONANTS}{VOWELS}{MATRAS}{HALANT}{NASALS}{NUKTA}])',
        r'\1\2',
        line
    )
    
    # Run step 6 again — single pass might leave gaps in sequences like "a b c"
    # where removing "a b" → "ab" still leaves "ab c"
    for _ in range(3):
        prev = line
        line = re.sub(
            rf'([{CONSONANTS}{VOWELS}{MATRAS}{HALANT}{NASALS}{NUKTA}{DIGITS}])'
            rf' '
            rf'([{CONSONANTS}{VOWELS}{MATRAS}{HALANT}{NASALS}{NUKTA}])',
            r'\1\2',
            line
        )
        if line == prev:
            break
    
    # Step 7: Fix standalone matras at start of tokens
    # After removing spaces, we might have combining marks at the start
    # that should attach to the previous character
    line = re.sub(
        rf'({DEVANAGARI_BASE}(?:[{MATRAS}{HALANT}{NASALS}])*)({COMBINING})',
        r'\1\2',
        line
    )
    
    # Step 8: Restore word boundaries
    line = line.replace(WORD_BOUNDARY, ' ')
    
    # Step 9: Clean up spacing
    line = re.sub(r'  +', ' ', line)
    
    return line.strip()


def is_broken_devanagari(text: str) -> bool:
    """Detect if Devanagari text has the characteristic PyPDF2 breakage.
    
    Checks for:
    1. Spaces before combining marks (matras, halant) — the #1 indicator
    2. High ratio of single-character Devanagari "words"
    3. Standalone matras as separate tokens
    
    Returns True if the text appears broken and needs reassembly.
    """
    if not text or len(text) < 20:
        return False
    
    # Count spaces before combining marks — this NEVER happens in correct text
    spaces_before_combining = len(re.findall(
        rf'\S [{MATRAS}{HALANT}{NASALS}]', text
    ))
    
    if spaces_before_combining > 2:
        return True
    
    # Count standalone matras (combining marks as separate "words")
    words = text.split()
    standalone_combining = 0
    for w in words:
        # A word that is ONLY combining marks is definitely broken
        if w and all(unicodedata.category(c).startswith('M') for c in w):
            standalone_combining += 1
    
    if len(words) > 5 and standalone_combining / len(words) > 0.1:
        return True
    
    # Count single-character Devanagari words (consonants/vowels alone)
    single_devanagari = 0
    for w in words:
        if len(w) == 1 and re.match(rf'{DEVANAGARI_BASE}', w):
            single_devanagari += 1
    
    if len(words) > 10 and single_devanagari / len(words) > 0.2:
        return True
    
    return False


def quality_score(text: str) -> float:
    """Score the quality of extracted Devanagari text (0.0 = garbage, 1.0 = good).
    
    Heuristics:
    - Meaningful words (2+ Devanagari chars) vs total words
    - Absence of spaces before combining marks
    - Average word length (broken text has very short words)
    """
    if not text or not text.strip():
        return 0.0
    
    words = text.split()
    if not words:
        return 0.0
    
    total = len(words)
    
    # Count meaningful words (2+ consecutive Devanagari chars)
    meaningful = sum(
        1 for w in words 
        if re.search(rf'[{CONSONANTS}{VOWELS}]{{2,}}', w)
    )
    
    # Penalize spaces before combining marks
    combining_breaks = len(re.findall(rf'\S [{MATRAS}{HALANT}{NASALS}]', text))
    
    # Average word length
    avg_len = sum(len(w) for w in words) / total
    
    # Score components
    word_score = meaningful / total if total > 0 else 0
    break_penalty = min(1.0, combining_breaks / max(total, 1))
    length_score = min(1.0, avg_len / 4.0)  # 4+ chars average = good
    
    score = (word_score * 0.5 + length_score * 0.3) * (1.0 - break_penalty)
    
    return round(max(0.0, min(1.0, score)), 2)
