import os
import librosa
import numpy as np
import pandas as pd
from pathlib import Path

def preprocess_audio(file_path, output_path):
    """Load an audio file, apply preprocessing, and save the processed audio."""
    try:
        # Load audio file
        audio, sr = librosa.load(file_path, sr=None)

        # Normalize audio
        audio = audio / np.max(np.abs(audio))

        # Save processed audio
        librosa.output.write_wav(output_path, audio, sr)
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_dataset(raw_data_dir, processed_data_dir):
    """Process all audio files in the raw data directory."""
    raw_data_path = Path(raw_data_dir)
    processed_data_path = Path(processed_data_dir)

    # Create processed data directory if it doesn't exist
    processed_data_path.mkdir(parents=True, exist_ok=True)

    # Iterate through all audio files in the raw data directory
    for audio_file in raw_data_path.glob('*.wav'):
        output_file = processed_data_path / audio_file.name
        success = preprocess_audio(audio_file, output_file)
        if success:
            print(f"Processed {audio_file.name} and saved to {output_file.name}")

if __name__ == "__main__":
    raw_data_directory = 'data/raw'
    processed_data_directory = 'data/processed'
    process_dataset(raw_data_directory, processed_data_directory)