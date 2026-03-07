#!/usr/bin/env python3
"""
FEAT-50: Transcript Alignment Pipeline

Aligns stotra transcript text to audio segments produced by preprocess_audio.py.
Uses verse structure (shloka numbers, ॥ markers) to map transcript lines to
audio segments. This creates the text↔audio pairs needed for Piper fine-tuning.

Strategy:
  1. Parse transcript → list of verse units (each shloka = one unit)
  2. Load segments.json from preprocessed audio
  3. Match verses to segments using:
     a. Verse count ↔ segment count ratio
     b. Duration-proportional assignment (longer verses ↔ longer audio)
  4. Output: aligned dataset with (audio_path, text, duration) tuples

Usage:
    python align_transcript.py \\
        --segments ../data/processed/ShriRamRakshaStotra/segments.json \\
        --transcript ../../recordings/ShreeRamRakshaStotram.txt \\
        --output ../data/aligned/ShriRamRakshaStotra/
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ── Verse parsing patterns ──────────────────────────────────────────────────
# Match shloka numbers like ॥१॥, ॥ 3 ॥, ॥१२॥, ||14||
SHLOKA_NUM_RE = re.compile(r'॥\s*\d+\s*॥|॥\s*[०-९]+\s*॥|\|\|\s*\d+\s*\|\|')

# Match double danda (verse end marker)
DOUBLE_DANDA_RE = re.compile(r'॥')

# Section headers
SECTION_RE = re.compile(r'॥\s*(?:अथ|इति)\s+.*?॥')


def parse_transcript(filepath: str) -> list:
    """Parse a stotra transcript into verse units.

    Returns list of dicts: [{text, verse_num, line_count, char_count}]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Split at shloka number markers (॥N॥)
    # Each chunk between markers is one verse
    parts = SHLOKA_NUM_RE.split(raw_text)
    numbers = SHLOKA_NUM_RE.findall(raw_text)

    verses = []
    for i, part in enumerate(parts):
        text = part.strip()
        if not text:
            continue

        # Clean up: remove section headers, normalize whitespace
        text = SECTION_RE.sub('', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Skip very short fragments (like "ॐ" alone or just a title)
        if len(text) < 10:
            # But keep it as metadata (title/invocation)
            if any(c in text for c in 'ॐ।॥'):
                verses.append({
                    "text": text,
                    "verse_num": 0,
                    "type": "invocation",
                    "char_count": len(text),
                })
            continue

        verse_num = 0
        if i < len(numbers):
            # Extract number from the marker that follows this text
            num_str = numbers[i] if i < len(numbers) else ""
            # Parse Devanagari or ASCII digits
            digits = re.findall(r'[0-9]+|[०-९]+', num_str)
            if digits:
                d = digits[0]
                # Convert Devanagari digits
                d = d.translate(str.maketrans('०१२३४५६७८९', '0123456789'))
                verse_num = int(d)

        verses.append({
            "text": text,
            "verse_num": verse_num,
            "type": "verse",
            "char_count": len(text),
        })

    return verses


def parse_transcript_by_double_danda(filepath: str) -> list:
    """Alternative parser: split at ॥ (double danda) for texts without numbered verses."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Split at double danda but keep meaningful chunks
    chunks = re.split(r'॥', raw_text)
    verses = []
    num = 0
    for chunk in chunks:
        text = chunk.strip()
        text = re.sub(r'\s+', ' ', text)
        # Skip if just a number or too short
        if not text or len(text) < 10:
            continue
        if re.match(r'^[0-9०-९\s]+$', text):
            continue
        num += 1
        verses.append({
            "text": text,
            "verse_num": num,
            "type": "verse",
            "char_count": len(text),
        })

    return verses


def align_verses_to_segments(verses: list, segments: list) -> list:
    """Align verse text to audio segments.

    Uses proportional character-count mapping: longer verses get
    proportionally more audio segments.
    """
    n_verses = len(verses)
    n_segments = len(segments)

    if n_verses == 0 or n_segments == 0:
        return []

    aligned = []

    if n_verses == n_segments:
        # Perfect 1:1 match
        for v, s in zip(verses, segments):
            aligned.append({
                "segment_id": s["id"],
                "audio_file": s["file"],
                "text": v["text"],
                "verse_num": v["verse_num"],
                "start_sec": s["start_sec"],
                "end_sec": s["end_sec"],
                "duration_sec": s["duration_sec"],
                "alignment": "exact",
            })
    elif n_segments > n_verses:
        # More segments than verses: group segments per verse (proportional)
        total_chars = sum(v["char_count"] for v in verses)
        if total_chars == 0:
            return []

        seg_idx = 0
        for v in verses:
            # Proportion of total text this verse represents
            proportion = v["char_count"] / total_chars
            n_segs = max(1, round(proportion * n_segments))
            # Don't exceed remaining segments
            n_segs = min(n_segs, n_segments - seg_idx)
            if n_segs <= 0:
                continue

            group = segments[seg_idx:seg_idx + n_segs]
            seg_idx += n_segs

            # Merge segment info
            aligned.append({
                "segment_id": group[0]["id"],
                "audio_files": [s["file"] for s in group],
                "text": v["text"],
                "verse_num": v["verse_num"],
                "start_sec": group[0]["start_sec"],
                "end_sec": group[-1]["end_sec"],
                "duration_sec": round(group[-1]["end_sec"] - group[0]["start_sec"], 3),
                "alignment": f"merged_{len(group)}_segments",
            })

        # Assign remaining segments to last verse
        if seg_idx < n_segments and aligned:
            remaining = segments[seg_idx:]
            last = aligned[-1]
            existing = last.get("audio_files", [last["audio_file"]] if "audio_file" in last else [])
            last["audio_files"] = existing + [s["file"] for s in remaining]
            last["end_sec"] = remaining[-1]["end_sec"]
            last["duration_sec"] = round(last["end_sec"] - last["start_sec"], 3)

    else:
        # More verses than segments: group verses per segment
        total_dur = sum(s["duration_sec"] for s in segments)
        if total_dur == 0:
            return []

        verse_idx = 0
        for s in segments:
            proportion = s["duration_sec"] / total_dur
            n_vrs = max(1, round(proportion * n_verses))
            n_vrs = min(n_vrs, n_verses - verse_idx)
            if n_vrs <= 0:
                continue

            group = verses[verse_idx:verse_idx + n_vrs]
            verse_idx += n_vrs

            combined_text = " ॥ ".join(v["text"] for v in group)
            aligned.append({
                "segment_id": s["id"],
                "audio_file": s["file"],
                "text": combined_text,
                "verse_num": group[0]["verse_num"],
                "start_sec": s["start_sec"],
                "end_sec": s["end_sec"],
                "duration_sec": s["duration_sec"],
                "alignment": f"merged_{len(group)}_verses",
            })

        # Assign remaining verses to last segment
        if verse_idx < n_verses and aligned:
            remaining_text = " ॥ ".join(v["text"] for v in verses[verse_idx:])
            aligned[-1]["text"] += " ॥ " + remaining_text

    return aligned


def create_piper_metadata(aligned: list, output_dir: str) -> str:
    """Create Piper-compatible metadata.csv.

    Format: audio_file|text (pipe-separated, no header)
    Audio files must be relative paths to WAVs.
    """
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "metadata.csv")

    with open(csv_path, "w", encoding="utf-8") as f:
        for entry in aligned:
            audio = entry.get("audio_file", entry.get("audio_files", [""])[0])
            # Strip .wav extension for Piper convention
            audio_id = Path(audio).stem
            text = entry["text"]
            # Clean text for TTS training: remove verse markers, normalize
            text = re.sub(r'[॥।\|]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                f.write(f"{audio_id}|{text}\n")

    return csv_path


def main():
    parser = argparse.ArgumentParser(description="Align stotra transcripts to audio segments")
    parser.add_argument("--segments", required=True, help="Path to segments.json from preprocess_audio.py")
    parser.add_argument("--transcript", required=True, help="Path to transcript .txt file")
    parser.add_argument("--output", default=None, help="Output directory for aligned data")
    parser.add_argument("--method", choices=["numbered", "danda"], default="numbered",
                        help="Verse parsing method: numbered (॥N॥) or danda (split at ॥)")
    args = parser.parse_args()

    # Load segments
    with open(args.segments, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    segments = manifest["segments"]
    print(f"Loaded {len(segments)} audio segments from {args.segments}")

    # Parse transcript
    if args.method == "numbered":
        verses = parse_transcript(args.transcript)
        if len(verses) < 3:
            print(f"Only {len(verses)} verses found with numbered method, trying danda split...")
            verses = parse_transcript_by_double_danda(args.transcript)
    else:
        verses = parse_transcript_by_double_danda(args.transcript)

    print(f"Parsed {len(verses)} verse units from {args.transcript}")

    if not verses:
        print("ERROR: No verses parsed from transcript.")
        sys.exit(1)

    # Align
    aligned = align_verses_to_segments(verses, segments)
    print(f"Aligned {len(aligned)} text↔audio pairs")

    # Output
    if args.output is None:
        args.output = os.path.join(os.path.dirname(args.segments), "aligned")
    os.makedirs(args.output, exist_ok=True)

    # Save alignment
    align_path = os.path.join(args.output, "alignment.json")
    with open(align_path, "w", encoding="utf-8") as f:
        json.dump(aligned, f, ensure_ascii=False, indent=2)
    print(f"Alignment saved: {align_path}")

    # Create Piper metadata
    csv_path = create_piper_metadata(aligned, args.output)
    print(f"Piper metadata: {csv_path}")

    # Summary
    total_dur = sum(a["duration_sec"] for a in aligned)
    avg_dur = total_dur / len(aligned) if aligned else 0
    print(f"\nSummary:")
    print(f"  Pairs: {len(aligned)}")
    print(f"  Total audio: {total_dur:.1f}s ({total_dur/60:.1f} min)")
    print(f"  Avg duration: {avg_dur:.1f}s")
    print(f"  Text coverage: {sum(len(a['text']) for a in aligned)} chars")

    # Show sample
    print(f"\nSample alignments:")
    for a in aligned[:5]:
        text_preview = a["text"][:60] + "..." if len(a["text"]) > 60 else a["text"]
        print(f"  [{a['verse_num']:3d}] {a['duration_sec']:5.1f}s | {text_preview}")


if __name__ == "__main__":
    main()
