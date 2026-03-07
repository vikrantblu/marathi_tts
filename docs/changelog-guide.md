# Changelog & Versioning Guide

## Version Scheme

Semantic Versioning: `MAJOR.MINOR.PATCH` with optional hotfix suffix.

| Component | When to bump |
|-----------|-------------|
| **MAJOR** | Breaking changes, large rewrites, major platform features |
| **MINOR** | New screens, TTS features, bridge capabilities |
| **PATCH** | Bug fixes, phonetic rule tweaks, dependency bumps |
| **Hotfix** | Emergency fix: `1.3.2-hotfix.1` |

## Sources of Truth

| File | What it stores |
|------|---------------|
| `version.json` | Canonical version, build number, date, feature flags |
| `marathi_tts_mobile/app/build.gradle.kts` | Android `versionCode` + `versionName` |

Both must stay in sync — use the `bump_version` MCP tool or `version-bump`
agent prompt.

## CHANGELOG.md Format

```markdown
## [Unreleased]
- feat: FEAT-XX short description
- fix: BUG-YY short description

## [4.0.0] — 2026-03-07
- feat: 3-tab bottom navigation (Input / Output / Me)
- feat: FEAT-80 per-verse metre detection
```

### Rules

1. **During development:** add entries under `## [Unreleased]`
2. **At release:** `deploy_mobile.ps1` auto-moves unreleased into a versioned section
3. **Prefix:** `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
4. **Reference:** Include `FEAT-XX` or `BUG-YY` IDs when applicable

## Release Checklist

1. All tests pass: `python test_all_platforms.py` → `RESULT: ALL PASS`
2. Stage entries under `## [Unreleased]` in `CHANGELOG.md`
3. Run `.\deploy_mobile.ps1`
4. Choose bump level at the interactive menu
5. Enter one-line release note
6. Confirm APK backup at `C:\My_Drive_Backup\builds\marathi_tts\`
7. Commit: `release: v<VERSION>`
8. Tag: `git tag v<VERSION>` and push

## Related Files

- `BUGS.txt` — open/fixed bugs with version references
- `FEATURES.txt` — planned/shipped features with FEAT-XX IDs
- `marathi_tts_web/tts_features.md` — detailed TTS capability docs
