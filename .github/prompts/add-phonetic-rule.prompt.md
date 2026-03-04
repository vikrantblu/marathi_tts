---
mode: 'agent'
description: 'Add a new Marathi/Sanskrit phonetic rule to the TTS engine'
---

I need to add a new phonetic rule to the Marathi TTS engine. Here is what needs to change:

${input:ruleDescription:Describe the phonetic transformation (e.g., "ळ before ी should nasalise")}

**Workflow:**
1. Identify which module owns this rule:
   - General Marathi phonetics → `tts/utils/phonetic/marathi_phonetics.py`
   - Sanskrit sandhi/accent → `tts/utils/phonetic/sandhi_engine.py`
   - G2P exception lexicon → `tts/constants/g2p_constants.py`
   - Schwa deletion exception → `SCHWA_EXCEPTIONS` in `g2p_constants.py`
   - Old Marathi / Sant literature → `apply_old_marathi_phonetics()` in `marathi_phonetics.py`
2. Implement the rule in the **web** platform first.
3. Sync to desktop and mobile (see copilot-instructions.md sync script).
4. Add a test assertion in `test_all_platforms.py` in the appropriate section (A–H) so regressions are caught.
5. Run `python test_all_platforms.py` and confirm `RESULT: ALL PASS`.
6. Update `FEATURES.txt` if this is a user-visible improvement.

**Critical:** Never apply schwa deletion inside `apply_old_marathi_phonetics()` — it breaks metre.  
**Critical:** G2P exception lexicon entries must use actual Devanagari Unicode, not Latin transliteration.
