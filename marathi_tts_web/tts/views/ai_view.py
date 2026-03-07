import os
import re
import logging
import json
import math
import sys
import time
import pandas as pd
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from ..utils.text.text_normalizer import MarathiTextNormalizer
from ..utils.ai.dictionary import MarathiDictionary

# Add the project root to the path to allow importing the models
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from models.correction_model import MarathiCorrectionModel

logger = logging.getLogger(__name__)

class MarathiTextCorrector:
    """Text corrector using our trained MarathiCorrectionModel"""
    
    def __init__(self, use_llm=False, use_morph=True):
        """Initialize the text corrector"""
        try:
            # Initialize our correction model
            base_path = Path(__file__).parent.parent.parent
            model_path = base_path / 'models' / 'marathi-correction-model'
            
            if not model_path.exists():
                raise ValueError(f"Model path not found: {model_path}")
                
            # Initialize the correction model
            self.correction_model = MarathiCorrectionModel(model_path=str(model_path))
            
        except Exception as e:
            logger.error(f"Error initializing correction model: {str(e)}")
            raise RuntimeError(f"Failed to initialize correction model: {str(e)}")
            
    def correct_marathi_text(self, text, operation_type='correction'):
        """Apply corrections using our trained model"""
        if not text or not text.strip():
            return text
        
        try:
            if operation_type == 'correction':
                start_time = time.time()
                logger.info(f"Starting correction for text length: {len(text)}")
                
                # Verify model is initialized
                if not self.correction_model:
                    logger.error("Correction model not initialized")
                    return text
                    
                # Split preserving formatting
                pattern = r'([\u0900-\u097F]+(?:[\s][\u0900-\u097F]+)*)'
                parts = re.split(pattern, text)
                result = []
                
                for part in parts:
                    if re.match(pattern, part):
                        try:
                            # Use model for correction
                            corrected = self.correction_model.correct_text_marathi(part)
                            if corrected and corrected != part:
                                logger.info(f"Model correction: '{part}' -> '{corrected}'")
                                result.append(corrected)
                            else:
                                result.append(part)
                        except Exception as word_error:
                            logger.error(f"Error correcting: '{part}': {str(word_error)}")
                            result.append(part)
                    else:
                        # Preserve non-Marathi text and formatting
                        result.append(part)

                corrected_text = ''.join(result)
                
                # Safety: strip any remaining MT5 sentinel tokens
                corrected_text = re.sub(r'<extra_id_\d+>', '', corrected_text)
                corrected_text = re.sub(r'\s{2,}', ' ', corrected_text).strip()
                
                end_time = time.time()
                logger.info(f"Correction completed in {end_time - start_time:.2f} seconds")
                
                return corrected_text
                
            # For text formatting and cleaning
            elif operation_type == 'formatting':
                # 1. Clean metadata and remove garbage text
                clean_text = self._clean_metadata(text)
                
                # 2. Remove OCR artifacts and gibberish
                clean_text = self._clean_ocr_artifacts(clean_text)
                
                # 3. Fix paragraph structure
                paragraphs = self._split_into_paragraphs(clean_text)
                
                # 4. Format each paragraph
                formatted_paras = []
                for para in paragraphs:
                    # Remove excessive spaces
                    clean_para = re.sub(r'\s+', ' ', para).strip()
                    # Fix punctuation spacing
                    clean_para = re.sub(r'\s+([,.!?:;)।॥])', r'\1', clean_para)
                    clean_para = re.sub(r'([,.!?:;(।॥])\s+', r'\1 ', clean_para)
                    formatted_paras.append(clean_para)
                
                # 5. Join with proper paragraph spacing
                formatted_text = '\n\n'.join(formatted_paras)
                
                # 6. Fix sentence endings
                formatted_text = self._fix_sentence_endings(formatted_text)
                
                return formatted_text.strip()
                
            return text
                
        except Exception as e:
            logger.error(f"Error in text processing: {str(e)}")
            return text

    def _clean_ocr_artifacts(self, text):
        """Clean OCR artifacts and garbage text"""
        if not text:
            return text
        
        try:
            # Remove common artifacts
            patterns = [
                (r'\d+\s*Dec\s*\d{4}', ''),  # Dates
                (r'https?://\S+', ''),  # URLs
                (r'\S+@\S+\.\S+', ''),  # Emails
                (r'[#*]{3,}', ''),  # Repeated symbols
                (r'(?:\={3,}|\-{3,}|\*{3,})', ''),  # Separator lines
                (r'(?m)^.{1,3}$\n', '\n'),  # Very short lines
                (r'[^\u0900-\u097F\s,.!?:;()।॥\'"a-zA-Z0-9-]', ' ')  # Non-Marathi/English chars
            ]
            
            result = text
            for pattern, replacement in patterns:
                result = re.sub(pattern, replacement, result)
            
            # Clean up extra whitespace
            result = re.sub(r'\s+', ' ', result)
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning OCR artifacts: {str(e)}")
            return text

    def _split_into_paragraphs(self, text):
        """Split text into paragraphs"""
        if not text:
            return []
        
        # Split by double newlines first, then by single newlines
        paragraphs = re.split(r'\n\n+', text)
        result = []
        
        for p in paragraphs:
            # For paragraphs that might have single newlines
            if '\n' in p:
                result.extend([part for part in p.split('\n') if part.strip()])
            else:
                if p.strip():
                    result.append(p)
        
        return result
        
    def _split_into_sentences(self, text):
        """Split text into sentences based on Marathi punctuation markers"""
        if not text:
            return []
        
        # Split by common Marathi sentence markers
        # Danda (।), Double Danda (॥), period, exclamation mark, question mark
        sentences = re.split(r'([।॥.!?])', text)
        
        # Recombine sentences with their punctuation
        result = []
        for i in range(0, len(sentences)-1, 2):
            if i+1 < len(sentences):
                result.append(sentences[i] + sentences[i+1])
            else:
                result.append(sentences[i])
        
        # Handle any remaining text
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])
        
        return [s.strip() for s in result if s.strip()]

    def _fix_paragraph_breaks(self, text):
        """Fix paragraph breaks for better readability"""
        # Normalize paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix broken paragraphs (sentences split across paragraphs)
        lines = text.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            if i > 0 and lines[i-1] and not any(lines[i-1].endswith(c) for c in ['.', '।', '?', '!']):
                # If previous line doesn't end with punctuation, join with current line
                fixed_lines[-1] += ' ' + line
            else:
                fixed_lines.append(line)
                
        return '\n'.join(fixed_lines)
        
    def _clean_metadata(self, text):
        """Clean common blog metadata and navigation elements"""
        if not text:
            return text

        patterns = [
            # Blog headers and navigation
            (r'\b(?:Newer Post|Older Post|Home|Next|Previous|Post a Comment|Comments)\b', ''),
            (r'\b(?:NewerPost|OlderPost|PostHome|NextPost|PrevPost)\b', ''),
            (r'Newer\s*Post\s*Older\s*Post\s*Home', ''),

            # Date formats
            (r'\d+\s*Dec\s*\d{4}', ''),
            (r'December\s*\d+\s*,?\s*\d{4}', ''),
            (r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}', ''),
            (r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[.,\s]+\d{4}', ''),

            # Social media links
            (r'\b(?:Twitter|Facebook|LinkedIn|Instagram|Pinterest)\b', ''),

            # Email addresses and URLs
            (r'\S+@\S+\.\S+', ''),
            (r'https?://\S+', ''),

            # HTML/XML elements
            (r'<[^>]*>', ''),
            (r'\&[a-zA-Z]+;', ' '),
        ]

        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)

        # Remove very short lines (likely page numbers or other metadata)
        lines = result.split('\n')
        cleaned_lines = [line for line in lines if len(line.strip()) > 5]

        return '\n'.join(cleaned_lines).strip()

    def _find_closest_match(self, word, threshold=0.75):
        """Find closest match in dictionary using fuzzy matching"""
        if not word or not self.dictionary:
            return word
        
        import difflib
        
        # Only consider words with similar length for efficiency
        word_len = len(word)
        candidates = [w for w in self.dictionary 
                     if abs(len(w) - word_len) <= min(3, word_len//2)]
        
        if not candidates:
            return word
        
        # Use get_close_matches with custom cutoff
        matches = difflib.get_close_matches(word, candidates, n=1, cutoff=threshold)
        return matches[0] if matches else word

    def correct_with_context(self, text, domain_hint='tts', context_level='paragraph'):
        """Correct text with word and sentence level improvements while preserving format"""
        if not text or not text.strip():
            logger.warning("Empty text provided for correction")
            return {
                'success': False,
                'message': 'Empty text provided',
                'correctedText': text,
                'hasChanges': False
            }
        
        try:
            # Keep original text for comparison
            original_text = text
            
            # Apply corrections while preserving format
            corrected_text = self.correct_marathi_text(text)
            
            # Check for changes
            has_changes = corrected_text != original_text
            
            # Count changes safely
            changes_count = 0
            try:
                changes_count = self._count_changes(original_text, corrected_text)
            except Exception as e:
                logger.warning(f"Error counting changes: {str(e)}")
                changes_count = 1 if has_changes else 0
            
            return {
                'success': True,
                'correctedText': corrected_text,
                'hasChanges': has_changes,
                'changes': changes_count
            }
                
        except Exception as e:
            logger.exception(f"Unexpected error during text correction: {str(e)}")
            return {
                'success': False,
                'message': f'Error during text correction: {str(e)}',
                'correctedText': text,
                'hasChanges': False
            }

    def _count_changes(self, original_text, corrected_text):
        """Count the number of changes between original and corrected text"""
        try:
            if not isinstance(original_text, str) or not isinstance(corrected_text, str):
                return 0
                
            if original_text == corrected_text:
                return 0
            
            import difflib
            
            # Convert inputs to string if needed
            original_text = str(original_text)
            corrected_text = str(corrected_text)
            
            # Use difflib to compare text differences
            diff = list(difflib.ndiff(original_text.splitlines(True), corrected_text.splitlines(True)))
            
            # Count changes (lines that start with + or -)
            changes_count = sum(1 for line in diff if line.startswith('+') or line.startswith('-'))
            
            return changes_count
            
        except Exception as e:
            logger.error(f"Error counting changes: {str(e)}")
            return 1 if original_text != corrected_text else 0


class TextCorrectionService:
    def __init__(self):
        self.corrector = None
        self._initialize_corrector()

    def _initialize_corrector(self):
        if not self.corrector:
            try:
                self.corrector = MarathiTextCorrector(use_llm=False)
                logger.info("Correction model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize corrector: {str(e)}")
                raise

    def correct_text_service(self, text, operation_type='correction'):
        """Handle text correction requests"""
        if not text or not text.strip():
            return {
                'success': False,
                'message': 'No text provided',
                'correctedText': text,
                'hasChanges': False
            }

        try:
            # Ensure corrector is initialized
            if not self.corrector:
                self._initialize_corrector()

            if operation_type == 'correction':
                # Use model for word corrections
                corrected_text = self.corrector.correct_marathi_text(text, operation_type='correction')
            else:
                # Use formatting logic
                corrected_text = self.corrector.correct_marathi_text(text, operation_type='formatting')

            return {
                'success': True,
                'correctedText': corrected_text,
                'hasChanges': corrected_text != text,
                'changes': self._count_changes(text, corrected_text)
            }

        except Exception as e:
            logger.error(f"Error in text service: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'correctedText': text,
                'hasChanges': False
            }

    def format_text_service(self, text, domain_hint='tts', context_level='paragraph'):
        """Service method to format text"""
        if not text:
            return None
            
        try:
            # Clean metadata and non-Marathi text
            cleaned_text = self._remove_metadata(text)
            
            # Fix paragraph formatting
            paragraphs = [p.strip() for p in cleaned_text.split('\n') if p.strip()]
            formatted_text = []
            
            for para in paragraphs:
                # Remove extra spaces
                para = ' '.join(para.split())
                # Fix punctuation spacing
                para = self._fix_punctuation(para)
                formatted_text.append(para)
                
            result = '\n\n'.join(formatted_text)
            
            return {
                'success': True,
                'formattedText': result,
                'hasChanges': result != text,
                'changes': self._count_changes(text, result)
            }
            
        except Exception as e:
            logger.error(f"Error in text formatting: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'formattedText': text,
                'hasChanges': False
            }

    def _remove_metadata(self, text):
        """Remove metadata and cleanup text"""
        # Remove date stamps
        text = re.sub(r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', '', text)
        # Remove blog/page navigation
        text = re.sub(r'Newer Post|Older Post|Home', '', text)
        # Remove special characters except Marathi
        text = re.sub(r'[^\u0900-\u097F\s\.\,\?\!\;\:\(\)\-]', ' ', text)
        # Cleanup extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _fix_punctuation(self, text):
        """Fix spacing around punctuation"""
        text = re.sub(r'\s+([।॥\,\.\!\?\:\;])', r'\1', text) 
        text = re.sub(r'([।॥\,\.\!\?\:\;])\s+', r'\1 ', text)
        return text

    def _count_changes(self, original_text, corrected_text):
        """Count the number of changes between original and corrected text"""
        if original_text == corrected_text:
            return 0
        
        import difflib
        
        # Use difflib to compare text differences
        diff = difflib.ndiff(original_text.splitlines(True), corrected_text.splitlines(True))
        
        # Count changes (lines that start with + or -)
        changes_count = 0
        for line in diff:
            if line.startswith('+') or line.startswith('-'):
                changes_count += 1
        
        return changes_count

    def correct_with_context(self, text, domain_hint='tts', context_level='paragraph'):
        """Delegate to the appropriate correction method based on text and context"""
        if not text or not text.strip():
            logger.warning("Empty text provided for correction")
            return {
                'success': False,
                'message': 'Empty text provided',
                'correctedText': text,
                'hasChanges': False
            }
        
        try:
            # If we have a MarathiTextCorrector with the required method
            if hasattr(self.corrector, 'correct_with_context'):
                return self.corrector.correct_with_context(text, domain_hint, context_level)
            
            # Otherwise use our own implementation or the corrector's default method
            if hasattr(self.corrector, 'correct_marathi_text'):
                corrected_text = self.corrector.correct_marathi_text(text)
            else:
                logger.warning("No suitable correction method found, returning text unchanged")
                corrected_text = text
                
            # Calculate changes safely
            has_changes = corrected_text != text
            changes_count = 0
            
            try:
                changes_count = self._count_changes(text, corrected_text)
            except Exception as e:
                logger.warning(f"Error counting changes: {str(e)}")
                changes_count = 1 if has_changes else 0
                
            return {
                'success': True,
                'correctedText': corrected_text,
                'hasChanges': has_changes,
                'changes': changes_count
            }
            
        except Exception as e:
            logger.exception(f"Unexpected error during text correction: {str(e)}")
            return {
                'success': False,
                'message': f"Error during text correction: {str(e)}",
                'correctedText': text,
                'hasChanges': False
            }

# Global correction service instance
_correction_service = None

def get_correction_service():
    global _correction_service
    if not _correction_service:
        _correction_service = TextCorrectionService()
    return _correction_service

@csrf_exempt
@require_POST
def correct_text_para(request):
    """Handle word correction requests"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        operation_type = data.get('operation_type', 'correction')
        
        if not text:
            return JsonResponse({
                'success': False,
                'message': 'No text provided'
            })
        
        correction_service = get_correction_service()
        result = correction_service.correct_text_service(text, operation_type=operation_type)
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in word correction: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def format_text(request):
    """API endpoint for text formatting"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if not text:
            return JsonResponse({
                'success': False,
                'message': 'No text provided',
                'formattedText': '',
                'hasChanges': False
            })
            
        correction_service = get_correction_service()
        result = correction_service.format_text_service(text)
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in text formatting: {str(e)}")
        return JsonResponse({
            'success': False,  
            'message': str(e),
            'formattedText': text if 'text' in locals() else '',
            'hasChanges': False
        }, status=500)

@csrf_exempt
def suggest_correction(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        incorrect = data.get('incorrect', '').strip()
        correct = data.get('correct', '').strip()
        category = data.get('category', '')
        notes = data.get('notes', '')
        if not incorrect or not correct:
            return JsonResponse({'success': False, 'error': 'Missing fields'}, status=400)
        csv_path = Path(__file__).parent / '../data/raw/marathi_correction_suggestions.csv'
        df = pd.DataFrame([{
            'incorrect_text': incorrect,
            'correct_text': correct,
            'category': category,
            'notes': notes
        }])
        if csv_path.exists():
            df.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            df.to_csv(csv_path, index=False)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

def highlightChanges(original, corrected):
    """Log changes between original and corrected text - Python version"""
    # Note: This function doesn't actually highlight anything since we're in Python
    # It just logs the changes for analytics purposes
    
    if original == corrected:
        logger.debug("No changes to highlight")
        return
    
    try:
        # Log some basic stats about the changes
        len_original = len(original)
        len_corrected = len(corrected)
        change_percentage = abs(len_original - len_corrected) / len_original * 100 if len_original > 0 else 0
        
        logger.info(f"Text corrections applied. Original length: {len_original}, " 
                   f"Corrected length: {len_corrected}, "
                   f"Change percentage: {change_percentage:.2f}%")
        
    except Exception as error:
        logger.error(f"Error while analyzing changes: {error}")

