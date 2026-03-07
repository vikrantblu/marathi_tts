# Copilot Instructions for Marathi TTS Project

## Constants-First Rule

Before creating any new constant, configuration value, or hardcoded string, **always check the existing constants files first**:

### Python Constants
All Python constants are centralized in `tts/constants/`:

| Module | Contents |
|--------|----------|
| `text_constants.py` | Abbreviations, special chars, pronunciation fixes, visarga/conjunct maps |
| `grammar_constants.py` | Spelling corrections, sandhi splits, vibhakti/agreement fixes, honorifics |
| `number_constants.py` | Marathi number words (ones, teens, tens), ordinals, months, currency |
| `audio_constants.py` | PauseType enum, conjunctions, clause starters, punctuation pause mappings |
| `emotion_constants.py` | Emotion keywords, voice params, SSML tags, patterns, translations, colors |
| `script_constants.py` | Modi/Devanagari Unicode ranges, script conversion maps, phonetic/matra maps |
| `tts_config.py` | Supported languages, TTS defaults, morph suffixes, pronunciation rules |
| `g2p_constants.py` | G2P engine data: valid conjuncts, anusvara assimilation, visarga sandhi, schwa rules, exception lexicon, loanword phonemes |

### JavaScript Constants
All JS constants are centralized in `static/tts/js/constants/`:

| Module | Contents |
|--------|----------|
| `api-endpoints.js` | All API URLs (generate audio, correct text, analyze emotion, extract text) |
| `text-constants.js` | Abbreviation maps, text replacements, emphasis/pause patterns, pause durations |
| `emotion-constants.js` | Emotion translations (Marathi), emotion display colors |

### What to Do
1. **Search constants files** before adding a new constant anywhere
2. **Add to the appropriate constants module** if the value doesn't exist yet
3. **Import from constants** in your source file — never duplicate values inline
4. **Update this document** if you create a new constants module

### What NOT to Do
- Do NOT define abbreviation maps, special character maps, or emotion data inline in source files
- Do NOT hardcode API endpoint URLs — use `api-endpoints.js`
- Do NOT duplicate constants that already exist in the centralized modules
