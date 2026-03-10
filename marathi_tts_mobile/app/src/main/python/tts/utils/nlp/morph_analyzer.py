import logging
import re
from tts.constants.tts_config import MORPH_SUFFIXES, MORPH_VERB_FORMS

logger = logging.getLogger(__name__)

class MarathiMorphAnalyzer:
    """
    A morphological analyzer for Marathi text.
    Handles word structure analysis, validation, and basic grammatical corrections.
    """
    
    def __init__(self):
        """Initialize the morphological analyzer"""
        logger.info("Initializing Marathi morphological analyzer")
        
        # Common Marathi suffixes (from centralized constants)
        self.common_suffixes = MORPH_SUFFIXES
        
        # Common verb forms (from centralized constants)
        self.verb_forms = MORPH_VERB_FORMS
        
    def validate_word(self, word):
        """
        Check if a word follows Marathi morphological rules.
        Returns corrected word if minor issues found, None if valid as is.
        """
        if not word or len(word) < 2:
            return None
            
        # Check for common morphological issues
        
        # Missing virama (halant) between consonants
        virama_pattern = re.compile(r'([क-ह])([क-ह])')
        if virama_pattern.search(word):
            return virama_pattern.sub(r'\1्\2', word)
            
        # Check for misplaced matras
        matra_pattern = re.compile(r'([ा-ौ])([क-ह])')
        if matra_pattern.search(word):
            return matra_pattern.sub(r'\2\1', word)
            
        # Word is valid
        return None
        
    def is_valid_word(self, word):
        """Check if word follows basic Marathi morphological structure"""
        if not word or len(word) < 2:
            return False
            
        # Very basic check for Devanagari characters
        devanagari_pattern = re.compile(r'^[\u0900-\u097F\s]+$')
        return bool(devanagari_pattern.match(word))
        
    def fix_sentence_structure(self, sentence):
        """Apply morphological fixes at the sentence level"""
        if not sentence or len(sentence) < 5:
            return sentence
            
        try:
            # Fix common subject-verb agreement issues
            sentence = re.sub(r'([\u0900-\u097F]+) होते आहे', r'\1 होत आहे', sentence)
            sentence = re.sub(r'([\u0900-\u097F]+) करते आहे', r'\1 करत आहे', sentence)
            
            # Fix common gender agreement issues
            for pair in [('माझा', 'माझी', 'माझे'), ('तुझा', 'तुझी', 'तुझे'), 
                         ('त्याचा', 'त्याची', 'त्याचे')]:
                masculine, feminine, neuter = pair
                
                # Fix neuter gender agreement (common error: masculine used with neuter nouns)
                neuter_nouns = ['पुस्तक', 'घर', 'गाव', 'शहर', 'काम']
                for noun in neuter_nouns:
                    pattern = fr'\b{masculine} {noun}\b'
                    replacement = f'{neuter} {noun}'
                    sentence = re.sub(pattern, replacement, sentence)
                    
                # Fix feminine gender agreement 
                feminine_nouns = ['बाई', 'मुलगी', 'गाय', 'शाळा', 'बहीण']
                for noun in feminine_nouns:
                    pattern = fr'\b{masculine} {noun}\b'
                    replacement = f'{feminine} {noun}'
                    sentence = re.sub(pattern, replacement, sentence)
            
            return sentence
            
        except Exception as e:
            logger.error(f"Error fixing sentence structure: {str(e)}")
            return sentence