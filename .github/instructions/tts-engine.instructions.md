---
applyTo: '**/tts/**/*.py'
---

# TTS Engine Rules (all platforms)

## Encoding
- All source files: UTF-8, no BOM.
- Always use actual Unicode Devanagari characters in string literals — **never** `\u0930\u093e\u092e` etc.

## Engine file sync
Any change to a file under `tts/` **must** be synced to all three platform locations:
- Web (canonical): `marathi_tts_web/tts/`
- Desktop: `marathi_tts_desktop/python_bridge/tts/`
- Mobile: `marathi_tts_mobile/app/src/main/python/tts/`

`tts_engine.py` on desktop/mobile has `try/except ImportError` guards around Django-only imports — preserve them.

## Phonetic rules
- **Schwa deletion**: never apply inside `apply_old_marathi_phonetics()` — it breaks metre.
- **G2P exception lexicon** entries in `g2p_constants.py` must be Devanagari word → correct-form pairs; no Latin transliteration.
- **ZWNJ** (`\u200c`) is used after G2P to prevent gTTS y-glide on word-internal `-cha` suffixes.
- Language detection order: Sanskrit (stotra markers) → Old Marathi (classical markers) → Modern Marathi (default).

## Prosody
- `ProsodyEngine` receives `speaking_rate=1.0` for natural pause calibration.
- Verse text bypasses prose prosody — it has its own MetreEngine segmentation path.
- Emotion modifiers adjust `tts_rate` and `pitch_shift` on segments, not globally.

## Testing
After any engine change run `python test_all_platforms.py` from the repo root. All 9 sections (A–K + Step 0 syntax) must pass before the task is done.
