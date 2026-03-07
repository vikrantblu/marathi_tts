import argparse
import numpy as np
import soundfile as sf
from models import YourVoiceModel  # Replace with your actual model import

def synthesize_speech(text, model_path, output_path):
    model = YourVoiceModel(model_path)
    audio = model.generate_audio(text)  # Replace with your model's audio generation method
    sf.write(output_path, audio, 22050)  # Adjust sample rate as needed

def main():
    parser = argparse.ArgumentParser(description="Synthesize speech from text using a trained voice model.")
    parser.add_argument("text", type=str, help="Text to synthesize")
    parser.add_argument("model_path", type=str, help="Path to the trained voice model")
    parser.add_argument("output_path", type=str, help="Output path for the synthesized audio file")
    
    args = parser.parse_args()
    
    synthesize_speech(args.text, args.model_path, args.output_path)

if __name__ == "__main__":
    main()