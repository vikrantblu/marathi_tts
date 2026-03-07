---
mode: 'agent'
description: 'Debug a TTS pronunciation or audio quality issue'
---

Debug a TTS engine issue where audio output is incorrect.

**Problem:** ${input:problem:Describe the issue (e.g., "word X is mispronounced", "pause too long after verse")}

**Diagnostic workflow:**
1. Identify the text and language mode (Modern Marathi / Sanskrit / Old Marathi).
2. Trace the text through the pipeline:
   a. **TextNormalizer** — was the input normalized correctly?
   b. **GrammarEngine** — did grammar correction alter anything unexpected?
   c. **G2P Engine** — check exception lexicon for the word, check schwa rules.
   d. **MarathiPhonetics / SandhiEngine** — trace phonetic transformations.
   e. **ProsodyEngine** — check segment boundaries, pause durations, pitch contour.
   f. **MetreEngine** — if verse, is the metre detected correctly?
3. Use `explain_phonetics(word, language)` bridge function to get a stage-by-stage trace.
4. Identify the root cause and the module that needs fixing.
5. Fix in the **web** platform first, then sync to desktop and mobile.
6. Add a regression test in `test_all_platforms.py`.
7. Run tests → ALL PASS.

**Common causes:**
- Missing G2P exception lexicon entry → add to `g2p_constants.py`
- Schwa deletion on a word that should be exempt → add to `SCHWA_EXCEPTIONS`
- Wrong metre detected → check syllable count / gaṇa pattern in `metre_engine.py`
- ZWNJ missing on `-cha` suffix → check `marathi_phonetics.py`
