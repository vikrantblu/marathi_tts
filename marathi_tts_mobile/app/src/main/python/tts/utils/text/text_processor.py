import re
import unicodedata
import logging
from typing import List, Dict, Any, Optional
# transformers is imported lazily inside MarathiTextCorrector to avoid
# loading the entire Hugging Face library at module import time.
import pickle
import os
from pathlib import Path
import indic_transliteration.sanscript as sanscript # type: ignore
from indicnlp.normalize.indic_normalize import IndicNormalizerFactory # type: ignore
from .script_converter import modi_to_devanagari
from tts.constants.text_constants import (
    ABBREVIATIONS, SPECIAL_CHARS, PRONUNCIATION_FIXES,
)
from tts.constants.script_constants import SCRIPT_RANGES
try:
    from tts.utils.phonetic.marathi_phonetics import (
        apply_sanskrit_phonetics,
        apply_marathi_phonetics,
    )
except ImportError:
    def apply_sanskrit_phonetics(t): return t
    def apply_marathi_phonetics(t): return t
# Standalone: resolve BASE_DIR without Django
import os as _os
_BASE_DIR = _os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..", "..")),
)


logger = logging.getLogger('tts.text')

class TextProcessor:
    """Unified text processing for TTS"""
    
    def __init__(self):
        # Initialize normalizer
        self.normalizer = IndicNormalizerFactory().get_normalizer('mr')
        self.supported_langs = {'mr', 'hi', 'sa', 'en'}
        
        # Define abbreviations — use centralized constants
        self.abbreviations = dict(ABBREVIATIONS)
        
        # Define special character replacements — use centralized constants
        self.special_chars = dict(SPECIAL_CHARS)
        # Add a few extras that TextProcessor-specific code needs
        self.special_chars.update({
            'स्वतः': 'स्वताहा',
        })
        
        # Define pronunciation fixes — use centralized constants
        # The destructive conjunct-stripping patterns have been removed
        # from PRONUNCIATION_FIXES; the G2P engine handles those now.
        self.pronunciation_fixes = dict(PRONUNCIATION_FIXES)

    def process_text(self, text: str, lang: str = 'mr') -> str:
        """Main text processing pipeline"""
        if not text:
            return ""
            
        try:
            # 1. Basic validation
            if lang not in self.supported_langs:
                logger.warning(f"Unsupported language: {lang}. Defaulting to Marathi (mr)")
                lang = 'mr'
            
            # 2. Script conversion if needed
            if self._detect_script(text) == 'modi':
                text = modi_to_devanagari(text)
            
            # 3. Clean and normalize
            text = self._clean_text(text)
            text = self.normalize_text(text)
            
            # 4. Language specific processing
            if lang == 'mr':
                text = self._process_marathi(text)
            elif lang == 'hi':
                text = self._process_hindi(text)
            elif lang == 'sa':
                text = self._process_sanskrit(text)
            elif lang == 'en':
                text = self._process_english(text)
            
            # 5. Fix pronunciation
            text = self._fix_pronunciation(text)
            
            # 6. Format text
            text = self._format_text(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error in text processing: {str(e)}")
            return text
    def _process_marathi(self, text: str) -> str:
        """Process Marathi text with special handling for common pronunciation patterns"""
        # Start with basic character replacements
        replacements = {
            'ॅ': 'अॅ',  'ऎ': 'ए',  'ऒ': 'ओ',
            '॰': '.',  '–': '-', 
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Fix common conjunct misspellings (safe — no halant stripping)
        conjunct_fixes = {
            'ध्द': 'द्ध',
        }
        for wrong, right in conjunct_fixes.items():
            text = text.replace(wrong, right)
        
        # NOTE: ZWJ insertion into conjuncts has been REMOVED.
        # The G2P engine (tts.utils.phonetic.g2p_engine) now handles
        # conjunct preservation with proper validation against the
        # VALID_CONJUNCTS table. Adding ZWJ blindly was breaking some
        # conjunct renderings.
        
        # Now fix the णा-या pattern with more direct approach
        # Define ALL Marathi consonants 
        all_consonants = 'कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळक्षज्ञ'
        consonant_class = f'[{all_consonants}]'
        
        # Define all possible suffixes that can follow the -या pattern
        suffix_list = 'ं|ना|च्या|ची|चे|ला|त|स|शी|हून|कडे|साठी|नी|पैकी|ंना|ंनी|ंच्या|नीच|ंनाच|ने|मध्ये|साठी|बरोबर'
        
        # Fix 1: First handle the EXACT case with no suffix (highest priority)
        text = re.sub(
            f'{consonant_class}णा-या\\b',
            lambda m: m.group(0).replace('णा-या', 'णाऱ्या'),
            text
        )
        
        # Fix 2: Then handle the case with suffixes
        text = re.sub(
            f'{consonant_class}णा-या({suffix_list})\\b',
            lambda m: m.group(0).replace('णा-या', 'णाऱ्या'),
            text
        )
        
        # Handle special cases directly
        direct_replacements = {
            'भासणा-या': 'भासणाऱ्या',
            'दिसणा-या': 'दिसणाऱ्या',
            'करणा-या': 'करणाऱ्या',
            'असणा-या': 'असणाऱ्या',
        }
        for old, new in direct_replacements.items():
            text = text.replace(old, new)
        
        # Also handle the pattern without any prefix
        text = re.sub(r'णा-या\b', r'णाऱ्या', text)
        
        # Handle "सा-या", "वा-या", etc. patterns (no suffixes)
        text = re.sub(r'([ाेोिीुूैौं])-या\b', r'\1ऱ्या', text)

        # Handle "सा-या", "वा-या", etc. patterns (with suffixes)
        text = re.sub(r'([ाेोिीुूैौं])-या(' + suffix_list + r')\b', r'\1ऱ्या\2', text)
        
        # Fix conjunct misspelling
        text = re.sub(r'ध्द', 'द्ध', text)
        
        # NOTE: Anusvara and visarga processing has been REMOVED from here.
        # The G2P engine handles these with full context awareness:
        #   - Anusvara: context-dependent assimilation vs nasalization
        #   - Visarga: context-dependent sibilant mapping (श/ष/स)
        # The old rules ('ं([यरलवशषसह])' → 'न् \1') were WRONG for Marathi
        # as they inserted a dental nasal where nasalization was intended.

        # Apply comprehensive Marathi phonetic rules
        text = apply_marathi_phonetics(text)

        return text
    
    def _process_hindi(self, text: str) -> str:
        """Process Hindi text"""
        # Convert common Hindi variations
        replacements = {
            'क़': 'क',   # Simplify nukta characters
            'ख़': 'ख',
            'ग़': 'ग',
            'ज़': 'ज',
            'ड़': 'ड',
            'ढ़': 'ढ',
            'फ़': 'फ'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        return text
    
    def _process_sanskrit(self, text: str) -> str:
        """Process Sanskrit text with full phonetic rules."""
        text = re.sub(r'([०-९])॰', r'\1', text)
        text = apply_sanskrit_phonetics(text)
        return text
    
    def _process_english(self, text: str) -> str:
        """Process English text"""
        # Basic English text normalization
        text = text.lower()  # Convert to lowercase
        text = re.sub(r'[^a-z0-9.,!? ]+', '', text)  # Remove special characters
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        return text
    def _detect_script(self, text: str) -> str:
        """Detect script type"""
        if not text:
            return 'unknown'
            
        if any(any(start <= ord(c) <= end for start, end in SCRIPT_RANGES['MODI']) for c in text):
            return 'modi'
        elif any(any(start <= ord(c) <= end for start, end in SCRIPT_RANGES['DEVANAGARI']) for c in text):
            return 'devanagari'
        return 'unknown'

    def _clean_text(self, text: str) -> str:
        """Clean text of unwanted characters and patterns"""
        # Remove URLs and emails
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove non-printable characters
        text = ''.join(char for char in text if char.isprintable())
        
        return text.strip()

    def _fix_pronunciation(self, text: str) -> str:
        """Apply pronunciation fixes"""
        for pattern, replacement in self.pronunciation_fixes.items():
            text = re.sub(pattern, replacement, text)
        return text

    def _format_text(self, text: str) -> str:
        """Format text for TTS processing"""
        # Handle line breaks
        text = re.sub(r'\s*॥\s*', '॥\n', text)
        text = re.sub(r'\s*।\s*', '।\n', text)
        
        # Add proper spacing
        text = re.sub(r'([^।])\s*\n\s*([^।])', r'\1। \2', text)
        
        # Clean up final text
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text

    def normalize_text(self, text: str) -> str:
        """Normalize text using IndicNLP"""
        if not text:
            return text
            
        try:
            if self.normalizer:
                text = self.normalizer.normalize(text)
            return unicodedata.normalize('NFC', text)
        except Exception as e:
            logger.error(f"Error in normalize_text: {str(e)}")
            return text

    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences with improved handling"""
        if not text:
            return []
            
        # Split on sentence boundaries
        sentences = re.split(r'([।॥.!?])\s*', text)
        
        # Recombine sentences with their punctuation
        result = []
        for i in range(0, len(sentences)-1, 2):
            if i+1 < len(sentences):
                result.append(sentences[i] + sentences[i+1])
            else:
                result.append(sentences[i])
                
        return [s.strip() for s in result if s.strip()]

    def split_into_chunks(self, text: str, target_size: int = 1000) -> List[str]:
        """Split text into manageable chunks for processing"""
        chunks = []
        sentences = self.split_into_sentences(text)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > target_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

class MarathiTextCorrector:
    def __init__(self):
        self.normalizer = IndicNormalizerFactory().get_normalizer('mr')
        self.model_path = os.path.join(_BASE_DIR, 'models', 'marathi_correction')
        
        os.makedirs(os.path.join(_BASE_DIR, 'models', 'marathi_correction'), exist_ok=True)
        os.makedirs(os.path.join(_BASE_DIR, 'data'), exist_ok=True)
        
        # Load the transformer model for Marathi text correction (lazy import)
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM  # type: ignore
            if os.path.exists(self.model_path):
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
            else:
                # Fallback to pretrained Indic model
                self.tokenizer = AutoTokenizer.from_pretrained('ai4bharat/indic-bert')
                self.model = AutoModelForSeq2SeqLM.from_pretrained('ai4bharat/indic-bert')
        except Exception as _e:
            logger.warning("transformers unavailable, correction model disabled: %s", _e)
            self.tokenizer = None
            self.model = None
        
        # Load Marathi word frequency dictionary
        self.word_freq = self._load_word_frequencies()
        
    def _load_word_frequencies(self):
        """Load or create Marathi word frequency dictionary"""
        freq_path = os.path.join(_BASE_DIR, 'data', 'marathi_word_freq.pkl')
        if os.path.exists(freq_path):
            # Use restricted unpickler — only allow builtins (dict, str, int)
            import io
            class _SafeUnpickler(pickle.Unpickler):
                def find_class(self, module, name):
                    if module == 'builtins' and name in ('dict', 'set', 'list', 'str', 'int', 'float', 'tuple', 'bool'):
                        return getattr(__import__('builtins'), name)
                    raise pickle.UnpicklingError(f"Blocked: {module}.{name}")
            with open(freq_path, 'rb') as f:
                return _SafeUnpickler(f).load()
        return {}
        
    def correct_text(self, text: str) -> str:
        """Correct OCR errors in Marathi text using ML model"""
        if not text:
            return text
        if self.tokenizer is None or self.model is None:
            logger.warning("Correction model not loaded; returning original text")
            return text
            
        # First normalize the text
        text = self.normalizer.normalize(text)
        
        # Split into sentences
        sentences = text.split('।')
        corrected_sentences = []
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Tokenize
            inputs = self.tokenizer(sentence, return_tensors="pt", padding=True)
            
            # Generate correction
            outputs = self.model.generate(
                inputs["input_ids"],
                max_length=512,
                num_beams=5,
                early_stopping=True
            )
            
            # Decode
            corrected = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Post-process the correction
            corrected = self._post_process_correction(corrected)
            corrected_sentences.append(corrected)
        
        return '।'.join(corrected_sentences)
        
    def _post_process_correction(self, text: str) -> str:
        """Apply post-processing rules to corrected text"""
        words = text.split()
        corrected_words = []
        
        for word in words:
            if self._is_marathi_word(word):
                # Check if word exists in frequency dictionary
                if word not in self.word_freq:
                    # Find closest matching word
                    closest = self._find_closest_word(word)
                    if closest:
                        word = closest
            corrected_words.append(word)
            
        return ' '.join(corrected_words)
        
    def _is_marathi_word(self, word: str) -> bool:
        """Check if word contains Marathi characters"""
        return bool(re.search(r'[\u0900-\u097F]', word))
        
    def _find_closest_word(self, word: str) -> str:
        """Find closest matching word from frequency dictionary"""
        min_distance = float('inf')
        closest_word = word
        
        # Only check words with similar length to improve performance
        length_diff = 2
        candidates = [w for w in self.word_freq 
                     if abs(len(w) - len(word)) <= length_diff]
        
        for candidate in candidates:
            distance = self._levenshtein_distance(word, candidate)
            
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


def clean_web_text(text: str) -> str:
    """Light cleaning for web-extracted text (URL fetch pipeline).
    
    Only removes noise (URLs, emails, garbage) and normalizes whitespace.
    Does NOT transform the text — no abbreviation expansion, no visarga
    replacement, no verse number stripping. Preserves the original content
    faithfully for display.
    """
    if not text:
        return text

    try:
        # 1. Unicode normalization
        text = unicodedata.normalize('NFC', text)

        # 2. Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 3. Remove URLs and emails
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)

        # 4. Strip OCR garbage segments (needs paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = strip_ocr_garbage(text)

        # 5. Remove blank lines but keep paragraph breaks
        lines = []
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
            elif lines and lines[-1] != '':
                lines.append('')  # preserve single blank line as paragraph break
        text = '\n'.join(lines)

        # 6. Collapse excessive whitespace within lines (but keep newlines)
        text = re.sub(r'[ \t]+', ' ', text)

        # 7. Final trim
        text = text.strip()

        return text

    except Exception as e:
        logger.error(f"Error in clean_web_text: {str(e)}")
        return text


def clean_text(text: str) -> str:
    
    if not text:
        return text

    try:
        # 2. Script conversion for Modi
        if detect_script(text):
            text = modi_to_devanagari(text)

        # 3. Protect time formats and numbers
        text = re.sub(r'(\d+)\.(\d+)', r'\1__DOT__\2', text)

        # 4. Remove unwanted content
        text = re.sub(r'http[s]?://\S+', '', text)  # URLs
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)  # Emails

        # 5. Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 6. Process line by line
        lines = []
        for line in text.split('\n'):
            # Remove verse numbers
            line = re.sub(r'^\s*\d+\s*', '', line)
            line = re.sub(r'\s*\d+\\s*$', '', line)
            
            if line.strip():
                # Replace abbreviations (from centralized constants)
                for abbr, full in ABBREVIATIONS.items():
                    line = line.replace(abbr, full)
                lines.append(line.strip())

        # 7. Join lines and normalize spaces
        text = '\n'.join(lines)
        text = re.sub(r'\s+', ' ', text)

        # 8. Replace special characters (from centralized constants)
        for old, new in SPECIAL_CHARS.items():
            text = text.replace(old, new)

        # 9. Handle punctuation and pauses
        text = re.sub(r'\s*॥\s*', '॥\n', text)  # Double danda
        text = re.sub(r'\s*।\s*', '।\n', text)  # Single danda
        text = re.sub(r'\s*,\s*', ', ', text)   # Comma

        # 10. Restore time formats
        text = text.replace('__DOT__', '.')

        # 11. Strip OCR garbage segments BEFORE collapsing newlines
        # (strip_ocr_garbage needs paragraph breaks to identify garbage blocks)
        text = re.sub(r'\n{3,}', '\n\n', text)  # Normalize to max 2 newlines
        text = strip_ocr_garbage(text)

        # 12. Final cleanup
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
        text = text.strip()

        # 13. Unicode normalization
        text = unicodedata.normalize('NFC', text)

        return text

    except Exception as e:
        logger.error(f"Error in clean_text: {str(e)}")
        return text

# Supporting functions
def detect_script(text):
    """Check if text contains Modi script characters"""
    if not text:
        return False
    return any(
        any(start <= ord(c) <= end for start, end in SCRIPT_RANGES['MODI'])
        for c in text
    )

def is_devnagari_text(text):
    """Check if text contains Devanagari/Sanskrit characters"""
    if not text:
        return False
    return any(
        any(start <= ord(c) <= end for start, end in SCRIPT_RANGES['DEVANAGARI'])
        for c in text
    )
# Add this function to fix text formatting issues
def clean_text_format(text):
    """Clean and format text to fix line break and punctuation issues."""
    import re
    
    # First normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Protect time formats first (both Marathi and English numbers)
    def protect_time(match):
        num1, num2 = match.groups()
        return f"{num1.strip()}__TIME_DOT__{num2.strip()}"
    
    # Protect patterns
    text = re.sub(r'([०-९\d]+)\s*\.\s*([०-९\d]+)', protect_time, text)  # Time formats
    text = re.sub(r'([प-ह])\.([प-ह])\.', r'\1__DOT__\2__DOT__', text)  # Abbreviations
    
    # Process paragraphs
    paragraphs = []
    current_para = []
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            if current_para:
                # Join sentences in paragraph properly
                paragraph = ' '.join(current_para)
                # Remove any automatic danda additions
                paragraph = re.sub(r'\s*।\s*(?=\S)', ' ', paragraph)
                paragraphs.append(paragraph)
                current_para = []
            continue
        current_para.append(line)
    
    if current_para:
        paragraph = ' '.join(current_para)
        paragraph = re.sub(r'\s*।\s*(?=\S)', ' ', paragraph)
        paragraphs.append(paragraph)
    
    # Join paragraphs with proper spacing
    text = '\n\n'.join(paragraphs)
    
    # Clean up spaces and restore protected patterns
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
    text = text.replace('__TIME_DOT__', '.')  # Restore time dots
    text = text.replace('__DOT__', '.')  # Restore abbreviation dots
    
    return text.strip()

def is_marathi_text(text: str) -> bool:
    """
    Check if the text contains Marathi characters.
    
    Args:
        text (str): Text to check
        
    Returns:
        bool: True if text contains Marathi characters
    """
    if not text:
        return False
        
    # Devanagari Unicode range
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    return bool(devanagari_pattern.search(text))


def is_ocr_garbage(text: str, min_word_ratio: float = 0.3) -> bool:
    """
    Detect if text is likely OCR garbage rather than meaningful Marathi content.
    Returns True if the text appears to be garbage/noise.
    """
    if not text or not text.strip():
        return True
    
    text = text.strip()
    
    # Count different character types
    total_chars = len(text)
    if total_chars < 5:
        return True
    
    # Devanagari LETTERS only (exclude digits U+0966-U+096F)
    devanagari_letters = len(re.findall(r'[\u0900-\u0965\u0970-\u097F]', text))
    devanagari_digits = len(re.findall(r'[\u0966-\u096F]', text))
    ascii_digits = len(re.findall(r'[0-9]', text))
    punctuation_symbols = len(re.findall(r'[|{}\[\]\\^~@#$%&*<>()\u00a6\u00a3\u20ac\u00a5+=\u00a4]', text))
    spaces = len(re.findall(r'\s', text))
    
    non_space_chars = total_chars - spaces
    if non_space_chars == 0:
        return True
    
    # If Devanagari LETTERS make up less than 30% of non-space characters, it's garbage
    letter_ratio = devanagari_letters / non_space_chars
    if letter_ratio < min_word_ratio:
        return True
    
    # If punctuation/symbols make up more than 20% of non-space chars, it's garbage
    symbol_ratio = punctuation_symbols / non_space_chars
    if symbol_ratio > 0.20:
        return True
    
    # If digits (Devanagari + ASCII) exceed Devanagari letters, likely garbage
    all_digits = devanagari_digits + ascii_digits
    if all_digits > devanagari_letters and all_digits > 3:
        return True
    
    # Check for meaningful words: words with 2+ consecutive Devanagari letters
    words = text.split()
    meaningful_words = 0
    for word in words:
        if re.search(r'[\u0900-\u0965\u0970-\u097F]{2,}', word):
            meaningful_words += 1
    
    if len(words) > 3 and meaningful_words / len(words) < 0.3:
        return True
    
    # If text is mostly single characters separated by spaces/pipes, it's garbage
    single_char_segments = len(re.findall(r'(?:^|\s)[^\s](?:\s|$)', text))
    if len(words) > 5 and single_char_segments / len(words) > 0.4:
        return True
    
    return False


def strip_ocr_garbage(text: str) -> str:
    """
    Remove OCR garbage portions from text while preserving good content.
    Splits text into segments and removes segments that look like garbage.
    """
    if not text:
        return text
    
    # Split into paragraphs/segments
    segments = re.split(r'\n\n+', text)
    clean_segments = []
    
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        
        # Check if this segment is garbage
        if is_ocr_garbage(segment):
            logger.debug(f"Stripped OCR garbage segment: {segment[:80]}...")
            continue
        
        # Also check sentence-level within a segment for trailing garbage
        # Split by sentence endings and check the last portion
        sentences = re.split(r'(?<=[।॥.!?])\s*', segment)
        clean_sentences = []
        for sentence in sentences:
            if sentence.strip() and not is_ocr_garbage(sentence.strip()):
                clean_sentences.append(sentence.strip())
        
        if clean_sentences:
            clean_segments.append(' '.join(clean_sentences))
    
    return '\n\n'.join(clean_segments)

def preprocess_marathi_text(text):
    """Comprehensive Marathi pronunciation correction"""
    # Log original text
    logger.debug(f"Original text: {text}")
    
    # 1. Create a comprehensive suffix list to handle all cases
    suffixes = r'(|ं|ना|च्या|ची|चे|ला|त|स|शी|हून|कडे|साठी|नी|पैकी|ंना|ंनी|ंच्या|नीच|ंनाच|ने|मध्ये|बरोबर|वर|तून|मुळे|पर्यंत|विना|पासून|द्वारे|सह|वाचून|समोर|मागे|खाली|वरून|खालून|बाहेर|आत|पलीकडे|सोबत|विषयी|मार्फत|पाशी)'
    
    # 2. First handle exact matches for the most common problematic words with their full suffix forms
    common_replacements = [
        # Most common words first - use raw strings and word boundaries
        (r'\bभासणा-या' + suffixes + r'\b', r'भासणाऱ्या\1'),
        (r'\bदिसणा-या' + suffixes + r'\b', r'दिसणाऱ्या\1'),
        (r'\bकरणा-या' + suffixes + r'\b', r'करणाऱ्या\1'),
        (r'\bअसणा-या' + suffixes + r'\b', r'असणाऱ्या\1'),
        (r'\bवाहणा-या' + suffixes + r'\b', r'वाहणाऱ्या\1'),
        (r'\bबोलणा-या' + suffixes + r'\b', r'बोलणाऱ्या\1'),
        (r'\bमिळणा-या' + suffixes + r'\b', r'मिळणाऱ्या\1'),
        (r'\bमिळणा-या' + suffixes + r'\b', r'मिळणाऱ्या\1'),
        (r'\bचालणा-या' + suffixes + r'\b', r'चालणाऱ्या\1'),
        (r'\bपडणा-या' + suffixes + r'\b', r'पडणाऱ्या\1'),
        (r'\bयेणा-या' + suffixes + r'\b', r'येणाऱ्या\1'),
        (r'\bजाणा-या' + suffixes + r'\b', r'जाणाऱ्या\1'),
        
        # Common conjunct fixes
        (r'\bबुध्दी\b', 'बुद्धी'),
        (r'\bबुध्द\b', 'बुद्ध'),
        (r'\bशुध्द\b', 'शुद्ध'),
        (r'\bविद्ध्यार्थी\b', 'विद्यार्थी'),
        (r'\bआश्चिर्य\b', 'आश्चर्य'),
    ]
    
    # Apply exact match replacements first
    for pattern, replacement in common_replacements:
        text = re.sub(pattern, replacement, text)
    
    # 3. Now handle more general patterns - using a more inclusive set of consonants
    all_consonants = r'[कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळक्षज्ञ]'
    
    # Apply more general rules
    general_patterns = [
        # More general णा-या rule
        (f'{all_consonants}णा-या{suffixes}\\b', lambda m: m.group(0).replace('णा-या', 'णाऱ्या')),
        
        # Very general pattern for any character followed by णा-या
        (r'([^\s])णा-या' + suffixes + r'\b', r'\1णाऱ्या\2'),
        
        # Handle other common variations
        (r'सा-या' + suffixes + r'\b', r'साऱ्या\1'),
        (r'वा-या' + suffixes + r'\b', r'वाऱ्या\1'),
        
        # General vowel followed by -या rule (lowest priority)
        (r'([ाेोिीुूैौं])-या' + suffixes + r'\b', r'\1ऱ्या\2'),
        
        # Fix ध्द -> द्ध without affecting other patterns
        (r'ध्द', 'द्ध'),
        
        # Fixed incorrect nasalization handling
        (r'([^ा])णीं\b', r'\1णी'),  # Fix unwanted nasalization at word endings
        (r'([^नां])ीं\b', r'\1ी'),   # Fix other nasalization cases
        (r'ं([यरलवशषसह])', r'न् \1')  # Better handling of anusvar before certain consonants
    ]
    
    # Apply general patterns
    for pattern, replacement in general_patterns:
        text = re.sub(pattern, replacement, text)
    
    # 4. Extra fixes for visarga and nasalization
    text = re.sub(r'ः([यरलवशषसह])', r'ह \1', text)  # Fix visarga before certain consonants
    text = re.sub(r'ं([यरलवशषसह])', r'न् \1', text)  # Fix anusvar before certain consonants
    
    # 5. Special fix for णीं issues (but preserve words with ांनी)
    text = re.sub(r'([^ा])णीं\b', r'\1णी', text)  # Fix unwanted nasalization
    text = re.sub(r'([^नां])ीं\b', r'\1ी', text)  # Fix other nasalization cases
    
    logger.debug(f"Processed text: {text}")
    return text

