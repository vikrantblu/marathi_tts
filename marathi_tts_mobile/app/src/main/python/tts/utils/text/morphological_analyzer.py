"""
Marathi Morphological Analyzer
===============================
Rule-based suffix stripping for Marathi, with an optional Morfessor
statistical model for finer segmentation on desktop and web platforms.

Mobile (Chaquopy) gets rule-based only — no runtime model to avoid APK bloat.
Web / Desktop (system Python or venv) also try to load the Morfessor model.

Public API
----------
    from tts.utils.text.morphological_analyzer import MarathiMorphologicalAnalyzer

    m = MarathiMorphologicalAnalyzer()
    m.stem('बोलतो')         # → 'बोल'
    m.segment('रामाचा')    # → ['राम', 'चा']   (or Morfessor split if available)
    m.is_same_stem('बोलतो', 'बोलते')  # → True  (same stem 'बोल')
    m.is_morfessor_available()         # → True / False
"""

import os
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger('tts.morphology')

# ─────────────────────────────────────────────────────────────────────────────
# Suffix table  (sorted longest → shortest within each category)
# Each entry: (suffix_str, suffix_type, min_stem_length)
# min_stem_length guards against stripping too much from short words.
# ─────────────────────────────────────────────────────────────────────────────

_MARATHI_SUFFIXES: List[Tuple[str, str, int]] = [
    # ── Genitive plural / postposition clusters ───────────────────────────
    ('च्यांकडून', 'gen_abl_pl',  2),
    ('च्यांकडे',  'gen_dir_pl',  2),
    ('च्यांसाठी', 'gen_purp_pl', 2),
    ('च्यांबद्दल', 'gen_about_pl', 2),
    ('च्यांमुळे',  'gen_caus_pl',  2),
    ('च्यांना',   'gen_dat_pl',   2),
    ('च्यांनी',   'gen_inst_pl',  2),
    ('च्यांचा',   'gen_gen',     2),
    ('च्यांची',   'gen_gen',     2),
    ('च_यांचे',   'gen_gen',     2),
    ('च्यांशी',   'gen_comit_pl', 2),
    ('च्यांत',    'gen_loc_pl',  2),
    ('च्या',      'gen_pl',      2),   # genitive plural / oblique

    # ── Purposive / about / causal postpositions ──────────────────────────
    ('मुळे',   'caus',    2),
    ('बद्दल',  'about',   2),
    ('साठी',   'purp',    2),
    ('मध्ये',  'loc_in',  2),
    ('पासून',  'abl',     2),
    ('हून',    'abl_comp', 2),
    ('जवळ',    'prox',    2),
    ('कडून',   'abl_dir', 2),
    ('कडे',    'dir',     2),
    ('पर्यंत', 'term',    2),
    ('खाली',   'loc_und', 2),
    ('वरून',   'abl_top', 2),
    ('सोबत',   'comit2',  2),
    ('बरोबर',  'comit3',  2),

    # ── Verb — infinitive / participial ───────────────────────────────────
    ('विणे',   'caus_inf',  2),   # causative infinitive
    ('वणे',    'caus_inf2', 2),
    ('ताना',   'prog',      2),   # while doing
    ('णारी',   'part_f',    2),
    ('णारा',   'part_m',    2),
    ('णारे',   'part_n',    2),
    ('णे',     'inf',       2),   # infinitive: करणे बोलणे जाणे

    # ── Verb — present tense ──────────────────────────────────────────────
    ('तोस',    'pres_2s_m', 2),
    ('तेस',    'pres_2s_f', 2),
    ('तात',    'pres_3pl',  2),
    ('तो',     'pres_ms',   2),
    ('ते',     'pres_fs',   2),
    ('तो',     'pres_ms2',  2),   # duplicate key — kept for order stability

    # ── Verb — past tense ─────────────────────────────────────────────────
    ('लास',    'past_2s',   2),
    ('लात',    'past_2pl',  2),
    ('लेत',    'past_3pl',  2),
    ('लो',     'past_1s',   2),
    ('ला',     'past_ms',   2),
    ('ली',     'past_fs',   2),
    ('ले',     'past_ns',   2),

    # ── Verb — future tense ───────────────────────────────────────────────
    ('शील',    'fut_2s',    2),
    ('ईल',     'fut_3s',    2),
    ('तील',    'fut_3pl',   2),

    # ── Verb — imperative / optative ──────────────────────────────────────
    ('ऊ',      'opt',       2),   # चलू / जाऊ

    # ── Nominal — genitive singular ───────────────────────────────────────
    ('चा',     'gen_ms',    2),
    ('ची',     'gen_fs',    2),
    ('चे',     'gen_ns',    2),

    # ── Nominal — case markers (vibhakti) ─────────────────────────────────
    ('ला',     'dat',       2),   # accusative/dative (दुपट with past above)
    ('ने',     'inst',      2),
    ('नी',     'inst_pl',   2),
    ('शी',     'comit',     2),
    ('स',      'dat2',      2),

    # ── Plural / honorific clusters ───────────────────────────────────────
    ('ांना',   'hdat',      2),
    ('ांनी',   'hinst',     2),
    ('ांचा',   'hgen_m',    2),
    ('ांची',   'hgen_f',    2),
    ('ांचे',   'hgen_n',    2),
    ('ांत',    'hloc',      2),
    ('ांशी',   'hcomit',    2),
    ('ांवर',   'hloc2',     2),
    ('ांनो',   'hvoc',      2),
    ('ांस',    'hdat2',     2),
    ('ां',     'hpl',       2),   # bare honorific plural

    # ── Simple locative / directional ─────────────────────────────────────
    ('वर',     'loc_top',   2),
    ('त',      'loc',       2),   # घरात → kept last — very short, high false-positive

    # ── Abstract noun suffix ──────────────────────────────────────────────
    ('पणा',    'abstr',     3),
    ('पण',     'abstr2',    3),

    # ── Agent / demonym ───────────────────────────────────────────────────
    ('कर',     'agent',     3),   # शेतकर, पुणेकर

    # ── Emphatic particles (stripped last) ────────────────────────────────
    ('सुद्धा', 'emph',      2),
    ('ही',     'emph2',     2),
    ('च',      'emph3',     2),
]

# Pre-sorted by suffix length descending to ensure greedy matching
_MARATHI_SUFFIXES_SORTED = sorted(
    _MARATHI_SUFFIXES, key=lambda x: len(x[0]), reverse=True
)


# ─────────────────────────────────────────────────────────────────────────────
# DO-NOT-STRIP words — common short words that must not be stemmed
# (prevents stripping 'ते' from 'ते' meaning 'they', etc.)
# ─────────────────────────────────────────────────────────────────────────────
_STOP_WORDS = frozenset({
    'मी', 'तू', 'तो', 'ती', 'ते', 'आम्ही', 'तुम्ही', 'ते', 'हे', 'हा', 'ही',
    'त्या', 'त्यो', 'माझा', 'तुझा', 'त्याचा', 'तिचा',
    'आणि', 'किंवा', 'पण', 'परंतु', 'म्हणून', 'कारण', 'जर', 'तर',
    'नाही', 'नको', 'हो', 'होय', 'अरे', 'बरं',
    'काय', 'कोण', 'कुठे', 'कधी', 'कसे', 'किती',
    'एक', 'दोन', 'तीन', 'चार', 'पाच',
    'मला', 'तला', 'त्याला', 'तिला',
    'इथे', 'तिथे', 'इकडे', 'तिकडे',
    'आता', 'तेव्हा', 'जेव्हा', 'नंतर', 'आधी',
    'खूप', 'थोडा', 'सर्व', 'काही',
    'श्री', 'राम', 'कृष्ण', 'देव', 'देवी',
})


# ─────────────────────────────────────────────────────────────────────────────
class MarathiMorphologicalAnalyzer:
    """Marathi morphological analyzer — rule-based with optional Morfessor.

    Thread-safe (stateless after __init__).
    """

    def __init__(self):
        self._morfessor = None
        self._try_load_morfessor()

    # ─── Morfessor loader ────────────────────────────────────────────────

    def _try_load_morfessor(self) -> None:
        """Attempt to load the Morfessor binary model.

        Silently degrades to rule-based if:
        - morfessor package is not installed (mobile/APK builds)
        - model file does not exist
        """
        try:
            import morfessor  # type: ignore[import]

            # Model lives at <package_root>/tts/morph/morfessor/mr.model
            # This file is at  <package_root>/tts/utils/text/morphological_analyzer.py
            # Path: ../../morph/morfessor/mr.model
            _this_dir = os.path.dirname(__file__)
            model_path = os.path.normpath(
                os.path.join(_this_dir, '..', '..', 'morph', 'morfessor', 'mr.model')
            )

            if os.path.isfile(model_path):
                io = morfessor.MorfessorIO()
                self._morfessor = io.read_binary_model_file(model_path)
                logger.info(f'Morfessor model loaded: {model_path}')
            else:
                logger.debug(f'Morfessor model not found at {model_path} — using rule-based')
        except ImportError:
            logger.debug('morfessor package not available — using rule-based morphology')
        except Exception as exc:
            logger.warning(f'Morfessor load failed ({exc}) — using rule-based morphology')

    # ─── Public API ──────────────────────────────────────────────────────

    def is_morfessor_available(self) -> bool:
        """Return True if the Morfessor statistical model is loaded."""
        return self._morfessor is not None

    def segment(self, word: str) -> List[str]:
        """Split *word* into a list of morpheme strings.

        Strategy:
            1. If Morfessor is available, use ``viterbi_segment`` (best quality).
            2. Otherwise apply rule-based suffix stripping (always available).

        Returns a list of morpheme strings e.g. ``['बोल', 'तो']``.
        A one-element list means no split was found.
        """
        if not word:
            return [word]

        # Morfessor path
        if self._morfessor is not None:
            try:
                morphemes, _score = self._morfessor.viterbi_segment(word)
                if len(morphemes) > 1:
                    return morphemes
                # Morfessor returned unsegmented — fall through to rules
            except Exception as exc:
                logger.debug(f'Morfessor segment error for {word!r}: {exc}')

        # Rule-based suffix stripping
        return self._rule_segment(word)

    def stem(self, word: str) -> str:
        """Return the canonical stem of *word*.

        This is the first (leftmost) element of ``segment()``, representing
        the root before inflectional suffixes.

        Short stop-words and words under 3 chars are returned as-is.
        """
        if not word or len(word) < 3 or word in _STOP_WORDS:
            return word
        parts = self.segment(word)
        return parts[0] if parts else word

    def is_same_stem(self, word1: str, word2: str) -> bool:
        """Return True if both words share the same morphological stem.

        Useful for near-duplicate detection in ``remove_repetitions``.

        Example::

            m.is_same_stem('बोलतो', 'बोलते')  # True — both stem 'बोल'
            m.is_same_stem('राम', 'कृष्ण')     # False
        """
        if word1 == word2:
            return True
        s1 = self.stem(word1)
        s2 = self.stem(word2)
        # Only match if stem is at least 2 syllables long (≥4 chars)
        # to avoid false positives from very short stems like 'क'
        return len(s1) >= 4 and s1 == s2

    def get_suffix_type(self, word: str) -> Optional[str]:
        """Return the detected suffix type string, or None if unstemmed."""
        if len(word) < 3 or word in _STOP_WORDS:
            return None
        stem, _, stype = self._rule_strip_one(word)
        return stype

    def morpheme_boundary_positions(self, word: str) -> List[int]:
        """Return character positions (0-indexed) of morpheme boundaries.

        Position *i* means there is a boundary after character index *i-1*,
        i.e. word[i] starts a new morpheme.

        Used by the G2P engine to place schwa-deletion markers at boundaries.
        """
        parts = self.segment(word)
        positions = []
        offset = 0
        for part in parts[:-1]:  # all but last
            offset += len(part)
            positions.append(offset)
        return positions

    # ─── Rule-based internals ─────────────────────────────────────────────

    def _rule_segment(self, word: str) -> List[str]:
        """Apply greedy longest-first suffix stripping, returning [stem, *suffixes]."""
        if word in _STOP_WORDS or len(word) < 3:
            return [word]

        remaining = word
        suffixes: List[str] = []

        # Strip at most 2 suffixes (avoid over-stripping)
        for _pass in range(2):
            stem_candidate, suffix, _stype = self._rule_strip_one(remaining)
            if suffix and len(stem_candidate) >= 2:
                suffixes.insert(0, suffix)
                remaining = stem_candidate
            else:
                break  # no more suffix found

        if suffixes:
            return [remaining] + suffixes
        return [word]

    def _rule_strip_one(self, word: str) -> Tuple[str, str, str]:
        """Strip the single longest matching suffix from *word*.

        Returns ``(stem, suffix, suffix_type)`` or ``(word, '', '')`` if none found.
        """
        for suffix, stype, min_stem in _MARATHI_SUFFIXES_SORTED:
            if word.endswith(suffix):
                stem = word[: -len(suffix)]
                if len(stem) >= min_stem:
                    return stem, suffix, stype
        return word, '', ''


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton (lazy) — import and reuse across the TTS pipeline
# ─────────────────────────────────────────────────────────────────────────────

_analyzer_instance: Optional['MarathiMorphologicalAnalyzer'] = None


def get_analyzer() -> 'MarathiMorphologicalAnalyzer':
    """Return the shared module-level ``MarathiMorphologicalAnalyzer`` instance.

    Creates it on first call; thread-safe for read-only ``stem()`` / ``segment()`` use.
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = MarathiMorphologicalAnalyzer()
    return _analyzer_instance
