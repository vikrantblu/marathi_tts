import os
import logging
from pathlib import Path
import sys
import pandas as pd
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path to allow importing from models
sys.path.append(str(Path(__file__).parent.parent))
from models.correction_model import MarathiCorrectionModel

def train_correction_model():
    """Initialize and save the correction model"""
    try:
        # Load the processed data
        data_path = Path(__file__).parent.parent / "data/processed/processed_corrections.csv"
        if not data_path.exists():
            logger.error(f"Processed data not found at {data_path}")
            return
            
        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df)} training examples")
        
        # Create the model directory
        model_dir = Path(__file__).parent.parent / "models/marathi-correction-model"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the correction rules to the model directory
        rules_path = model_dir / "correction_rules.csv"
        df.to_csv(rules_path, index=False)
        logger.info(f"Saved correction rules to {rules_path}")
        
        # Initialize the model
        model = MarathiCorrectionModel(model_path=str(model_dir))
        
        # Test the model on a few examples
        test_examples = [
            "भ्‌ गवान",
            "त्या ुळे",
            "आ जाता [न",
            "मनू महाराजांचा मौलिक बोध रोहन उपळेकरमनू महाराजांचा"
        ]
        
        logger.info("Testing model on examples:")
        for example in test_examples:
            corrected = model.correct_text_marathi(example)
            logger.info(f"Input:  {example}")
            logger.info(f"Output: {corrected}")
            logger.info("---")
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        raise

if __name__ == "__main__":
    train_correction_model()