import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import pandas as pd
import re
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarathiTextPreprocessor:
    def __init__(self):
        # Custom RegEx patterns for Marathi text normalization
        self.special_chars_pattern = re.compile(r'[^\u0900-\u097F\s\-\।]')
        self.space_pattern = re.compile(r'\s+')
        self.zero_width_chars = re.compile(r'[\u200B-\u200F\u202A-\u202E\uFEFF]')
        self.broken_matras = re.compile(r'(\S) (\u093e|\u093f|\u0940|\u0941|\u0942|\u0943|\u0944|\u0945|\u0947|\u0948|\u0949|\u094b|\u094c|\u094d)')
        
    def normalize_text(self, text: str) -> str:
        """Normalize single text input with improved handling for Marathi text"""
        if not isinstance(text, str) or not text.strip():
            return ""
        
        try:
            # Basic normalization
            text = text.strip()
            
            # Remove zero-width characters
            text = self.zero_width_chars.sub('', text)
            
            # Fix broken matras (vowel marks separated from consonants)
            text = self.broken_matras.sub(r'\1\2', text)
            
            # Remove non-Devanagari characters (except allowed punctuation)
            text = self.special_chars_pattern.sub('', text)
            
            # Normalize spaces
            text = self.space_pattern.sub(' ', text)
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error normalizing text: {text}\nError: {str(e)}")
            return ""

    def validate_pair(self, incorrect: str, correct: str) -> Tuple[bool, str]:
        """Validate text pair with detailed feedback"""
        if not correct.strip():
            return False, "Empty correction"
        
        if len(incorrect) < 2 or len(correct) < 2:
            return False, "Text too short"
            
        if incorrect == correct:
            return False, "No change in correction"
            
        if not re.search(r'[\u0900-\u097F]', incorrect) or not re.search(r'[\u0900-\u097F]', correct):
            return False, "No Devanagari characters found"
            
        return True, "Valid pair"

def create_sample_data() -> Dict[str, List[str]]:
    """Create comprehensive sample data with various error types"""
    return {
        'incorrect_text': [
            "भ्‌ गवान",              # Zero-width character error
            "त्या ुळे",              # Broken matras
            "आ जाता [न",            # Special character intrusion
            "मनू महाराजांचा मौलिक बोध रोहन उपळेकरमनू महाराजांचा",  # Repetition
            "प्रेम",                # No error (control)
            "विद्यार्थी॔ने",        # Wrong diacritic
            "क रतात",              # Extra space
            "शाळेत जा तो",         # Wrong tense ending
            "पुस्तकं",             # Wrong plural marker
            "राम राम लिहितो",      # Word repetition
            "तेथे॰",               # Wrong punctuation
            "स्वतःला",             # Missing halant
            "आई वडिल",            # Missing conjunction
            "खूप मोठा झाला आहे",   # Agreement error
            "पाऊस पडत आहे होता",   # Tense confusion
            "माझा पुस्तक",         # Gender agreement error
            "घरा मध्ये",           # Wrong spacing
            "दोन किलोमीटर",        # Unit spacing error
            "संगणका वर",           # Wrong postposition spacing
            "शिक्षण घेत आहेत",     # Number agreement error
            "कालशक््ती",
            "विक्रत"
        ],
        'correct_text': [
            "भगवान",
            "त्यामुळे",
            "आजातन",
            "मनू महाराजांचा मौलिक बोध रोहन उपळेकर",
            "प्रेम",
            "विद्यार्थ्याने",
            "करतात",
            "शाळेत जातो",
            "पुस्तके",
            "राम लिहितो",
            "तेथे",
            "स्वतःला",
            "आई-वडील",
            "खूप मोठा झाला",
            "पाऊस पडत होता",
            "माझे पुस्तक",
            "घरामध्ये",
            "दोन किलोमिटर",
            "संगणकावर",
            "शिक्षण घेत आहे",
            "कलाशक्ति",
            "विक्रांत",
        ]
    }

def preprocess_dataset(input_file: Optional[Path] = None, output_file: Optional[Path] = None) -> None:
    """Preprocess dataset with improved validation and logging"""
    try:
        # Initialize paths
        BASE_DIR = Path(__file__).parent.parent
        DATA_DIR = BASE_DIR / "data"
        RAW_DATA_DIR = DATA_DIR / "raw"
        PROCESSED_DATA_DIR = DATA_DIR / "processed"
        
        input_file = input_file or RAW_DATA_DIR / "marathi_corrections.csv"
        output_file = output_file or PROCESSED_DATA_DIR / "processed_corrections.csv"
        
        # Create directories
        os.makedirs(RAW_DATA_DIR, exist_ok=True)
        os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

        # Load or create data
        if not input_file.exists():
            logger.info(f"Creating sample data at {input_file}")
            df = pd.DataFrame(create_sample_data())
            df.to_csv(input_file, index=False)
        else:
            logger.info(f"Loading existing data from {input_file}")
            df = pd.read_csv(input_file)

        # Initialize preprocessor
        preprocessor = MarathiTextPreprocessor()
        
        # Process data with validation feedback
        processed_data = {
            'incorrect_text': [],
            'correct_text': [],
            'validation_status': []
        }
        
        skipped_count = 0
        for idx, row in df.iterrows():
            incorrect = preprocessor.normalize_text(str(row['incorrect_text']))
            correct = preprocessor.normalize_text(str(row['correct_text']))
            
            is_valid, reason = preprocessor.validate_pair(incorrect, correct)
            
            if is_valid:
                processed_data['incorrect_text'].append(incorrect)
                processed_data['correct_text'].append(correct)
                processed_data['validation_status'].append('valid')
            else:
                skipped_count += 1
                logger.debug(f"Skipped pair: {incorrect} -> {correct}, Reason: {reason}")
        
        # Create processed DataFrame
        processed_df = pd.DataFrame(processed_data)
        
        # Save processed data
        output_file.parent.mkdir(parents=True, exist_ok=True)
        processed_df.to_csv(output_file, index=False)
        
        logger.info(f"Processed data saved to {output_file}")
        logger.info(f"Total valid samples: {len(processed_df)}")
        logger.info(f"Skipped samples: {skipped_count}")
        
        if len(processed_df) < 5:
            logger.warning("Very small dataset detected. Consider adding more training examples.")
        
    except Exception as e:
        logger.error(f"Error during preprocessing: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    preprocess_dataset()