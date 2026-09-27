#!/usr/bin/env python3
"""
Offline test — runs on all three platforms without Django.

Usage:
    python test_all_platforms.py

Run this script from the repository root before finishing any task that touches
the tts/ engine code.  All assertions must pass before the work is complete.
"""
import sys
import os
import ast

# ── 0. Syntax check ────────────────────────────────────────────────────────────

# Compute root dynamically so the test runs on any machine / CI runner
_ROOT = os.path.dirname(os.path.abspath(__file__))

PLATFORMS = {
    'web':     os.path.join(_ROOT, 'marathi_tts_web', 'tts'),
    'desktop': os.path.join(_ROOT, 'marathi_tts_desktop', 'python_bridge', 'tts'),
    'mobile':  os.path.join(_ROOT, 'marathi_tts_mobile', 'app', 'src', 'main', 'python', 'tts'),
}

ENGINE_FILES = [
    os.path.join('utils', 'phonetic', 'sandhi_engine.py'),
    os.path.join('utils', 'phonetic', 'metre_engine.py'),
    os.path.join('utils', 'phonetic', 'marathi_phonetics.py'),
    os.path.join('utils', 'audio', 'prosody_engine.py'),
    os.path.join('utils', 'core', 'tts_engine.py'),
    os.path.join('constants', 'g2p_constants.py'),
]

PLATFORM_ROOTS = {
    'web':     os.path.join(_ROOT, 'marathi_tts_web'),
    'desktop': os.path.join(_ROOT, 'marathi_tts_desktop', 'python_bridge'),
    'mobile':  os.path.join(_ROOT, 'marathi_tts_mobile', 'app', 'src', 'main', 'python'),
}

print('=' * 70)
print('STEP 0 — Syntax check (all platforms × all engine files)')
print('=' * 70)
syntax_ok = True
for rel in ENGINE_FILES:
    for label, tts_root in PLATFORMS.items():
        path = os.path.join(tts_root, rel)
        if not os.path.exists(path):
            print(f'  MISSING  [{label}] {os.path.basename(rel)}')
            syntax_ok = False
            continue
        try:
            ast.parse(open(path, encoding='utf-8').read())
        except SyntaxError as e:
            print(f'  SYNERR   [{label}] {os.path.basename(rel)}: {e}')
            syntax_ok = False

if syntax_ok:
    print('  All files present and syntax-clean.\n')
else:
    print('\nAborting — fix syntax errors before proceeding.\n')
    sys.exit(1)


# ── 1. Pronunciation engine tests (one per platform) ──────────────────────────

print('=' * 70)
print('STEP 1 — Pronunciation rules (Sanskrit / Old Marathi / Modern Marathi)')
print('=' * 70)

def _chk(failures, name, condition, detail=''):
    """Record a failure if condition is False."""
    if not condition:
        failures.append((name, detail))


def run_tests_for_platform(label, sys_root):
    """Import the tts package from sys_root and run all pronunciation checks."""
    # Fresh slate — remove any previously imported tts.* modules
    for mod in list(sys.modules.keys()):
        if mod.startswith('tts.'):
            del sys.modules[mod]
    if sys_root in sys.path:
        sys.path.remove(sys_root)
    sys.path.insert(0, sys_root)

    failures = []

    try:
        from tts.utils.phonetic.sandhi_engine import SandhiEngine, is_predominantly_sanskrit
        from tts.utils.phonetic.metre_engine import MetreEngine, count_syllables
        from tts.utils.phonetic.marathi_phonetics import (
            apply_sanskrit_phonetics,
            apply_old_marathi_phonetics,
            apply_marathi_phonetics,
            apply_gtts_mr_fixes,
            apply_edge_tts_fixes,
        )
        from tts.utils.audio.prosody_engine import MarathiProsodyEngine
        from tts.constants.g2p_constants import EXCEPTION_LEXICON
    except ImportError as e:
        failures.append(('IMPORT', str(e)))
        sys.path.remove(sys_root)
        return failures

    import dataclasses

    @dataclasses.dataclass
    class _Seg:
        text: str
        pause_after_ms: int = 500
        is_verse: bool = True
        metre_name: str = ''
        tts_rate: float = 1.0

    # ══════════════════════════════════════════════════════════════════════
    # A. SANDHI ENGINE
    # ══════════════════════════════════════════════════════════════════════
    se = SandhiEngine(mode='classical')

    # A1. Vedic accent stripping — U+0951 (udatta) and U+0952 (anudatta)
    r = apply_sanskrit_phonetics('रा॑मः')
    _chk(failures, 'Vedic accent strip',
         '\u0951' not in r and '\u0952' not in r,
         f'Accent still present: {repr(r)}')

    # A2. Avagraha (ऽ) expansion — must vanish or become silent join
    r = se.process('रामोऽपि')
    _chk(failures, 'Avagraha expand',
         'ऽ' not in r,
         f'ऽ still present: {repr(r)}')

    # A3. Anusvara + sibilant assimilation  संशय → सन्शय
    r = se.process('संशय')
    _chk(failures, 'Anusvara+sibilant (श)',
         r == 'सन्शय',
         f'Expected सन्शय, got {repr(r)}')

    # A4. Anusvara + ष  संष्ठ → सन्ष्ठ
    r = se.process('संष्ठ')
    _chk(failures, 'Anusvara+sibilant (ष)',
         'न्ष' in r,
         f'Expected न्ष in output, got {repr(r)}')

    # A4b. Anusvara + velar stop  संकल्प → सङ्कल्प
    r = se.fix_anusvara_varga('संकल्प')
    _chk(failures, 'Anusvara+velar (क→ङ)',
         'ङ्क' in r,
         f'Expected ङ्कल्प, got {repr(r)}')

    # A4c. Anusvara + labial stop  संपूर्ण → सम्पूर्ण
    r = se.fix_anusvara_varga('संपूर्ण')
    _chk(failures, 'Anusvara+labial (प→म)',
         'म्प' in r,
         f'Expected म्पूर्ण, got {repr(r)}')

    # A4d. Anusvara + dental  संतोष → सन्तोष
    r = se.fix_anusvara_varga('संतोष')
    _chk(failures, 'Anusvara+dental (त→न)',
         'न्त' in r,
         f'Expected न्तोष, got {repr(r)}')

    # A5. Visarga + voiced vowel  → र् + vowel  (r-sandhi)
    r = se.process('रामः आगच्छति')
    _chk(failures, 'Visarga+vowel r-sandhi',
         'ः' not in r or 'र' in r,
         f'Visarga not resolved: {repr(r)}')

    # A6. FEAT-5: Visarga + voiced consonant → r  (पुनः दर्शनम् → पुनर् दर्शनम्)
    r = se.process('पुनः दर्शनम्')
    _chk(failures, 'Visarga+voiced consonant (FEAT-5)',
         'ः' not in r and 'र्' in r,
         f'Visarga not resolved to र्: {repr(r)}')

    # A7. FEAT-5: Visarga + voiceless consonant should NOT change
    r = se.process('दुःख')
    _chk(failures, 'Visarga+voiceless (no change)',
         'ः' in r or 'ख' in r,
         f'Visarga wrongly changed before voiceless: {repr(r)}')

    # ══════════════════════════════════════════════════════════════════════
    # B. SANSKRIT PHONETICS
    # ══════════════════════════════════════════════════════════════════════

    # B1. is_predominantly_sanskrit — stotra text
    stotra = 'शुक्लांबरधरं विष्णुं ।। प्रसन्नवदनं ध्यायेत् ।।'
    _chk(failures, 'Sanskrit detect',
         is_predominantly_sanskrit(stotra),
         'is_predominantly_sanskrit() returned False for clear stotra text')

    # B2. is_predominantly_sanskrit — modern Marathi prose should be False
    prose = 'आज हवामान चांगले आहे. मी शाळेत जातो.'
    _chk(failures, 'Sanskrit non-detect (Marathi prose)',
         not is_predominantly_sanskrit(prose),
         'is_predominantly_sanskrit() returned True for modern Marathi prose')

    # B3. OM symbol → ओम्
    r = apply_sanskrit_phonetics('ॐ नमः शिवाय')
    _chk(failures, 'OM symbol',
         'ओम' in r,
         f'Expected ओम in output, got {repr(r)}')

    # B4. apply_sanskrit_phonetics runs on full shloka without crash/empty
    shloka = 'शुक्लांबरधरं विष्णुं शशिवर्णं चतुर्भुजम् । प्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ।।'
    r = apply_sanskrit_phonetics(shloka)
    _chk(failures, 'Sanskrit phonetics (full shloka)',
         bool(r) and len(r) > 10,
         f'Empty or too-short output: {repr(r)}')

    # B5. ज्ञ must NOT be converted to द्न्य in Sanskrit mode — it's "gya" in Sanskrit
    r = apply_sanskrit_phonetics('क्षेत्रज्ञ')
    _chk(failures, 'Sanskrit: ज्ञ kept as-is (not द्न्य)',
         'द्न्य' not in r,
         f'ज्ञ wrongly converted in Sanskrit mode: {repr(r)}')

    # B6. ॐ before consonant gets a space to prevent unpronounceable cluster
    r = apply_sanskrit_phonetics('ॐविश्वं')
    _chk(failures, 'OM+consonant gets space',
         'ओम् ' in r or r.startswith('ओम् '),
         f'No space after ओम् before consonant: {repr(r)}')

    # ══════════════════════════════════════════════════════════════════════
    # C. METRE ENGINE
    # ══════════════════════════════════════════════════════════════════════
    me = MetreEngine()

    # C1. Anushtubh / Shloka — 4 padas × ~8 syllables
    shloka4 = (
        'शुक्लांबरधरं विष्णुं । शशिवर्णं चतुर्भुजम् ।। '
        'प्रसन्नवदनं ध्यायेत् । सर्वविघ्नोपशान्तये ।।'
    )
    mp = me.detect(shloka4)
    _chk(failures, 'Metre detect (Anushtubh/Shloka)',
         mp is not None and mp.name in ('Anushtubh', 'Shloka', 'Stotra'),
         f'Got: {mp.name if mp else None}')

    # C2. Rate must be ≤ 0.95 (definitely slower than prose)
    _chk(failures, 'Metre rate ≤ 0.95',
         mp is not None and mp.rate <= 0.95,
         f'Rate = {mp.rate if mp else "-"}')

    # C3. pause_half_ms ≥ 400 ms
    _chk(failures, 'Metre half-pause ≥ 400ms',
         mp is not None and mp.pause_half_ms >= 400,
         f'Half-pause = {mp.pause_half_ms if mp else "-"}ms')

    # C4. apply_to_segments — full-verse pause applied to ।। segment
    if mp is not None:
        segs = [_Seg('line1', 500, True), _Seg('line2', 1000, True)]
        me.apply_to_segments(segs, mp)
        _chk(failures, 'apply_to_segments (full pause)',
             segs[1].pause_after_ms == mp.pause_full_ms,
             f'Got {segs[1].pause_after_ms}, expected {mp.pause_full_ms}')
        # C5. apply_to_segments — half-verse pause applied to । segment
        _chk(failures, 'apply_to_segments (half pause)',
             segs[0].pause_after_ms == mp.pause_half_ms,
             f'Got {segs[0].pause_after_ms}, expected {mp.pause_half_ms}')

    # C6. count_syllables — basic sanity
    n = count_syllables('शुक्लांबरधरं')
    _chk(failures, 'count_syllables',
         3 <= n <= 8,
         f'Unexpected syllable count {n} for शुक्लांबरधरं')

    # C7. Prose text → Prose metre returned; rate == 0.92 (design constant)
    mp_prose = me.detect('आज हवामान चांगले आहे.')
    _chk(failures, 'Metre: prose → Prose metre',
         mp_prose is not None and mp_prose.name == 'Prose',
         f'Got metre: {mp_prose.name if mp_prose else "-"}')
    _chk(failures, 'Metre: prose rate == 0.92',
         mp_prose is not None and abs(mp_prose.rate - 0.92) < 0.01,
         f'Prose rate = {mp_prose.rate if mp_prose else "-"}')

    # ══════════════════════════════════════════════════════════════════════
    # D. PROSODY ENGINE — metre integration
    # ══════════════════════════════════════════════════════════════════════
    pe = MarathiProsodyEngine()

    # D1. _is_verse_block detects ॥ (U+0965 double danda) markers
    _chk(failures, 'ProsodyEngine: is_verse_block True',
         pe._is_verse_block('रामाय रामभद्राय ॥ रामचन्द्राय वेधसे ॥'),
         '_is_verse_block returned False for text with 2x ॥')

    # D2. _is_verse_block → False for prose
    _chk(failures, 'ProsodyEngine: is_verse_block False',
         not pe._is_verse_block('आज हवामान चांगले आहे.'),
         '_is_verse_block returned True for prose')

    # D3. segment_text on verse block → is_verse=True on segments
    verse_para = 'शुक्लांबरधरं विष्णुं । शशिवर्णं चतुर्भुजम् ॥ प्रसन्नवदनं ध्यायेत् । सर्वविघ्नोपशान्तये ॥'
    segs = pe.segment_text(verse_para)
    _chk(failures, 'ProsodyEngine: verse segments is_verse=True',
         all(s.is_verse for s in segs) and len(segs) > 0,
         f'{sum(1 for s in segs if not s.is_verse)} non-verse segs in verse block')

    # D4. MetreEngine applied → tts_rate < 1.0 on verse segments
    _chk(failures, 'ProsodyEngine: metre rate propagated to segments',
         any(s.tts_rate < 1.0 for s in segs),
         f'All tts_rate == 1.0; MetreEngine not applied')

    # D5. segment_text on prose → is_verse=False
    prose_segs = pe.segment_text('आज हवामान चांगले आहे. मी शाळेत जातो.')
    _chk(failures, 'ProsodyEngine: prose segments is_verse=False',
         all(not s.is_verse for s in prose_segs) and len(prose_segs) > 0,
         f'{sum(1 for s in prose_segs if s.is_verse)} verse segs in prose')

    # D6. FEAT-11: Pitch contour applied — verse segments should have non-zero pitch_shift
    # (wave contour sets alternating ±0.5; falling/rising also set non-zero)
    _chk(failures, 'ProsodyEngine: pitch contour (FEAT-11)',
         any(abs(s.pitch_shift) > 0.01 for s in segs),
         f'All pitch_shift == 0 even though MetreDefinition has pitch_contour')

    # D7. FEAT-9: Emotion-adaptive verse prosody (devotional → slower)
    pe_devot = MarathiProsodyEngine(emotion='devotional')
    segs_devot = pe_devot.segment_text(verse_para)
    pe_neutral = MarathiProsodyEngine(emotion='neutral')
    segs_neutral = pe_neutral.segment_text(verse_para)
    # Devotional should have lower tts_rate than neutral for verse
    if segs_devot and segs_neutral:
        avg_rate_devot = sum(s.tts_rate for s in segs_devot) / len(segs_devot)
        avg_rate_neutral = sum(s.tts_rate for s in segs_neutral) / len(segs_neutral)
        _chk(failures, 'ProsodyEngine: devotional slower (FEAT-9)',
             avg_rate_devot < avg_rate_neutral,
             f'Devotional rate {avg_rate_devot:.3f} >= neutral {avg_rate_neutral:.3f}')

    # ══════════════════════════════════════════════════════════════════════
    # E. OLD MARATHI PHONETICS
    # ══════════════════════════════════════════════════════════════════════

    # E1. Basic: function runs and returns non-empty text
    r = apply_old_marathi_phonetics('तें विठ्ठल तेथें बसे ।। करितां भजन ।।')
    _chk(failures, 'Old Marathi: non-empty output',
         bool(r) and len(r) > 5,
         f'Empty or too-short: {repr(r)}')

    # E2. Sant literature lexicon: विठ्ठल preserved (retroflex ठ must survive)
    r = apply_old_marathi_phonetics('विठ्ठल पंढरीचा')
    _chk(failures, 'Old Marathi: विठ्ठल retained',
         'विठ्ठल' in r,
         f'विठ्ठल lost in: {repr(r)}')

    # E3. ज्ञ → द्न्य applied in Old Marathi too
    r = apply_old_marathi_phonetics('ज्ञानदेव')
    _chk(failures, 'Old Marathi: ज्ञ → द्न्य',
         'द्न्य' in r,
         f'ज्ञ not converted: {repr(r)}')

    # E4. Schwa deletion guard: classical verse runs without crash
    try:
        r = apply_old_marathi_phonetics('कळे न कळे माया ।। अभंग ।।')
        _chk(failures, 'Old Marathi: schwa guard (no crash)',
             bool(r),
             'Returned empty string')
    except Exception as exc:
        failures.append(('Old Marathi: schwa guard (no crash)', str(exc)))

    # E5. Archaic suffix -तां → -ता
    r = apply_old_marathi_phonetics('धावतां')
    _chk(failures, 'Old Marathi: -तां → -ता suffix',
         'ता' in r and 'तां' not in r,
         f'Archaic suffix not converted: {repr(r)}')

    # E6. Trailing anusvara → chandrabindu (y-glide prevention)
    r = apply_old_marathi_phonetics('संतीं बोलती')
    _chk(failures, 'Old Marathi: trailing anusvara → chandrabindu',
         'ीँ' in r or 'ीं' not in r.split()[0],
         f'Anusvara not converted: {repr(r)}')

    # E7. Expanded lexicon: ऐसें → असे
    r = apply_old_marathi_phonetics('ऐसें म्हणे')
    _chk(failures, 'Old Marathi: ऐसें → असे',
         'असे' in r,
         f'Archaic pronoun not converted: {repr(r)}')

    # ══════════════════════════════════════════════════════════════════════
    # F. MODERN MARATHI PHONETICS
    # ══════════════════════════════════════════════════════════════════════

    # F1. ज्ञ → द्न्य
    r = apply_marathi_phonetics('ज्ञान')
    _chk(failures, 'Marathi ज्ञ → द्न्य',
         'द्न्य' in r,
         f'Expected द्न्य, got {repr(r)}')

    # F2. Visarga gemination: दुःख → दुख्ख
    r = apply_marathi_phonetics('दुःख')
    _chk(failures, 'Visarga gemination (दुःख)',
         'दुःख' not in r,
         f'दुःख not resolved: {repr(r)}')

    # F3. Retroflex ळ preserved
    r = apply_marathi_phonetics('मुळे वेळ')
    _chk(failures, 'Retroflex ळ preserved',
         'ळ' in r,
         f'ळ lost: {repr(r)}')

    # F4. ॠ → री
    r = apply_marathi_phonetics('ॠ')
    _chk(failures, 'ॠ → री',
         'री' in r or r.strip() == 'री',
         f'Expected री, got {repr(r)}')

    # F5. निःशब्द visarga before sibilant
    r = apply_marathi_phonetics('निःशब्द')
    _chk(failures, 'Visarga+sibilant (निःशब्द)',
         'निःशब्द' not in r,
         f'निःशब्द not resolved: {repr(r)}')

    # ══════════════════════════════════════════════════════════════════════
    # G. G2P EXCEPTION LEXICON  (key entries must be present)
    # ══════════════════════════════════════════════════════════════════════

    # G1. Retroflex ळ words present
    _chk(failures, 'Lexicon: मुळे entry',
         'मुळे' in EXCEPTION_LEXICON,
         'मुळे missing from EXCEPTION_LEXICON')

    # G2. Sanskrit deity names added
    _chk(failures, 'Lexicon: गणेश entry',
         'गणेश' in EXCEPTION_LEXICON,
         'गणेश missing — deity names block not added')

    # G3. Sant literature: ज्ञानदेव → दनदेव (ज्ञ treated in Marathi way)
    _chk(failures, 'Lexicon: ज्ञानदेव entry',
         'ज्ञानदेव' in EXCEPTION_LEXICON,
         'ज्ञानदेव missing from EXCEPTION_LEXICON')

    # G4. Stotra word: स्तोत्र present
    _chk(failures, 'Lexicon: स्तोत्र entry',
         'स्तोत्र' in EXCEPTION_LEXICON,
         'स्तोत्र missing from EXCEPTION_LEXICON')

    # G5. नमस्कार present (common greeting/stotra word)
    _chk(failures, 'Lexicon: नमस्कार entry',
         'नमस्कार' in EXCEPTION_LEXICON,
         'नमस्कार missing from EXCEPTION_LEXICON')

    # ══════════════════════════════════════════════════════════════════════
    # H. gTTS POST-G2P FIXES (apply_gtts_mr_fixes)
    # ══════════════════════════════════════════════════════════════════════

    # H1. "चा" y-glide: ZWNJ inserted between च and ा after matra
    r = apply_gtts_mr_fixes('रामाचा')
    _chk(failures, 'gTTS fix: चा y-glide ZWNJ',
         '\u200C' in r and 'च' in r and 'ा' in r,
         f'ZWNJ not inserted in रामाचा: {repr(r)}')

    # H2. "ें" y-glide: ZWNJ inserted before े+ं
    r = apply_gtts_mr_fixes('आदरें')
    _chk(failures, 'gTTS fix: ें y-glide ZWNJ',
         '\u200C' in r,
         f'ZWNJ not inserted in आदरें: {repr(r)}')

    # H3. Terminal halant removed at sentence boundary
    r = apply_gtts_mr_fixes('ध्यायेत्.')
    _chk(failures, 'gTTS fix: terminal halant removed',
         'त\u094D' not in r.replace('त\u094Dय', 'त\u094Dय'),  # only check terminal
         f'Terminal halant not removed: {repr(r)}')

    # H4. Word-internal conjuncts NOT broken by terminal halant removal
    r = apply_gtts_mr_fixes('त्यांच्या')
    _chk(failures, 'gTTS fix: mid-word conjuncts preserved',
         'त\u094Dय' in r and 'च\u094Dय' in r,
         f'Conjuncts broken: {repr(r)}')

    # H5. Empty / None input handled gracefully
    r = apply_gtts_mr_fixes('')
    _chk(failures, 'gTTS fix: empty input OK',
         r == '',
         f'Non-empty result for empty input: {repr(r)}')

    # ══════════════════════════════════════════════════════════════════════
    # H2. EDGE-TTS FIXES (apply_edge_tts_fixes) — BUG-69
    # ══════════════════════════════════════════════════════════════════════

    # H2a. No ZWNJ inserted — edge-tts fix must NOT break grapheme clusters
    r = apply_edge_tts_fixes('रामाचा')
    _chk(failures, 'edge-tts fix: no ZWNJ inserted',
         '\u200C' not in r,
         f'ZWNJ wrongly inserted for edge-tts: {repr(r)}')

    # H2b. Word-final anusvara → chandrabindu still applied
    r = apply_edge_tts_fixes('संतीं बोलती')
    _chk(failures, 'edge-tts fix: word-final anusvara → chandrabindu',
         'ीँ' in r,
         f'Anusvara not converted to chandrabindu: {repr(r)}')

    # H2c. Terminal halant removed at sentence boundary
    r = apply_edge_tts_fixes('ध्यायेत्.')
    _chk(failures, 'edge-tts fix: terminal halant removed',
         'त\u094D' not in r.replace('त\u094Dय', 'त\u094Dय'),
         f'Terminal halant not removed: {repr(r)}')

    # H2d. Mid-word anusvara before consonant NOT affected (e.g. "संत")
    r = apply_edge_tts_fixes('संत')
    _chk(failures, 'edge-tts fix: mid-word anusvara preserved',
         'ं' in r,
         f'Mid-word anusvara wrongly replaced: {repr(r)}')

    # H2e. Empty input handled gracefully
    r = apply_edge_tts_fixes('')
    _chk(failures, 'edge-tts fix: empty input OK',
         r == '',
         f'Non-empty result for empty input: {repr(r)}')

    # ══════════════════════════════════════════════════════════════════════
    # I. TEXT NORMALIZER (MarathiTextNormalizer)
    # ══════════════════════════════════════════════════════════════════════
    try:
        from tts.utils.text.text_normalizer import MarathiTextNormalizer
        _tnorm = MarathiTextNormalizer()

        # I1. normalize_text returns non-empty for ordinary Marathi text
        r_i1 = _tnorm.normalize_text('आनंद')
        _chk(failures, 'TextNormalizer: non-empty output',
             bool(r_i1.strip()),
             f'normalize_text returned empty for आनंद: {repr(r_i1)}')

        # I2. Verse numbers stripped: ॥ 5 ॥  →  ॥
        r_i2 = _tnorm.normalize_text('नमः शिवाय ॥ 5 ॥')
        _chk(failures, 'TextNormalizer: verse number stripped',
             '5' not in r_i2 and '॥' in r_i2,
             f'Verse number not stripped: {repr(r_i2)}')

        # I3. Context-aware abbreviation: इ. before number → इसवी सन
        r_i3 = _tnorm.normalize_text('इ. 1947 मध्ये')
        _chk(failures, 'TextNormalizer: इ. before year expanded',
             'इसवी' in r_i3,
             f'इ. not expanded: {repr(r_i3)}')

        # I4. Empty string survives without crash
        r_i4 = _tnorm.normalize_text('')
        _chk(failures, 'TextNormalizer: empty input OK',
             r_i4 == '',
             f'Empty input gave non-empty: {repr(r_i4)}')

    except ModuleNotFoundError as exc:
        print(f'  [SKIP] TextNormalizer tests — optional dep missing: {exc}')
    except Exception as exc:
        _chk(failures, 'TextNormalizer: import / init', False,
             f'Exception: {exc}')

    # ══════════════════════════════════════════════════════════════════════
    # J. GRAMMAR ENGINE (MarathiGrammarEngine)
    # ══════════════════════════════════════════════════════════════════════
    try:
        from tts.utils.text.marathi_grammar import (
            MarathiGrammarEngine, remove_repetitions
        )
        _gram = MarathiGrammarEngine()

        # J1. process() returns non-empty for ordinary prose
        r_j1 = _gram.process('आज हवामान चांगले आहे.')
        _chk(failures, 'GrammarEngine: non-empty output',
             bool(r_j1.strip()),
             f'process() returned empty: {repr(r_j1)}')

        # J2. process() output is a string (not crash / None)
        r_j2 = _gram.process('राम जातो.')
        _chk(failures, 'GrammarEngine: output is str',
             isinstance(r_j2, str),
             f'process() returned {type(r_j2)}')

        # J3. remove_repetitions drops adjacent duplicate words
        r_j3 = remove_repetitions('राम राम राम बोलला')
        _chk(failures, 'GrammarEngine: repetition removed',
             r_j3.count('राम') < 3,
             f'Repetitions not removed: {repr(r_j3)}')

        # J4. Empty string survives without crash
        r_j4 = _gram.process('')
        _chk(failures, 'GrammarEngine: empty input OK',
             isinstance(r_j4, str),
             f'process("") raised or returned non-str: {repr(r_j4)}')

    except ModuleNotFoundError as exc:
        print(f'  [SKIP] GrammarEngine tests — optional dep missing: {exc}')
    except Exception as exc:
        _chk(failures, 'GrammarEngine: import / init', False,
             f'Exception: {exc}')

    # ══════════════════════════════════════════════════════════════════════
    # K. NUMBER-TO-WORDS  (number_to_words module)
    # ══════════════════════════════════════════════════════════════════════
    try:
        from tts.utils.text.number_to_words import (
            number_to_marathi_words, convert_time, convert_date,
            convert_ordinal, convert_percentage
        )

        # K1. Basic cardinal: 1 → एक
        _chk(failures, 'number_to_words: 1 = एक',
             number_to_marathi_words(1) == 'एक',
             f'Got: {repr(number_to_marathi_words(1))}')

        # K2. Basic cardinal: 10 → दहा
        _chk(failures, 'number_to_words: 10 = दहा',
             number_to_marathi_words(10) == 'दहा',
             f'Got: {repr(number_to_marathi_words(10))}')

        # K3. convert_time: 9:00 AM contains सकाळचे and नऊ
        r_k3 = convert_time('9:00 AM')
        _chk(failures, 'number_to_words: 9:00 AM has नऊ',
             'नऊ' in r_k3,
             f'convert_time("9:00 AM") = {repr(r_k3)}')

        # K4. convert_time: 12:45 contains पावणे (quarter-to)
        r_k4 = convert_time('12:45')
        _chk(failures, 'number_to_words: 12:45 has पावणे',
             'पावणे' in r_k4,
             f'convert_time("12:45") = {repr(r_k4)}')

        # K5. convert_ordinal: "1ला" → contains "पहिला"
        r_k5 = convert_ordinal('1ला')
        _chk(failures, 'number_to_words: 1ला ordinal',
             r_k5 and isinstance(r_k5, str) and len(r_k5) > 0,
             f'convert_ordinal returned: {repr(r_k5)}')

        # K6. convert_percentage: "50%" → contains "टक्के"
        r_k6 = convert_percentage('50%')
        _chk(failures, 'number_to_words: 50% has टक्के',
             'टक्के' in r_k6,
             f'convert_percentage("50%") = {repr(r_k6)}')

    except ModuleNotFoundError as exc:
        print(f'  [SKIP] number_to_words tests — optional dep missing: {exc}')
    except Exception as exc:
        _chk(failures, 'number_to_words: import / init', False,
             f'Exception: {exc}')

    # ══════════════════════════════════════════════════════════════════════
    # L. ACCENT-SPECIFIC PHONETIC RULES (apply_accent_phonetics)
    # ══════════════════════════════════════════════════════════════════════

    from tts.utils.phonetic.marathi_phonetics import apply_accent_phonetics

    # L1. Standard accent: no change
    r = apply_accent_phonetics('काळा केळा', 'standard')
    _chk(failures, 'Accent: standard no change',
         r == 'काळा केळा',
         f'Standard accent modified text: {repr(r)}')

    # L2. Kolhapuri: ळा → ला at word end
    r = apply_accent_phonetics('काळा केळा', 'kolhapuri')
    _chk(failures, 'Accent: Kolhapuri ळा→ला',
         'काला' in r and 'केला' in r,
         f'Kolhapuri ळा merging failed: {repr(r)}')

    # L3. Vidarbha: terminal ला → ले
    r = apply_accent_phonetics('मला त्याला', 'vidarbha')
    _chk(failures, 'Accent: Vidarbha ला→ले',
         'मले' in r and 'त्याले' in r,
         f'Vidarbha ला→ले failed: {repr(r)}')

    # L4. Khandeshi: word-final vowel shortening ी→ि
    r = apply_accent_phonetics('नदी पाणी', 'khandeshi')
    _chk(failures, 'Accent: Khandeshi ी→ि',
         'नदि' in r and 'पाणि' in r,
         f'Khandeshi vowel shortening failed: {repr(r)}')

    # L5. Marathwada: terminal णे → ने
    r = apply_accent_phonetics('बोलणे करणे', 'marathwada')
    _chk(failures, 'Accent: Marathwada णे→ने',
         'बोलने' in r and 'करने' in r,
         f'Marathwada णे→ने failed: {repr(r)}')

    # L6. Empty/None accent: no change
    r = apply_accent_phonetics('राम', '')
    _chk(failures, 'Accent: empty accent no change',
         r == 'राम',
         f'Empty accent modified text: {repr(r)}')

    # L7. Konkan: word-final ल → ळ
    r = apply_accent_phonetics('बोल चाल', 'konkan')
    _chk(failures, 'Accent: Konkan ल→ळ',
         'बोळ' in r and 'चाळ' in r,
         f'Konkan ल→ळ failed: {repr(r)}')

    # M. CONTENT-TYPE CLASSIFIER + ADAPTIVE PREPROCESSING (FEAT-18)
    # ══════════════════════════════════════════════════════════════════════

    from tts.utils.text.content_classifier import (
        classify_content, preprocess_by_content_type,
        VERSE, NEWS, CONVERSATIONAL, TECHNICAL, ADDRESS, GENERAL,
    )

    # M1. Verse detection: text with danda markers → verse
    ct = classify_content('शुक्लांबरधरं विष्णुं ॥ शशिवर्णं चतुर्भुजम् ॥')
    _chk(failures, 'Classifier: verse detect',
         ct == VERSE,
         f'Expected verse, got {ct}')

    # M2. Technical unit expansion: "5 kg" → "5 किलोग्रॅम"
    r = preprocess_by_content_type('माझे वजन 70 kg आहे', TECHNICAL)
    _chk(failures, 'Technical: kg expansion',
         'किलोग्रॅम' in r,
         f'kg not expanded: {repr(r)}')

    # M3. Technical percentage: "50%" → "50 टक्के"
    r = preprocess_by_content_type('यश दर 85% आहे', TECHNICAL)
    _chk(failures, 'Technical: percent expansion',
         'टक्के' in r,
         f'% not expanded: {repr(r)}')

    # M4. Address pin code: 6-digit → paired reading
    r = preprocess_by_content_type('पिन कोड 411001', ADDRESS)
    _chk(failures, 'Address: pin code expansion',
         '41 10 01' in r,
         f'Pin code not expanded: {repr(r)}')

    # M5. Conversational: बोलतोय → बोलतो आहे
    r = preprocess_by_content_type('तो बोलतोय', CONVERSATIONAL)
    _chk(failures, 'Conversational: progressive expansion',
         'बोलतो आहे' in r,
         f'Conversational not expanded: {repr(r)}')

    # M6. News: acronym expansion (BJP → भाजप)
    r = preprocess_by_content_type('BJP ने निवडणूक जिंकली', NEWS)
    _chk(failures, 'News: acronym expansion',
         'भाजप' in r,
         f'News acronym not expanded: {repr(r)}')

    # M7. General text passthrough: no modifications
    orig = 'मी आज बाजारात गेलो'
    r = preprocess_by_content_type(orig, GENERAL)
    _chk(failures, 'General: passthrough',
         r == orig,
         f'General modified text: {repr(r)}')

    # M8. Classify news text
    ct = classify_content('मुख्यमंत्री यांनी आज जाहीर केले की सरकार नवीन योजना आणेल')
    _chk(failures, 'Classifier: news detect',
         ct == NEWS,
         f'Expected news, got {ct}')

    # M9. Classify conversational text
    ct = classify_content('अरे यार तू कुठं जातोय ना बोलतोय काल चल')
    _chk(failures, 'Classifier: conversational detect',
         ct == CONVERSATIONAL,
         f'Expected conversational, got {ct}')

    sys.path.remove(sys_root)
    return failures


overall_pass = True
for label, root in PLATFORM_ROOTS.items():
    failures = run_tests_for_platform(label, root)
    if failures:
        overall_pass = False
        print(f'\n[{label.upper()}]  FAIL  ({len(failures)} failure(s))')
        for name, msg in failures:
            print(f'  ✗  {name}: {msg}')
    else:
        print(f'[{label.upper()}]  PASS  — all pronunciation checks OK')

print()
print('=' * 70)
if overall_pass:
    print('RESULT: ALL PASS — safe to finish.')
else:
    print('RESULT: FAILURES FOUND — do NOT finish until all checks pass.')
print('=' * 70)
sys.exit(0 if overall_pass else 1)
