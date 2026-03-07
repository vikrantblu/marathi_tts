# Marathi TTS — Claude Skill

## Domain

Marathi Text-to-Speech engine spanning three platforms (Web/Django, Desktop/JavaFX,
Mobile/Android) with a shared Python TTS engine package.

## Key Workflows

### 1. Three-Platform Sync

Any change under any platform's `tts/` directory must be mirrored to all three:
- **Web (canonical):** `marathi_tts_web/tts/`
- **Desktop:** `marathi_tts_desktop/python_bridge/tts/`
- **Mobile:** `marathi_tts_mobile/app/src/main/python/tts/`

Desktop/mobile `tts_engine.py` has `try/except ImportError` guards around Django-only
imports — preserve those when syncing.

### 2. Phonetic Pipeline

```
Input → Language detect (Sanskrit / Old Marathi / Modern Marathi)
      → SandhiEngine (Sanskrit) or GrammarEngine (Modern Marathi)
      → TextNormalizer → G2P → apply_*_phonetics → ProsodyEngine
```

Rules:
- Never apply schwa deletion in Old Marathi phonetics (breaks metre).
- G2P lexicon entries: Devanagari → Devanagari only, no Latin.
- ZWNJ after G2P prevents gTTS y-glide on `-cha` suffixes.
- Devanagari string literals must use actual Unicode — never escape sequences.

### 3. Bridge Fallback Chains

**Verse:** edge-verse-prosody → edge-tts single → gTTS verse → bare gTTS  
**Prose:** edge-prosody → edge-tts single → prosody-gTTS → single gTTS → bare gTTS  

Each stage returns `None` on failure → transparent fallthrough.

### 4. Testing Protocol

After any `tts/` change:
```
python test_all_platforms.py
```
Must show `RESULT: ALL PASS` (Sections A–K + syntax check across 18 files).

### 5. Deployment

```powershell
.\deploy_mobile.ps1          # Interactive: version bump + APK build + install
```
Backs up APK + docs to `C:\My_Drive_Backup\builds\marathi_tts\`.

## Common Patterns

- Bridge functions return `{"success": True/False, "error": str, ...}`.
- Wrap bridge logic in `try/except Exception` — never let exceptions propagate to Java/Kotlin.
- Grammar engine (`_apply_grammar()`) is a lazy singleton; safe to double-apply (idempotent).
- ProsodyEngine receives `speaking_rate=1.0` for natural pause calibration.
- Verse text bypasses prose prosody — uses MetreEngine segmentation path instead.
