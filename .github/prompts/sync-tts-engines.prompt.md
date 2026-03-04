---
mode: 'agent'
description: 'Sync a modified TTS engine file from web (canonical) to desktop and mobile'
---

You are syncing a Python TTS engine file across all three platforms.

**Canonical source:** `marathi_tts_web/tts/`  
**Targets:**
- `marathi_tts_desktop/python_bridge/tts/`
- `marathi_tts_mobile/app/src/main/python/tts/`

Rules to follow:
1. Read the modified file(s) from the web platform first to understand changes.
2. Apply **identical** changes to the same relative path in both desktop and mobile.
3. Preserve the `try/except ImportError` guards in `tts_engine.py` on desktop/mobile — they wrap Django-only imports (`from django.conf import settings`, `VoiceModulator`) and must not be removed.
4. After syncing, run `python test_all_platforms.py` in `d:\marathi_tts` and confirm `RESULT: ALL PASS`.
5. Update `copilot-instructions.md` if any file was renamed or added.

Which file(s) were modified in the web platform? List them and I will sync them now.
