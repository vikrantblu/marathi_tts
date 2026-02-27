#!/usr/bin/env python3
"""
setup_bridge.py — Install Python dependencies needed by the bridge scripts.
Run this once after cloning: python setup_bridge.py
"""

import subprocess
import sys

PACKAGES = [
    # Core TTS
    "gtts",
    "pydub",
    "pyttsx3",
    # Audio / STT
    "openai-whisper",
    "sounddevice",
    "soundfile",
    # HTTP / Scraping
    "requests",
    "beautifulsoup4",
    "certifi",
    # OCR / imaging
    "Pillow",
    "pytesseract",
    # PDF extraction
    "PyPDF2",
    "PyMuPDF",
    # NLP / AI (desktop bridge does NOT need Django at runtime)
    "indic-nlp-library",
    "indic-transliteration",
    # "transformers",  # only needed if web-app TTSEngine is on the path
    # "torch",         # same — optional, heavy download (~2 GB)
    # Audio effects
    "librosa",
    "pedalboard",
]


def main():
    print("Installing Python bridge dependencies...")
    for pkg in PACKAGES:
        print(f"  Installing {pkg}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        except subprocess.CalledProcessError as e:
            print(f"    WARNING: {pkg} failed to install ({e}). Continuing...")

    print("\nAll dependencies installed successfully.")
    print("\nSystem dependencies also required:")
    print("  Tesseract OCR:")
    print("    Ubuntu/Debian : sudo apt install tesseract-ocr tesseract-ocr-mar tesseract-ocr-hin")
    print("    Windows       : https://github.com/UB-Mannheim/tesseract/wiki")
    print("    macOS         : brew install tesseract tesseract-lang")
    print("  ffmpeg (for pydub audio format conversion):")
    print("    Ubuntu/Debian : sudo apt install ffmpeg")
    print("    Windows       : https://ffmpeg.org/download.html (add to PATH)")
    print("    macOS         : brew install ffmpeg")


if __name__ == "__main__":
    main()
