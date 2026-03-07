import pandas as pd
from pathlib import Path

def add_correction(incorrect, correct, category="", notes=""):
    """Add a new correction to the dataset"""
    csv_path = Path(__file__).parent.parent / "data/raw/marathi_corrections.csv"
    
    # Load existing data
    try:
        df = pd.read_csv(csv_path)
    except:
        df = pd.DataFrame(columns=["incorrect_text", "correct_text", "category", "notes"])
    
    # Check if correction already exists
    if incorrect in df["incorrect_text"].values:
        print(f"Warning: '{incorrect}' already exists in dataset")
        return False
    
    # Add new row
    new_row = {
        "incorrect_text": incorrect,
        "correct_text": correct,
        "category": category,
        "notes": notes
    }
    df = df._append(new_row, ignore_index=True)
    
    # Save updated CSV
    df.to_csv(csv_path, index=False)
    print(f"Added: '{incorrect}' → '{correct}'")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python add_correction.py <incorrect_text> <correct_text> [category] [notes]")
        sys.exit(1)
    
    incorrect = sys.argv[1]
    correct = sys.argv[2]
    category = sys.argv[3] if len(sys.argv) > 3 else ""
    notes = sys.argv[4] if len(sys.argv) > 4 else ""
    
    add_correction(incorrect, correct, category, notes)