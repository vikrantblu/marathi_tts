# Marathi TTS Mobile - Build & Deploy Script (PowerShell)
# Usage: .\deploy_mobile.ps1 [-NoDeploy] [-DeviceSerial <serial>]
#
#   -NoDeploy          Build only; do not push to a connected device/emulator.
#   -DeviceSerial <s>  Target a specific ADB device serial (use: adb devices).
#
# The script always asks interactively how to version and build.
# Signing credentials are read from marathi_tts_mobile/keystore.properties (excluded from git).
# Release APKs and doc snapshots are backed up to C:\My_Drive_Backup\builds\marathi_tts\.

param(
    [switch]$NoDeploy,
    [string]$DeviceSerial = ""
)

$ErrorActionPreference = "Stop"
$Root      = Join-Path $PSScriptRoot "marathi_tts_mobile"
$GradleW   = Join-Path $Root "gradlew.bat"
$BackupDir = "C:\My_Drive_Backup\builds\marathi_tts"
$sep       = "-" * 44

Write-Host ""
Write-Host "=== Marathi TTS Mobile ===" -ForegroundColor Cyan
Write-Host ""

# ── Git pull ─────────────────────────────────────────────────────────────────
Write-Host "Pulling latest changes from git..." -ForegroundColor DarkGray
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    Push-Location $PSScriptRoot
    & git pull 2>&1 | ForEach-Object { "  $_" } | Write-Host -ForegroundColor DarkGray
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: git pull failed (exit $LASTEXITCODE). Continuing with local files." -ForegroundColor DarkYellow
    }
    Pop-Location
} else {
    Write-Host "  git not found -- skipping pull." -ForegroundColor DarkYellow
}
Write-Host ""

# ── Locate ADB early so we can show connected devices in the menu ─────────────
$ADB     = $null
$adbCmd  = Get-Command adb -ErrorAction SilentlyContinue
$adbCandidates = @(
    $(if ($adbCmd) { $adbCmd.Source }),
    "$env:ANDROID_HOME\platform-tools\adb.exe",
    "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe",
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
    "C:\Android\Sdk\platform-tools\adb.exe"
)
foreach ($c in $adbCandidates) {
    if ($c -and (Test-Path $c)) { $ADB = $c; break }
}
if ($ADB) {
    $SdkDir = Split-Path (Split-Path $ADB)
    if (-not $env:ANDROID_HOME) { $env:ANDROID_HOME = $SdkDir }
}

Write-Host "Checking for connected devices..." -ForegroundColor DarkGray
if ($ADB) {
    $deviceLines = & { $ErrorActionPreference = 'Continue'; & $ADB devices 2>&1 } |
                   ForEach-Object { "$_" } |
                   Select-String "device$" |
                   ForEach-Object { ($_ -split "\s+")[0] }
    if ($deviceLines) {
        Write-Host "Connected devices:" -ForegroundColor Gray
        $deviceLines | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    } else {
        Write-Host "  No devices connected." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  ADB not found -- device check skipped." -ForegroundColor DarkYellow
}
Write-Host ""

# ── 0. Read current version from build.gradle.kts ────────────────────────────
$gradleFile    = Join-Path $Root "app\build.gradle.kts"
$gradleContent = Get-Content $gradleFile -Raw

if ($gradleContent -match 'versionName\s*=\s*"([^"]+)"') {
    $currentVersion = $Matches[1]
} else {
    Write-Host "ERROR: Cannot parse versionName from build.gradle.kts" -ForegroundColor Red
    exit 1
}
if ($gradleContent -match 'versionCode\s*=\s*(\d+)') {
    $currentCode = [int]$Matches[1]
} else {
    $currentCode = 1
}

# Parse base version parts
$hotfixNum = 0
$basePart  = $currentVersion
if ($currentVersion -match '^(\d+\.\d+\.\d+)-hotfix\.(\d+)$') {
    $basePart  = $Matches[1]
    $hotfixNum = [int]$Matches[2]
}
$vParts = $basePart -split '\.'
$major  = [int]$vParts[0]
$minor  = [int]$vParts[1]
$patch  = [int]$vParts[2]

# Pre-compute option versions for menu display
$vMajor = "$($major+1).0.0"
$vMinor = "$major.$($minor+1).0"
$vPatch = "$major.$minor.$($patch+1)"
$vBuild = $currentVersion
if ($hotfixNum -gt 0) {
    $vHotfix = "$major.$minor.$patch-hotfix.$($hotfixNum+1)"
} else {
    $vHotfix = "$major.$minor.$patch-hotfix.1"
}

# ── Version menu ──────────────────────────────────────────────────────────────
Write-Host $sep
Write-Host "  Current version: v$currentVersion (build $currentCode)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Version this build?" -ForegroundColor White
Write-Host "    [1] Major release  (v$vMajor) -- breaking changes, new major feature" -ForegroundColor Cyan
Write-Host "    [2] Minor release  (v$vMinor) -- new features, backward compatible"   -ForegroundColor Cyan
Write-Host "    [3] Hotfix/patch   (v$vPatch) -- bug fixes"                            -ForegroundColor Cyan
Write-Host "    [4] Build only     (v$vBuild build $($currentCode+1)) -- no version bump, just increment build" -ForegroundColor Cyan
Write-Host "    [n] Skip           -- no versioning"                                    -ForegroundColor DarkGray
Write-Host ""
$vChoice = (Read-Host "  Choice [1/2/3/4/n]").Trim().ToLower()
Write-Host $sep

# Resolve new version + code from choice
$newVersion   = $currentVersion
$newCode      = $currentCode
$isRelease    = $false
$releaseNotes = ""

if ($vChoice -eq "1") {
    $newVersion = $vMajor; $newCode = $currentCode + 1; $isRelease = $true
} elseif ($vChoice -eq "2") {
    $newVersion = $vMinor; $newCode = $currentCode + 1; $isRelease = $true
} elseif ($vChoice -eq "3") {
    $newVersion = $vPatch; $newCode = $currentCode + 1; $isRelease = $true
} elseif ($vChoice -eq "4") {
    $newVersion = $currentVersion; $newCode = $currentCode + 1; $isRelease = $false
} else {
    $newVersion = $currentVersion; $newCode = $currentCode; $isRelease = $false
}

# Ask release notes for proper releases
if ($vChoice -eq "1" -or $vChoice -eq "2" -or $vChoice -eq "3") {
    $releaseNotes = (Read-Host "  Release notes (one line)").Trim()
}

# Write version back to build.gradle.kts if changed
if ($newCode -ne $currentCode) {
    $gradleContent = $gradleContent -replace 'versionCode\s*=\s*\d+', "versionCode = $newCode"
    $gradleContent = $gradleContent -replace 'versionName\s*=\s*"[^"]+"', "versionName = `"$newVersion`""
    Set-Content $gradleFile $gradleContent -NoNewline
    Write-Host ""
    if ($newVersion -ne $currentVersion) {
        Write-Host "  Version: v$currentVersion -> v$newVersion  (build $currentCode -> $newCode)" -ForegroundColor Magenta
    } else {
        Write-Host "  Version: v$newVersion  (build $currentCode -> $newCode)" -ForegroundColor Magenta
    }
} else {
    Write-Host ""
    Write-Host "  Version: v$newVersion (build $newCode) -- no change" -ForegroundColor DarkGray
}
Write-Host ""

# ── 1. Check Java ─────────────────────────────────────────────────────────────
Write-Host "[1/4] Checking Java..." -ForegroundColor Yellow
$javaCmd = Get-Command java -ErrorAction SilentlyContinue
$Java    = if ($javaCmd) { $javaCmd.Source } else { $null }
if (-not $Java) {
    Write-Host "ERROR: Java not found. Install JDK 17+." -ForegroundColor Red
    exit 1
}
$javaVersion = & { $ErrorActionPreference = 'Continue'; java -version 2>&1 } |
               ForEach-Object { "$_" } | Select-String "version" | Select-Object -First 1
Write-Host "  $javaVersion" -ForegroundColor DarkGray
$env:JAVA_HOME = Split-Path (Split-Path $Java)
Write-Host "  JAVA_HOME: $($env:JAVA_HOME)" -ForegroundColor DarkGray

# ── 2. Build ──────────────────────────────────────────────────────────────────
Write-Host ""
$gradleTask = if ($isRelease) { "assembleRelease" } else { "assembleDebug" }
$buildLabel = if ($isRelease) { "Release APK" } else { "Debug APK" }
Write-Host "[2/4] Building $buildLabel..." -ForegroundColor Yellow
Write-Host "  (Chaquopy will download Python packages on first build - may take a while)" `
           -ForegroundColor DarkGray

Push-Location $Root
& $GradleW $gradleTask 2>&1
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -ne 0) {
    Write-Host "ERROR: Gradle $gradleTask failed (exit $exitCode)." -ForegroundColor Red
    exit $exitCode
}

$apkSubdir  = if ($isRelease) { "release" } else { "debug" }
$apkPattern = if ($isRelease) { "*.apk" } else { "*-debug.apk" }
$ApkPath    = Get-ChildItem (Join-Path $Root "app\build\outputs\apk\$apkSubdir") `
                  -Filter $apkPattern -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $ApkPath) {
    Write-Host "ERROR: Could not find APK in app/build/outputs/apk/$apkSubdir" -ForegroundColor Red
    exit 1
}
$apkSizeMB = [math]::Round($ApkPath.Length / 1MB, 1)
Write-Host "  Built : $($ApkPath.Name)  ($apkSizeMB MB)" -ForegroundColor Green
Write-Host "  Path  : $($ApkPath.FullName)" -ForegroundColor DarkGray

# ── 3. Deploy via ADB ─────────────────────────────────────────────────────────
Write-Host ""
if ($NoDeploy) {
    Write-Host "[3/4] Skipping deploy (-NoDeploy)." -ForegroundColor DarkGray
    Write-Host "  $($ApkPath.FullName)" -ForegroundColor White
} elseif (-not $ADB) {
    Write-Host "[3/4] ADB not found -- skipping install." -ForegroundColor DarkYellow
} else {
    Write-Host "[3/4] Deploying to device..." -ForegroundColor Yellow

    $devices = & { $ErrorActionPreference = 'Continue'; & $ADB devices 2>&1 } |
               ForEach-Object { "$_" } |
               Select-String "device$" |
               ForEach-Object { ($_ -split "\s+")[0] }

    if (-not $devices) {
        Write-Host "  WARNING: No devices connected. Skipping install." -ForegroundColor DarkYellow
        Write-Host "  Run: adb install -r `"$($ApkPath.FullName)`"" -ForegroundColor White
    } elseif ($ApkPath.Name -match 'unsigned') {
        Write-Host "  WARNING: APK is unsigned -- cannot install via ADB." -ForegroundColor DarkYellow
        Write-Host "  Add a signing config to app/build.gradle.kts." -ForegroundColor DarkGray
    } else {
        $adbArgs = @()
        if ($DeviceSerial) { $adbArgs += @("-s", $DeviceSerial) }
        $adbArgs += @("install", "-r", $ApkPath.FullName)
        Write-Host "  Device(s): $($devices -join ', ')" -ForegroundColor DarkGray
        & { $ErrorActionPreference = 'Continue'; & $ADB @adbArgs 2>&1 } | ForEach-Object { "$_" } | Write-Host
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Installed successfully." -ForegroundColor Green
            $package  = "com.marathitts.mobile"
            $activity = ".MainActivity"
            Write-Host "  Launching $package..." -ForegroundColor DarkGray
            $launchArgs = @()
            if ($DeviceSerial) { $launchArgs += @("-s", $DeviceSerial) }
            $launchArgs += @("shell", "am", "start", "-n", "${package}/${package}${activity}")
            & { $ErrorActionPreference = 'Continue'; & $ADB @launchArgs 2>&1 } | ForEach-Object { "$_" } | Out-Null
        } else {
            Write-Host "  ERROR: adb install failed." -ForegroundColor Red
            exit 1
        }
    }
}

# ── 4. Backup ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Updating backup folder..." -ForegroundColor Yellow
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Host "  Created: $BackupDir" -ForegroundColor DarkGray
}

if ($isRelease) {
    $timestamp  = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupName = "marathi-tts-v${newVersion}-release-${timestamp}.apk"
    $backupPath = Join-Path $BackupDir $backupName
    Copy-Item $ApkPath.FullName $backupPath -Force
    $backupSizeMB = [math]::Round((Get-Item $backupPath).Length / 1MB, 1)
    Write-Host "  APK   : $backupName  ($backupSizeMB MB)" -ForegroundColor Green

    if ($releaseNotes) {
        $notesName = "marathi-tts-v${newVersion}-release-${timestamp}.txt"
        Set-Content (Join-Path $BackupDir $notesName) "v$newVersion`n`n$releaseNotes" -Encoding UTF8
        Write-Host "  Notes : $notesName" -ForegroundColor DarkGray
    }

    # ── Auto-update CHANGELOG.md ───────────────────────────────────────────
    $clPath = Join-Path $PSScriptRoot "CHANGELOG.md"
    if (Test-Path $clPath) {
        $clRaw   = Get-Content $clPath -Raw -Encoding UTF8
        $today   = Get-Date -Format "yyyy-MM-dd"

        # Extract any items staged in the [Unreleased] block
        $unreleasedItems = ""
        if ($clRaw -match '(?s)## \[Unreleased\]\s*\n(.*?)\n---') {
            $unreleasedItems = $Matches[1].Trim()
        }

        # Build new release entry
        $bumpLabel = switch ($vChoice) {
            '1' { 'Major release' }
            '2' { 'Minor release' }
            '3' { 'Hotfix / patch' }
        }
        $newEntry = "## [$newVersion] — $today  (build $newCode)`n### $bumpLabel`n"
        if ($releaseNotes)     { $newEntry += "- $releaseNotes`n" }
        if ($unreleasedItems)  { $newEntry += "$unreleasedItems`n" }

        # Clear the [Unreleased] block and insert new release section after it
        $clRaw = $clRaw -replace '(?s)(## \[Unreleased\]\s*\n).*?(\n---)', "`$1<!-- Changes staged but not yet released go here -->`$2"
        $clRaw = $clRaw -replace '(\n---\n)(\n## \[)', "`n---`n`n## [$newVersion] — $today  (build $newCode)`n### $bumpLabel`n$(if ($releaseNotes) { "- $releaseNotes`n" })$(if ($unreleasedItems) { "$unreleasedItems`n" })`n---`n`n## ["

        Set-Content $clPath $clRaw -Encoding UTF8 -NoNewline
        Write-Host "  CHANGELOG.md updated  (v$newVersion added)" -ForegroundColor Green
    }

} else {
    Write-Host "  APK   : skipped (not a release build)" -ForegroundColor DarkGray
}

$docsToCopy = @(
    @{ Src = (Join-Path $PSScriptRoot "marathi_tts_web\tts_features.md"); Dst = "tts_features.txt" },
    @{ Src = (Join-Path $PSScriptRoot "BUGS.txt");                        Dst = "bugs.txt" },
    @{ Src = (Join-Path $PSScriptRoot "FEATURES.txt");                    Dst = "features.txt" },
    @{ Src = (Join-Path $PSScriptRoot "CHANGELOG.md");                    Dst = "CHANGELOG.md" }
)
foreach ($doc in $docsToCopy) {
    if (Test-Path $doc.Src) {
        Copy-Item $doc.Src (Join-Path $BackupDir $doc.Dst) -Force
        Write-Host "  Docs  : $($doc.Dst)" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host $sep
Write-Host "  Done.  v$newVersion  (build $newCode)" -ForegroundColor Cyan
Write-Host $sep
Write-Host ""

# ── Auto-stage changed files + optional commit ────────────────────────────────
$gitExe = if (Get-Command git -ErrorAction SilentlyContinue) { "git" } `
          elseif (Test-Path "C:\Program Files\Git\bin\git.exe") { "C:\Program Files\Git\bin\git.exe" } `
          else { $null }

if ($gitExe) {
    Push-Location $PSScriptRoot

    # Stage files that the deploy script may have modified
    $filesToStage = @(
        "marathi_tts_mobile/app/build.gradle.kts",
        "CHANGELOG.md",
        "BUGS.txt",
        "FEATURES.txt",
        "deploy_mobile.ps1",
        ".github/copilot-instructions.md"
    )
    foreach ($f in $filesToStage) {
        if (Test-Path (Join-Path $PSScriptRoot $f)) {
            & $gitExe add $f 2>&1 | Out-Null
        }
    }

    $staged = & $gitExe diff --cached --name-only 2>&1
    if ($staged) {
        Write-Host "Staged for commit:" -ForegroundColor DarkGray
        $staged | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        Write-Host ""

        if ($isRelease) {
            $defaultMsg = "release: v$newVersion$(if ($releaseNotes) { " - $releaseNotes" })"
        } else {
            $defaultMsg = "build: v$newVersion (build $newCode)"
        }
        $commitMsg = (Read-Host "  Commit message (Enter = `"$defaultMsg`")").Trim()
        if (-not $commitMsg) { $commitMsg = $defaultMsg }

        & $gitExe commit -m $commitMsg 2>&1 | ForEach-Object { "  $_" } | Write-Host -ForegroundColor DarkGray

        if ($LASTEXITCODE -eq 0 -and $isRelease) {
            $tag = "v$newVersion"
            & $gitExe tag $tag 2>&1 | Out-Null
            Write-Host "  Tagged: $tag" -ForegroundColor Green

            $pushChoice = (Read-Host "  Push to remote? [y/n]").Trim().ToLower()
            if ($pushChoice -eq 'y') {
                & $gitExe push 2>&1 | ForEach-Object { "  $_" } | Write-Host -ForegroundColor DarkGray
                & $gitExe push --tags 2>&1 | ForEach-Object { "  $_" } | Write-Host -ForegroundColor DarkGray
            }
        }
    } else {
        Write-Host "  Nothing to commit." -ForegroundColor DarkGray
    }

    Pop-Location
    Write-Host ""
}
