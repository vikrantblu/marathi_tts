# Marathi TTS Mobile - Build & Deploy Script (PowerShell)
# Usage: .\deploy_mobile.ps1 [-NoDeploy] [-DeviceSerial <serial>]
#
#   -NoDeploy          Build only; do not push to a connected device/emulator.
#   -DeviceSerial <s>  Target a specific ADB device serial (use: adb devices).

param(
    [switch]$NoDeploy,
    [string]$DeviceSerial = ""
)

$ErrorActionPreference = "Stop"
$Root = Join-Path $PSScriptRoot "marathi_tts_mobile"
$GradleW = Join-Path $Root "gradlew.bat"
$sep = "-" * 44

Write-Host ""
Write-Host "=== Marathi TTS Mobile ===" -ForegroundColor Cyan
Write-Host ""

# ── Locate ADB ────────────────────────────────────────────────────────────────
$ADB = $null
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
$adbCandidates = @(
    $(if ($adbCmd) { $adbCmd.Source }),
    "$env:ANDROID_HOME\platform-tools\adb.exe",
    "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe",
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
    $(if ($env:SystemDrive) { "$env:SystemDrive\Android\Sdk\platform-tools\adb.exe" })
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
    }
    else {
        Write-Host "  No devices connected." -ForegroundColor DarkYellow
    }
}
else {
    Write-Host "  ADB not found -- device check skipped." -ForegroundColor DarkYellow
}
Write-Host ""

# ── Show current version ─────────────────────────────────────────────────────
$gradleFile = Join-Path $Root "app\build.gradle.kts"
$gradleContent = Get-Content $gradleFile -Raw

if ($gradleContent -match 'versionName\s*=\s*"([^"]+)"') {
    $currentVersion = $Matches[1]
}
else {
    $currentVersion = "unknown"
}
if ($gradleContent -match 'versionCode\s*=\s*(\d+)') {
    $currentCode = [int]$Matches[1]
}
else {
    $currentCode = 0
}
Write-Host "  Version: v$currentVersion (build $currentCode)" -ForegroundColor Yellow
Write-Host ""

# ── 1. Check Java ─────────────────────────────────────────────────────────────
Write-Host "[1/3] Checking Java..." -ForegroundColor Yellow
$javaCmd = Get-Command java -ErrorAction SilentlyContinue
$Java = if ($javaCmd) { $javaCmd.Source } else { $null }
if (-not $Java) {
    Write-Host "ERROR: Java not found. Install JDK 17+." -ForegroundColor Red
    exit 1
}
$javaVersion = & { $ErrorActionPreference = 'Continue'; java -version 2>&1 } |
ForEach-Object { "$_" } | Select-String "version" | Select-Object -First 1
Write-Host "  $javaVersion" -ForegroundColor DarkGray
$env:JAVA_HOME = Split-Path (Split-Path $Java)
Write-Host "  JAVA_HOME: $($env:JAVA_HOME)" -ForegroundColor DarkGray

# ── 2. Build Debug APK ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/3] Building Debug APK..." -ForegroundColor Yellow
Write-Host "  (Chaquopy will download Python packages on first build - may take a while)" `
    -ForegroundColor DarkGray

Push-Location $Root
& $GradleW assembleDebug 2>&1
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -ne 0) {
    Write-Host "ERROR: Gradle assembleDebug failed (exit $exitCode)." -ForegroundColor Red
    exit $exitCode
}

$ApkPath = Get-ChildItem (Join-Path $Root "app\build\outputs\apk\debug") `
    -Filter "*-debug.apk" -ErrorAction SilentlyContinue |
Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $ApkPath) {
    Write-Host "ERROR: Could not find APK in app/build/outputs/apk/debug" -ForegroundColor Red
    exit 1
}
$apkSizeMB = [math]::Round($ApkPath.Length / 1MB, 1)
Write-Host "  Built : $($ApkPath.Name)  ($apkSizeMB MB)" -ForegroundColor Green
Write-Host "  Path  : $($ApkPath.FullName)" -ForegroundColor DarkGray

# ── 3. Deploy via ADB ─────────────────────────────────────────────────────────
Write-Host ""
if ($NoDeploy) {
    Write-Host "[3/3] Skipping deploy (-NoDeploy)." -ForegroundColor DarkGray
    Write-Host "  $($ApkPath.FullName)" -ForegroundColor White
}
elseif (-not $ADB) {
    Write-Host "[3/3] ADB not found -- skipping install." -ForegroundColor DarkYellow
}
else {
    Write-Host "[3/3] Deploying to device..." -ForegroundColor Yellow

    $devices = & { $ErrorActionPreference = 'Continue'; & $ADB devices 2>&1 } |
    ForEach-Object { "$_" } |
    Select-String "device$" |
    ForEach-Object { ($_ -split "\s+")[0] }

    if (-not $devices) {
        Write-Host "  WARNING: No devices connected. Skipping install." -ForegroundColor DarkYellow
        Write-Host "  Run: adb install -r `"$($ApkPath.FullName)`"" -ForegroundColor White
    }
    elseif ($ApkPath.Name -match 'unsigned') {
        Write-Host "  WARNING: APK is unsigned -- cannot install via ADB." -ForegroundColor DarkYellow
    }
    else {
        $package = "com.marathitts.mobile"
        $activity = ".MainActivity"

        $adbArgs = @()
        if ($DeviceSerial) { $adbArgs += @("-s", $DeviceSerial) }
        $adbArgs += @("install", "-r", $ApkPath.FullName)
        Write-Host "  Device(s): $($devices -join ', ')" -ForegroundColor DarkGray
        $installOut = & { $ErrorActionPreference = 'Continue'; & $ADB @adbArgs 2>&1 } | ForEach-Object { "$_" }
        $installOut | Write-Host
        $installFailed = $LASTEXITCODE -ne 0

        # ── Auto-retry on signature mismatch ─────────────────────────────────
        if ($installFailed -and ($installOut -join "`n") -match 'INSTALL_FAILED_UPDATE_INCOMPATIBLE') {
            Write-Host ""
            Write-Host "  Signature mismatch detected -- uninstalling old package and retrying..." -ForegroundColor DarkYellow
            $uninstArgs = @()
            if ($DeviceSerial) { $uninstArgs += @("-s", $DeviceSerial) }
            $uninstArgs += @("uninstall", $package)
            & { $ErrorActionPreference = 'Continue'; & $ADB @uninstArgs 2>&1 } | ForEach-Object { "$_" } | Write-Host
            Write-Host "  Reinstalling..." -ForegroundColor DarkGray
            & { $ErrorActionPreference = 'Continue'; & $ADB @adbArgs 2>&1 } | ForEach-Object { "$_" } | Write-Host
            $installFailed = $LASTEXITCODE -ne 0
        }

        if (-not $installFailed) {
            Write-Host "  Installed successfully." -ForegroundColor Green
            Write-Host "  Launching $package..." -ForegroundColor DarkGray
            $launchArgs = @()
            if ($DeviceSerial) { $launchArgs += @("-s", $DeviceSerial) }
            $launchArgs += @("shell", "am", "start", "-n", "${package}/${package}${activity}")
            & { $ErrorActionPreference = 'Continue'; & $ADB @launchArgs 2>&1 } | ForEach-Object { "$_" } | Out-Null
        }
        else {
            Write-Host "  ERROR: adb install failed." -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host $sep
Write-Host "  Done.  v$currentVersion  (build $currentCode)" -ForegroundColor Cyan
Write-Host $sep
Write-Host ""
