---
applyTo: '**/tts_bridge.py, **/emotion_bridge.py, **/stt_bridge.py, **/ocr_bridge.py, **/pdf_bridge.py, **/web_bridge.py, **/correction_bridge.py, **/script_converter_bridge.py'
---

# Bridge Script Rules (Mobile + Desktop)

## Return value contract
Every bridge function must return a `dict` with at minimum:
- `"success": True/False`
- `"error": str` (present when `success=False`)
- All documented output keys (e.g., `tts_bridge` → `"audio_path"`, `emotion_bridge` → `"emotion"`, `"score"`, `"scores"`)

## Error handling
Always wrap the main logic in `try/except Exception as e` and return `{"success": False, "error": str(e)}` — never let exceptions propagate to the Java/Kotlin caller.

## Thread safety
Bridge scripts are called from a single worker thread (mobile: Chaquopy's Python thread; desktop: subprocess). Do not use Python threading inside bridge scripts.

## Fallback chains
`tts_bridge.py` has a strict fallback order — do not reorder it:

**Verse path:**
1. `_generate_edge_verse_prosody()` → prosody-segmented edge-tts for verse
2. `_generate_edge_tts()` → single-call edge-tts
3. gTTS verse mode (slow=True) + pydub effects
4. Bare gTTS fallback

**Prose path:**
1. `_generate_edge_prosody()` → prosody-segmented edge-tts
2. `_generate_edge_tts()` → single-call edge-tts
3. `_generate_prosody_audio()` → prosody-segmented gTTS
4. Stage 1 / Stage 3b → single-call gTTS + pydub
5. Stage 2 / Stage 4 → bare gTTS fallback

Each stage returns `None` on failure to trigger the next stage transparently.

## Grammar engine
`_apply_grammar()` is a lazy singleton — applied to prose Marathi text (not verse, not Sanskrit/English) before any TTS engine call. It is safe to double-apply (idempotent).
