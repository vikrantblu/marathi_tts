---
mode: 'agent'
description: 'Fix a bug and update BUGS.txt'
---

Fix the following bug:

${input:bugDescription:Describe the bug — what happens vs. what should happen, and on which platform(s)}

**Workflow:**
1. Check `BUGS.txt` — is this bug already listed? Note its ID (e.g., BUG-42).
2. If it affects TTS engine code (`tts/` tree), fix in **web** first then sync to desktop and mobile.
3. If it is platform-specific (Kotlin/Java/FXML only), fix it directly on that platform.
4. Add or update a test in `test_all_platforms.py` if the bug is in engine code.
5. Run `python test_all_platforms.py` and confirm `RESULT: ALL PASS` (if engine code changed).
6. Update `BUGS.txt`:
   - If the bug was in the Open section → move it to Fixed with the current date and a one-line fix description.
   - If it was not listed → add a new entry in Fixed directly.
7. Add a line under `## [Unreleased]` in `CHANGELOG.md` describing the fix.

Start by reading `BUGS.txt` to check if this is a known issue.
