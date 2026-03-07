#!/usr/bin/env python3
"""
FEAT-50: Training Dataset Validator

Validates the aligned dataset for Piper fine-tuning readiness.
Checks: audio quality, text consistency, duration ranges, silence ratios,
and produces a quality report.

Usage:
    python validate_dataset.py --alignment ../data/aligned/ShriRamRakshaStotra/alignment.json
    python validate_dataset.py --data-dir ../data/aligned/  (validate all)
"""

import argparse
import json
import os
import sys
from pathlib import Path

import librosa
import numpy as np


# ── Quality thresholds ──────────────────────────────────────────────────────
MIN_DURATION = 1.0      # Minimum segment duration (seconds)
MAX_DURATION = 15.0     # Maximum segment duration (seconds)
IDEAL_MIN = 2.0         # Ideal range lower bound
IDEAL_MAX = 12.0        # Ideal range upper bound
MIN_TEXT_LEN = 5        # Minimum text length (chars)
MAX_SILENCE_RATIO = 0.4 # Max fraction of segment that's silence
MIN_SNR_DB = 10         # Minimum signal-to-noise ratio (dB)
TARGET_SR = 22050


def compute_snr(y: np.ndarray) -> float:
    """Estimate SNR by comparing speech energy to silence energy."""
    # Use energy percentiles
    frame_len = 1024
    hop = 512
    energy = []
    for i in range(0, len(y) - frame_len, hop):
        frame = y[i:i + frame_len]
        energy.append(np.sqrt(np.mean(frame ** 2)))
    energy = np.array(energy)
    if len(energy) < 2:
        return 0.0

    # Bottom 10% = noise estimate, top 10% = signal estimate
    sorted_e = np.sort(energy)
    noise = np.mean(sorted_e[:max(1, len(sorted_e) // 10)])
    signal = np.mean(sorted_e[-(len(sorted_e) // 10):])

    if noise <= 0:
        return 60.0  # Very clean
    return 20 * np.log10(signal / noise)


def compute_silence_ratio(y: np.ndarray, sr: int, thresh_db: float = -35) -> float:
    """Fraction of audio that is silence."""
    frame_len = int(sr * 0.025)  # 25ms
    hop = int(sr * 0.010)  # 10ms

    rms_peak = np.sqrt(np.mean(y ** 2))
    if rms_peak <= 0:
        return 1.0
    thresh = rms_peak * (10 ** (thresh_db / 20))

    silent_frames = 0
    total_frames = 0
    for i in range(0, len(y) - frame_len, hop):
        frame = y[i:i + frame_len]
        rms = np.sqrt(np.mean(frame ** 2))
        if rms < thresh:
            silent_frames += 1
        total_frames += 1

    return silent_frames / total_frames if total_frames > 0 else 1.0


def validate_entry(entry: dict, audio_dir: str) -> dict:
    """Validate a single aligned entry."""
    issues = []
    warnings = []

    audio_file = entry.get("audio_file", "")
    if isinstance(audio_file, list):
        audio_file = audio_file[0]
    audio_path = os.path.join(audio_dir, audio_file) if audio_file else None

    text = entry.get("text", "")
    duration = entry.get("duration_sec", 0)

    # Text checks
    if len(text) < MIN_TEXT_LEN:
        issues.append(f"Text too short ({len(text)} chars)")

    has_devanagari = any('\u0900' <= c <= '\u097F' for c in text)
    if not has_devanagari:
        issues.append("No Devanagari text found")

    # Duration checks
    if duration < MIN_DURATION:
        issues.append(f"Too short ({duration:.1f}s < {MIN_DURATION}s)")
    elif duration > MAX_DURATION:
        issues.append(f"Too long ({duration:.1f}s > {MAX_DURATION}s)")
    elif duration < IDEAL_MIN:
        warnings.append(f"Short ({duration:.1f}s < {IDEAL_MIN}s ideal)")
    elif duration > IDEAL_MAX:
        warnings.append(f"Long ({duration:.1f}s > {IDEAL_MAX}s ideal)")

    # Audio quality checks (if file exists)
    snr = 0.0
    silence_ratio = 0.0
    if audio_path and os.path.exists(audio_path):
        try:
            y, sr = librosa.load(audio_path, sr=TARGET_SR, mono=True)
            snr = compute_snr(y)
            silence_ratio = compute_silence_ratio(y, sr)

            if snr < MIN_SNR_DB:
                warnings.append(f"Low SNR ({snr:.1f} dB)")
            if silence_ratio > MAX_SILENCE_RATIO:
                warnings.append(f"High silence ({silence_ratio:.0%})")
        except Exception as e:
            issues.append(f"Audio load error: {e}")
    elif audio_path:
        issues.append(f"Audio file missing: {audio_file}")

    # Characters per second (speech rate consistency)
    if duration > 0:
        cps = len(text) / duration
        if cps > 20:
            warnings.append(f"Very fast speech rate ({cps:.0f} chars/s)")
        elif cps < 2:
            warnings.append(f"Very slow speech rate ({cps:.0f} chars/s)")

    return {
        "segment_id": entry.get("segment_id", "?"),
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "snr_db": round(snr, 1),
        "silence_ratio": round(silence_ratio, 3),
        "chars_per_sec": round(len(text) / duration, 1) if duration > 0 else 0,
    }


def validate_alignment(align_path: str) -> dict:
    """Validate an entire alignment file."""
    with open(align_path, "r", encoding="utf-8") as f:
        aligned = json.load(f)

    audio_dir = os.path.dirname(align_path)
    # Audio files are in parent (processed) directory
    parent_dir = os.path.dirname(audio_dir)
    # Try multiple possible audio locations
    possible_dirs = [audio_dir, parent_dir, os.path.join(parent_dir, "..")]

    results = []
    for entry in aligned:
        # Find the audio file
        audio_file = entry.get("audio_file", "")
        if isinstance(audio_file, list):
            audio_file = audio_file[0]

        found_dir = audio_dir
        for d in possible_dirs:
            if os.path.exists(os.path.join(d, audio_file)):
                found_dir = d
                break

        result = validate_entry(entry, found_dir)
        results.append(result)

    n_valid = sum(1 for r in results if r["valid"])
    n_total = len(results)
    n_warnings = sum(1 for r in results if r["warnings"])
    avg_snr = np.mean([r["snr_db"] for r in results]) if results else 0

    return {
        "alignment_file": align_path,
        "total_entries": n_total,
        "valid_entries": n_valid,
        "entries_with_warnings": n_warnings,
        "invalid_entries": n_total - n_valid,
        "avg_snr_db": round(avg_snr, 1),
        "piper_ready": n_valid >= n_total * 0.8,  # 80%+ valid = ready
        "details": results,
    }


def print_report(report: dict):
    """Pretty-print validation report."""
    print(f"\n{'='*60}")
    print(f"Dataset Validation Report")
    print(f"{'='*60}")
    print(f"Source: {report['alignment_file']}")
    print(f"Total entries: {report['total_entries']}")
    print(f"Valid: {report['valid_entries']} ({report['valid_entries']/max(1,report['total_entries']):.0%})")
    print(f"Warnings: {report['entries_with_warnings']}")
    print(f"Invalid: {report['invalid_entries']}")
    print(f"Avg SNR: {report['avg_snr_db']:.1f} dB")
    print(f"Piper-ready: {'YES ✓' if report['piper_ready'] else 'NO ✗'}")

    # Show issues
    problem_entries = [r for r in report["details"] if not r["valid"] or r["warnings"]]
    if problem_entries:
        print(f"\nEntries needing attention:")
        for r in problem_entries[:20]:  # Show first 20
            status = "INVALID" if not r["valid"] else "WARNING"
            msgs = r["issues"] + r["warnings"]
            print(f"  [{status:7s}] {r['segment_id']}: {'; '.join(msgs)}")

    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Validate aligned training dataset")
    parser.add_argument("--alignment", help="Path to alignment.json")
    parser.add_argument("--data-dir", help="Validate all alignment.json files in a directory tree")
    parser.add_argument("--output", help="Save report to JSON file")
    args = parser.parse_args()

    reports = []

    if args.alignment:
        report = validate_alignment(args.alignment)
        reports.append(report)
        print_report(report)

    elif args.data_dir:
        for root, dirs, files in os.walk(args.data_dir):
            for f in files:
                if f == "alignment.json":
                    path = os.path.join(root, f)
                    report = validate_alignment(path)
                    reports.append(report)
                    print_report(report)
    else:
        parser.error("Provide --alignment or --data-dir")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        print(f"\nFull report saved: {args.output}")

    # Overall summary
    if len(reports) > 1:
        total_valid = sum(r["valid_entries"] for r in reports)
        total_all = sum(r["total_entries"] for r in reports)
        all_ready = all(r["piper_ready"] for r in reports)
        print(f"\nOverall: {total_valid}/{total_all} entries valid, "
              f"Piper-ready: {'YES ✓' if all_ready else 'NO ✗'}")

    # Exit code
    if reports and all(r["piper_ready"] for r in reports):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
