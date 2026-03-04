---
mode: 'agent'
description: 'Add a new stotra to all three platforms'
---

Add a new stotra to the Marathi TTS stotra library across all three platforms.

**Stotra details:**
- Name: ${input:stotraName:Stotra name in English (e.g., "Ganesh Aarti")}
- Filename: ${input:filename:Filename without extension (e.g., "ganesh_aarti")}
- Source text file: (user will provide or I will create it)

**Steps:**
1. Create/verify the `.txt` file with Devanagari text (UTF-8, no BOM).
2. Copy the `.txt` file to all three stotra asset locations:
   - `marathi_tts_desktop/stotras/`
   - `marathi_tts_mobile/app/src/main/assets/stotras/`
   - `marathi_tts_web/data/stotras/`
3. Add an entry to `stotra_catalog.json` in all three locations:
   ```json
   {
     "id": "<filename>",
     "name": "<Marathi name>",
     "nameEn": "<English name>",
     "deity": "<deity>",
     "filename": "<filename>.txt"
   }
   ```
4. Verify the StotraRepository / StotraController picks it up (no code changes needed — catalog is loaded at runtime).
5. Run `python test_all_platforms.py` to confirm no regressions.
6. Update `FEATURES.txt` with the new stotra addition.

Provide the stotra text or the file path and I will handle the rest.
