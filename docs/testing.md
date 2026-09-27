# Testing Guide

## Cross-Platform Test Suite

### Running tests

```powershell
cd marathi_tts
python test_all_platforms.py
```

Expected output: `RESULT: ALL PASS — safe to finish.`

### Test sections

| Section | Module | Checks |
|---------|--------|--------|
| Step 0 | Syntax | All engine files across 3 platforms parse cleanly |
| A | SandhiEngine | Vedic accent, avagraha, anusvara, visarga rules |
| B | Sanskrit phonetics | Language detection, OM symbol, shloka processing |
| C | MetreEngine | Metre detection, rate, pauses, syllable counting |
| D | ProsodyEngine | Verse/prose detection, pitch contour, emotion modifiers |
| E | Old Marathi | Phonetic preservation, retroflex, schwa guard |
| F | Modern Marathi | ज्ञ→द्न्य, visarga, retroflex ळ, ॠ→री |
| G | G2P lexicon | Key words present in exception dictionary |
| I | TextNormalizer | Output, verse strip, abbreviation expansion |
| J | GrammarEngine | Processing, deduplication, empty input |
| K | number_to_words | Cardinal, time, ordinal, percentage conversion |

### Adding new tests

Add assertions to the appropriate section in `test_all_platforms.py`:

```python
# In the section loop for each platform:
result = some_function("input")
ok = expected_condition(result)
tag = "✓" if ok else "✗"
print(f"  {tag} Description of check")
if not ok:
    all_ok = False
```

### CI Integration

Tests run automatically via GitHub Actions:
- **test.yml**: Runs `test_all_platforms.py` on push/PR to main
- **validate.yml**: Runs syntax check, compile check, version consistency, TTS sync check

### Mobile-specific tests (on device)

Run via `run_mobile_tests.ps1`:
- T13: OCR (ML Kit Devanagari)
- T14: PDF extraction
- T23: Emotion detection
- T24: Streaming TTS
- T25: OCR → TTS pipeline
- T26: PDF OCR

## Troubleshooting

### TextNormalizer tests skip
Sections I/J/K skip when `indicnlp` is not installed — this is expected in CI.

### Syntax errors after sync
Run `python -c "import ast; ast.parse(open('file.py').read())"` to check specific files.

### Platform drift
Use `check_tts_sync` MCP tool or the validate workflow to detect drifted files.
