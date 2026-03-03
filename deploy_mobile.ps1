# Marathi TTS Mobile - Build & Deploy Script (PowerShell)
# Usage: .\deploy_mobile.ps1 [-Release] [-NoDeploy] [-DeviceSerial <serial>]
#                             [-BumpMajor] [-BumpMinor] [-BumpPatch] [-Hotfix]
#
#   -Release           Build a release APK (assembleRelease) instead of debug.
#                      Requires signing config in app/build.gradle.kts.
#   -NoDeploy          Build only; do not push to a connected device/emulator.
#   -DeviceSerial <s>  Target a specific ADB device serial (use: adb devices).
#   -BumpMajor         Bump major version   (e.g. 1.2.3 -> 2.0.0)
#   -BumpMinor         Bump minor version   (e.g. 1.2.3 -> 1.3.0)
#   -BumpPatch         Bump patch version   (e.g. 1.2.3 -> 1.2.4)
#   -Hotfix            Append/bump hotfix   (e.g. 1.2.3 -> 1.2.3-hotfix.1,
#                                             1.2.3-hotfix.1 -> 1.2.3-hotfix.2)
#
# Version is read from and written back to app/build.gradle.kts automatically.
# The built APK is always copied to C:\My_Drive_Backup\builds\marathi_tts\ with
# a timestamped, versioned filename.

param(
    [switch]$Release,
    [switch]$NoDeploy,
    [string]$DeviceSerial = "",
    [switch]$BumpMajor,
    [switch]$BumpMinor,
    [switch]$BumpPatch,
    [switch]$Hotfix
)

$ErrorActionPreference = "Stop"
$Root    = Join-Path $PSScriptRoot "marathi_tts_mobile"
$GradleW = Join-Path $Root "gradlew.bat"
$BackupDir = "C:\My_Drive_Backup\builds\marathi_tts"

Write-Host ""
Write-Host "=== Marathi TTS Mobile ===" -ForegroundColor Cyan
Write-Host ""

# ── 0. Version management ────────────────────────────────────────────────────
$gradleFile = Join-Path $Root "app\build.gradle.kts"
$gradleContent = Get-Content $gradleFile -Raw

# Parse current versionName and versionCode
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

# Split version: base may be "1.2.3" or "1.2.3-hotfix.N"
$hotfixNum = 0
$basePart  = $currentVersion
if ($currentVersion -match '^(\d+\.\d+\.\d+)-hotfix\.(\d+)$') {
    $basePart  = $Matches[1]
    $hotfixNum = [int]$Matches[2]
}
$vParts = $basePart -split '\.'
$major = [int]$vParts[0]; $minor = [int]$vParts[1]; $patch = [int]$vParts[2]

# Compute proposed new version (without writing yet)
$bumped = $false
$proposedBase = "$major.$minor.$patch"
$proposedHotfix = $hotfixNum
if ($BumpMajor) {
    $major++; $minor = 0; $patch = 0; $proposedHotfix = 0; $bumped = $true
} elseif ($BumpMinor) {
    $minor++; $patch = 0; $proposedHotfix = 0; $bumped = $true
} elseif ($BumpPatch) {
    $patch++; $proposedHotfix = 0; $bumped = $true
} elseif ($Hotfix) {
    $proposedHotfix++; $bumped = $true
}

if ($bumped) {
    $newBase = "$major.$minor.$patch"
    if ($proposedHotfix -gt 0) {
        $proposedVersion = "$newBase-hotfix.$proposedHotfix"
    } else {
        $proposedVersion = $newBase
    }
    $proposedCode = $currentCode + 1

    # Ask for confirmation
    Write-Host "[0/5] Current version: $currentVersion (code $currentCode)" -ForegroundColor Yellow
    Write-Host "       Proposed bump : $proposedVersion (code $proposedCode)" -ForegroundColor Cyan
    $confirm = Read-Host "  Proceed with version bump? (Y/n)"
    if ($confirm -eq '' -or $confirm -match '^[Yy]') {
        $newVersion = $proposedVersion
        $newCode    = $proposedCode

        # Write back to build.gradle.kts
        $gradleContent = $gradleContent -replace 'versionCode\s*=\s*\d+', "versionCode = $newCode"
        $gradleContent = $gradleContent -replace 'versionName\s*=\s*"[^"]+"', "versionName = `"$newVersion`""
        Set-Content $gradleFile $gradleContent -NoNewline
        Write-Host "  Version bumped -> $newVersion (code $newCode)" -ForegroundColor Magenta
    } else {
        $newVersion = $currentVersion
        $newCode    = $currentCode
        Write-Host "  Skipped version bump. Building as $newVersion (code $newCode)" -ForegroundColor DarkGray
    }
} else {
    # No bump flag passed — ask if user wants to tag/version this build
    Write-Host "[0/5] Current version: $currentVersion (code $currentCode)" -ForegroundColor Yellow
    $tagChoice = Read-Host "  Bump version before building? (major/minor/patch/hotfix/N)"
    switch -Regex ($tagChoice.Trim().ToLower()) {
        '^ma'    { $major++; $minor = 0; $patch = 0; $hotfixNum = 0; $bumped = $true }
        '^mi'    { $minor++; $patch = 0; $hotfixNum = 0; $bumped = $true }
        '^p'     { $patch++; $hotfixNum = 0; $bumped = $true }
        '^h'     { $hotfixNum++; $bumped = $true }
        default  { $bumped = $false }
    }
    if ($bumped) {
        $newBase = "$major.$minor.$patch"
        if ($hotfixNum -gt 0) {
            $newVersion = "$newBase-hotfix.$hotfixNum"
        } else {
            $newVersion = $newBase
        }
        $newCode = $currentCode + 1
        $gradleContent = $gradleContent -replace 'versionCode\s*=\s*\d+', "versionCode = $newCode"
        $gradleContent = $gradleContent -replace 'versionName\s*=\s*"[^"]+"', "versionName = `"$newVersion`""
        Set-Content $gradleFile $gradleContent -NoNewline
        Write-Host "  Version bumped -> $newVersion (code $newCode)" -ForegroundColor Magenta
    } else {
        $newVersion = $currentVersion
        $newCode    = $currentCode
        Write-Host "  No bump. Building as $newVersion (code $newCode)" -ForegroundColor DarkGray
    }
}
Write-Host ""

# ── 1. Locate ADB (skip if -NoDeploy) ────────────────────────────────────────
$ADB = $null
if (-not $NoDeploy) {
    Write-Host "[1/5] Locating ADB..." -ForegroundColor Yellow

    # Common locations
    $adbCmd = Get-Command adb -ErrorAction SilentlyContinue
    $candidates = @(
        $(if ($adbCmd) { $adbCmd.Source }),
        "$env:ANDROID_HOME\platform-tools\adb.exe",
        "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe",
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        "C:\Android\Sdk\platform-tools\adb.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { $ADB = $c; break }
    }

    if (-not $ADB) {
        Write-Host "  WARNING: adb not found. Build will proceed but APK will NOT be deployed." `
                   -ForegroundColor DarkYellow
        Write-Host "  Set ANDROID_HOME or add platform-tools to PATH." -ForegroundColor DarkGray
        $NoDeploy = $true
    } else {
        Write-Host "  ADB: $ADB" -ForegroundColor DarkGray
        # Derive ANDROID_HOME from ADB path (…\platform-tools\adb.exe -> …)
        $SdkDir = Split-Path (Split-Path $ADB)
        if (-not $env:ANDROID_HOME) {
            $env:ANDROID_HOME = $SdkDir
            Write-Host "  ANDROID_HOME set to: $SdkDir" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "[1/5] Skipping ADB check (-NoDeploy)" -ForegroundColor DarkGray
}

# ── 2. Check Java ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/5] Checking Java..." -ForegroundColor Yellow
$javaCmd = Get-Command java -ErrorAction SilentlyContinue
$Java = if ($javaCmd) { $javaCmd.Source } else { $null }
if (-not $Java) {
    Write-Host "ERROR: Java not found. Install JDK 17+ (required by Gradle)." -ForegroundColor Red
    exit 1
}
$javaVersion = & { $ErrorActionPreference = 'Continue'; java -version 2>&1 } | ForEach-Object { "$_" } | Select-String "version" | Select-Object -First 1
Write-Host "  $javaVersion" -ForegroundColor DarkGray

# Derive JAVA_HOME from the java executable so Gradle uses this JDK
$JavaHome = (Split-Path (Split-Path $Java))   # …\bin\java.exe → …\bin → …
$env:JAVA_HOME = $JavaHome
Write-Host "  JAVA_HOME set to: $JavaHome" -ForegroundColor DarkGray

# ── 3. Build APK ──────────────────────────────────────────────────────────────
Write-Host ""
$buildVariant = if ($Release) { "Release" } else { "Debug" }
Write-Host "[3/5] Building $buildVariant APK..." -ForegroundColor Yellow
Write-Host "  (Chaquopy will download Python packages on first build - may take a while)" `
           -ForegroundColor DarkGray

Push-Location $Root
$gradleTask = if ($Release) { "assembleRelease" } else { "assembleDebug" }
# Redirect stderr→stdout so pip/Chaquopy warnings don't trigger PowerShell error handling.
# Build success/failure is determined solely by $LASTEXITCODE (Gradle exit code).
& $GradleW $gradleTask 2>&1
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -ne 0) {
    Write-Host "ERROR: Gradle $gradleTask failed (exit $exitCode)." -ForegroundColor Red
    exit $exitCode
}

# Locate the output APK
$apkSubdir = if ($Release) { "release" } else { "debug" }
$apkPattern = if ($Release) { "*.apk" } else { "*-debug.apk" }
$ApkPath = Get-ChildItem (Join-Path $Root "app\build\outputs\apk\$apkSubdir") `
               -Filter $apkPattern -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending |
           Select-Object -First 1

if (-not $ApkPath) {
    Write-Host "ERROR: Could not find built APK in app/build/outputs/apk/$apkSubdir" `
               -ForegroundColor Red
    exit 1
}

$apkSizeMB = [math]::Round($ApkPath.Length / 1MB, 1)
Write-Host "  Built: $($ApkPath.Name)  ($($apkSizeMB) MB)" -ForegroundColor Green
Write-Host "  Path : $($ApkPath.FullName)" -ForegroundColor DarkGray

# ── 4. Deploy via ADB ─────────────────────────────────────────────────────────
Write-Host ""
if ($NoDeploy) {
    Write-Host "[4/5] Skipping deploy (-NoDeploy). Copy the APK manually:" -ForegroundColor DarkGray
    Write-Host "  $($ApkPath.FullName)" -ForegroundColor White
} else {
    Write-Host "[4/5] Deploying to device..." -ForegroundColor Yellow

    # List connected devices (adb prints daemon startup to stderr; suppress with Continue)
    $devices = & { $ErrorActionPreference = 'Continue'; & $ADB devices 2>&1 } |
               ForEach-Object { "$_" } |
               Select-String "device$" |
               ForEach-Object { ($_ -split "\s+")[0] }

    if (-not $devices) {
        Write-Host "  WARNING: No devices/emulators connected. Skipping install." `
                   -ForegroundColor DarkYellow
        Write-Host "  Connect a device or start an emulator, then run:" -ForegroundColor DarkGray
        Write-Host "  adb install -r `"$($ApkPath.FullName)`"" -ForegroundColor White
    } else {
        $adbArgs = @()
        if ($DeviceSerial) { $adbArgs += @("-s", $DeviceSerial) }
        $adbArgs += @("install", "-r", $ApkPath.FullName)

        Write-Host "  Device(s): $($devices -join ', ')" -ForegroundColor DarkGray
        & { $ErrorActionPreference = 'Continue'; & $ADB @adbArgs 2>&1 } | ForEach-Object { "$_" } | Write-Host
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Installed successfully." -ForegroundColor Green

            # Launch the app
            $package = "com.marathitts.mobile"
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

# ── 5. Copy APK to backup folder (release builds only) ────────────────────────
Write-Host ""
if ($Release) {
    Write-Host "[5/5] Copying APK to backup..." -ForegroundColor Yellow
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        Write-Host "  Created: $BackupDir" -ForegroundColor DarkGray
    }
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupName = "marathi-tts-v${newVersion}-release-${timestamp}.apk"
    $backupPath = Join-Path $BackupDir $backupName
    Copy-Item $ApkPath.FullName $backupPath -Force
    $backupSizeMB = [math]::Round((Get-Item $backupPath).Length / 1MB, 1)
    Write-Host "  Copied: $backupName  ($backupSizeMB MB)" -ForegroundColor Green
    Write-Host "  Path  : $backupPath" -ForegroundColor DarkGray

    # Copy features and bugs docs as .txt to backup folder
    $docsToCopy = @(
        @{ Src = (Join-Path $PSScriptRoot "marathi_tts_web\tts_features.md");  Dst = "tts_features.txt" },
        @{ Src = (Join-Path $PSScriptRoot "BUGS.txt");                          Dst = "bugs.txt" },
        @{ Src = (Join-Path $PSScriptRoot "FEATURES.txt");                      Dst = "features.txt" }
    )
    foreach ($doc in $docsToCopy) {
        if (Test-Path $doc.Src) {
            $dstPath = Join-Path $BackupDir $doc.Dst
            Copy-Item $doc.Src $dstPath -Force
            Write-Host "  Copied: $($doc.Dst)" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "[5/5] Skipping backup (debug build -- only release builds are copied)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Done. v$newVersion (code $newCode)" -ForegroundColor Cyan
