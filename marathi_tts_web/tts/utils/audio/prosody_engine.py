"""
Marathi Prosody Engine — Natural Pause & Intonation for TTS
===========================================================
Since gTTS does not support SSML, this engine works at the **audio level**:
it splits text at natural pause points, generates audio for each segment,
and stitches them together with calibrated silence gaps.

This produces human-like speech with proper breathing pauses, clause breaks,
sentence boundaries, and paragraph transitions — matching how a Marathi
speaker actually talks.
"""
import re
import logging
from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Optional
from tts.constants.audio_constants import (
    PauseType, CONJUNCTIONS, CLAUSE_STARTERS, VOCATIVES,
    QUOTE_VERBS, EMPHASIS_WORDS,
    SENTENCE_ENDINGS, INTERNAL_PUNCTUATION,
    VERSE_MIN_LINES,
)

logger = logging.getLogger(__name__)

# Lazy import — MetreEngine is a pure-Python module with no heavy deps
_metre_engine_cls = None

def _get_metre_engine():
    """Return a cached MetreEngine instance (imported lazily)."""
    global _metre_engine_cls
    if _metre_engine_cls is None:
        try:
            from tts.utils.phonetic.metre_engine import MetreEngine
            _metre_engine_cls = MetreEngine()
            logger.debug('MetreEngine loaded')
        except Exception as _e:
            logger.warning('MetreEngine unavailable: %s', _e)
            _metre_engine_cls = False  # sentinel — don't retry
    return _metre_engine_cls if _metre_engine_cls else None


@dataclass
class TextSegment:
    """A piece of text with the pause that should follow it."""
    text: str
    pause_after_ms: int = PauseType.NONE
    emotion: str = 'neutral'
    emphasis: float = 1.0       # 1.0 = normal, >1 = louder/slower
    pitch_shift: float = 0.0    # semitones shift for this segment
    is_verse: bool = False      # True = recitation/chanting mode (slow, melodic)
    metre_name: str = ''        # e.g. 'anushtubh', 'ovi', 'abhanga' — set by MetreEngine
    tts_rate: float = 1.0       # speaking rate hint for this segment (used by TTS engine)


# ── Marathi-specific linguistic patterns (imported from tts.constants.audio_constants) ──


class MarathiProsodyEngine:
    """Split text into segments with calibrated pauses for human-like speech."""

    # ── FEAT-9: Emotion → verse prosody modifier table ──────────────────
    # Maps detected emotion to (rate_multiplier, pitch_shift_st, pause_scale)
    # Applied only to verse segments so stotra recitation adapts to emotion.
    _EMOTION_VERSE_MODIFIERS = {
        'devotional': (0.90, -1.0, 1.2),   # slower, deeper, longer pauses
        'peaceful':   (0.85,  0.0, 1.3),   # slowest, neutral pitch, longest pauses
        'happy':      (1.05, +1.0, 0.9),   # slightly upbeat
        'love':       (0.92, -0.5, 1.1),   # warm, slightly slower
        'sad':        (0.88, -1.5, 1.25),  # very slow, deep
        'neutral':    (1.0,   0.0, 1.0),   # no modification
    }

    def __init__(self, speaking_rate: float = 1.0, emotion: str = 'neutral'):
        """
        Args:
            speaking_rate: 1.0 = normal. Lower = slower with longer pauses.
            emotion: detected emotion label (e.g. 'devotional', 'peaceful').
                     Used by FEAT-9 to adjust verse prosody.
        """
        self.speaking_rate = speaking_rate
        self.emotion = emotion.lower() if emotion else 'neutral'

    def segment_text(self, text: str) -> List[TextSegment]:
        """Break text into natural segments with appropriate pauses.

        This is the main entry point — it returns a list of TextSegments
        that the TTS engine should synthesize individually, inserting
        the specified pause (silence) between each.
        
        Verse/shloka detection: if a paragraph has 2+ lines ending with ॥,
        the entire paragraph is treated as verse/recitation mode — segments
        get is_verse=True, slower pauses, and the TTS engine will use
        slow=True for a chanting quality.
        """
        if not text or not text.strip():
            return []

        # Step 1: Split into paragraphs
        paragraphs = self._split_paragraphs(text)
        segments: List[TextSegment] = []

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue

            # Check if this paragraph is a verse block
            is_verse_block = self._is_verse_block(para)

            if is_verse_block:
                # Verse mode: segment each verse line individually
                verse_segments = self._segment_verse_block(para)
                # Metre detection: override pauses & rate per detected metre
                self._apply_metre_prosody(para, verse_segments)
                # FEAT-9: Emotion-adaptive prosody for verse mode
                self._apply_emotion_verse_modifiers(verse_segments)
                segments.extend(verse_segments)
            else:
                # Prose mode: normal clause/sentence segmentation
                sentences = self._split_sentences(para)

                for j, sentence in enumerate(sentences):
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    clause_segments = self._split_into_clauses(sentence)
                    segments.extend(clause_segments)

                    if segments:
                        end_pause = self._get_sentence_end_pause(sentence)
                        segments[-1].pause_after_ms = max(
                            segments[-1].pause_after_ms, end_pause
                        )

            # Paragraph/stanza break
            if segments and i < len(paragraphs) - 1:
                if is_verse_block:
                    segments[-1].pause_after_ms = max(
                        segments[-1].pause_after_ms,
                        PauseType.VERSE_STANZA
                    )
                else:
                    segments[-1].pause_after_ms = max(
                        segments[-1].pause_after_ms,
                        PauseType.PARAGRAPH
                    )

        # Step 4: Apply speaking rate scaling
        if self.speaking_rate != 1.0:
            rate_factor = 1.0 / self.speaking_rate
            for seg in segments:
                seg.pause_after_ms = int(seg.pause_after_ms * rate_factor)

        # Step 5: Mark emphasis
        self._apply_emphasis(segments)

        return segments

    # ── Verse Detection & Segmentation ──────────────────────────────────

    # ── Metre-aware Prosody ─────────────────────────────────────────────

    def _apply_metre_prosody(self, paragraph: str,
                              segments: List[TextSegment]) -> None:
        """Detect the metre of a verse paragraph and adjust segment pauses.

        Mutates ``segments`` in-place: overrides ``pause_after_ms``,
        ``tts_rate``, ``metre_name``, and ``pitch_shift`` fields based on
        the detected metre.  Also applies Ovi rhythmic pulse (FEAT-7) and
        pitch contour from MetreDefinition (FEAT-11).
        Falls back gracefully if MetreEngine is unavailable.
        """
        engine = _get_metre_engine()
        if engine is None or not segments:
            return

        try:
            prosody = engine.detect(paragraph)
            if prosody is None:
                return

            logger.debug(
                'Metre detected: %s (rate=%.2f, half=%dms, full=%dms)',
                prosody.name, prosody.rate,
                prosody.pause_half_ms, prosody.pause_full_ms
            )

            # Apply metre-specific pauses to all segments
            engine.apply_to_segments(segments, prosody)

            # Also propagate rate & metre_name into each segment
            for seg in segments:
                seg.tts_rate = prosody.rate
                if not seg.metre_name:
                    seg.metre_name = prosody.name

            # ── FEAT-7: Ovi rhythmic pulse ──────────────────────────────
            # Ovi has a 4-line stanza: lines 1-3 flow at the same tempo,
            # line 4 (cadence) slows down with a longer concluding pause.
            if prosody.name == 'Ovi' and len(segments) >= 4:
                self._apply_ovi_rhythmic_pulse(segments)

            # ── FEAT-11: Pitch contour from MetreDefinition ─────────────
            # Apply wave/falling/rising/level pitch contour across segments
            # within each stanza for musical verse recitation quality.
            contour = prosody.metre.pitch_contour
            if contour and contour != 'level':
                self._apply_pitch_contour(segments, contour, prosody.metre.padas)
            # ── FEAT-6: Yati caesura pauses ───────────────────────────────
            # Split verse segments at metre-defined caesura (yati) positions.
            # Each half-verse gets its own TTS call with pause_yati_ms between.
            if prosody.metre.yati_syllables:
                self._apply_yati_splits(segments, prosody)

            # ── FEAT-13: Abhanga refrain detection ───────────────────────
            # Detect repeat lines (धृवपद) in Abhanga verse and mark with
            # extra emphasis + pitch boost (call-response musical effect).
            if prosody.metre.name == 'Abhanga':
                self._detect_abhanga_refrain(segments)
        except Exception as exc:
            logger.warning('MetreEngine.detect() failed: %s', exc)

    def _apply_ovi_rhythmic_pulse(self, segments: List[TextSegment]) -> None:
        """FEAT-7: Apply Ovi 4-line rhythmic pulse.

        Ovi stanza: lines 1-3 flow (same tempo), line 4 cadence (slower).
        Line 4 gets lower tts_rate and longer pause for conclusive feel.
        Between stanzas: extra-long pause with pitch reset.
        """
        # Process in groups of 4 (each stanza)
        for base in range(0, len(segments), 4):
            stanza = segments[base:base + 4]
            for i, seg in enumerate(stanza):
                if i < 3:
                    # Lines 1-3: flowing, musical
                    seg.tts_rate = 0.82
                    seg.pause_after_ms = min(seg.pause_after_ms, 400) if seg.pause_after_ms > 0 else 400
                else:
                    # Line 4: cadence — slower, conclusive
                    seg.tts_rate = 0.75
                    seg.pause_after_ms = max(seg.pause_after_ms, 800)

            # Stanza break after line 4
            if len(stanza) == 4:
                stanza[-1].pause_after_ms = max(stanza[-1].pause_after_ms, 1200)

    def _apply_pitch_contour(self, segments: List[TextSegment],
                              contour: str, padas: int) -> None:
        """FEAT-11: Apply pitch contour pattern across verse segments.

        Contour types:
          'wave'    — alternating +0.5/-0.5 semitones (gentle melodic wave)
          'falling' — progressive -0.3st per segment within stanza (descent)
          'rising'  — progressive +0.3st per segment (invocatory/celebratory)
          'level'   — no change (prose-like)

        Applied within each stanza (group of `padas` segments) so the
        contour resets per verse unit.
        """
        stanza_size = max(padas, 2)

        for base in range(0, len(segments), stanza_size):
            stanza = segments[base:base + stanza_size]
            for i, seg in enumerate(stanza):
                if contour == 'wave':
                    # Odd segments up, even segments down
                    seg.pitch_shift += 0.5 if (i % 2 == 0) else -0.5
                elif contour == 'falling':
                    # Progressive descent within stanza
                    seg.pitch_shift += -0.3 * i
                elif contour == 'rising':
                    # Progressive ascent within stanza
                    seg.pitch_shift += 0.3 * i

    def _apply_emotion_verse_modifiers(self, segments: List[TextSegment]) -> None:
        """FEAT-9: Adjust verse prosody based on detected emotion.

        Maps emotions to (rate_multiplier, pitch_shift, pause_scale) using
        the _EMOTION_VERSE_MODIFIERS table.  Applied on top of metre prosody
        so that a 'devotional' stotra is recited slower & deeper than a
        'happy' celebratory one.

        Only modifies verse segments (is_verse=True).
        """
        mods = self._EMOTION_VERSE_MODIFIERS.get(self.emotion)
        if mods is None or self.emotion == 'neutral':
            return  # no modification for unknown or neutral emotions

        rate_mult, pitch_st, pause_scale = mods
        for seg in segments:
            if seg.is_verse:
                seg.tts_rate *= rate_mult
                seg.pitch_shift += pitch_st
                seg.pause_after_ms = int(seg.pause_after_ms * pause_scale)

    # ── FEAT-6: Yati caesura pause splitting ─────────────────────────────────

    def _split_pada_at_yati(self, text: str,
                            yati_positions: List[int]) -> List[str]:
        """Split verse text at metre-defined yati (caesura) syllable positions.

        Uses word-boundary approximation: accumulates syllable count per word
        until each target position is reached or exceeded, then splits at the
        word boundary.  This avoids unpronounceable mid-word splits while
        still placing the pause close to the correct metrical position.

        Returns a list of text parts.  Returns [text] unchanged if splitting
        is not possible (too short, missing imports, etc.).
        """
        if not yati_positions or not text:
            return [text]
        words = text.split()
        if len(words) <= 1:
            return [text]
        try:
            from tts.utils.phonetic.metre_engine import count_syllables
        except ImportError:
            return [text]

        targets  = sorted(set(yati_positions))
        splits   = []   # word indices (exclusive upper bound) where we cut
        syl_sum  = 0
        t_idx    = 0
        for w_idx, word in enumerate(words):
            syl_sum += count_syllables(word)
            if t_idx < len(targets) and syl_sum >= targets[t_idx]:
                splits.append(w_idx + 1)
                t_idx += 1
                if t_idx >= len(targets):
                    break

        if not splits:
            return [text]

        parts = []
        prev = 0
        for sp in splits:
            chunk = ' '.join(words[prev:sp]).strip()
            if chunk:
                parts.append(chunk)
            prev = sp
        tail = ' '.join(words[prev:]).strip()
        if tail:
            parts.append(tail)
        return parts if len(parts) > 1 else [text]

    def _apply_yati_splits(self, segments: List[TextSegment],
                           prosody: 'MetreProsody') -> None:
        """FEAT-6: Insert yati pause sub-segments within verse lines.

        For each verse segment, attempts to split it at the metre-defined
        yati syllable positions and inserts a pause of ``pause_yati_ms``
        between the resulting halves.  Modifies the ``segments`` list
        in-place (may increase its length).
        """
        yati_ms  = prosody.metre.pause_yati_ms
        positions = prosody.metre.yati_syllables
        if not positions:
            return

        new_segs: List[TextSegment] = []
        for seg in segments:
            if not seg.is_verse or not seg.text.strip():
                new_segs.append(seg)
                continue
            parts = self._split_pada_at_yati(seg.text, positions)
            if len(parts) <= 1:
                new_segs.append(seg)
                continue
            for j, part in enumerate(parts):
                part = part.strip()
                if not part:
                    continue
                is_last = (j == len(parts) - 1)
                new_segs.append(TextSegment(
                    text=part,
                    pause_after_ms=seg.pause_after_ms if is_last else yati_ms,
                    is_verse=True,
                    metre_name=seg.metre_name,
                    tts_rate=seg.tts_rate,
                    emphasis=seg.emphasis,
                    pitch_shift=seg.pitch_shift,
                ))
        segments[:] = new_segs

    # ── FEAT-13: Abhanga refrain detection ──────────────────────────────────

    def _detect_abhanga_refrain(self, segments: List[TextSegment]) -> None:
        """FEAT-13: Mark धृवपद (refrain) lines in Abhanga verse.

        In kirtan/bhajan performance, the refrain line repeats across stanzas.
        Detects segments whose stripped text appears 2+ times across the full
        segment list and applies a slight emphasis boost + pitch lift so the
        recurring line feels familiar and call-like (like a human cantor
        singing the same refrain line in each verse).
        """
        if len(segments) < 4:
            return

        # Count exact text occurrences
        counts: dict = {}
        for seg in segments:
            key = seg.text.strip()
            counts[key] = counts.get(key, 0) + 1

        # Also check rhyme-based refrain: same last 2 Devanagari chars
        # (handles minor spelling variation like trailing ‌)
        dev_suffix: dict = {}
        for seg in segments:
            dev = [c for c in seg.text if '\u0900' <= c <= '\u097F']
            suf = ''.join(dev[-2:]) if len(dev) >= 2 else ''
            if suf:
                dev_suffix[suf] = dev_suffix.get(suf, 0) + 1

        for seg in segments:
            exact_count = counts.get(seg.text.strip(), 0)
            dev = [c for c in seg.text if '\u0900' <= c <= '\u097F']
            suf = ''.join(dev[-2:]) if len(dev) >= 2 else ''
            rhyme_count = dev_suffix.get(suf, 0)

            # Refrain if same line appears 2+ times OR same suffix appears 3+ times
            if exact_count >= 2 or rhyme_count >= 3:
                seg.emphasis = max(seg.emphasis, 1.1)
                seg.pitch_shift += 0.5

    def _is_verse_block(self, paragraph: str) -> bool:
        """Detect if a paragraph is structured verses (ovi/shloka/abhanga).
        
        Works on flat text (no newlines) by counting ॥ markers.
        A verse block has VERSE_MIN_LINES (2+) occurrences of ॥.
        In verse text, ॥ appears at the end of every couplet/verse.
        """
        # Count ॥ occurrences
        danda_count = paragraph.count('॥')
        return danda_count >= VERSE_MIN_LINES

    def _segment_verse_block(self, paragraph: str) -> List[TextSegment]:
        """Segment a verse block into individual verse lines for recitation.
        
        Works on flat text (post-grammar, no newlines) by splitting
        at । and ॥ markers.
        
        Half-verse (।) gets VERSE_HALF pause, full verse (॥) gets VERSE_FULL.
        Section headers like ॥श्री स्वामी समर्थ॥ are kept as single segments.
        """
        segments: List[TextSegment] = []
        
        # Split at दंड markers, keeping the delimiters
        parts = re.split(r'([।॥])', paragraph)
        
        i = 0
        while i < len(parts):
            verse_text = parts[i].strip()
            danda = parts[i + 1].strip() if i + 1 < len(parts) else ''
            
            if not verse_text:
                # Lone danda (e.g., ॥ at the very start) — check for header
                if danda == '॥' and i + 2 < len(parts):
                    # Look ahead for ॥...॥ pattern (section header)
                    header_text = parts[i + 2].strip() if i + 2 < len(parts) else ''
                    next_danda = parts[i + 3].strip() if i + 3 < len(parts) else ''
                    
                    if header_text and next_danda == '॥':
                        # Section header: ॥ header_text ॥
                        segments.append(TextSegment(
                            text=header_text,
                            pause_after_ms=PauseType.VERSE_STANZA,
                            is_verse=True,
                            emphasis=1.1,
                        ))
                        i += 4  # skip: empty + ॥ + header + ॥
                        continue
                i += 2
                continue
            
            # Normal verse line
            if danda == '॥':
                pause = PauseType.VERSE_FULL
            elif danda == '।':
                pause = PauseType.VERSE_HALF
            else:
                pause = PauseType.VERSE_HALF  # default for verse lines
            
            segments.append(TextSegment(
                text=verse_text,
                pause_after_ms=pause,
                is_verse=True,
            ))
            
            i += 2  # advance past text + danda
        
        return segments

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split at double newlines or section breaks."""
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Split at blank lines
        paras = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paras if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """Split text at sentence boundaries (Marathi punctuation aware).

        Preserves the sentence-ending marker with the sentence.
        """
        # Split at Devanagari danda, double danda, period, ?, !
        # But not at abbreviation dots (preceded by single letter)
        parts = re.split(r'([।॥.?!…])', text)

        sentences = []
        current = ''
        for part in parts:
            if part in SENTENCE_ENDINGS:
                current += part
                sentences.append(current.strip())
                current = ''
            else:
                current += part

        if current.strip():
            sentences.append(current.strip())

        return sentences

    def _split_into_clauses(self, sentence: str) -> List[TextSegment]:
        """Split a sentence at clause boundaries & punctuation.

        Returns TextSegments with appropriate pause_after_ms.
        """
        segments: List[TextSegment] = []

        # First, split at internal punctuation (commas, semicolons, dashes)
        # Use a regex that keeps the delimiter attached to the preceding text
        parts = re.split(r'([,;:—–])', sentence)

        # Reassemble: attach delimiter back to preceding text
        assembled = []
        for i, part in enumerate(parts):
            if part in INTERNAL_PUNCTUATION:
                if assembled:
                    assembled[-1] += part
                else:
                    assembled.append(part)
            else:
                assembled.append(part)

        # Now process each comma-separated chunk for conjunction breaks
        for chunk in assembled:
            chunk = chunk.strip()
            if not chunk:
                continue

            # Determine pause from trailing punctuation
            trailing_pause = PauseType.NONE
            for punct, pause in INTERNAL_PUNCTUATION.items():
                if chunk.endswith(punct):
                    trailing_pause = pause
                    break

            # Split at conjunctions within this chunk
            sub_segments = self._split_at_conjunctions(chunk)

            for k, sub in enumerate(sub_segments):
                seg = TextSegment(text=sub.strip())
                if k < len(sub_segments) - 1:
                    # Internal conjunction pause
                    seg.pause_after_ms = PauseType.CONJUNCTION
                else:
                    # Last sub-segment gets the trailing punctuation pause
                    seg.pause_after_ms = trailing_pause
                if seg.text:
                    segments.append(seg)

        return segments

    def _split_at_conjunctions(self, text: str) -> List[str]:
        """Split text at Marathi conjunctions, keeping the conjunction
        attached to the following clause (as in natural speech).
        
        Also splits at natural phrase boundaries:
        - Postpositions that mark clause ends (मध्ये, साठी, etc.)
        - Quotation verbs (म्हणाला, म्हणून, etc.)
        - Long phrases (8+ words) get split at the midpoint conjunction
        """
        words = text.split()
        parts = []
        current: List[str] = []

        for word in words:
            clean_word = re.sub(r'[,;:।॥.?!]', '', word)
            if clean_word in CONJUNCTIONS and current:
                parts.append(' '.join(current))
                current = [word]
            elif clean_word in CLAUSE_STARTERS and current:
                parts.append(' '.join(current))
                current = [word]
            elif clean_word in QUOTE_VERBS and current:
                # Split before quotation verbs for natural phrasing
                current.append(word)
                parts.append(' '.join(current))
                current = []
            else:
                current.append(word)

        if current:
            parts.append(' '.join(current))

        # Second pass: split any very long phrases (8+ words) at a
        # natural break point if one exists
        refined = []
        for part in parts:
            part_words = part.split()
            if len(part_words) >= 8:
                mid = len(part_words) // 2
                # Look for a conjunction or postposition near the midpoint
                best_split = None
                for i in range(max(0, mid - 2), min(len(part_words), mid + 3)):
                    clean = re.sub(r'[,;:।॥.?!]', '', part_words[i])
                    if clean in CONJUNCTIONS or clean in CLAUSE_STARTERS:
                        best_split = i
                        break
                if best_split is not None:
                    refined.append(' '.join(part_words[:best_split]))
                    refined.append(' '.join(part_words[best_split:]))
                else:
                    refined.append(part)
            else:
                refined.append(part)

        return refined

    def _get_sentence_end_pause(self, sentence: str) -> int:
        """Determine the pause for the end of a sentence."""
        sentence = sentence.rstrip()
        for marker, pause in SENTENCE_ENDINGS.items():
            if sentence.endswith(marker):
                return pause
        return PauseType.SENTENCE  # default

    def _apply_emphasis(self, segments: List[TextSegment]):
        """Mark segments for emphasis, question intonation, and vocative pauses."""
        for seg in segments:
            words = set(re.sub(r'[,;:।॥.?!]', '', seg.text).split())
            if words & EMPHASIS_WORDS:
                seg.emphasis = 1.15  # slightly louder / slower
            if words & VOCATIVES:
                seg.emphasis = 1.1
                # Add a micro-pause after vocatives
                if seg.pause_after_ms < PauseType.COMMA:
                    seg.pause_after_ms = PauseType.COMMA

            # Question intonation: apply slight pitch shift for questions
            if seg.text.rstrip().endswith('?') or seg.text.rstrip().endswith('का'):
                seg.pitch_shift = 1.5  # slight upward pitch at end

            # Exclamatory: boost emphasis
            if seg.text.rstrip().endswith('!'):
                seg.emphasis = max(seg.emphasis, 1.2)

    # ── Utility ────────────────────────────────────────────────────────────

    def get_total_duration_estimate(self, segments: List[TextSegment]) -> float:
        """Estimate total pause duration in seconds (not including speech)."""
        return sum(s.pause_after_ms for s in segments) / 1000.0

    def describe_segments(self, segments: List[TextSegment]) -> str:
        """Debug helper: show segments with pause annotations."""
        lines = []
        for i, seg in enumerate(segments):
            pause_label = ''
            if seg.pause_after_ms > 0:
                pause_label = f'  [{seg.pause_after_ms}ms]'
            emph = ' *emphasis*' if seg.emphasis > 1.0 else ''
            verse = ' 🎵verse' if seg.is_verse else ''
            lines.append(f"  [{i+1}] \"{seg.text}\"{pause_label}{emph}{verse}")
        return '\n'.join(lines)
