## Summary

<!-- One-line description of the change -->

## Type

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation / config only
- [ ] Refactor / code quality

## Platforms affected

- [ ] Web (`marathi_tts_web/`)
- [ ] Desktop (`marathi_tts_desktop/`)
- [ ] Mobile (`marathi_tts_mobile/`)
- [ ] Shared TTS engine (`tts/` tree)
- [ ] CI / build / config only

## Checklist

- [ ] `python test_all_platforms.py` → **ALL PASS**
- [ ] TTS engine files synced to all 3 platforms (if `tts/` changed)
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] `BUGS.txt` updated (if fixing a known bug)
- [ ] `FEATURES.txt` updated (if shipping a planned feature)
- [ ] `copilot-instructions.md` updated (if adding/renaming files, classes, or screens)
- [ ] No `\uXXXX` escapes — all Devanagari uses actual Unicode characters
- [ ] No new lint/compile warnings introduced

## Test results

```
paste test_all_platforms.py output here
```

## Related issues

<!-- e.g., Fixes #42, Implements FEAT-80 -->
