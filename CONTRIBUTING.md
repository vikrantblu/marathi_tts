# Contributing to Marathi TTS

Thank you for your interest in contributing to the Marathi Text-to-Speech (TTS) platform!

## Code of Conduct

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions within this project.

## Development Workflow

Marathi TTS spans three platforms:
- **Web (`marathi_tts_web/`)**: Django 5.x backend & REST APIs.
- **Desktop (`marathi_tts_desktop/`)**: JavaFX + Kotlin with Python bridge subprocess.
- **Mobile (`marathi_tts_mobile/`)**: Android (API 26+) Kotlin application running Python via Chaquopy.

### Canonical Engine Source & Sync Rule

1. `marathi_tts_web/tts/` is the **canonical source** for all shared phonetic and TTS engine code.
2. If you modify any file under `tts/`:
   - Edit in `marathi_tts_web/tts/` first.
   - Sync the changes to `marathi_tts_desktop/python_bridge/tts/` and `marathi_tts_mobile/app/src/main/python/tts/`.
   - Preserve `try/except ImportError` guards in desktop and mobile `tts_engine.py`.
3. **Devanagari Unicode:** Always use native Devanagari characters in Python strings (e.g., `शब्द`, `ॐ`), never unicode escape sequences like `\uXXXX`.

### Running Tests Locally

Before submitting a Pull Request, verify that all test suites pass:

```powershell
python test_all_platforms.py
```

All 3 platforms must show `PASS` with the final status:
```
RESULT: ALL PASS — safe to finish.
```

## Pull Request Guidelines

1. **Fork & Branch:** Create a feature or bugfix branch from `main`.
2. **Commit Messages:** Follow conventional commits:
   - `feat:` new features
   - `fix:` bug fixes or pronunciation adjustments
   - `docs:` documentation improvements
   - `test:` test suite expansions
3. **Continuous Integration:** CI status checks will automatically run:
   - Python Syntax Check across all 3 platforms and bridge scripts
   - Shared TTS Engine Sync Check
   - Version Consistency Check
   - Pronunciation & Metre Rule Test Suite
4. **Branch Protection:** Pull requests require passing status checks and resolved review conversations before merging.
