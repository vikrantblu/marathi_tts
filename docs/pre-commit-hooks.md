# Pre-commit Hooks

## Overview

Pre-commit checks run automatically before each `git commit` to catch common
issues. The project does not use the `pre-commit` Python framework — instead,
checks are implemented as a Git hook script.

## Setup

Copy the hook to your local Git hooks directory:

```powershell
Copy-Item docs\pre-commit-hook.sh .git\hooks\pre-commit
```

Or manually create `.git/hooks/pre-commit` with the content below.

## Hook Script

```bash
#!/bin/sh
# Marathi TTS — pre-commit hook
set -e

echo "=== Pre-commit: TTS syntax check ==="
python -c "
import ast, pathlib, sys
errors = []
for d in ['marathi_tts_web/tts', 'marathi_tts_desktop/python_bridge/tts',
           'marathi_tts_mobile/app/src/main/python/tts']:
    for f in pathlib.Path(d).rglob('*.py'):
        try:
            ast.parse(f.read_text('utf-8'))
        except SyntaxError as e:
            errors.append(f'{f}: {e}')
if errors:
    print('Syntax errors found:')
    for e in errors: print(f'  {e}')
    sys.exit(1)
print('Syntax OK')
"

echo "=== Pre-commit: TTS sync check ==="
python -c "
import pathlib, hashlib, sys
web = pathlib.Path('marathi_tts_web/tts')
drifted = []
for f in web.rglob('*.py'):
    rel = f.relative_to(web)
    wh = hashlib.md5(f.read_bytes()).hexdigest()
    for name, base in [('desktop', pathlib.Path('marathi_tts_desktop/python_bridge/tts')),
                        ('mobile', pathlib.Path('marathi_tts_mobile/app/src/main/python/tts'))]:
        other = base / rel
        if other.exists() and hashlib.md5(other.read_bytes()).hexdigest() != wh:
            drifted.append(f'{name}/{rel}')
if drifted:
    print('TTS files out of sync:')
    for d in drifted: print(f'  {d}')
    print('Run sync before committing.')
    sys.exit(1)
print('Sync OK')
"

echo "=== Pre-commit: version.json consistency ==="
python -c "
import json, re, sys
try:
    vj = json.load(open('version.json'))
    gradle = open('marathi_tts_mobile/app/build.gradle.kts').read()
    gv = re.search(r'versionName\s*=\s*\"([^\"]+)\"', gradle)
    if gv and gv.group(1) != vj['version']:
        print(f'Version mismatch: version.json={vj[\"version\"]} gradle={gv.group(1)}')
        sys.exit(1)
    print('Version OK')
except FileNotFoundError:
    print('version.json not found, skipping')
"

echo "All pre-commit checks passed ✓"
```

## Checks performed

| Check | What it catches |
|-------|----------------|
| TTS syntax | Python syntax errors in any engine file |
| TTS sync | Files drifted between web/desktop/mobile |
| Version consistency | version.json ↔ build.gradle.kts mismatch |

## Bypassing (emergency only)

```bash
git commit --no-verify -m "hotfix: ..."
```

Only use `--no-verify` for emergencies — document why in the commit message.
