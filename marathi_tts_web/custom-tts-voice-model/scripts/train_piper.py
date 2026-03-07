#!/usr/bin/env python3
"""
FEAT-50: Piper TTS Fine-Tuning Script (Colab-Ready)

Fine-tunes Piper's VITS model on Sanskrit/Marathi stotra recordings.
Designed to run on Google Colab with A100/T4 GPU.

Prerequisites (auto-installed on Colab):
    pip install piper-tts piper-phonemize onnxruntime torch torchaudio

Usage (local):
    python train_piper.py --dataset ../data/piper_dataset --epochs 1000

Usage (Colab):
    Upload the piper_dataset/ directory, then run this script.

Output: ONNX model file ready for Sherpa-ONNX / Piper inference.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Check if running in Colab
IN_COLAB = "google.colab" in sys.modules if "google" in sys.modules else False


def install_piper_training():
    """Install Piper training dependencies."""
    print("Installing Piper training dependencies...")
    cmds = [
        "pip install piper-tts piper-phonemize onnxruntime",
        "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121",
    ]
    for cmd in cmds:
        print(f"  Running: {cmd}")
        subprocess.run(cmd.split(), check=False)

    # Clone piper training repo if not present
    if not os.path.exists("piper"):
        subprocess.run([
            "git", "clone", "--depth", "1",
            "https://github.com/rhasspy/piper.git"
        ], check=True)
        subprocess.run([
            "pip", "install", "-e", "piper/src/python/"
        ], check=True)


def download_base_model(model_name: str, output_dir: str) -> str:
    """Download Piper Hindi base model for fine-tuning."""
    model_dir = os.path.join(output_dir, "base_model")
    os.makedirs(model_dir, exist_ok=True)

    ckpt_path = os.path.join(model_dir, "checkpoint.ckpt")
    if os.path.exists(ckpt_path):
        print(f"  Base model already downloaded: {ckpt_path}")
        return ckpt_path

    # Piper model URLs (official)
    base_urls = {
        "piper-tts/hi_IN-swara-medium": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
            "hi/hi_IN/swara/medium/hi_IN-swara-medium.onnx"
        ),
    }

    if model_name in base_urls:
        url = base_urls[model_name]
        print(f"  Downloading base model: {model_name}")
        subprocess.run([
            "wget", "-q", "-O", os.path.join(model_dir, "model.onnx"), url
        ], check=False)
    else:
        print(f"  WARNING: Base model {model_name} not in registry. "
              f"Training from scratch (needs more data).")

    return model_dir


def phonemize_dataset(dataset_dir: str) -> str:
    """Convert text metadata to phonemes using espeak-ng."""
    metadata_path = os.path.join(dataset_dir, "metadata.csv")
    phoneme_path = os.path.join(dataset_dir, "metadata_phonemes.csv")

    try:
        from piper_phonemize import phonemize_espeak
        print("  Phonemizing with piper_phonemize...")

        with open(metadata_path, "r", encoding="utf-8") as fin, \
             open(phoneme_path, "w", encoding="utf-8") as fout:

            for line in fin:
                parts = line.strip().split("|", 1)
                if len(parts) != 2:
                    continue
                uid, text = parts

                try:
                    phonemes = phonemize_espeak(text, "hi")
                    fout.write(f"{uid}|{phonemes[0] if phonemes else text}\n")
                except Exception:
                    # Fall back to character-level
                    fout.write(f"{uid}|{text}\n")

        print(f"  Phonemized: {phoneme_path}")

    except ImportError:
        print("  WARNING: piper_phonemize not available.")
        print("  Using character-level tokenization (still works for Devanagari).")
        # Copy metadata as-is
        import shutil
        shutil.copy2(metadata_path, phoneme_path)

    return phoneme_path


def run_training(dataset_dir: str, training_config: dict, output_dir: str):
    """Run Piper VITS fine-tuning."""
    epochs = training_config.get("epochs", 1000)
    batch_size = training_config.get("batch_size", 16)
    lr = training_config.get("learning_rate", 0.0001)
    base_model = training_config.get("base_model", "")

    print(f"\n{'='*60}")
    print(f"Starting Piper fine-tuning")
    print(f"  Dataset: {dataset_dir}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Learning rate: {lr}")
    print(f"  Base model: {base_model}")
    print(f"{'='*60}\n")

    # Try using Piper's training script
    piper_train = os.path.join("piper", "src", "python", "piper_train",
                               "__main__.py")

    if os.path.exists(piper_train):
        cmd = [
            sys.executable, piper_train,
            "--dataset-dir", dataset_dir,
            "--accelerator", "gpu" if _has_gpu() else "cpu",
            "--devices", "1",
            "--batch-size", str(batch_size),
            "--validation-split", "0.1",
            "--max-epochs", str(epochs),
            "--checkpoint-epochs", str(training_config.get("save_every_n_epochs", 100)),
            "--precision", "16" if training_config.get("fp16", True) and _has_gpu() else "32",
        ]

        if base_model and os.path.exists(os.path.join(output_dir, "base_model")):
            cmd.extend(["--resume-from-checkpoint",
                         os.path.join(output_dir, "base_model", "checkpoint.ckpt")])

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("\nTraining complete!")
            return True
    else:
        print("Piper training scripts not found.")
        print("This script is designed to run on Google Colab after cloning Piper.")
        print("\nTo train locally:")
        print("  1. git clone https://github.com/rhasspy/piper.git")
        print("  2. pip install -e piper/src/python/")
        print("  3. Re-run this script")

    return False


def export_onnx(training_output_dir: str, export_dir: str) -> str:
    """Export the trained model to ONNX format for mobile/desktop inference."""
    os.makedirs(export_dir, exist_ok=True)

    # Find the best checkpoint
    ckpt_files = list(Path(training_output_dir).glob("**/*.ckpt"))
    if not ckpt_files:
        print("No checkpoint files found. Training may not have completed.")
        return ""

    # Sort by epoch (latest)
    best_ckpt = sorted(ckpt_files)[-1]
    print(f"Exporting from checkpoint: {best_ckpt}")

    export_script = os.path.join("piper", "src", "python", "piper_train",
                                 "export_onnx.py")
    onnx_path = os.path.join(export_dir, "stotra_voice.onnx")

    if os.path.exists(export_script):
        cmd = [
            sys.executable, export_script,
            "--model", str(best_ckpt),
            "--output", onnx_path,
        ]
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0 and os.path.exists(onnx_path):
            size_mb = os.path.getsize(onnx_path) / (1024 * 1024)
            print(f"ONNX model exported: {onnx_path} ({size_mb:.1f} MB)")
            return onnx_path
    else:
        print("Export script not found. Manual export needed:")
        print(f"  python -m piper_train.export_onnx --model {best_ckpt} --output {onnx_path}")

    return ""


def _has_gpu() -> bool:
    """Check if GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Piper TTS on stotra recordings")
    parser.add_argument("--dataset", required=True,
                        help="Path to Piper dataset (from generate_piper_config.py)")
    parser.add_argument("--epochs", type=int, help="Override number of epochs")
    parser.add_argument("--output", default=None,
                        help="Output directory for trained model")
    parser.add_argument("--install", action="store_true",
                        help="Install dependencies first")
    parser.add_argument("--export-only", action="store_true",
                        help="Only export ONNX from existing checkpoint")
    args = parser.parse_args()

    if args.output is None:
        args.output = os.path.join(args.dataset, "output")

    # Load training config
    config_path = os.path.join(args.dataset, "training_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            training_config = json.load(f)
    else:
        training_config = dict(TRAINING_CONFIG)

    if args.epochs:
        training_config["epochs"] = args.epochs

    # Load stats
    stats_path = os.path.join(args.dataset, "training_stats.json")
    if os.path.exists(stats_path):
        with open(stats_path, "r") as f:
            stats = json.load(f)
        print(f"Dataset: {stats.get('total_utterances', '?')} utterances, "
              f"{stats.get('total_duration_min', '?')} min")
        if not stats.get("piper_ready", False):
            print("WARNING: Dataset may be too small for good results.")
            print("         Consider adding more recordings.")

    if args.install or IN_COLAB:
        install_piper_training()

    if args.export_only:
        onnx_path = export_onnx(args.output, os.path.join(args.output, "export"))
        if onnx_path:
            print(f"\nONNX model: {onnx_path}")
            print("Copy this to your app's assets for offline inference.")
        return

    # Step 1: Download base model
    base_model = training_config.get("base_model", "")
    if base_model:
        download_base_model(base_model, args.output)

    # Step 2: Phonemize
    phonemize_dataset(args.dataset)

    # Step 3: Train
    success = run_training(args.dataset, training_config, args.output)

    if success:
        # Step 4: Export ONNX
        onnx_path = export_onnx(args.output, os.path.join(args.output, "export"))
        if onnx_path:
            print(f"\n{'='*60}")
            print(f"TRAINING COMPLETE!")
            print(f"  ONNX model: {onnx_path}")
            print(f"  Size: {os.path.getsize(onnx_path)/(1024*1024):.1f} MB")
            print(f"\nNext steps:")
            print(f"  1. Copy {onnx_path} to mobile app assets")
            print(f"  2. Wire into TtsEngineManager as highest-priority verse engine")
            print(f"  3. Test with: python synthesize.py --model {onnx_path} --text 'ॐ नमः शिवाय'")
            print(f"{'='*60}")


TRAINING_CONFIG = {
    "batch_size": 16,
    "learning_rate": 0.0001,
    "epochs": 1000,
    "warmup_epochs": 50,
    "grad_clip": 1.0,
    "fp16": True,
    "save_every_n_epochs": 100,
    "eval_every_n_epochs": 50,
    "base_model": "piper-tts/hi_IN-swara-medium",
    "max_phoneme_length": 300,
    "max_audio_length_sec": 15.0,
}


if __name__ == "__main__":
    main()
