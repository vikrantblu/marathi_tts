#!/usr/bin/env python3
"""
FEAT-50: Master Pipeline — Process recordings into TTS training data.

Runs the full pipeline end-to-end:
  1. Preprocess audio (normalize, segment at verse boundaries)
  2. Align transcripts to audio segments
  3. Validate dataset quality
  4. Generate Piper-compatible training config

Usage:
    python run_pipeline.py --recordings ../../recordings --output ../data/piper_dataset

    # Skip steps already completed:
    python run_pipeline.py --recordings ../../recordings --output ../data/piper_dataset --skip preprocess

    # Just validate:
    python run_pipeline.py --recordings ../../recordings --output ../data/piper_dataset --only validate
"""

import argparse
import json
import os
import subprocess
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _run_step(name: str, script_name: str, args: list):
    """Run a pipeline step as a subprocess."""
    print(f"\n{'='*60}")
    print(f"  Step: {name}")
    print(f"{'='*60}")
    t0 = time.time()

    script_path = os.path.join(_SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"  Script not found: {script_path}")
        return False

    cmd = [sys.executable, script_path] + args
    print(f"  Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - t0

    if result.returncode == 0:
        print(f"\n  [{name}] DONE ({elapsed:.1f}s)")
        return True
    else:
        print(f"\n  [{name}] FAILED (exit code {result.returncode})")
        return False


def find_recording_pairs(recordings_dir: str) -> list:
    """Find matching audio + transcript pairs in the recordings directory."""
    audio_exts = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
    text_exts = {".txt"}

    audio_files = {}
    text_files = {}

    for name in os.listdir(recordings_dir):
        path = os.path.join(recordings_dir, name)
        if not os.path.isfile(path):
            continue
        base, ext = os.path.splitext(name)
        ext = ext.lower()
        if ext in audio_exts:
            audio_files[base.lower()] = path
        elif ext in text_exts:
            text_files[base.lower()] = path

    # Match by name similarity
    pairs = []
    matched_texts = set()

    for audio_key, audio_path in audio_files.items():
        best_text = None
        best_score = 0

        for text_key, text_path in text_files.items():
            if text_key in matched_texts:
                continue

            # Simple similarity: shared character ratio
            shorter = min(len(audio_key), len(text_key))
            if shorter == 0:
                continue

            common = 0
            for a, b in zip(audio_key.lower(), text_key.lower()):
                if a == b:
                    common += 1
                else:
                    break

            score = common / shorter
            if score > best_score:
                best_score = score
                best_text = (text_key, text_path)

        if best_text and best_score > 0.3:
            pairs.append({
                "audio": audio_path,
                "transcript": best_text[1],
                "name": os.path.splitext(os.path.basename(audio_path))[0],
            })
            matched_texts.add(best_text[0])
        else:
            # Audio without matching transcript
            pairs.append({
                "audio": audio_path,
                "transcript": None,
                "name": os.path.splitext(os.path.basename(audio_path))[0],
            })

    return pairs


def main():
    parser = argparse.ArgumentParser(
        description="Run the full TTS training data pipeline")
    parser.add_argument("--recordings", required=True,
                        help="Directory containing audio + transcript files")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: ../data/piper_dataset)")
    parser.add_argument("--skip", nargs="*", default=[],
                        choices=["preprocess", "align", "validate", "config"],
                        help="Skip specific steps")
    parser.add_argument("--only", default=None,
                        choices=["preprocess", "align", "validate", "config"],
                        help="Run only a specific step")
    args = parser.parse_args()

    recordings_dir = os.path.abspath(args.recordings)
    if not os.path.isdir(recordings_dir):
        print(f"ERROR: Recordings directory not found: {recordings_dir}")
        sys.exit(1)

    if args.output is None:
        args.output = os.path.join(_SCRIPT_DIR, "..", "data", "piper_dataset")
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    segments_dir = os.path.join(output_dir, "segments")
    os.makedirs(segments_dir, exist_ok=True)

    # Find recording pairs
    pairs = find_recording_pairs(recordings_dir)
    print(f"\nFound {len(pairs)} recording(s) in {recordings_dir}:")
    for p in pairs:
        has_text = "+" if p["transcript"] else "-"
        print(f"  [{has_text}] {p['name']}")
        print(f"      Audio: {p['audio']}")
        if p["transcript"]:
            print(f"      Text:  {p['transcript']}")

    if not pairs:
        print("ERROR: No audio files found.")
        sys.exit(1)

    steps = ["preprocess", "align", "validate", "config"]
    if args.only:
        steps = [args.only]
    steps = [s for s in steps if s not in (args.skip or [])]

    results = {}
    overall_ok = True

    # ── Step 1: Preprocess audio ──
    if "preprocess" in steps:
        # preprocess_audio.py --input-dir <recordings_dir> --output-dir <segments_dir>
        step_args = [
            "--input-dir", recordings_dir,
            "--output-dir", segments_dir,
        ]
        ok = _run_step("Preprocess Audio", "preprocess_audio.py", step_args)
        results["preprocess"] = ok
        if not ok:
            overall_ok = False

    # ── Step 2: Align transcripts ──
    if "align" in steps:
        for pair in pairs:
            if not pair["transcript"]:
                print(f"\n  SKIP align for {pair['name']} (no transcript)")
                continue
            seg_json = os.path.join(segments_dir, pair["name"], "segments.json")
            if not os.path.exists(seg_json):
                print(f"\n  SKIP align for {pair['name']} (no segments.json)")
                continue
            step_args = [
                "--segments", seg_json,
                "--transcript", pair["transcript"],
                "--output", os.path.join(segments_dir, pair["name"]),
            ]
            ok = _run_step(
                f"Align: {pair['name']}",
                "align_transcript.py",
                step_args
            )
            results[f"align_{pair['name']}"] = ok
            if not ok:
                overall_ok = False

    # ── Step 3: Validate ──
    if "validate" in steps:
        # validate_dataset.py --data-dir <segments_dir> --output <report.json>
        report_path = os.path.join(output_dir, "validation_report.json")
        step_args = [
            "--data-dir", segments_dir,
            "--output", report_path,
        ]
        ok = _run_step("Validate", "validate_dataset.py", step_args)
        results["validate"] = ok
        if not ok:
            overall_ok = False

    # ── Step 4: Generate Piper config ──
    if "config" in steps:
        # generate_piper_config.py --aligned-dir <segments_dir> --output-dir <output_dir>
        step_args = [
            "--aligned-dir", segments_dir,
            "--output-dir", output_dir,
        ]
        ok = _run_step("Generate Piper Config", "generate_piper_config.py",
                        step_args)
        results["config"] = ok
        if not ok:
            overall_ok = False

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'='*60}")
    for step_name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {step_name}")

    print(f"\n  Output: {output_dir}")
    if overall_ok:
        print(f"  Status: ALL STEPS PASSED")
        print(f"\n  Next: Train the model:")
        print(f"    python train_piper.py --dataset {output_dir}")
    else:
        print(f"  Status: SOME STEPS FAILED")
        print(f"  Check logs above for details.")

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
