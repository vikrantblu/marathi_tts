---
mode: 'agent'
description: 'Pre-deploy checklist and release notes helper for the Android mobile app'
---

Prepare the mobile app for deployment.

**Pre-deploy checklist:**

1. Run `python test_all_platforms.py` — must show `RESULT: ALL PASS` before building.
2. Check `BUGS.txt` for any open bugs that should block this release.
3. Check `FEATURES.txt` for features listed as `[Unreleased]` that are now ready to ship.
4. Review `CHANGELOG.md` — summarise unreleased changes since the last tag.
5. Determine the appropriate bump level:
   - **Major** — breaking changes or new platform
   - **Minor** — new screens, new TTS features, new bridge capabilities
   - **Patch** — bug fixes, phonetic tweaks, dependency bumps
6. Suggest one-line release notes summarising the key changes.
7. Remind the user to run `.\deploy_mobile.ps1` interactively to perform the actual build/sign/install.

**After deployment:**
- Update `BUGS.txt`: move fixed bugs to the Fixed section with the version.
- Update `FEATURES.txt`: move shipped `[Unreleased]` features to Shipped with the version.
- Commit with message: `release: v<VERSION>`
- Tag the commit: `git tag v<VERSION>`

What version are we currently on and what changes are going out in this release?
