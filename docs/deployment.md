# Deployment Guide

## Mobile App (Android)

### Interactive deploy

```powershell
.\deploy_mobile.ps1
```

The script:
1. Lists connected ADB devices
2. Shows version menu (Major/Minor/Patch/Build-only/Skip)
3. Bumps version in `build.gradle.kts` (if selected)
4. Builds APK (debug or release)
5. Installs on connected device
6. Copies APK + docs to `C:\My_Drive_Backup\builds\marathi_tts\`

### Options

```powershell
.\deploy_mobile.ps1 -NoDeploy          # Build only, no install
.\deploy_mobile.ps1 -DeviceSerial XXX  # Target specific device
```

### Release checklist

1. `python test_all_platforms.py` → ALL PASS
2. Update `## [Unreleased]` in `CHANGELOG.md`
3. Run `.\deploy_mobile.ps1`, choose bump level
4. Enter one-line release notes
5. Verify APK at `C:\My_Drive_Backup\builds\marathi_tts\`
6. Commit: `release: v<VERSION>`
7. Tag: `git tag v<VERSION>`
8. Push: `git push && git push --tags`

## Web App (Django)

### Local development

```powershell
cd marathi_tts_web
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

### Docker deployment

```bash
docker compose up -d
```

Uses `Dockerfile` + `docker-compose.yml` at project root.

## Desktop App (JavaFX)

```powershell
cd marathi_tts_desktop
.\gradlew run
```

Or use the VS Code task: "Start Desktop App (Gradle)"

## Version Management

Version source of truth: `version.json` (root)

```json
{
  "version": "4.0.0",
  "buildNumber": 17,
  "date": "2026-03-07"
}
```

Also mirrored in `marathi_tts_mobile/app/build.gradle.kts`:
- `versionName` ↔ `version.json → version`
- `versionCode` ↔ `version.json → buildNumber`

Use the `bump_version` MCP tool or `version-bump` prompt to keep them in sync.
