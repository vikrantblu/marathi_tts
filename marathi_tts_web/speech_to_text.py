#!/usr/bin/env python3
"""
Marathi Speech-to-Text using OpenAI Whisper.

Usage:
    python speech_to_text.py path/to/audio.wav
    python speech_to_text.py path/to/audio.wav --model large-v2
    python speech_to_text.py path/to/audio.wav --model medium --output result.txt

Available models (smallest to most accurate):
    tiny, base, small (default), medium, large, large-v2, large-v3

GPU is used automatically when available; falls back to CPU.
"""

import argparse
import gc
import os
import time
from pathlib import Path

import torch
import whisper


def get_device() -> str:
    """Return 'cuda' if a GPU is available, otherwise 'cpu'."""
    if torch.cuda.is_available():
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
        torch.cuda.set_per_process_memory_fraction(0.7)
        torch.backends.cudnn.benchmark = True
        return 'cuda'
    return 'cpu'


def transcribe(audio_path: str, model_name: str = 'small') -> str:
    """Transcribe a Marathi audio file using Whisper.

    Args:
        audio_path: Path to the audio file (WAV, MP3, FLAC, etc.)
        model_name: Whisper model variant to use.

    Returns:
        Transcribed Marathi text as a string.
    """
    device = get_device()
    gpu_label = f" ({torch.cuda.get_device_name()})" if device == 'cuda' else ''
    print(f"Device  : {device}{gpu_label}")
    print(f"Model   : {model_name}")

    print("Loading model...")
    model = whisper.load_model(model_name).to(device)
    model.eval()

    print(f"Transcribing {Path(audio_path).name}...")
    start = time.time()

    result = model.transcribe(
        audio_path,
        language='mr',
        task='transcribe',
        verbose=False,
        fp16=(device == 'cuda'),
        temperature=0.0,
        initial_prompt=(
            'he marathi bhashetil bhashan ahe. '
            'krupaya auchcha shabdanmadhe likha. '
            'marathi bhashet spashta uchchar kara.'
        ),
        condition_on_previous_text=False,
        best_of=1,
    )

    duration = time.time() - start
    print(f"Done in {duration:.1f}s")

    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return result['text'].strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Transcribe Marathi audio to text using OpenAI Whisper.',
    )
    parser.add_argument('audio', help='Path to the audio file (WAV/MP3/FLAC/etc.)')
    parser.add_argument(
        '--model',
        default='small',
        choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
        help='Whisper model size (default: small)',
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output text file path (default: <audio_stem>_transcription.txt)',
    )
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        parser.error(f"Audio file not found: {audio_path}")

    text = transcribe(str(audio_path), model_name=args.model)

    print('\n' + '-' * 50)
    print(text)
    print('-' * 50)

    output_path = (
        Path(args.output)
        if args.output
        else audio_path.with_name(audio_path.stem + '_transcription.txt')
    )
    output_path.write_text(text, encoding='utf-8-sig')
    print(f'\nSaved to {output_path}')


if __name__ == '__main__':
    main()