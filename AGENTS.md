# AGENTS.md — Marathi TTS

Agent role definitions for automated coding workflows.

---

## tts-engine

**Scope:** All files under `tts/` in any platform.

**Responsibilities:**
- Add or modify phonetic rules (sandhi, schwa, G2P, metre)
- Update prosody engine (pause calibration, pitch contour, emotion modifiers)
- Sync changes across all three platforms (web → desktop → mobile)
- Run `python test_all_platforms.py` and confirm ALL PASS before committing

**Rules:**
- Web is the canonical source — edit there first, then sync.
- Preserve `try/except ImportError` guards in desktop/mobile `tts_engine.py`.
- Use actual Devanagari characters, never `\uXXXX` escapes.
- Add test assertions for new rules in the same commit.

---

## mobile-build

**Scope:** `marathi_tts_mobile/` (Kotlin, Gradle, Android resources).

**Responsibilities:**
- Implement UI features (Fragments, ViewModels, Adapters)
- Wire bridge calls through `PythonBridge` / `TtsEngineManager`
- Build and deploy via `deploy_mobile.ps1`
- Update nav graph, layouts, Room DB migrations

**Rules:**
- Follow 3-tab bottom navigation pattern (Input / Output / Me).
- Text flow between screens: `savedStateHandle` + `popBackStack()`.
- Log to Room via `HistoryLogger` (fire-and-forget, IO dispatcher).
- Use `OutputActions` for copy/share/save operations.

---

## phonetic-qa

**Scope:** Pronunciation accuracy and regression testing.

**Responsibilities:**
- Validate phonetic output for Sanskrit, Old Marathi, Modern Marathi
- Test metre detection (12+ metres in catalogue)
- Verify prosody segmentation (pauses, pitch, rate)
- Review community phonetic corrections (FEAT-59)

**Rules:**
- Run full test suite after any phonetic change.
- Cross-reference G2P exception lexicon for new words.
- Ensure chandrabindu nasalization and ZWNJ fixes are preserved.
