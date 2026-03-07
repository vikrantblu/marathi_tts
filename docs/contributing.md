# Contributing Guide

## Setup

1. Clone the repo: `git clone https://github.com/vikrantblu/marathi_tts.git`
2. Create Python venv: `python -m venv .venv`
3. Activate: `.\.venv\Scripts\Activate.ps1`
4. Install deps: `pip install -r requirements.txt`
5. Run tests: `python test_all_platforms.py`

## Workflow

1. Create a branch: `git checkout -b feat/your-feature`
2. Make changes following the rules below
3. Run `python test_all_platforms.py` → ALL PASS
4. Commit with conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
5. Push and open a PR

## Rules

### TTS Engine Changes
- Edit in `marathi_tts_web/tts/` first (canonical source)
- Sync to desktop + mobile via `sync_tts_file` MCP tool or manual copy
- Preserve `try/except ImportError` guards in desktop/mobile `tts_engine.py`
- Add test assertions in `test_all_platforms.py`

### Devanagari Text
- Always use actual Unicode: `'राम'` not `'\u0930\u093e\u092e'`
- G2P lexicon entries: Devanagari word → Devanagari form

### Bridge Scripts
- Every function returns `dict` with `success` key
- Wrap main logic in `try/except Exception`
- Follow the fallback chain order (don't reorder)

### Documentation
- Update `copilot-instructions.md` for structural changes
- Update `BUGS.txt` / `FEATURES.txt` as appropriate
- Add `CHANGELOG.md` entry under `[Unreleased]`

## Code Style

- Python: UTF-8, no BOM, PEP 8
- Kotlin: ktlint-compatible, camelCase
- XML: 4-space indent
- Max line: 100 characters

## Pre-commit Checks

Before committing, verify:
```powershell
# 1. Syntax check
python -c "import ast, pathlib; [ast.parse(f.read_text('utf-8')) for d in ['marathi_tts_web/tts','marathi_tts_desktop/python_bridge/tts','marathi_tts_mobile/app/src/main/python/tts'] for f in pathlib.Path(d).rglob('*.py')]"

# 2. TTS sync check
python -c "import pathlib,hashlib; web=pathlib.Path('marathi_tts_web/tts'); [(print(f'DRIFT: {f.relative_to(web)}') if hashlib.md5(f.read_bytes()).hexdigest()!=hashlib.md5((pathlib.Path('marathi_tts_desktop/python_bridge/tts')/f.relative_to(web)).read_bytes()).hexdigest() else None) for f in web.rglob('*.py') if (pathlib.Path('marathi_tts_desktop/python_bridge/tts')/f.relative_to(web)).exists()]"

# 3. Full test suite
python test_all_platforms.py
```
