"""
Marathi & Sanskrit Metre Detection Engine
==========================================
Detects the verse metre (छंद / chhand) of Marathi and Sanskrit text and
returns the prosody parameters (rate, pitch contour, pause pattern) that
make TTS sound like a *human reciter* of that metre — not a machine.

WHY METRE MATTERS FOR TTS
--------------------------
Each metre has a fixed rhythmic contract with the listener.
  • Anushtubh  (अनुष्टुभ्): 8 syllables/pāda, 4 pādas/shloka.
    Recited with a clear 4-stress pulse. The 5th syllable is the pivot.
  • Mandākrāntā (मन्दाक्रान्ता): 17 syllables/pāda. Slow, "creeping" feel.
  • Shārdūlavikrīḍita: 19 syllables/pāda. Stately, lion-paced.
  • Ovi (ओवी): Marathi — 4 lines, lines 1-3 rhyme, 4 is shorter cadence.
  • Abhanga (अभंग): 4 lines, complex rhyme scheme. Tukaram, Eknath.
  • Arya (आर्या): Semi-metrical, used in Meghaduta. Alternates 12+18 mātrās.

Reading ANY of these at prose-speed sounds robotic.
Reading them at proper metre-tempo with the correct pause pattern sounds human.

PROSODY PARAMETERS RETURNED
----------------------------
The engine returns a ``MetreProsody`` object with:
  rate          : float   — speaking rate multiplier (0.7=slow, 1.0=normal, 1.1=brisk)
  pause_half_ms : int     — pause at half-verse (ardha-shloka / danda) in ms
  pause_full_ms : int     — pause at full-verse / stanza end in ms
  pause_yati_ms : int     — pause at metrical caesura (yati) within a pāda
  pitch_contour : str     — "rising", "falling", "level", "wave"
  slow_mode     : bool    — True → gTTS slow=True (recitation mode)
  note          : str     — human-readable description for logs

USAGE
-----
    from tts.utils.phonetic.metre_engine import MetreEngine

    engine = MetreEngine()
    metre  = engine.detect(verse_text)
    engine.apply_to_segments(segments, metre)   # modifies TextSegment list in-place
"""
from __future__ import annotations

import re
import math
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from tts.utils.audio.prosody_engine import TextSegment

log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════
# Syllable counting helpers
# ══════════════════════════════════════════════════════════════════════════

_HALANT  = '\u094D'   # ्
_MATRA_RE = re.compile(r'[\u093E-\u094C\u0902\u0901]')  # matras + anusvara/chandrabindu
_CONS_RE  = re.compile(r'[\u0915-\u0939\u0933]')        # consonants

def count_syllables(pada: str) -> int:
    """Count syllables (akshara) in a Devanagari pāda.

    Each syllable = one vowel event (independent vowel or consonant + matra
    or consonant with implicit schwa, but NOT consonant+halant which has no vowel).

    This is an approximation sufficient for metre detection:
      - Each matra  = 1 syllable event
      - Each anusvara/chandrabindu = counts with its vowel (already in matra count)
      - Each independent vowel = 1 syllable
      - Each consonant-without-matra-or-halant = 1 syllable (implicit schwa)
      - Consonant+halant = 0 additional syllables (part of cluster)
    """
    count = 0
    i = 0
    while i < len(pada):
        ch = pada[i]
        if '\u0904' <= ch <= '\u0914':    # independent vowel (अ–औ)
            count += 1
            i += 1
        elif '\u0915' <= ch <= '\u0939' or ch == '\u0933':   # consonant
            # Look ahead
            if i + 1 < len(pada) and pada[i + 1] == _HALANT:
                # consonant + halant = cluster, no vowel — skip both
                i += 2
            elif i + 1 < len(pada) and '\u093E' <= pada[i + 1] <= '\u094C':
                # consonant + matra = 1 syllable
                count += 1
                i += 2
            else:
                # consonant with implicit schwa = 1 syllable
                count += 1
                i += 1
        elif '\u093E' <= ch <= '\u094C':  # lone matra (shouldn't happen but tolerate)
            count += 1
            i += 1
        elif ch in ('\u0902', '\u0901'):  # anusvara/chandrabindu — part of prev syllable
            i += 1
        else:
            i += 1
    return max(count, 0)


def count_maatras(pada: str) -> int:
    """Count mātrā (mora) weight of a pāda for quantitative metres.

    Short vowel = 1 mātrā (laghu: अ, इ, उ, ऋ)
    Long vowel  = 2 mātrā (guru: आ, ई, ऊ, ए, ऐ, ओ, औ, anusvara, visarga)
    Consonant cluster at start of syllable makes it heavy (saṃyoga-guru).
    """
    maatras = 0
    i = 0
    while i < len(pada):
        ch = pada[i]
        # Short independent vowels
        if ch in ('अ', 'इ', 'उ', 'ऋ'):
            maatras += 1
            i += 1
        # Long independent vowels
        elif ch in ('आ', 'ई', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ', 'ॠ'):
            maatras += 2
            i += 1
        elif '\u0915' <= ch <= '\u0939' or ch == '\u0933':
            if i + 1 < len(pada) and pada[i + 1] == _HALANT:
                i += 2  # cluster — weight counted with following syllable
            elif i + 1 < len(pada):
                matra = pada[i + 1]
                if matra in ('ि', 'ु', 'ृ'):      # short matra
                    maatras += 1
                    i += 2
                elif '\u093E' <= matra <= '\u094C':  # long matra
                    maatras += 2
                    i += 2
                else:
                    maatras += 1   # implicit short schwa
                    i += 1
            else:
                maatras += 1
                i += 1
        elif ch == '\u0902' or ch == '\u0903':   # anusvara/visarga = guru
            maatras += 1   # adds weight to previous syllable
            i += 1
        else:
            i += 1
    return maatras


# ══════════════════════════════════════════════════════════════════════════
# Metre definitions
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class MetreDefinition:
    """Describes one metre's syllable pattern and prosody parameters."""
    name: str                     # Metre name in English
    marathi_name: str             # Metre name in Marathi/Sanskrit
    padas: int                    # Pādas per śloka (verse unit)
    syllables_per_pada: int       # Expected syllables per pāda (0 = variable/mātrābased)
    maatras_per_pada: int         # Expected mātrās per pāda (0 = silabic)
    is_marathi: bool = False      # True = Marathi folk/bhakti metre
    # Prosody parameters
    rate: float = 0.82            # Speaking rate multiplier
    pause_half_ms: int = 650      # Pause at half-verse
    pause_full_ms: int = 1100     # Pause at full-verse
    pause_yati_ms: int = 200      # Internal caesura pause
    pitch_contour: str = 'wave'   # 'rising', 'falling', 'level', 'wave'
    slow_mode: bool = True        # Use gTTS slow=True
    note: str = ''


# Metre catalogue — ordered by detection priority (most specific first)
METRE_CATALOGUE: List[MetreDefinition] = [

    # ── Sanskrit samavritta (syllabic metres) ────────────────────────
    MetreDefinition(
        name='Shardula-vikridita',
        marathi_name='शार्दूलविक्रीडित',
        padas=4, syllables_per_pada=19, maatras_per_pada=0,
        rate=0.78, pause_half_ms=700, pause_full_ms=1200, pause_yati_ms=250,
        pitch_contour='wave', slow_mode=True,
        note='Stately, lion-gait metre — used in Mahimna Stotra, Shivanandalahari'
    ),
    MetreDefinition(
        name='Vasanta-tilaka',
        marathi_name='वसन्ततिलक',
        padas=4, syllables_per_pada=14, maatras_per_pada=0,
        rate=0.82, pause_half_ms=600, pause_full_ms=1100, pause_yati_ms=220,
        pitch_contour='wave', slow_mode=True,
        note='Spring-tile metre — lyrical, medium pace'
    ),
    MetreDefinition(
        name='Mandakranta',
        marathi_name='मन्दाक्रान्ता',
        padas=4, syllables_per_pada=17, maatras_per_pada=0,
        rate=0.76, pause_half_ms=750, pause_full_ms=1300, pause_yati_ms=280,
        pitch_contour='falling', slow_mode=True,
        note='Slow-creeping metre — Meghaduta, Kumarasambhava'
    ),
    MetreDefinition(
        name='Malini',
        marathi_name='मालिनी',
        padas=4, syllables_per_pada=15, maatras_per_pada=0,
        rate=0.80, pause_half_ms=650, pause_full_ms=1100, pause_yati_ms=240,
        pitch_contour='wave', slow_mode=True,
        note='Garland metre — Amarushataka'
    ),
    MetreDefinition(
        name='Anushtubh',
        marathi_name='अनुष्टुभ्',
        padas=4, syllables_per_pada=8, maatras_per_pada=0,
        rate=0.85, pause_half_ms=550, pause_full_ms=900, pause_yati_ms=150,
        pitch_contour='wave', slow_mode=True,
        note='Most common Sanskrit metre — Bhagavad Gita, Ramayana, Mahabharata'
    ),
    MetreDefinition(
        name='Trishtubh',
        marathi_name='त्रिष्टुभ्',
        padas=4, syllables_per_pada=11, maatras_per_pada=0,
        rate=0.83, pause_half_ms=600, pause_full_ms=1050, pause_yati_ms=200,
        pitch_contour='wave', slow_mode=True,
        note='Second most common — Rigveda, Mahabharata'
    ),
    MetreDefinition(
        name='Jagati',
        marathi_name='जगती',
        padas=4, syllables_per_pada=12, maatras_per_pada=0,
        rate=0.83, pause_half_ms=620, pause_full_ms=1050, pause_yati_ms=200,
        pitch_contour='level', slow_mode=True,
        note='12-syllable metre — less common, found in Rigveda'
    ),

    # ── Sanskrit mātric metres (mātrā / morae-based) ─────────────────
    MetreDefinition(
        name='Arya',
        marathi_name='आर्या',
        padas=4, syllables_per_pada=0, maatras_per_pada=30,  # line1=12+18, line2=12+15
        rate=0.80, pause_half_ms=650, pause_full_ms=1000, pause_yati_ms=200,
        pitch_contour='wave', slow_mode=True,
        note='Mātrā-based, lyrical — Amarushataka, Meghaduta epilogue'
    ),

    # ── Marathi metres ────────────────────────────────────────────────
    MetreDefinition(
        name='Ovi',
        marathi_name='ओवी',
        padas=4, syllables_per_pada=0, maatras_per_pada=0, is_marathi=True,
        rate=0.80, pause_half_ms=600, pause_full_ms=1000, pause_yati_ms=180,
        pitch_contour='wave', slow_mode=True,
        note='Dnyaneshwari metre — 4 lines, 1-3 rhyme, line 4 shorter cadence'
    ),
    MetreDefinition(
        name='Abhanga',
        marathi_name='अभंग',
        padas=4, syllables_per_pada=0, maatras_per_pada=0, is_marathi=True,
        rate=0.82, pause_half_ms=580, pause_full_ms=950, pause_yati_ms=160,
        pitch_contour='wave', slow_mode=True,
        note='Bhakti metre — Tukaram, Eknath, Namdev. Rhythmic call-response.'
    ),
    MetreDefinition(
        name='Shloka',       # Generic for unknown Sanskrit verse
        marathi_name='श्लोक',
        padas=2, syllables_per_pada=16, maatras_per_pada=0,
        rate=0.83, pause_half_ms=600, pause_full_ms=1000, pause_yati_ms=180,
        pitch_contour='wave', slow_mode=True,
        note='Generic Sanskrit verse (undetermined specific metre)'
    ),
    MetreDefinition(
        name='Stotra',       # Prose-like devotional verse
        marathi_name='स्तोत्र',
        padas=0, syllables_per_pada=0, maatras_per_pada=0,
        rate=0.80, pause_half_ms=700, pause_full_ms=1100, pause_yati_ms=200,
        pitch_contour='wave', slow_mode=True,
        note='Devotional prose–verse hybrid (e.g. Hanuman Chalisa, Lalitha Sahasranama)'
    ),
    MetreDefinition(
        name='Prose',        # NOT verse — just chanting/recitation of prose
        marathi_name='गद्य',
        padas=0, syllables_per_pada=0, maatras_per_pada=0,
        rate=0.92, pause_half_ms=400, pause_full_ms=700, pause_yati_ms=100,
        pitch_contour='level', slow_mode=False,
        note='Conversational Marathi prose — normal TTS speed'
    ),
]

# Quick lookup by name
_METRE_BY_NAME: Dict[str, MetreDefinition] = {m.name: m for m in METRE_CATALOGUE}
_METRE_BY_MARATHI_NAME: Dict[str, MetreDefinition] = {m.marathi_name: m for m in METRE_CATALOGUE}


# ══════════════════════════════════════════════════════════════════════════
# MetreProsody (result type)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class MetreProsody:
    """Detected metre + its prosody parameters. Passed to the prosody engine."""
    metre: MetreDefinition
    confidence: float = 0.0      # 0.0–1.0 detection confidence
    detected_pada_count: int = 0
    avg_syllables: float = 0.0
    avg_maatras: float = 0.0
    all_lines: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.metre.name

    @property
    def rate(self) -> float:
        return self.metre.rate

    @property
    def slow_mode(self) -> bool:
        return self.metre.slow_mode

    @property
    def pause_half_ms(self) -> int:
        return self.metre.pause_half_ms

    @property
    def pause_full_ms(self) -> int:
        return self.metre.pause_full_ms

    @property
    def pause_yati_ms(self) -> int:
        return self.metre.pause_yati_ms


# Default prosody (prose): used when no verse detected
_PROSE_PROSODY = MetreProsody(
    metre=_METRE_BY_NAME['Prose'],
    confidence=1.0,
)


# ══════════════════════════════════════════════════════════════════════════
# MetreEngine
# ══════════════════════════════════════════════════════════════════════════

class MetreEngine:
    """Detect verse metre and compute prosody parameters for TTS.

    Example::

        engine = MetreEngine()
        prosody = engine.detect(text)
        print(prosody.name, prosody.rate, prosody.slow_mode)
        # → "Anushtubh", 0.85, True
    """

    def detect(self, text: str) -> MetreProsody:
        """Detect the dominant metre of the text.

        Returns a MetreProsody with the best-matching metre and
        confidence score.  Returns Prose prosody if no verse detected.
        """
        if not text or not text.strip():
            return _PROSE_PROSODY

        lines = self._extract_verse_lines(text)
        if len(lines) < 2:
            return _PROSE_PROSODY

        # Count syllables and mātrās per line
        syllable_counts = [count_syllables(l) for l in lines]
        maatra_counts   = [count_maatras(l)   for l in lines]

        avg_syl  = sum(syllable_counts) / len(syllable_counts) if syllable_counts else 0
        avg_maat = sum(maatra_counts)   / len(maatra_counts)   if maatra_counts else 0

        log.debug(
            "Metre detection: %d lines, avg_syl=%.1f, avg_maat=%.1f",
            len(lines), avg_syl, avg_maat
        )

        # ── 1. Marathi-specific markers ─────────────────────────────────
        if self._has_ovi_markers(text):
            return MetreProsody(
                metre=_METRE_BY_NAME['Ovi'],
                confidence=0.9,
                detected_pada_count=len(lines),
                avg_syllables=avg_syl, avg_maatras=avg_maat,
                all_lines=lines,
            )

        if self._has_abhanga_markers(text):
            return MetreProsody(
                metre=_METRE_BY_NAME['Abhanga'],
                confidence=0.88,
                detected_pada_count=len(lines),
                avg_syllables=avg_syl, avg_maatras=avg_maat,
                all_lines=lines,
            )

        # ── 2. Sanskrit syllabic metre matching ─────────────────────────
        best_metre, best_conf = self._match_syllabic_metre(avg_syl, syllable_counts)
        if best_conf >= 0.70:
            return MetreProsody(
                metre=best_metre,
                confidence=best_conf,
                detected_pada_count=len(lines),
                avg_syllables=avg_syl, avg_maatras=avg_maat,
                all_lines=lines,
            )

        # ── 3. Generic stotra / verse fallback ──────────────────────────
        if self._is_verse_text(text):
            return MetreProsody(
                metre=_METRE_BY_NAME['Stotra'],
                confidence=0.70,
                detected_pada_count=len(lines),
                avg_syllables=avg_syl, avg_maatras=avg_maat,
                all_lines=lines,
            )

        return _PROSE_PROSODY

    def apply_to_segments(self, segments: list, prosody: MetreProsody) -> None:
        """Apply metre-derived prosody parameters to TextSegment list in-place.

        This is called by the TTS engine after prosody_engine.segment_text()
        has already assigned initial pause values.  We OVERRIDE with
        metre-specific values where they differ.

        args:
            segments : list of TextSegment objects
            prosody  : MetreProsody from detect()
        """
        if prosody.metre.name == 'Prose':
            return   # nothing to override

        for seg in segments:
            # Apply slow_mode flag (used by gTTS generator)
            seg.is_verse = True

            # Override pause values based on metre
            if seg.pause_after_ms > 0:
                # Scale pauses to metre profile
                # Determine whether this is a half-verse or full-verse pause
                # by checking the current value against thresholds
                from tts.constants.audio_constants import PauseType
                if seg.pause_after_ms >= PauseType.VERSE_FULL:
                    seg.pause_after_ms = prosody.pause_full_ms
                elif seg.pause_after_ms >= PauseType.VERSE_HALF:
                    seg.pause_after_ms = prosody.pause_half_ms
                # Small pauses (yati) stay small

    # ── Private helpers ──────────────────────────────────────────────────

    def _extract_verse_lines(self, text: str) -> List[str]:
        """Extract clean verse lines from text.

        Splits on dandas and newlines, strips verse numbers.
        """
        # Normalize dandas and newlines
        text = re.sub(r'॥\s*[\d०-९]+\s*॥', '।', text)  # strip verse numbers
        text = re.sub(r'[।॥]', '।', text)                # normalize
        lines = re.split(r'[।\n]+', text)
        lines = [l.strip() for l in lines if l.strip()]
        # Filter very short lines (likely verse numbers or headers)
        lines = [l for l in lines if count_syllables(l) >= 3]
        return lines

    def _has_ovi_markers(self, text: str) -> bool:
        """Detect Ovi metre markers.

        Ovi (ओवी): 4-line stanza with triple-rhyme on lines 1-3.
        Marker: presence of -ची/-चि/-त्या/-तो rhyme patterns in groups.
        Also: texts from Dnyaneshwari context.
        """
        # Dnyaneshwari-specific words
        ovi_words = ['ज्ञानेश्वरी', 'ज्ञानदेव', 'ओवी', 'पसायदान', 'ज्ञानराज']
        for word in ovi_words:
            if word in text:
                return True
        # Check for triple-rhyme pattern: 3 consecutive lines sharing suffix
        lines = self._extract_verse_lines(text)
        if len(lines) >= 3:
            rhymes = self._find_rhyme_groups(lines)
            if any(r >= 3 for r in rhymes):
                return True
        return False

    def _has_abhanga_markers(self, text: str) -> bool:
        """Detect Abhanga metre markers."""
        abhanga_words = [
            'तुकाराम', 'तुका', 'एकनाथ', 'नामदेव', 'ज्ञानेश्वर',
            'अभंग', 'जय जय', 'विठ्ठल', 'पंढरीचा',
        ]
        for word in abhanga_words:
            if word in text:
                return True
        return False

    def _match_syllabic_metre(
        self, avg_syl: float, syl_counts: List[int]
    ) -> Tuple[MetreDefinition, float]:
        """Find best matching metre by syllable count.

        Returns (MetreDefinition, confidence_score).
        """
        syllabic_metres = [
            m for m in METRE_CATALOGUE
            if m.syllables_per_pada > 0 and not m.is_marathi
        ]

        best_metre  = _METRE_BY_NAME['Shloka']
        best_conf   = 0.0

        for metre in syllabic_metres:
            expected = metre.syllables_per_pada
            # Tolerance: ±2 syllables (counting errors are common)
            err = abs(avg_syl - expected)
            if err <= 2.0:
                conf = max(0.0, 1.0 - err / (expected + 0.001))
                # Boost for exact match
                exact_matches = sum(1 for s in syl_counts if abs(s - expected) <= 1)
                exact_ratio = exact_matches / max(len(syl_counts), 1)
                conf = conf * 0.5 + exact_ratio * 0.5

                if conf > best_conf:
                    best_conf  = conf
                    best_metre = metre

        return best_metre, best_conf

    def _is_verse_text(self, text: str) -> bool:
        """Is the text verse (has dandas or structured line breaks)?"""
        return bool(re.search(r'[।॥]', text)) or text.count('\n') >= 2

    def _find_rhyme_groups(self, lines: List[str]) -> List[int]:
        """Find consecutive rhyming lines.

        Returns a list of run lengths of consecutive lines sharing a suffix.
        """
        def _suffix(line: str, n: int = 2) -> str:
            """Last n syllable characters of a line."""
            # Just use last 2 Devanagari chars as proxy for rhyme
            dev_chars = [c for c in line if '\u0900' <= c <= '\u097F']
            return ''.join(dev_chars[-n:]) if len(dev_chars) >= n else ''

        runs = []
        i = 0
        while i < len(lines):
            run = 1
            suf = _suffix(lines[i])
            j = i + 1
            while j < len(lines) and _suffix(lines[j]) == suf and suf:
                run += 1
                j += 1
            runs.append(run)
            i = j if j > i else i + 1
        return runs
