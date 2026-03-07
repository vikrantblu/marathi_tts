#!/usr/bin/env python3
"""
FEAT-50: Piper TTS Training Configuration & Dataset Exporter

Creates a Piper-compatible training dataset from aligned audio+text pairs.
Generates the directory structure and config that Piper's training scripts expect.

Piper (https://github.com/rhasspy/piper) uses VITS architecture — a neural
TTS model that produces natural speech from text input. Fine-tuning requires:
  1. WAV files (22050 Hz, mono, 16-bit)
  2. Phoneme transcriptions (IPA or language-specific)
  3. config.json with model/training hyperparameters
  4. A pre-trained checkpoint (e.g., Piper's Hindi base model)

For Sanskrit/Marathi stotra recitation:
  - Base model: hi_IN-swara (Hindi female) — closest Indic language
  - Fine-tune epochs: 500-2000 depending on data size
  - Expected quality: Good after ~1hr of data, excellent after ~3hrs

Usage:
    python generate_piper_config.py \\
        --aligned-dir ../data/aligned/ \\
        --output-dir ../data/piper_dataset/ \\
        --speaker-name "stotra_reciter"
"""

import argparse
import json
import os
import re
import shutil
from pathlib import Path

# ── Piper training configuration ────────────────────────────────────────────

# Hindi phonemes (Devanagari) — Piper uses espeak-ng for phonemization
# but for Devanagari-script languages we can use character-level tokenization
PIPER_CONFIG = {
    "audio": {
        "sample_rate": 22050,
        "quality": "medium",  # medium = 22050 Hz, VITS
    },
    "espeak": {
        "voice": "hi",  # Hindi (closest for Sanskrit/Marathi Devanagari)
    },
    "inference": {
        "noise_scale": 0.667,
        "length_scale": 1.0,
        "noise_w": 0.8,
    },
    "language": {
        "code": "hi_IN",
        "family": "indo-aryan",
        "name_english": "Hindi",
        "name_native": "हिन्दी",
        "country_english": "India",
    },
    "model": "vits",
    "num_speakers": 1,
    "num_symbols": 256,
    "phoneme_type": "espeak",
    "streaming": False,
}

# Training hyperparameters (Piper fine-tuning defaults for small datasets)
TRAINING_CONFIG = {
    "batch_size": 16,          # Reduced for small dataset
    "learning_rate": 0.0001,   # Lower LR for fine-tuning
    "epochs": 1000,            # Fine-tune epochs
    "warmup_epochs": 50,
    "grad_clip": 1.0,
    "fp16": True,
    "save_every_n_epochs": 100,
    "eval_every_n_epochs": 50,
    "base_model": "piper-tts/hi_IN-swara-medium",  # Hindi base
    "max_phoneme_length": 300,
    "max_audio_length_sec": 15.0,
}


def prepare_piper_dataset(aligned_dirs: list, output_dir: str, speaker_name: str) -> dict:
    """
    Create Piper training directory structure:
        output_dir/
            config.json
            training_config.json
            wav/
                segment_0001.wav
                segment_0002.wav
                ...
            metadata.csv       (id|text per line)
            training_stats.json
    """
    os.makedirs(output_dir, exist_ok=True)
    wav_dir = os.path.join(output_dir, "wav")
    os.makedirs(wav_dir, exist_ok=True)

    all_entries = []
    wav_count = 0
    total_duration = 0

    for aligned_dir in aligned_dirs:
        align_path = os.path.join(aligned_dir, "alignment.json")
        if not os.path.exists(align_path):
            print(f"  Skipping {aligned_dir}: no alignment.json")
            continue

        with open(align_path, "r", encoding="utf-8") as f:
            aligned = json.load(f)

        # Find the audio directory (parent of aligned/)
        audio_dir = os.path.dirname(aligned_dir)

        for entry in aligned:
            audio_file = entry.get("audio_file", "")
            if not audio_file:
                # Merged entry — use first file from audio_files list
                audio_files = entry.get("audio_files", [])
                audio_file = audio_files[0] if audio_files else ""
            if isinstance(audio_file, list):
                audio_file = audio_file[0]
            if not audio_file:
                continue

            src_audio = os.path.join(audio_dir, audio_file)
            if not os.path.exists(src_audio):
                # Try in aligned dir
                src_audio = os.path.join(aligned_dir, audio_file)
                if not os.path.exists(src_audio):
                    print(f"  WARNING: Audio not found: {audio_file}")
                    continue

            # Clean text for training
            text = entry.get("text", "")
            text = re.sub(r'[॥।\|]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            if not text or len(text) < 5:
                continue

            # Copy WAV with sequential naming
            wav_count += 1
            wav_name = f"stotra_{wav_count:05d}"
            dst_audio = os.path.join(wav_dir, f"{wav_name}.wav")
            shutil.copy2(src_audio, dst_audio)

            total_duration += entry.get("duration_sec", 0)
            all_entries.append({
                "id": wav_name,
                "text": text,
                "source": entry.get("segment_id", ""),
                "duration_sec": entry.get("duration_sec", 0),
            })

    # Write metadata.csv (Piper format: id|text)
    csv_path = os.path.join(output_dir, "metadata.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        for e in all_entries:
            f.write(f"{e['id']}|{e['text']}\n")

    # Write config.json
    config = dict(PIPER_CONFIG)
    config["dataset"] = speaker_name
    config_path = os.path.join(output_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # Write training config
    train_config = dict(TRAINING_CONFIG)
    # Adapt batch size and epochs to dataset size
    if len(all_entries) < 100:
        train_config["batch_size"] = 8
        train_config["epochs"] = 2000  # More epochs for tiny dataset
    elif len(all_entries) > 1000:
        train_config["batch_size"] = 32
        train_config["epochs"] = 500

    train_config_path = os.path.join(output_dir, "training_config.json")
    with open(train_config_path, "w", encoding="utf-8") as f:
        json.dump(train_config, f, indent=2)

    # Stats
    stats = {
        "speaker_name": speaker_name,
        "total_utterances": len(all_entries),
        "total_duration_sec": round(total_duration, 1),
        "total_duration_min": round(total_duration / 60, 1),
        "avg_duration_sec": round(total_duration / len(all_entries), 1) if all_entries else 0,
        "total_chars": sum(len(e["text"]) for e in all_entries),
        "piper_ready": len(all_entries) >= 50,
        "recommended_epochs": train_config["epochs"],
    }
    stats_path = os.path.join(output_dir, "training_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate Piper training dataset")
    parser.add_argument("--aligned-dir", required=True,
                        help="Directory containing aligned/ subdirectories (or a single aligned/ dir)")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory for Piper dataset (default: ../data/piper_dataset)")
    parser.add_argument("--speaker-name", default="stotra_reciter",
                        help="Speaker identifier for multi-speaker models")
    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "piper_dataset")

    # Find aligned directories
    aligned_dirs = []
    if os.path.exists(os.path.join(args.aligned_dir, "alignment.json")):
        aligned_dirs.append(args.aligned_dir)
    else:
        for item in sorted(os.listdir(args.aligned_dir)):
            subdir = os.path.join(args.aligned_dir, item, "aligned")
            if os.path.exists(os.path.join(subdir, "alignment.json")):
                aligned_dirs.append(subdir)
            elif os.path.exists(os.path.join(args.aligned_dir, item, "alignment.json")):
                aligned_dirs.append(os.path.join(args.aligned_dir, item))

    if not aligned_dirs:
        print("No alignment.json files found. Run align_transcript.py first.")
        return 1

    print(f"Found {len(aligned_dirs)} aligned dataset(s)")

    stats = prepare_piper_dataset(aligned_dirs, args.output_dir, args.speaker_name)

    print(f"\n{'='*60}")
    print(f"Piper Dataset Ready")
    print(f"{'='*60}")
    print(f"  Utterances: {stats['total_utterances']}")
    print(f"  Duration: {stats['total_duration_min']:.1f} min")
    print(f"  Output: {args.output_dir}")
    print(f"  Piper-ready: {'YES ✓' if stats['piper_ready'] else 'NO ✗ (need ≥50 utterances)'}")
    print(f"  Recommended epochs: {stats['recommended_epochs']}")

    if stats['piper_ready']:
        print(f"\nNext step: Upload to Google Colab and run training:")
        print(f"  python train_piper.py --dataset {args.output_dir}")
    else:
        print(f"\nNeed more recordings! Current: {stats['total_utterances']} utterances")
        print(f"  Target: ≥50 utterances (~10 min of aligned audio)")


if __name__ == "__main__":
    main()
