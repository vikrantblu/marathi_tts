---
mode: 'agent'
description: 'Bump the project version in version.json and build.gradle.kts'
---

Bump the project version for a new release.

**Inputs:**
- Bump level: ${input:bumpLevel:major, minor, or patch}
- Release notes: ${input:releaseNotes:One-line summary of key changes}

**Steps:**
1. Read current version from `version.json`.
2. Compute new version based on bump level (major/minor/patch).
3. Update `version.json`: bump `version`, increment `buildNumber`, set `date`.
4. Update `marathi_tts_mobile/app/build.gradle.kts`: set `versionName` and increment `versionCode`.
5. Add entry to `CHANGELOG.md` under `## [Unreleased]` or create a new version section.
6. Run `python test_all_platforms.py` to confirm nothing is broken.
7. Stage and commit with message: `release: v<NEW_VERSION>`.

**Do NOT push or tag** — the user will do that after review.
