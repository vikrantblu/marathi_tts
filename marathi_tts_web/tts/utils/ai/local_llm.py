import os
import re
import logging
import unicodedata
from .dictionary import MarathiDictionary

class LocalLLM:
    _instance = None
    
    @classmethod
    def get_instance(cls, model_path=None):
        if cls._instance is None:
            cls._instance = cls(model_path)
        return cls._instance
    
    def __init__(self, model_path=None):
        """Initialize local LLM with rule-based processing only"""
        self.is_loaded = True  # Always set to True since we don't need models
        default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                   'models', 'llm')
        self.model_path = model_path or default_path
        
        # Load dictionary for spelling correction
        self.dictionary = MarathiDictionary()
        
        # Try to load morfessor model if available
        self.morph_analyzer = None
        try:
            import morfessor
            morfessor_model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                             'morph', 'morfessor', 'mr.model')
            if os.path.exists(morfessor_model_path):
                logging.info(f"Loading Morfessor model from {morfessor_model_path}")
                self.morph_analyzer = morfessor.MorfessorIO().read_binary_model_file(morfessor_model_path)
                logging.info("Morfessor model loaded successfully")
            else:
                logging.warning(f"Morfessor model not found at {morfessor_model_path}")
        except ImportError:
            logging.warning("Morfessor not installed, morphological analysis disabled")
        except Exception as e:
            logging.error(f"Error loading Morfessor model: {str(e)}")
        
        logging.info("Using rule-based text processing with dictionary and morphological analysis")
        
        # Dictionary of common Marathi misspellings and their corrections
        self.spelling_corrections = {
            'अँड': 'आणि',
            'अन': 'आणि',
            'एंड': 'आणि',
            'कि': 'की',
            'हे': 'हा',
            'हि': 'ही',
            'होत': 'होते',
            'करत': 'करीत',
            'वेळेलएक': 'वेळेला एक',
            'करायचा': 'करायचे',
            'करायचे': 'करायचे',
            'आहे': 'आहेत',
            'नाहि': 'नाही',
            'नाइ': 'नाही',
            'नाय': 'नाही',
            'असत': 'असते',
            'जात': 'जाते',
            'येत': 'येते',
            'राहत': 'राहते',
            'बघत': 'बघते',
            'खात': 'खाते',
            'पित': 'पिते',
            'लिहित': 'लिहिते',
            'वाचत': 'वाचते',
            'बोलत': 'बोलते',
            'ऐकत': 'ऐकते',
            'झोपत': 'झोपते',
            'उठत': 'उठते',
            'खेळत': 'खेळते',
            'धावत': 'धावते',
            'पळत': 'पळते',
            'न्हाइ': 'नाही',
            'न्हाय': 'नाही',
            'होन': 'होऊन',
            'करन': 'करून',
            'येन': 'येऊन',
            'जान': 'जाऊन',
            'कधि': 'कधी',
            'केव्हा': 'कधी',
            'तेव्हा': 'तेव्हा',
            'कसं': 'कसे',
            'कश्या': 'कशा',
            'कुठं': 'कुठे',
            'इथं': 'येथे',
            'तिथं': 'तेथे',
        }
        
        # Load Marathi-specific punctuation rules
        self.punctuation_chars = "।॥,.!?:;\"'()[]{}—"
        
        # Marathi sentence ending markers
        self.sentence_endings = ["।", "॥", ".", "!", "?"]
    
    def load_model(self):
        """Dummy method for compatibility, no models are loaded"""
        logging.info("No models to load, using rule-based processing with dictionary support")
        return
    
    def correct_text_llm(self, text):
        """Apply extensive rules to correct Marathi text with dictionary support"""
        if not text:
            return text
        
        # Apply all rule-based corrections
        corrected_text = self._rule_based_correction(text)
        
        # Improve with dictionary-based word correction
        corrected_text = self._dictionary_based_correction(corrected_text)
        
        # Apply morphological analysis if available
        if self.morph_analyzer:
            corrected_text = self._morphological_correction(corrected_text)
        
        return corrected_text
    
    def correct_word(self, word):
        """Correct a single Marathi word via model → dict → morph."""
        if not word:
            return word

        corrected = word
        # A. Model‐based correction
        if self.correction_model:
            try:
                logging.info(f"LocalLLM.correct_word: model fixing '{word}'")
                corrected = self.correction_model.correct_text_llm(word)
            except Exception as e:
                logging.error(f"LocalLLM.correct_word: model error on '{word}': {e}")
                corrected = word

        # B. Dictionary suggestion
        try:
            suggestion = self.dictionary.suggest_with_context(corrected)
            corrected = suggestion or corrected
        except Exception:
            pass

        # C. Morphological analyzer
        if self.morph_analyzer:
            try:
                corrected = self.morph_analyzer.fix_sentence_structure(corrected)
            except Exception:
                pass

        return corrected
    
    def _rule_based_correction(self, text):
        """Apply comprehensive rules to correct common Marathi text issues"""
        if not text:
            return text
        
        # Normalize Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Fix common spacing issues
        text = re.sub(r'\s+', ' ', text)  # Remove multiple spaces
        
        # Fix punctuation spacing
        text = re.sub(r'\s*([।॥,.!?:;])', r'\1', text)  # Remove spaces before punctuation
        text = re.sub(r'([।॥,.!?:;])\s*', r'\1 ', text)  # Add space after punctuation
        
        # Fix common Marathi punctuation issues
        text = re.sub(r'([^\s])\.([^\s])', r'\1। \2', text)  # Replace period between words with Marathi danda
        
        # Normalize ellipses
        text = re.sub(r'\.\.\.+', '...', text)
        
        # Fix quotation marks
        text = re.sub(r'"([^"]*)"', r'"\1"', text)
        
        # Fix paragraph breaks
        text = re.sub(r'([।॥!?])\s*(?!\n)', r'\1\n\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix common Marathi spacing issues
        for word in ["च", "की", "तर", "पण", "आणि", "परंतु", "म्हणजे", "कारण"]:
            # Ensure spaces around conjunctions
            text = re.sub(f'([^\\s]){word}([^\\s])', f'\\1 {word} \\2', text)
            text = re.sub(f'([^\\s]){word}(\\s)', f'\\1 {word}\\2', text)
            text = re.sub(f'(\\s){word}([^\\s])', f'\\1{word} \\2', text)
        
        # Fix common spelling mistakes
        for wrong, correct in self.spelling_corrections.items():
            # Only replace whole words, not substrings
            text = re.sub(f'\\b{wrong}\\b', correct, text)
        
        # Fix number-word spacing
        text = re.sub(r'(\d)([^\d\s])', r'\1 \2', text)
        text = re.sub(r'([^\d\s])(\d)', r'\1 \2', text)
        
        # Fix formatting for lists
        text = re.sub(r'(\n|^)([०-९]+)(\s*\.\s*)', r'\1\2. ', text)  # Marathi numerals
        text = re.sub(r'(\n|^)([0-9]+)(\s*\.\s*)', r'\1\2. ', text)  # Arabic numerals
        
        return text.strip()
    
    def _dictionary_based_correction(self, text):
        """Use dictionary for additional corrections"""
        if not text or not self.dictionary:
            return text
        
        words = text.split()
        corrected_words = [self.dictionary.correct_word(word) for word in words]
        return ' '.join(corrected_words)
    
    def _morphological_correction(self, text):
        """Apply morphological analysis for corrections"""
        if not text or not self.morph_analyzer:
            return text
        
        words = text.split()
        corrected_words = []
        
        for word in words:
            try:
                segments = self.morph_analyzer.viterbi_segment(word)
                corrected_words.append(' '.join(segments))
            except Exception as e:
                logging.error(f"Error in morphological analysis for word '{word}': {str(e)}")
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _rule_based_structuring(self, text):
        """Apply rules to structure Marathi text"""
        if not text:
            return text
        
        # Fix paragraph breaks after sentence endings
        for ending in self.sentence_endings:
            text = re.sub(f'({ending})\s*(?!\n)', f'\\1\n\n', text)
        
        # Fix multiple line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Format section headings (common in Marathi documents)
        # Number followed by text and then newline
        text = re.sub(r'(\n|^)([०-९]+)\.\s*([^\n।॥]+)(\n|$)', r'\1\2. \3:\4', text)
        text = re.sub(r'(\n|^)([0-9]+)\.\s*([^\n।॥]+)(\n|$)', r'\1\2. \3:\4', text)
        
        # Ensure consistent indentation for paragraphs
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            # Remove leading/trailing whitespace from paragraphs
            formatted_paragraphs.append(para.strip())
        
        return '\n\n'.join(formatted_paragraphs)
    
    def fix_content_structure(self, text):
        """Fix content structure issues"""
        if not text:
            return text
            
        try:
            # First apply basic text normalization
            result = self._rule_based_correction(text)
            
            # Fix structure using rules
            result = self._rule_based_structuring(result)
            
            # Remove duplicates and fix paragraph breaks
            paragraphs = result.split('\n\n')
            unique_paragraphs = []
            seen = set()
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                    
                # Normalize for comparison
                normalized = re.sub(r'\s+', ' ', para.lower())
                if normalized not in seen:
                    unique_paragraphs.append(para)
                    seen.add(normalized)
            
            # Add proper paragraph breaks
            result = '\n\n'.join(unique_paragraphs)
            
            # Fix sentence endings
            for ending in self.sentence_endings:
                result = re.sub(f'({ending})([^\n\\s])', f'\\1 \\2', result)
            
            return result.strip()
            
        except Exception as e:
            logging.error(f"Error in fixing content structure: {str(e)}")
            return text
    
    def summarize_text(self, text, max_length=200):
        """Create a summary using rule-based extraction"""
        if not text:
            return text
        
        return self._rule_based_summarization(text, max_length)
    
    def _rule_based_summarization(self, text, max_length=200):
        """Enhanced extraction-based summarization"""
        words = text.split()
        
        if len(words) <= max_length:
            return text
        
        # Split text into sentences
        for ending in self.sentence_endings:
            text = text.replace(ending, ending + "||SPLIT||")
        
        sentences = text.split("||SPLIT||")
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Calculate a score for each sentence
        sentence_scores = {}
        
        # Important Marathi keywords that signal important content
        importance_markers = [
            "महत्वाचे", "महत्त्वाचे", "प्रमुख", "मुख्य", "विशेष", "निष्कर्ष", 
            "सारांश", "परिणाम", "कारण", "म्हणून", "अर्थात", "उल्लेखनीय",
            "लक्षणीय", "विशेष", "पहिले", "शेवटी", "निश्चित"
        ]
        
        # Position-based weighting
        position_weight = 1.5  # First sentences are important
        
        for i, sentence in enumerate(sentences):
            # Base score - position matters (first/last sentences often important)
            if i < len(sentences) * 0.2:  # First 20% of sentences
                position_score = position_weight
            elif i > len(sentences) * 0.8:  # Last 20% of sentences
                position_score = position_weight * 0.8
            else:
                position_score = 1.0
            
            # Importance markers score
            marker_score = sum(2.0 for marker in importance_markers if marker in sentence)
            
            # Length score - favor medium-length sentences
            words_count = len(sentence.split())
            if 5 <= words_count <= 25:
                length_score = 1.2
            elif words_count < 5:
                length_score = 0.8
            else:
                length_score = 1.0
            
            # Final score
            sentence_scores[i] = position_score + marker_score + length_score
        
        # Select top sentences to include in summary
        num_words = 0
        selected_sentences = []
        
        # Always include first sentence
        if sentences:
            selected_sentences.append((0, sentences[0]))
            num_words += len(sentences[0].split())
        
        # Sort other sentences by score and add until max_length
        sorted_sentences = sorted(
            [(i, sentences[i]) for i in range(1, len(sentences))],
            key=lambda x: sentence_scores.get(x[0], 0),
            reverse=True
        )
        
        for i, sentence in sorted_sentences:
            sentence_words = len(sentence.split())
            if num_words + sentence_words <= max_length:
                selected_sentences.append((i, sentence))
                num_words += sentence_words
            else:
                break
        
        # Sort by original position to maintain coherence
        selected_sentences.sort(key=lambda x: x[0])
        
        # Join sentences and clean up any artifacts
        summary = ' '.join(sentence for _, sentence in selected_sentences)
        summary = summary.replace("||SPLIT||", "")
        
        return summary