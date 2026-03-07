# Phonetic Engine Specification

## Language Detection

The engine auto-detects language from text markers:

| Language | Markers | Module |
|----------|---------|--------|
| Sanskrit | `॥`, `ॐ`, `नमः`, stotra patterns | `is_predominantly_sanskrit()` |
| Old Marathi | Sant literature markers, classical forms | `apply_old_marathi_phonetics()` |
| Modern Marathi | Default fallback | `apply_marathi_phonetics()` |

## Phonetic Transformations

### Modern Marathi
- `ज्ञ` → `द्न्य` (Marathi pronunciation)
- Visarga gemination: `दुःख` → nasal-stop replacement
- Visarga + sibilant: `निःशब्द` → resolved
- Retroflex `ळ` preserved
- `ॠ` → `री` (vocalic R conversion)
- ZWNJ insertion after G2P for word-internal `-cha` suffix (prevents gTTS y-glide)

### Sanskrit (via SandhiEngine)
- Vedic accent stripping (U+0951 udātta)
- Avagraha `ऽ` expansion
- Anusvara assimilation (`संशय` → `सन्शय` before palatal)
- Visarga + voiced → `र्` sandhi
- Visarga + voiceless → no change
- `ॐ` → `ओम्`

### Old Marathi
- No schwa deletion (preserves metre)
- Retroflex clusters retained (`विठ्ठल`)
- `ज्ञ` → `द्न्य` (same as modern Marathi)

## Metre Detection

18 metres in catalogue with gaṇa pattern matching:

| Metre | Syllables/pāda | Yati positions |
|-------|----------------|----------------|
| Anushtubh/Shloka | 8 | [4] |
| Trishtubh | 11 | [5] |
| Jagati | 12 | [4, 8] |
| Shardula-vikridita | 19 | [12] |
| Vasanta-tilaka | 14 | [8] |
| Mandakranta | 17 | [4, 10] |
| Malini | 15 | [8] |
| Sragdharā | 21 | [7, 14] |
| Indravajra | 11 | [6] |
| Upendravajra | 11 | [6] |
| Rathoddhatā | 11 | [5] |
| Upajati | 11 | [6] |
| Vamshastha | 12 | [6] |
| Abhanga | 6–8 (Marathi) | — |
| Ovi | variable | — |
| Arya | variable | — |
| Stotra | 8 (default) | — |
| Prose | — | — |

## G2P Exception Lexicon

`g2p_constants.py` contains:
- **SCHWA_EXCEPTIONS**: 220+ words bypassing schwa deletion
- **Sanskrit deity names**: गणेश, विष्णु, etc.
- **Sant literature forms**: ज्ञानदेव, विठोबा, etc.
- **Common words**: नमस्कार, स्तोत्र, मुळे, etc.

## Prosody Engine

Segments text and assigns per-segment:
- `tts_rate`: speaking rate (verse < 1.0, prose ≈ 0.92)
- `pitch_shift`: pitch contour (wave/falling/rising patterns for verse)
- `pause_after_ms`: silence between segments
- `emphasis`: 1.0 default; 1.1 for Abhanga refrains
- `is_verse`: boolean flag
- `metre_name`: detected metre

Emotion modifiers adjust tts_rate and pitch_shift:
- Devotional → slower rate
- Happy → higher pitch
- Sad → lower rate, lower pitch
