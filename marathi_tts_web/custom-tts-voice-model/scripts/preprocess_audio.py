#!/usr/bin/env python3
"""
FEAT-50: Audio Preprocessing Pipeline for Stotra Voice Training

Converts raw MP3 recordings to normalized WAV segments aligned to verse
boundaries. Uses silence detection to split at natural pause points
(between shlokas/verses).

Usage:
    python preprocess_audio.py --input-dir ../../recordings --output-dir ../data/processed
    python preprocess_audio.py --file ../../recordings/ShriRamRakshaStotra.mp3

Output: WAV files (22050 Hz, mono, 16-bit) in output-dir, one per detected segment.
Also produces a segments.json manifest for downstream alignment.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


# ── Audio normalization parameters ──────────────────────────────────────────
TARGET_SR = 22050       # Piper/VITS standard sample rate
TARGET_DB = -20.0       # Target RMS loudness in dB
MIN_SEGMENT_SEC = 2.0   # Minimum segment duration (skip very short fragments)
MAX_SEGMENT_SEC = 15.0  # Maximum segment duration (force-split longer ones)

# ── Silence detection parameters ──────────────────────────────────────────
SILENCE_THRESH_DB = -35  # dB below peak to consider silence
MIN_SILENCE_MS = 400     # Minimum silence gap to split at (verse boundaries)
SILENCE_HOP_MS = 50      # Hop size for silence detection window


def load_and_normalize(filepath: str) -> tuple:
    """Load audio file, convert to mono 22050 Hz, normalize loudness."""
    try:
        y, sr = librosa.load(filepath, sr=TARGET_SR, mono=True)
    except Exception:
        # Fallback: use pydub (ffmpeg) to decode, then load from WAV
        import tempfile
        from pydub import AudioSegment
        audio = AudioSegment.from_file(filepath)
        audio = audio.set_frame_rate(TARGET_SR).set_channels(1).set_sample_width(2)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        audio.export(tmp_path, format="wav")
        try:
            y, sr = librosa.load(tmp_path, sr=TARGET_SR, mono=True)
        finally:
            os.unlink(tmp_path)

    # Trim leading/trailing silence
    y, _ = librosa.effects.trim(y, top_db=30)

    # Normalize RMS loudness
    rms = np.sqrt(np.mean(y ** 2))
    if rms > 0:
        target_rms = 10 ** (TARGET_DB / 20)
        y = y * (target_rms / rms)

    # Clip to prevent overflow
    y = np.clip(y, -1.0, 1.0)

    return y, TARGET_SR


def detect_silence_regions(y: np.ndarray, sr: int,
                           silence_thresh_db: int = None,
                           min_silence_ms: int = None) -> list:
    """Find silence regions in audio using energy thresholding."""
    if silence_thresh_db is None:
        silence_thresh_db = SILENCE_THRESH_DB
    if min_silence_ms is None:
        min_silence_ms = MIN_SILENCE_MS

    hop_samples = int(sr * SILENCE_HOP_MS / 1000)
    win_samples = hop_samples * 4  # Window = 4x hop

    # Compute short-time energy
    energy = []
    for i in range(0, len(y) - win_samples, hop_samples):
        frame = y[i:i + win_samples]
        rms = np.sqrt(np.mean(frame ** 2))
        energy.append(rms)

    energy = np.array(energy)
    if len(energy) == 0:
        return []

    # Convert threshold from dB relative to peak energy
    peak_energy = np.max(energy)
    if peak_energy <= 0:
        return []
    thresh = peak_energy * (10 ** (silence_thresh_db / 20))

    # Find contiguous silence regions
    is_silent = energy < thresh
    regions = []
    start = None
    for i, s in enumerate(is_silent):
        if s and start is None:
            start = i
        elif not s and start is not None:
            dur_ms = (i - start) * SILENCE_HOP_MS
            if dur_ms >= min_silence_ms:
                start_sec = start * SILENCE_HOP_MS / 1000
                end_sec = i * SILENCE_HOP_MS / 1000
                regions.append((start_sec, end_sec))
            start = None

    # Handle trailing silence
    if start is not None:
        dur_ms = (len(is_silent) - start) * SILENCE_HOP_MS
        if dur_ms >= min_silence_ms:
            start_sec = start * SILENCE_HOP_MS / 1000
            end_sec = len(is_silent) * SILENCE_HOP_MS / 1000
            regions.append((start_sec, end_sec))

    return regions


def split_at_silence(y: np.ndarray, sr: int, silence_regions: list) -> list:
    """Split audio at silence midpoints, returning (start_sec, end_sec) per segment."""
    total_dur = len(y) / sr
    if not silence_regions:
        return [(0.0, total_dur)]

    segments = []
    prev_end = 0.0

    for sil_start, sil_end in silence_regions:
        midpoint = (sil_start + sil_end) / 2
        seg_dur = midpoint - prev_end
        if seg_dur >= MIN_SEGMENT_SEC:
            segments.append((prev_end, midpoint))
        elif segments:
            # Merge short segment with previous
            segments[-1] = (segments[-1][0], midpoint)
        prev_end = midpoint

    # Add final segment
    if total_dur - prev_end >= MIN_SEGMENT_SEC:
        segments.append((prev_end, total_dur))
    elif segments:
        segments[-1] = (segments[-1][0], total_dur)

    # Force-split segments exceeding MAX_SEGMENT_SEC
    final_segments = []
    for start, end in segments:
        dur = end - start
        if dur <= MAX_SEGMENT_SEC:
            final_segments.append((start, end))
        else:
            n_splits = int(np.ceil(dur / MAX_SEGMENT_SEC))
            chunk = dur / n_splits
            for i in range(n_splits):
                final_segments.append((start + i * chunk, start + (i + 1) * chunk))

    return final_segments


def process_file(filepath: str, output_dir: str, file_id: str = None) -> dict:
    """Process a single audio file: normalize, segment, export WAVs."""
    filepath = os.path.abspath(filepath)
    if file_id is None:
        file_id = Path(filepath).stem

    print(f"\n{'='*60}")
    print(f"Processing: {Path(filepath).name}")
    print(f"{'='*60}")

    # Load and normalize
    print("  Loading and normalizing audio...")
    y, sr = load_and_normalize(filepath)
    total_dur = len(y) / sr
    print(f"  Duration: {total_dur:.1f}s ({total_dur/60:.1f} min), SR: {sr} Hz")

    # Detect silence regions (adaptive: retry with more sensitive params if no gaps found)
    print("  Detecting silence regions...")
    silence_regions = detect_silence_regions(y, sr)
    print(f"  Found {len(silence_regions)} silence gaps (≥{MIN_SILENCE_MS}ms, thresh={SILENCE_THRESH_DB}dB)")

    if not silence_regions:
        adaptive_configs = [
            (-28, 300), (-25, 250), (-22, 200), (-20, 150),
        ]
        for thresh_db, min_ms in adaptive_configs:
            print(f"  Retrying with thresh={thresh_db}dB, min_silence={min_ms}ms...")
            silence_regions = detect_silence_regions(y, sr,
                                                     silence_thresh_db=thresh_db,
                                                     min_silence_ms=min_ms)
            print(f"  Found {len(silence_regions)} silence gaps")
            if len(silence_regions) >= 3:
                break

    # Split at verse boundaries
    segments = split_at_silence(y, sr, silence_regions)
    print(f"  Split into {len(segments)} segments")

    # Export segments
    os.makedirs(output_dir, exist_ok=True)
    manifest = {
        "source_file": filepath,
        "file_id": file_id,
        "sample_rate": sr,
        "total_duration_sec": total_dur,
        "segments": []
    }

    for i, (start, end) in enumerate(segments):
        seg_id = f"{file_id}_{i:04d}"
        out_path = os.path.join(output_dir, f"{seg_id}.wav")

        start_sample = int(start * sr)
        end_sample = int(end * sr)
        segment_audio = y[start_sample:end_sample]

        sf.write(out_path, segment_audio, sr, subtype='PCM_16')

        seg_info = {
            "id": seg_id,
            "file": f"{seg_id}.wav",
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(end - start, 3),
        }
        manifest["segments"].append(seg_info)
        dur = end - start
        print(f"    [{i:3d}] {start:7.2f}s - {end:7.2f}s  ({dur:.1f}s)  -> {seg_id}.wav")

    print(f"\n  Total segments: {len(manifest['segments'])}")
    durations = [s["duration_sec"] for s in manifest["segments"]]
    if durations:
        print(f"  Duration range: {min(durations):.1f}s - {max(durations):.1f}s")
        print(f"  Mean duration: {np.mean(durations):.1f}s")

    return manifest


def main():
    global SILENCE_THRESH_DB, MIN_SILENCE_MS

    parser = argparse.ArgumentParser(description="Preprocess stotra recordings for voice training")
    parser.add_argument("--input-dir", help="Directory with MP3 recordings")
    parser.add_argument("--file", help="Single MP3 file to process")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: ../data/processed)")
    parser.add_argument("--min-silence-ms", type=int, default=MIN_SILENCE_MS,
                        help=f"Minimum silence gap for splitting (default: {MIN_SILENCE_MS}ms)")
    parser.add_argument("--silence-thresh-db", type=int, default=SILENCE_THRESH_DB,
                        help=f"Silence threshold in dB below peak (default: {SILENCE_THRESH_DB})")
    args = parser.parse_args()

    # Apply CLI overrides to module-level globals
    SILENCE_THRESH_DB = args.silence_thresh_db
    MIN_SILENCE_MS = args.min_silence_ms

    if args.output_dir is None:
        args.output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

    files = []
    if args.file:
        files.append(args.file)
    elif args.input_dir:
        for f in sorted(os.listdir(args.input_dir)):
            if f.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg', '.flac')):
                files.append(os.path.join(args.input_dir, f))
    else:
        parser.error("Provide --input-dir or --file")

    if not files:
        print("No audio files found.")
        sys.exit(1)

    print(f"Found {len(files)} audio file(s) to process")

    all_manifests = []
    for filepath in files:
        file_id = Path(filepath).stem
        out_subdir = os.path.join(args.output_dir, file_id)
        manifest = process_file(filepath, out_subdir, file_id)
        all_manifests.append(manifest)

        # Save per-file manifest
        manifest_path = os.path.join(out_subdir, "segments.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"  Manifest: {manifest_path}")

    # Save combined manifest
    combined_path = os.path.join(args.output_dir, "all_segments.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_manifests, f, ensure_ascii=False, indent=2)
    print(f"\nCombined manifest: {combined_path}")

    # Summary
    total_segs = sum(len(m["segments"]) for m in all_manifests)
    total_dur = sum(m["total_duration_sec"] for m in all_manifests)
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(all_manifests)} files, {total_segs} segments, {total_dur/60:.1f} min total")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
