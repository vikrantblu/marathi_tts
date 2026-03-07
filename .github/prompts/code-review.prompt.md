---
mode: 'agent'
description: 'Review code changes for quality, security, and project conventions'
---

Review the current uncommitted changes or a specific file for code quality.

**Target:** ${input:target:File path or "all" for all uncommitted changes}

**Review checklist:**

### Project conventions
- [ ] Devanagari text uses actual Unicode characters, not `\uXXXX` escapes
- [ ] TTS engine files are identical across web/desktop/mobile
- [ ] Desktop/mobile `tts_engine.py` preserves `try/except ImportError` guards
- [ ] Bridge functions return `dict` with `success` key
- [ ] No schwa deletion inside `apply_old_marathi_phonetics()`

### Security (OWASP Top 10)
- [ ] No SQL injection (Django ORM parameterized, Room type-safe)
- [ ] No command injection (subprocess with list args, no shell=True)
- [ ] No path traversal (inputs validated before file operations)
- [ ] No hardcoded secrets or credentials

### Code quality
- [ ] Error handling: exceptions caught at boundaries, not swallowed silently
- [ ] No unused imports or dead code
- [ ] Consistent naming conventions (snake_case Python, camelCase Kotlin)
- [ ] Comments only where logic is non-obvious

### Testing
- [ ] New features have corresponding test assertions
- [ ] `test_all_platforms.py` still passes after changes

Report findings with severity levels and suggest fixes.
