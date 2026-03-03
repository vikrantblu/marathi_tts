import re
import logging
import unicodedata
try:
    from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
except ImportError:
    IndicNormalizerFactory = None
from .number_to_words import normalize_numbers_for_tts
from tts.constants.text_constants import (
    ABBREVIATIONS, SPECIAL_CHARS, VISARGA_WORDS
)

logger = logging.getLogger(__name__)

class MarathiTextNormalizer:
    """Normalizes Marathi text for various purposes including TTS"""
    
    def __init__(self):
        """Initialize the normalizer"""
        self.indic_normalizer = None
        if IndicNormalizerFactory is not None:
            try:
                self.indic_normalizer = IndicNormalizerFactory().get_normalizer("mr")
                logger.info("Indic normalizer initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing indic normalizer: {str(e)}")

    def normalize_text(self, text: str) -> str:
        """Normalize special Sanskrit/Marathi characters for TTS"""
        if not text:
            return text
            
        try:
            # Apply indic normalization first if available
            if self.indic_normalizer:
                text = self.indic_normalizer.normalize(text)
            
            # Protect time format dots
            text = re.sub(r'(\d)\.(\d)', r'\1__DOT__\2', text)
            
            # Context-aware abbreviation: इ. before a number → इसवी सन
            # (standalone इ. at end of sentence means इत्यादी, handled by ABBREVIATIONS)
            text = re.sub(r'इ\.\s*(?=[०-९\d])', 'इसवी सन ', text)
            
            # Replace HTML tags with newlines
            text = re.sub(r'</(p|div|br|h[1-6])>', '\n', text, flags=re.I)
            
            # Strip verse numbers after dandas: ॥ 1 ॥, ॥१२॥, ॥ ३ ॥ etc.
            # Keep only the closing ॥ (the number is just a verse count)
            text = re.sub(r'॥\s*[0-9०-९]+\s*॥', '॥', text)
            # Also strip standalone numbers at line ends before ॥
            text = re.sub(r'\s+[0-9०-९]+\s*॥', ' ॥', text)
            # Strip standalone numbers at line ends (verse numbering)
            text = re.sub(r'\s+[0-9०-९]+\s*$', '', text, flags=re.MULTILINE)
            
            # Handle hyphens in Marathi words that represent eyelash-ra (ऱ्)
            # क-हा, क-हे, टाळक-या → कऱ्हा, कऱ्हे, टाळकऱ्या
            text = re.sub(r'(\u0915)-(\u0939)', r'\1\u0931\u094d\2', text)  # क-ह → कऱ्ह
            text = re.sub(r'([कखगघटठडढणतथदधनपफबभमयरलवशषसह])-([रलवशषसह])',
                         lambda m: m.group(1) + 'ऱ्' + m.group(2), text)
            # Note: -य excluded from second pattern because ऱ्य is converted to र्य 
            # by the conjunct fix below. The क-ह pattern handles the main eyelash-ra case.
            
            # Common replacements with better pause handling
            # Use centralized constants — do NOT duplicate here
            replacements = {}
            
            # Special characters (from centralized constants)
            replacements.update(SPECIAL_CHARS)
            
            # NOTE: VISARGA_WORDS intentionally NOT applied here.
            # The G2P engine (g2p_engine._process_visarga) handles visarga
            # with full context awareness using VISARGA_EXCEPTIONS from
            # g2p_constants.py.  Applying VISARGA_WORDS here would cause
            # double-processing of words like दुःख, नमः, स्वतः.
            
            # Conjunct fix
            replacements['ऱ्य'] = 'र्य'
            
            # Abbreviations (from centralized constants)
            # Apply LONGEST abbreviations first to avoid partial matches
            # (e.g., 'इ.स.' before 'इ.')
            abbrev_sorted = sorted(ABBREVIATIONS.items(), key=lambda x: len(x[0]), reverse=True)
            
            # NOTE: Generic visarga conversion ('ः' → 'हा') has been REMOVED.
            # The G2P engine (tts.utils.phonetic.g2p_engine) now handles
            # visarga with full context awareness — it maps ः to the
            # correct sibilant (श/ष/स) based on the following consonant.
            
            # Remove abbreviation dot
            replacements['॰'] = ''
            
            # Clean up text line by line
            lines = []
            for line in text.split('\n'):
                if line.strip():
                    lines.append(line.strip())
            
            text = '\n'.join(lines)
            
            # Apply abbreviations first (longest first)
            for old, new in abbrev_sorted:
                text = text.replace(old, new)
            
            # Apply other replacements
            for old, new in replacements.items():
                text = text.replace(old, new)
            
            # Fix pause markers and spacing
            text = re.sub(r'([^।\d])\s*\n\s*([^।\d])', r'\1। \2', text)
            text = re.sub(r'।+', '।', text)
            text = re.sub(r'\s+', ' ', text)
            text = text.replace('। ।', '।')
            text = re.sub(r'।\s*', '। ', text)
            text = re.sub(r'\s*।', ' ।', text)
            
            # Restore time format dots
            text = text.replace('__DOT__', '.')
            
            # Convert numbers to Marathi words for TTS
            text = normalize_numbers_for_tts(text)
            
            # Final cleanup
            text = text.strip()
            text = unicodedata.normalize('NFC', text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error in normalize_text: {str(e)}")
            return text

    def normalize_for_tts(self, text: str) -> str:
        """Enhanced normalization specifically for TTS"""
        if not text or not text.strip():
            return text
            
        try:
            # First apply basic normalization
            text = self.normalize_text(text)
            
            # TTS-specific normalization rules
            replacements = [
                (r'([।.!?]),', r'\1 ,'),
                (r'\s*([।.!?])\s*', r'\1 '),
                (r'(\d+)', r' \1 '),
                (r'\n{3,}', r'\n\n'),
                (r'&[a-zA-Z]+;', ' ')
            ]
            
            for pattern, replacement in replacements:
                text = re.sub(pattern, replacement, text)
            
            # Remove any double spaces created
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error in normalize_for_tts: {str(e)}")
            return text
