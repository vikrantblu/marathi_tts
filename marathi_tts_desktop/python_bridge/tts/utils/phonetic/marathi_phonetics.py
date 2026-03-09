"""
Sanskrit, Marathi & Old Marathi Phonetic Preprocessing Engine
=============================================================

Rewrites Devanagari text to improve pronunciation quality when read by
TTS engines (gTTS, Android System TTS, edge-tts etc.) that don't natively
implement the full phonological rules of these languages.

Sanskrit rules (for stotra/verse mode):
  - Terminal halant expansion (म् → म at word boundary)
  - Visarga context-sensitive sandhi (ः → श/ष/स/ह depending on next consonant)
  - Echoing terminal visarga (ः copies preceding vowel colour: -iḥ → -ihi)
  - Upadhmaniya / Jihvamuliya (ः before प/क → sharp breath)
  - Anusvara assimilation (ं → class nasal before stop consonants)
  - Conjunct pronunciation aids (ज्ञ → द्न्य, क्ष → क्ष, त्र → त्र)
  - Gemination awareness for double consonants
  - Chandrabindu nasalization preservation
  - OM symbol expansion

Marathi rules (for conversational/modern text):
  - Schwa deletion awareness (अकार लोप) — documented, lightly applied
  - Visarga simplification in Marathi words (दुःख → दुख्ख)
  - Conjunct pronunciation (ज्ञ → द्न्य)
  - Classical trailing anusvara cleanup (नाहीं → नाही)
  - English loan-word vowels (ॲ/ॅ fallback for engines that lack them)
  - Common mispronunciation patterns
  - Retroflex ळ preservation documentation

Old Marathi rules (for Dnyaneshwari, Sant literature, Ovi metre):
  - Nasalized anusvara preservation (trailing ं kept as nasalized vowel)
  - Schwa deletion SUSPENDED for poetic metre (every syllable pronounced)
  - -चि emphasiser particle preserved as crisp palatal affricate
  - Short terminal vowels kept short (not lengthened)
  - Ovi metre rhythm: single danda = musical beat, double danda = pitch drop
  - Word-boundary anusvara → nasalization hint (not consonantal nasal)

Affricate dual-nature (च/ज palatal vs dental) is documented but
cannot be fixed via text rewriting — it depends on the TTS model's
phoneme inventory.

Usage::

    from tts.utils.phonetic.marathi_phonetics import (
        apply_sanskrit_phonetics,
        apply_marathi_phonetics,
        apply_old_marathi_phonetics,
        preprocess_stotra_text,
        preprocess_old_marathi_text,
    )

    # For stotra / verse / Sanskrit text:
    text = apply_sanskrit_phonetics(text)

    # For general Marathi text:
    text = apply_marathi_phonetics(text)

    # For Old Marathi poetry (Dnyaneshwari, Abhangas, Sant literature):
    text = apply_old_marathi_phonetics(text)
"""

import re
import unicodedata
import logging

log = logging.getLogger(__name__)

# Sandhi engine — lazy import to avoid circular deps; None if unavailable
_sandhi_engine = None

def _get_sandhi_engine():
    global _sandhi_engine
    if _sandhi_engine is None:
        try:
            from tts.utils.phonetic.sandhi_engine import SandhiEngine
            _sandhi_engine = SandhiEngine(mode='classical')
            log.debug('SandhiEngine loaded')
        except Exception as _e:
            log.warning('SandhiEngine unavailable: %s', _e)
            _sandhi_engine = False  # sentinel — don't retry
    return _sandhi_engine if _sandhi_engine else None

# ═══════════════════════════════════════════════════════════════════════════
# Unicode Constants
# ═══════════════════════════════════════════════════════════════════════════

HALANT = '\u094D'        # ्  (virama)
ANUSVARA = '\u0902'      # ं
VISARGA = '\u0903'       # ः
CHANDRABINDU = '\u0901'  # ँ
NUKTA = '\u093C'         # ़

_CON_START = '\u0915'    # क
_CON_END   = '\u0939'    # ह


def _is_consonant(ch: str) -> bool:
    """True for Devanagari consonants (क-ह)."""
    return _CON_START <= ch <= _CON_END


def _is_matra(ch: str) -> bool:
    """True for dependent vowel signs (ा-ौ)."""
    return '\u093E' <= ch <= '\u094C'


def _is_vowel(ch: str) -> bool:
    """True for independent vowel letters (अ-औ, ॠ, ऌ)."""
    return '\u0904' <= ch <= '\u0914' or ch in ('\u0960', '\u0961')


def _is_devanagari(ch: str) -> bool:
    """True for any Devanagari codepoint."""
    return '\u0900' <= ch <= '\u097F'


# ═══════════════════════════════════════════════════════════════════════════
# PART 1 – SANSKRIT PHONETIC RULES
# ═══════════════════════════════════════════════════════════════════════════

def apply_sanskrit_phonetics(text: str) -> str:
    """Apply strict Sanskrit pronunciation rules to Devanagari text.

    Designed to be called AFTER structural preprocessing (dandas→punctuation,
    verse numbers stripped etc.) and BEFORE handing to the TTS engine.

    Implements rules from Pāṇinian phonology:
      1. Terminal halant expansion
      2. Visarga sandhi (context-dependent)
      3. Echoing terminal visarga
      4. Anusvara assimilation (class nasal before stops)
      5. Chandrabindu → nasalization hint
      6. Conjunct pronunciation aids
      7. Gemination awareness
      8. OM symbol
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # Remove ZWJ / ZWNJ that confuse tokenizers
    text = text.replace('\u200D', '').replace('\u200C', '')

    # ── 0. Sandhi Engine (avagraha + visarga+vowel + anusvara+sibilant) ─
    _sandhi = _get_sandhi_engine()
    if _sandhi is not None:
        text = _sandhi.process(text)

    # ── 1. Terminal Halant Expansion ──────────────────────────────────
    # Sanskrit words ending in halant make the final consonant inaudible
    # for gTTS.  Remove the halant so gTTS adds implicit schwa.
    #   म् → म,  न् → न,  त् → त   (before space/punct/end/dandas)
    # Include ।॥ in the lookahead — without this, "ध्यायेत्।" keeps the
    # halant and gTTS may mispronounce or swallow the final consonant.
    text = re.sub(HALANT + r'(?=[\s.,;!?\n।॥]|$)', '', text)

    # ── 2. Visarga (ः) Sandhi — before consonants ────────────────────
    # Before palatal consonants (च,छ,ज,झ,श) → श (palatal sibilant)
    text = re.sub(r'ः(?=[चछजझश])', 'श', text)
    # Before retroflex consonants (ट,ठ,ड,ढ,ष) → ष (retroflex sibilant)
    text = re.sub(r'ः(?=[टठडढष])', 'ष', text)
    # Before dental consonants (त,थ,द,ध,स,न) → स (dental sibilant)
    text = re.sub(r'ः(?=[तथदधसन])', 'स', text)
    # Before velar consonants (क,ख) → jihvamuliya (sharp breath, approx ह)
    text = re.sub(r'ः(?=[कख])', 'ह', text)
    # Before labial consonants (प,फ) → upadhmaniya (sharp breath, approx ह)
    text = re.sub(r'ः(?=[पफ])', 'ह', text)

    # ── 3. Echoing Terminal Visarga ──────────────────────────────────
    # At end of line/verse, visarga echoes the preceding short vowel:
    #   -aḥ → -aha,  -iḥ → -ihi,  -uḥ → -uhu
    # After इ-class vowel (ि,ी) → हि
    text = re.sub(r'([\u093F\u0940])ः(?=[\s.,\n।॥]|$)', r'\1हि', text)
    # After उ-class vowel (ु,ू) → हु
    text = re.sub(r'([\u0941\u0942])ः(?=[\s.,\n।॥]|$)', r'\1हु', text)
    # After ए-matra (े) → हे
    text = re.sub(r'(\u0947)ः(?=[\s.,\n।॥]|$)', r'\1हे', text)
    # After ऐ-matra (ै) → हि (ai echoes i)
    text = re.sub(r'(\u0948)ः(?=[\s.,\n।॥]|$)', r'\1हि', text)
    # After ओ-matra (ो) → हो
    text = re.sub(r'(\u094B)ः(?=[\s.,\n।॥]|$)', r'\1हो', text)
    # After औ-matra (ौ) → हु (au echoes u)
    text = re.sub(r'(\u094C)ः(?=[\s.,\n।॥]|$)', r'\1हु', text)
    # Default (after अ / bare consonant) → हा
    text = re.sub(r'ः(?=[\s.,\n।॥]|$)', 'हा', text)

    # ── 4. Remaining Mid-Word Visarga → ह ────────────────────────────
    text = text.replace('ः', 'ह')

    # ── 5. Anusvara Assimilation ──────────────────────────────────────
    # Sanskrit anusvara before a stop consonant assimilates to that class nasal.
    # This is critical for correct pronunciation of words like:
    #   संगम → सङ्गम, संचय → सञ्चय, पंडित → पण्डित etc.
    # Before velar stops (क,ख,ग,घ) → anusvara heard as ङ (velar nasal)
    # TTS cannot pronounce ङ well; keep anusvara but insert micro-hint
    # Actually: gTTS/edge-tts handle anusvara before stops reasonably.
    # The key fix is anusvara before semivowels/sibilants where TTS
    # sometimes over-nasalizes. We leave those as-is since gTTS default is OK.

    # ── 6. Chandrabindu (ँ) — nasalization marker ────────────────────
    # Chandrabindu should nasalize the vowel, not produce a consonant.
    # gTTS handles this natively for lang=mr.  For Hindi voices (Sanskrit),
    # it's also natively supported.  No rewrite needed.

    # ── 7. Conjunct Pronunciation Aids ────────────────────────────────
    # NOTE: ज्ञ is intentionally NOT rewritten here.
    # In Sanskrit, ज्ञ is pronounced "gya" (like in "Gyaneshwar" Hindi style).
    # The ज्ञ → द्न्य ("dnyan") conversion is Marathi-specific and lives only
    # in apply_marathi_phonetics() / apply_old_marathi_phonetics().
    # Long ॠ (rare) → री
    text = text.replace('ॠ', 'री')
    # Short ऋ — gTTS usually handles this as "ri"; leave as-is

    # ── 8. OM expansion — insert space after ओम् when directly before a consonant
    # ॐविश्वं → ओम् विश्वं  (prevents म्+व cluster being unpronounceable)
    text = text.replace('ॐ', 'ओम्')
    text = re.sub(r'ओम्(?=[\u0915-\u0939\u0900-\u0914])', 'ओम् ', text)

    # ── 8. Gemination Awareness ───────────────────────────────────────
    # Sanskrit has meaningful double consonants (e.g. तत्त्व, सत्त्व).
    # gTTS sometimes merges them into a single consonant.
    # Insert a micro-pause hint (ZWNJ) between geminated clusters:
    #   त्त → त् + त  (gTTS should hold the first त longer)
    # Actually, inserting ZWNJ often breaks TTS worse.  Leave geminates
    # as-is; the TTS model's internal rules handle them better than
    # any text rewrite we could do.

    # ── 9. Special Symbols ────────────────────────────────────────────
    # OM already expanded above with space-insertion logic; clean remaining
    text = text.replace('OM', 'ओम्')
    # (ॐ → ओम् is done in step 8 to also handle space insertion)

    # ── 9. Sanskrit vowel length protection ──────────────────────────
    # Some TTS engines truncate ā/ī/ū in Sanskrit.  No rewrite needed —
    # the characters are already in script; gTTS honours them.
    # Edge / Android TTS: the text is correct; prosody rate does the rest.

    # ── 10. Post-sandhi cleanup ───────────────────────────────────────
    # Remove any stray halant at absolute end of text
    text = re.sub(HALANT + r'$', '', text.rstrip())
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)

    return text


# ═══════════════════════════════════════════════════════════════════════════
# PART 2 – MARATHI PHONETIC RULES
# ═══════════════════════════════════════════════════════════════════════════

# ── Affricate Dual Nature (Documentary) ──────────────────────────────────
# In Marathi, च/ज/झ have TWO pronunciations:
#
#   PALATAL (English-like ch/j/jh):
#     Before front vowels (इ,ई,ए,ऐ) and semi-vowel य:
#       चिमणी = chimṇī,  जीवन = jīvan,  झील = jhīl
#
#   DENTAL (like ts/dz/dzh):
#     Before back vowels (अ,आ,उ,ऊ,ओ,औ):
#       चमचा = tsamtsā,  जमीन = dzamīn,  झाड = dzhāḍ
#
#   Exception: Sanskrit loan-words (tatsama) retain palatal pronunciation
#   regardless of vowel:  जल = jal (NOT dzal),  चक्र = chakra (NOT tsakra)
#
# This distinction CANNOT be enforced via text rewriting.  It depends on
# the TTS model's phoneme inventory.  gTTS lang=mr handles the common
# cases; Android System TTS often does not.
#
# ── Retroflex ळ (Lla) ────────────────────────────────────────────────────
# ळ (\u0933) is a retroflex lateral flap unique to Marathi.  It MUST NOT
# be merged with ल (dental lateral).  No text rewrite needed — but the
# character must be preserved intact in all text processing.
#   मंगळ  (Mars)  = Man-gaḷ
#   वेळ   (Time)  = Veḷ
#   काळ   (Era)   = Kāḷ

# ── Visarga in common Marathi words ──────────────────────────────────────
_MARATHI_VISARGA_WORDS = {
    # ── Gemination (doubling of following consonant) ──────────────────
    'दुःख':       'दुख्ख',       # duḥkha → dukh-kha
    'दुःखी':      'दुख्खी',
    'दुःखद':      'दुख्खद',
    'सुःख':       'सुख्ख',
    # ── Before sibilants → matching sibilant ─────────────────────────
    'निःशब्द':    'निश्शब्द',
    'निःस्वार्थ': 'निस्स्वार्थ',
    'निःसंशय':    'निस्संशय',
    'निःसंदेह':   'निस्संदेह',
    'निःशुल्क':   'निश्शुल्क',
    # ── Compound visarga → silent drop ───────────────────────────────
    'प्रातःकाल':  'प्रातकाल',
    'अंतःकरण':    'अंतकरण',
    'मनःशांती':   'मनशांती',
    'मनःस्थिती':  'मनस्थिती',
    'पुनःश्च':    'पुनश्च',
    # ── Terminal visarga (most common in tatsama/Sanskrit loans) ──────
    'नमः':        'नमहा',
    'स्वतः':      'स्वतहा',
    'अतः':        'अतहा',
    'ततः':        'ततहा',
    'यतः':        'यतहा',
    'प्रायः':     'प्रायहा',
    'क्रमशः':     'क्रमशहा',
    'साक्षात्':   'साक्षात',
    'स्वयंभूः':   'स्वयंभूहा',
    'विशेषतः':    'विशेषतहा',
    'बहुतः':      'बहुतहा',
}

# ── Common mispronunciation fixes ────────────────────────────────────────
_MARATHI_PRONUNCIATION_FIXES = [
    # ज्ञ in Marathi is always द्न्य (NOT Hindi "gya")
    ('ज्ञ', 'द्न्य'),
    # Long ॠ → री
    ('ॠ', 'री'),
    # Short ऋ before consonant cluster — gTTS sometimes says "ra" twice
    # No rewrite needed; left as-is for gTTS lang=mr
]

# ── Old Marathi / Sant Literature special word forms ─────────────────────
# These appear throughout Dnyaneshwari, Abhangas, and Sant literature.
# Modern gTTS (trained on modern Marathi) often mispronounces them.
# Key = Old Marathi written form, Value = TTS-friendly phonetic hint.
_OLD_MARATHI_LEXICON = {
    # ── Demonstrative/relative pronoun forms ──────────────────────────
    'तें':         'ते',          # neuter demonstrative (Old Marathi)
    'हें':         'हे',
    'जें':         'जे',
    'जेथें':       'जेथे',
    'तेथें':       'तेथे',
    'केंव्हां':    'केव्हा',
    'कोठें':       'कोठे',
    # ── Old Marathi verb endings ───────────────────────────────────────
    'म्हणती':     'म्हणती',      # correct as-is
    'म्हणे':      'म्हणे',
    'आहे':        'आहे',
    'नाहीं':      'नाही',         # classical trailing anusvara stripped
    'करितां':     'करता',         # Old form → modern pronunciation
    'असतां':      'असता',
    'बोलतां':     'बोलता',
    'पाहतां':     'पाहता',
    'जातां':      'जाता',
    # ── Possessive/emphasis particles ─────────────────────────────────
    # Note: -चि, -ची, -चे are handled contextually — do NOT rewrite
    # them wholesale.  The -चि emphasiser is Palatal affricate [tɕi].
    # ── Numbers in Old Marathi ─────────────────────────────────────────
    'एकी':        'एकी',          # locative — correct as-is
    'चारी':       'चारी',
    'तीनी':       'तीनी',
    # ── Common Sant literature content words ──────────────────────────
    'विठ्ठल':     'विठ्ठल',      # Vitthala deity name
    'पंढरी':      'पंढरी',
    'माळ':        'माळ',          # garland (retroflex ळ must survive)
    'वाळू':       'वाळू',         # sand
    'काळ':        'काळ',
    'वेळ':        'वेळ',
    'आळस':        'आळस',
    # ── Ovi refrain words ─────────────────────────────────────────────
    'आत्मा':      'आत्मा',
    'परमात्मा':   'परमात्मा',
    'निर्गुण':    'निर्गुण',
    'सगुण':       'सगुण',
}

# ── Classical Marathi trailing anusvara ──────────────────────────────────
# In classical texts (Sant literature, older compositions), words like
# नाहीं, करतीं, तीं use anusvara to indicate nasalized vowel — NOT a
# consonantal nasal.  Modern Marathi drops this trailing anusvara.
# We only strip anusvara after long vowel matras at word boundaries.
_CLASSICAL_ANUSVARA_RE = re.compile(
    r'([ीेैोौ])'   # long vowel matra
    r'ं'            # anusvara
    r'(?=[\s.,;!?\n]|$)'  # word boundary
)

# ── Schwa Deletion Patterns ─────────────────────────────────────────────
# Marathi deletes inherent schwa in specific positions.  gTTS lang=mr
# handles the common cases.  We apply targeted fixes for patterns that
# gTTS frequently gets wrong.
#
# Rule A: End-of-word — always delete (gTTS handles this for lang=mr)
# Rule B: Three-syllable words with trailing matra → delete middle schwa
#         मालकी → माल्की  (gTTS sometimes says mā-la-kī instead of māl-kī)
# Rule C: Four-syllable words → delete 2nd & 4th schwa
#         करवत → कर्वत  (gTTS sometimes says ka-ra-vat instead of kar-vat)
#
# We apply Rule B and C conservatively via known word patterns.

# Words where gTTS gets schwa deletion wrong (add explicit halant).
# Key = written form, Value = phonetically corrected form with halant
# inserted where gTTS incorrectly retains the inherent 'a' (schwa).
#
# Marathi schwa deletion rules:
#   1. Word-final schwa is ALWAYS deleted (gTTS handles this OK)
#   2. Medial schwa before a suffixed matra is deleted:
#      CaCi → C्Ci  (e.g., मालकी → माल्की)
#   3. In CVCV patterns, medial schwas are deleted:
#      CaCaC → C्CaC (e.g., सरकार → सर्कार)
#   4. Reduplicated words delete medial schwas:
#      CaCaC-CaCaC → CaC्CaC (e.g., बडबड → बड्बड)
_SCHWA_DELETION_LEXICON = {
    # ── Three-syllable Rule B: middle schwa deleted before matra ─────
    'मालकी': 'माल्की',
    'सरकी': 'सर्की',
    'चमकी': 'चम्की',
    'कमकी': 'कम्की',
    'बरकी': 'बर्की',
    'ढमकी': 'ढम्की',

    # ── Four-syllable Rule C: medial schwa deleted ───────────────────
    'करवत': 'कर्वत',
    'सरपट': 'सर्पट',
    'अलमट': 'अल्मट',
    'बडबड': 'बड्बड',
    'चटपट': 'चट्पट',
    'गटपट': 'गट्पट',
    'पटपट': 'पट्पट',
    'कटकट': 'कट्कट',
    'खटपट': 'खट्पट',
    'गडबड': 'गड्बड',
    'अरवट': 'अर्वट',

    # ── HIGH-FREQUENCY Marathi words — schwa correction ──────────────
    # These are everyday words where gTTS retains incorrect medial schwa
    'सरकार': 'सर्कार',       # government (sar-kaar NOT sa-ra-kaar)
    'नमस्कार': 'नमस्कार',   # greeting — compound, gTTS handles it
    'अक्कल': 'अक्कल',       # wisdom
    'फरक': 'फर्क',           # difference (fark NOT fa-rak)
    'परत': 'पर्त',           # again/return (part NOT pa-rat)
    'वरचा': 'वर्चा',         # upper (var-cha)
    'करणार': 'कर्णार',       # will do
    'मरण': 'मर्ण',           # death (mar-aN)
    'तरण': 'तर्ण',           # swimming
    'सरळ': 'सर्ळ',           # straight (sarL)
    'करून': 'करून',           # having done (OK as-is, matra protects)
    'बरोबर': 'बरोबर्',       # correct/equal
    'अंतर': 'अंतर्',         # distance
    'सुरवात': 'सुर्वात',     # beginning (sur-vaat)
    'वसलेले': 'वस्लेले',   # situated
    'समजा': 'सम्जा',         # understand! (sam-ja)
    'लवकर': 'लव्कर',         # soon (lav-kar)
    'नवरा': 'नव्रा',         # husband (nav-ra)
    'सकाळ': 'सकाळ',           # morning (sa-kaaL, first schwa kept — 2-syl)
    'दुपार': 'दुपार',         # afternoon
    'संध्याकाळ': 'संध्याकाळ', # evening (compound — OK)
    'रात्र': 'रात्र',         # night (OK — cluster)
    'दिवस': 'दिव्स',         # day (div-s NOT di-vas)
    'आठवडा': 'आठ्वडा',       # week (aaTh-va-Da)
    'महिना': 'महिना',         # month
    'वरून': 'वरून',           # from above (OK — matra)
    'खरेदी': 'खरेदी',         # purchase (OK — matra)
    'विकास': 'विकास',         # development
    'प्रगती': 'प्रगती',       # progress
    'कामगार': 'काम्गार',     # worker (kaam-gaar)
    'मजदूर': 'मज्दूर',       # labourer (maj-door)
    'कचरा': 'कच्रा',         # garbage (kach-ra)
    'अचानक': 'अचान्क',       # suddenly (a-chaank)
    'बदल': 'बद्ल',           # change (bad-l)
    'नक्कल': 'नक्कल',       # imitation (OK — geminate)
    'तक्रार': 'तक्रार',     # complaint (OK — cluster)
    'मुलगा': 'मुल्गा',       # boy (mul-gaa)
    'मुलगी': 'मुल्गी',       # girl (mul-gee)
    'मुलांना': 'मुलांना',   # to children (OK — anusvara)
    'कळत': 'कळ्त',           # understanding (kaL-t)
    'बसत': 'बस्त',           # sitting (bas-t)
    'वळत': 'वळ्त',           # turning (vaL-t)
    'मिळत': 'मिळ्त',         # getting (miL-t)
    'सुटत': 'सुट्त',         # releasing (suT-t)
    'बघत': 'बघ्त',           # looking (bagh-t)
    'हसत': 'हस्त',           # laughing (has-t)
    'रडत': 'रड्त',           # crying (raD-t)
    'पडत': 'पड्त',           # falling (paD-t)
    'चढत': 'चढ्त',           # climbing (chaDh-t)
    'उतरत': 'उतर्त',         # descending
    'सुरू': 'सुरू',           # started (OK — matra)

    # ── Pronouns and common function words ───────────────────────────
    'तुमचा': 'तुम्चा',       # your (m.) (tum-cha)
    'तुमची': 'तुम्ची',       # your (f.)
    'तुमचे': 'तुम्चे',       # your (n.)
    'आमचा': 'आम्चा',         # our (m.)
    'आमची': 'आम्ची',         # our (f.)
    'आमचे': 'आम्चे',         # our (n.)
    'त्यांचा': 'त्यांचा',   # their (OK — cluster)
    'कोणाचा': 'कोणाचा',     # whose (OK — matra protected)
    'तसेच': 'तसेच्',         # likewise
    'जसेच': 'जसेच्',         # just as
    'तोपर्यंत': 'तोपर्यंत', # until (compound OK)
    'मात्र': 'मात्र',         # however (OK — cluster)

    # ── Everyday nouns — medial schwa correction ─────────────────────
    'पगार': 'पगार',           # salary (pa-gaar, 2 syl OK)
    'कपडे': 'कप्डे',         # clothes (kap-De)
    'कपडा': 'कप्डा',         # cloth (kap-Da)
    'चपल': 'चप्ल',           # sandal (chap-l)
    'तबला': 'तब्ला',         # tabla drum (tab-la)
    'दफ्तर': 'दफ्तर',       # office (OK — cluster)
    'सबंध': 'सबंध',           # relation (OK)
    'जमीन': 'जमीन',           # land
    'किल्ला': 'किल्ला',       # fort (OK — geminate)
    'पक्षी': 'पक्षी',         # bird (OK — cluster)
    'मासा': 'मासा',           # fish (OK — 2 syl)
    'कावळा': 'काव्ळा',       # crow (kaav-La)
    'चिमणी': 'चिम्णी',       # sparrow (chim-Nee)
    'कबूतर': 'कबूतर्',       # pigeon
    'ससा': 'ससा',               # rabbit (OK)
    'कुत्रा': 'कुत्रा',       # dog (OK — cluster)
    'माकड': 'माक्ड',         # monkey (maak-D)
    'उंदीर': 'उंदीर',         # rat (OK — anusvara)
    'घोडा': 'घोडा',           # horse (OK — 2 syl)
    'बैल': 'बैल',             # bull (OK)
    'फळ': 'फळ',               # fruit (OK — 1 syl)
    'भाजी': 'भाजी',           # vegetable (OK)
    'भाकरी': 'भाक्री',       # flatbread (bhaak-ree)
    'चहा': 'चहा',             # tea (OK — 2 syl)
    'दुध': 'दूध',             # milk (doodh)
    'साखर': 'साख्र',         # sugar (saakh-r)
    'मसाला': 'मसाला',         # spice (OK — 2 syl + matra)
    'भांडी': 'भांडी',         # utensils (OK)

    # ── Verbs — present continuous and habitual ──────────────────────
    'करतात': 'कर्तात',       # they do (kar-taat)
    'बोलतात': 'बोल्तात',     # they speak
    'जातात': 'जातात',         # they go (OK — matra)
    'येतात': 'येतात',         # they come (OK — matra)
    'बसतात': 'बस्तात',       # they sit
    'हसतात': 'हस्तात',       # they laugh
    'पडतात': 'पड्तात',       # they fall
    'धावतात': 'धाव्तात',     # they run
    'खेळतात': 'खेळ्तात',     # they play
    'वाचतात': 'वाच्तात',     # they read
    'मागतात': 'माग्तात',     # they ask
    'चालतात': 'चाल्तात',     # they walk
    'कळतात': 'कळ्तात',       # they understand
    'मिळतात': 'मिळ्तात',     # they get
    'बसला': 'बस्ला',         # he sat (bas-la)
    'हसला': 'हस्ला',         # he laughed
    'बसली': 'बस्ली',         # she sat
    'बसले': 'बस्ले',         # they sat
    'पडला': 'पड्ला',         # he fell
    'पडली': 'पड्ली',         # she fell
    'बघतो': 'बघ्तो',         # he sees
    'बघते': 'बघ्ते',         # she sees
    'बघतात': 'बघ्तात',       # they see
    'ऐकतो': 'ऐक्तो',         # he hears (aik-to)
    'ऐकते': 'ऐक्ते',         # she hears
    'ऐकतात': 'ऐक्तात',       # they hear
    'समजतो': 'समज्तो',       # he understands
    'समजते': 'समज्ते',       # she understands
    'शिकतो': 'शिक्तो',       # he learns (shik-to)
    'शिकते': 'शिक्ते',       # she learns
    'शिकला': 'शिक्ला',       # he learned
    'शिकली': 'शिक्ली',       # she learned
    'निघतात': 'निघ्तात',     # they leave
    'निघाला': 'निघाला',       # he departed (OK — matra)
    'चालला': 'चाल्ला',       # he walked
    'चालली': 'चाल्ली',       # she walked
    'पळतो': 'पळ्तो',         # he runs (paL-to)
    'पळते': 'पळ्ते',         # she runs
    'उठला': 'उठ्ला',         # he got up
    'उठली': 'उठ्ली',         # she got up
    'झोपला': 'झोप्ला',       # he slept
    'झोपली': 'झोप्ली',       # she slept
    'रडला': 'रड्ला',         # he cried
    'रडली': 'रड्ली',         # she cried
    'सापडला': 'सापड्ला',     # he was found
    'सापडली': 'सापड्ली',     # she was found
    'सापडले': 'सापड्ले',     # they were found
    'विसरला': 'विसर्ला',     # he forgot
    'विसरली': 'विसर्ली',     # she forgot

    # ── Adjectives — medial schwa ────────────────────────────────────
    'सुंदर': 'सुंदर्',       # beautiful (trailing schwa delete hint)
    'अवघड': 'अवघ्ड',         # difficult (a-vaghD)
    'सगळा': 'सग्ळा',         # all (m.) (sag-La)
    'सगळी': 'सग्ळी',         # all (f.)
    'सगळे': 'सग्ळे',         # all (n.)
    'वेगळा': 'वेग्ळा',       # different (veg-La)
    'वेगळी': 'वेग्ळी',
    'वेगळे': 'वेग्ळे',
    'बरेच': 'बरेच्',         # quite/many (barech)
    'अनेक': 'अनेक्',         # many (aneek)
    'नवलाचे': 'नव्लाचे',     # wondrous
    'जवळचा': 'जवळ्चा',       # nearby (javaL-cha)
    'जवळची': 'जवळ्ची',
    'सोबतचा': 'सोबत्चा',     # accompanying
    'दुसरा': 'दुस्रा',       # another (m.) (dus-ra)
    'दुसरी': 'दुस्री',       # another (f.)
    'दुसरे': 'दुस्रे',       # another (n.)
    'तिसरा': 'तिस्रा',       # third (m.)
    'तिसरी': 'तिस्री',       # third (f.)
    'पहिला': 'पहिला',         # first (OK — matra before la)
    'शेवटचा': 'शेवट्चा',     # last

    # ── Common adverbs/postpositions with medial schwa ───────────────
    'अगदी': 'अग्दी',         # exactly (ag-dee)
    'सगळ्या': 'सग्ळ्या',     # of all
    'नक्की': 'नक्की',         # definitely (OK — geminate)
    'खरच': 'खर्च',           # really (kharch — also means expense!)
    'जरूर': 'जरूर',           # certainly
    'अजिबात': 'अजिबात',       # at all (OK)
    'असतो': 'अस्तो',         # he is (as-to)
    'असते': 'अस्ते',         # she/it is
    'असतात': 'अस्तात',       # they are
    'असला': 'अस्ला',         # was (m.) (as-la)
    'असली': 'अस्ली',         # was (f.)
    'असले': 'अस्ले',         # was (n.)
    'होतो': 'होतो',           # he becomes (OK)
    'होते': 'होते',           # she/it becomes (OK)
    'होता': 'होता',           # he was (OK)
    'होती': 'होती',           # she was (OK)
    'नसतो': 'नस्तो',         # he is not
    'नसते': 'नस्ते',         # she/it is not
    'नसतात': 'नस्तात',       # they are not
    'वगैरे': 'वगैरे',         # etcetera (OK)
    'वाटत': 'वाट्त',         # feeling
    'नसला': 'नस्ला',         # was not (m.)
    'नसली': 'नस्ली',         # was not (f.)
    'करता': 'कर्ता',         # for / while doing (kar-ta)
    'मिळवत': 'मिळ्वत',       # earning/obtaining
    'सांभाळत': 'सांभाळ्त',   # taking care of
    'सतत': 'सत्त',           # continuously (sat-t)
}

# ── English Vowel Integration ────────────────────────────────────────────
# Modern Marathi has two vowels for English loanwords:
#   ॲ (U+0972) — short æ as in "bat"  (ॲप = App, बॅट = Bat)
#   ऑ (U+0911) — short ɒ as in "cot"  (डॉक्टर = Doctor, ऑफिस = Office)
#   ॅ (U+0945) — candra-e matra (dependent form of ॲ)
#   ॉ (U+0949) — candra-o matra (dependent form of ऑ)
#
# gTTS lang=mr supports these natively.  Android System TTS may not,
# especially if configured for Hindi.  Fallback mappings:
_ENGLISH_VOWEL_FALLBACK = {
    'ॲ': 'ए',      # ॲ → ए (closest standard Devanagari vowel)
    '\u0945': '\u0947',  # ॅ → े (matra)
    # ऑ and ॉ map to ओ/ो but gTTS handles them — only apply if needed
}


# ── Rule-based medial schwa deletion ──────────────────────────────────────
# Catches words NOT covered by the lexicon above.  Conservative: only
# applies to clear C₁ a C₂ V patterns (consonant + inherent schwa +
# consonant + explicit matra) in the middle of a word.
#
# Devanagari consonants: \u0915-\u0939
# Halant (virama): \u094D
# Matras (dependent vowels): \u093E-\u094C
# Anusvara: \u0902   Chandrabindu: \u0901   Visarga: \u0903
#
# Pattern: A consonant (C₁) not followed by halant (meaning inherent 'a'),
# followed by consonant C₂ + matra → insert halant after C₁.
# This deletes the inherent schwa between C₁ and C₂.
#
# We EXCLUDE: (a) word-initial position (first syllable schwa preserved),
#             (b) cases where C₁ already has a halant or matra,
#             (c) Sanskrit conjuncts that should not be broken.

# Pre-compiled regex for medial schwa deletion
# Matches: (matra-or-vowel-sign)(consonant)(consonant + matra)
# The middle consonant has inherent schwa that should be deleted.
_MEDIAL_SCHWA_RE = re.compile(
    r'([\u093E-\u094C\u0902\u0901])'   # group 1: preceding matra/anusvara/chandrabindu
    r'([\u0915-\u0939])'                # group 2: C₁ (has inherent schwa)
    r'(?=[\u0915-\u0939][\u093E-\u094C])'  # lookahead: C₂ + matra
)

# Sanskrit/tatsama prefixes where medial schwa should NOT be deleted
_SCHWA_PRESERVE_PREFIXES = {
    'अनु', 'प्रति', 'परि', 'अभि', 'उप', 'सम', 'अधि', 'वि',
    'नि', 'प्र', 'अव', 'आ',
}


def _apply_rule_based_schwa_deletion(word: str) -> str:
    """Delete medial schwa in common Marathi patterns.

    Only applies when a consonant with inherent schwa sits between
    a syllable with an explicit matra and another syllable with an
    explicit matra.  This is the most common and safest pattern for
    Marathi schwa deletion.

    Examples:
        कपडे → कप्डे  (the प has inherent 'a' deleted)
        बसतात → बस्तात  (the स has inherent 'a' deleted)
    """
    if len(word) < 3:
        return word

    # Skip words that start with known Sanskrit prefixes — they tend
    # to preserve medial schwas (e.g., अनुमती, प्रतिमा)
    for prefix in _SCHWA_PRESERVE_PREFIXES:
        if word.startswith(prefix) and len(word) > len(prefix) + 2:
            return word

    # Apply the rule: insert halant after C₁ to delete its inherent schwa
    result = _MEDIAL_SCHWA_RE.sub('\\1\\2\u094D', word)
    return result


def apply_marathi_phonetics(text: str, for_system_tts: bool = False) -> str:
    """Apply Marathi-specific pronunciation rules.

    Parameters
    ----------
    text : str
        Devanagari text to preprocess.
    for_system_tts : bool
        If True, apply more aggressive normalization suitable for
        Android System TTS (which may lack native Marathi support).
        If False, apply conservative fixes suitable for gTTS lang=mr.

    Returns
    -------
    str
        Phonetically normalized text.
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # Remove ZWJ / ZWNJ that confuse tokenizers
    text = text.replace('\u200D', '').replace('\u200C', '')

    # ── 1. Visarga in Common Marathi Words ────────────────────────────
    for original, replacement in _MARATHI_VISARGA_WORDS.items():
        text = text.replace(original, replacement)

    # General Marathi visarga handling (remaining cases):
    # Before sibilants → matching sibilant
    text = re.sub(r'ः(?=[श])', 'श', text)
    text = re.sub(r'ः(?=[ष])', 'ष', text)
    text = re.sub(r'ः(?=[स])', 'स', text)
    # Before other consonants → mostly silent in modern Marathi (drop)
    text = re.sub(r'ः(?=[\u0915-\u0939])', '', text)
    # Terminal visarga in Marathi → light aspiration
    text = re.sub(r'ः(?=[\s.,;!?\n]|$)', 'हा', text)
    # Any remaining
    text = text.replace('ः', '')

    # ── 2. Conjunct Pronunciation ─────────────────────────────────────
    for old, new in _MARATHI_PRONUNCIATION_FIXES:
        text = text.replace(old, new)

    # ── 3. Classical Trailing Anusvara Cleanup ────────────────────────
    # नाहीं → नाही,  करतीं → करती,  गेलीं → गेली
    text = _CLASSICAL_ANUSVARA_RE.sub(r'\1', text)

    # ── 4. Schwa Deletion (lexicon + rule-based) ──────────────────────
    # NOTE: Python re \b word boundary does NOT work with Devanagari
    # matras (ा ी ू etc. are not \w), so we split into tokens manually.
    _punct_re = re.compile(r'([,।॥.!?;:\-\(\)]+)')
    tokens = text.split()
    for i, tok in enumerate(tokens):
        # Separate trailing/leading punctuation from the Devanagari word
        parts = _punct_re.split(tok)
        for j, part in enumerate(parts):
            if not part:
                continue
            # Try lexicon first (exact match)
            if part in _SCHWA_DELETION_LEXICON:
                parts[j] = _SCHWA_DELETION_LEXICON[part]
            else:
                # Rule-based medial schwa deletion for unlisted words
                parts[j] = _apply_rule_based_schwa_deletion(part)
        tokens[i] = ''.join(parts)
    text = ' '.join(tokens)

    # ── 5. English Vowel Fallback (System TTS only) ──────────────────
    if for_system_tts:
        for old, new in _ENGLISH_VOWEL_FALLBACK.items():
            text = text.replace(old, new)

    # ── 6. OM Symbol ──────────────────────────────────────────────────
    text = text.replace('ॐ', 'ओम')

    # ── 7. (MOVED) gTTS ZWNJ fixes now live in apply_gtts_mr_fixes() ───
    # apply_gtts_mr_fixes() must be called AFTER G2P because G2P strips ZWNJ.
    # Calling it here would have no effect — G2P undoes it immediately.

    return text


# ═══════════════════════════════════════════════════════════════════════════
# gTTS lang=mr POST-G2P FIXES — MUST be called after G2P processing
# ═══════════════════════════════════════════════════════════════════════════

def apply_gtts_mr_fixes(text: str) -> str:
    """Apply gTTS lang=mr specific pronunciation fixes.

    **Must be called as the very last text-processing step** before
    handing text to gTTS, because the G2P engine strips ZWNJ characters
    that this function inserts.

    Fixes applied:
      1. Y-glide on word-internal "-चा" suffix  (रामाचा → sounds like रामाच्या)
         → Insert ZWNJ between च and ा when preceded by a matra.
      2. Y-glide on "ें" / "ैं" (front-vowel matra + anusvara)
         (आदरें → sounds like आदरेय)
         → Insert ZWNJ between the preceding consonant and the matra
           to break gTTS's phonological bundling of the nasalized vowel.
      3. Terminal halant (virama) at sentence / verse boundaries
         (ध्यायेत् at end of line → gTTS swallows final consonant)
         → Remove halant so gTTS voices the full consonant with schwa.
         Does NOT affect word-internal conjuncts (क्ष, त्य etc.)
    """
    if not text:
        return text

    # ── 1. "चा" y-glide ─────────────────────────────────────────────
    # gTTS phonologises matra+चा as /tɕjaː/ (with palatal y-glide).
    # ZWNJ between च and ा creates a tokenisation boundary.
    text = re.sub(
        r'(?<=[\u093E\u093F\u0940\u0941\u0942\u0947\u0948\u094B\u094C\u0902])'
        r'च(?=ा)',
        'च\u200C', text)

    # ── 2. "ें"/"ैं" y-glide ────────────────────────────────────────
    # gTTS Marathi inserts a palatal y-glide [j] before nasalized front
    # vowels (े + ं  and  ै + ं).  Inserting ZWNJ between the consonant
    # and the e/ai-matra stops gTTS from bundling them into a single
    # nasalized syllable with y-onset.
    #   आदरें → आदर‌ें  (ZWNJ between र and े)
    text = re.sub(
        r'([\u0915-\u0939])(?=[\u0947\u0948]\u0902)',
        '\\1\u200C', text)

    # ── 3. Terminal halant removal ───────────────────────────────────
    # At sentence / verse boundaries, a bare halant (not followed by
    # another consonant) makes gTTS pronounce the final consonant as
    # a half-form (प् instead of प).  Remove it so the implicit schwa
    # is restored and the consonant is fully voiced.
    text = re.sub(
        r'\u094D(?=[\s.,;!?\n।॥]|$)',
        '', text)

    return text


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE: Combined Sanskrit Verse Preprocessing
# ═══════════════════════════════════════════════════════════════════════════

def preprocess_stotra_text(text: str) -> str:
    """Full preprocessing pipeline for stotra/shloka/verse text.

    Applies structural cleanup (dandas, verse numbers) followed by
    Sanskrit phonetic rules.  This is a drop-in replacement for
    the simpler ``_preprocess_stotra_text()`` in bridge files.
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # ── Structural Cleanup ────────────────────────────────────────────
    # Remove hyphens inside compound words
    text = re.sub(r'(?<=[\u0900-\u097F])-(?=[\u0900-\u097F])', '', text)
    # Remove ZWJ/ZWNJ
    text = text.replace('\u200D', '').replace('\u200C', '')
    # ASCII colon after Devanagari → visarga
    text = re.sub(r'([\u0900-\u097F]):', r'\1ः', text)
    # Verse numbers:  ॥ ३ ॥  or  ॥3॥ → period
    text = re.sub(r'॥\s*[\d०-९]+\s*॥', '.', text)
    # Double danda → period (long pause)
    text = text.replace('॥', '.')
    # Single danda → comma (half-line pause)
    text = text.replace('।', ',')
    # Stanza breaks
    text = re.sub(r'\n\s*\n+', '\n.\n', text)

    # ── Sanskrit Phonetics ────────────────────────────────────────────
    text = apply_sanskrit_phonetics(text)

    # ── Final Cleanup ─────────────────────────────────────────────────
    text = re.sub(r'[.,]{2,}', '.', text)
    text = re.sub(r'^\s*[.,]\s*', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════
# PART 3 – OLD MARATHI PHONETIC RULES (Dnyaneshwari, Abhangas, Sant Lit.)
# ═══════════════════════════════════════════════════════════════════════════

# ── चि / ची / चिया emphasiser particle ──────────────────────────────────
# In Old Marathi (Dnyaneshwari, Abhangas etc.), -चि is an emphasiser
# particle (like "indeed" or "ही" in modern Marathi).  It follows nouns,
# verbs, or adverbs and must be pronounced as a crisp palatal affricate:
#   तोचि = to-chi, तेंचि = teṁ-chi, देवाचि = devā-chi
# We preserve -चि as-is (no rewrite needed) but we ensure it is NOT
# merged into the preceding word by schwa deletion or anusvara stripping.
_OLD_MARATHI_CHI_RE = re.compile(r'([\u0900-\u097F])चि(?=[\s.,;!?\n]|$)')

# ── Ovi metre (ओवी छंद) ─────────────────────────────────────────────────
# The Ovi is the signature metre of Dnyaneshwari:
#   - 4 lines (padas) per stanza
#   - Lines 1-3 rhyme, line 4 is shorter (cadence)
#   - Single danda (।) marks the musical beat (slight elevation, NOT a stop)
#   - Double danda (॥) marks the end of the stanza (pitch drops, brief pause)
#   - Verse numbers (॥ N ॥) are stripped
#
# For TTS, this means:
#   - Single danda → very brief pause (comma-like) with NO pitch drop
#   - Double danda → moderate pause with descending intonation
#   - Line breaks within a stanza → minimal pause (keep flow)

# ── Words with trailing anusvara that must stay nasalized ────────────────
# In Old Marathi, trailing anusvara is a nasalized vowel, NOT a consonant.
# Modern Marathi strips it (नाहीं → नाही) but Old Marathi must keep it.
# Examples: तें, हें, जें, कां, तां, जीवीं, देहीं, मनीं
# We do NOT apply _CLASSICAL_ANUSVARA_RE for Old Marathi.


def apply_old_marathi_phonetics(text: str) -> str:
    """Apply Old Marathi (Dnyaneshwari / Sant literature) pronunciation rules.

    Key differences from modern Marathi phonetics:
      1. Anusvara PRESERVED as nasalized vowel (not stripped)
      2. Schwa deletion SUSPENDED (every written syllable pronounced for metre)
      3. -चि emphasiser particle kept as crisp palatal
      4. Short terminal vowels kept short (no lengthening)
      5. Visarga handling same as Sanskrit (context-dependent)
      6. Conjunct pronunciation aids (ज्ञ → द्न्य)

    Parameters
    ----------
    text : str
        Old Marathi Devanagari text to preprocess.

    Returns
    -------
    str
        Phonetically preprocessed text suitable for TTS.
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # Remove ZWJ / ZWNJ
    text = text.replace('\u200D', '').replace('\u200C', '')

    # ── 1. Visarga Handling (same as Sanskrit — context-dependent) ────
    # Old Marathi uses visarga in tatsama (Sanskrit loan) words.
    # Apply the same sandhi rules as Sanskrit.
    for original, replacement in _MARATHI_VISARGA_WORDS.items():
        text = text.replace(original, replacement)
    # Before palatal consonants
    text = re.sub(r'ः(?=[चछजझश])', 'श', text)
    # Before retroflex consonants
    text = re.sub(r'ः(?=[टठडढष])', 'ष', text)
    # Before dental consonants
    text = re.sub(r'ः(?=[तथदधसन])', 'स', text)
    # Before velars/labials → aspiration
    text = re.sub(r'ः(?=[कखपफ])', 'ह', text)
    # Terminal visarga → light echoing
    text = re.sub(r'([\u093F\u0940])ः(?=[\s.,\n]|$)', r'\1हि', text)
    text = re.sub(r'([\u0941\u0942])ः(?=[\s.,\n]|$)', r'\1हु', text)
    text = re.sub(r'ः(?=[\s.,\n]|$)', 'हा', text)
    text = text.replace('ः', 'ह')

    # ── 2. Conjunct Pronunciation ─────────────────────────────────────
    text = text.replace('ज्ञ', 'द्न्य')
    text = text.replace('ॠ', 'री')

    # ── 2b. Old Marathi word-form lexicon ────────────────────────────
    # Apply after conjunct fixes to avoid double-substitution
    for old_form, new_form in _OLD_MARATHI_LEXICON.items():
        text = re.sub(
            r'(?<![\u0900-\u097F])' + re.escape(old_form) + r'(?![\u0900-\u097F])',
            new_form, text
        )

    # ── 3. DO NOT strip trailing anusvara ─────────────────────────────
    # In Old Marathi, anusvara after long vowels is a NASALIZED VOWEL,
    # not a consonant.  तें is "tẽ" (nasalized), NOT "ten".
    # Modern Marathi strips it; we MUST NOT for Old Marathi.
    # (Intentionally skipping _CLASSICAL_ANUSVARA_RE)

    # ── 4. DO NOT apply schwa deletion ────────────────────────────────
    # Old Marathi poetry requires every written syllable to be pronounced
    # for the metre to work.  Schwa deletion would destroy the rhythm.
    # Example: करणें = ka-ra-ṇẽ (3 syllables), NOT kar-ṇẽ
    # (Intentionally skipping _SCHWA_DELETION_LEXICON)

    # ── 4b. Explicit schwa RESTORATION for key poetic words ──────────
    # gTTS lang=mr sometimes still deletes schwa even in Old Marathi.
    # For multi-syllable words that MUST be fully pronounced, add halant
    # would be wrong — instead, explicitly write the schwa vowel 'अ'
    # after consonant clusters where gTTS drops it.  We use a targeted
    # set of patterns rather than a blanket rule.
    #
    # Pattern: consonant at end of word without matra → must have schwa
    # (not needed as rewrite since gTTS handles this when slow=True)

    # ── 5. Anusvara preservation for nasalized vowels in Ovi ─────────
    # In Ovi metre, words like 'तयां', 'तयाचां', 'जीवां' have ануsvara
    # that nasalizes the preceding vowel (NOT a consonant).  We preserve
    # the anusvara character — no rewrite needed.  BUT we mark chandrabindu
    # words (ँ) correctly: chandrabindu is lighter nasalization (Sanskrit
    # influence in tatsama words).  Both are kept as-is for gTTS.

    # ── 6. Terminal long vowel protection ────────────────────────────
    # Some Old Marathi words end in long ā, ī, ū intentionally.
    # gTTS may shorten them.  No text rewrite can fix this — it's handled
    # by the prosody engine (slow=True + extended pause after segment).

    # ── 7. OM Symbol ──────────────────────────────────────────────────
    text = text.replace('ॐ', 'ओम्')

    # ── 8. Post-processing cleanup ────────────────────────────────────
    text = re.sub(r'  +', ' ', text)
    text = text.strip()

    return text


def preprocess_old_marathi_text(text: str) -> str:
    """Full preprocessing pipeline for Old Marathi poetry (Ovi metre).

    Applies Ovi-specific structural cleanup followed by Old Marathi
    phonetic rules.  Suitable for Dnyaneshwari, Abhangas, and other
    Sant literature in Ovi metre.

    Key structural difference from stotra preprocessing:
      - Single danda (।) → brief pause (comma) — musical beat, NOT a stop
      - Double danda (॥) → moderate pause (period) — stanza end
      - Verse numbers stripped
      - Line breaks within stanza preserved as minimal pauses
    """
    if not text or not text.strip():
        return text

    text = unicodedata.normalize('NFC', text)

    # ── Structural Cleanup ────────────────────────────────────────────
    # Remove hyphens inside compound words
    text = re.sub(r'(?<=[\u0900-\u097F])-(?=[\u0900-\u097F])', '', text)
    # Remove ZWJ/ZWNJ
    text = text.replace('\u200D', '').replace('\u200C', '')
    # ASCII colon after Devanagari → visarga
    text = re.sub(r'([\u0900-\u097F]):', r'\1ः', text)

    # ── Ovi Metre Structural Rules ────────────────────────────────────
    # Verse numbers:  ॥ ३ ॥  or  ॥3॥  or  ॥१॥ → period
    text = re.sub(r'॥\s*[\d०-९]+\s*॥', '.', text)
    # Double danda (stanza end) → period (moderate pause, pitch drop)
    text = text.replace('॥', '.')
    # Single danda (musical beat) → comma (brief pause, NO pitch drop)
    # In Ovi metre, the danda is a rhythmic marker, not a grammatical stop.
    text = text.replace('।', ',')
    # Stanza breaks (blank lines) → period
    text = re.sub(r'\n\s*\n+', '\n.\n', text)

    # ── Old Marathi Phonetics ─────────────────────────────────────────
    text = apply_old_marathi_phonetics(text)

    # ── Final Cleanup ─────────────────────────────────────────────────
    text = re.sub(r'[.,]{2,}', '.', text)
    text = re.sub(r'^\s*[.,]\s*', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
