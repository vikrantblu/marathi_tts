# Marathi TTS Mobile - Build & Deploy Script (PowerShell)
# Usage: .\deploy_mobile.ps1 [-Release] [-NoDeploy] [-DeviceSerial <serial>]
#
#   -Release           Build a release APK (assembleRelease) instead of debug.
#                      Requires signing config in app/build.gradle.kts.
#   -NoDeploy          Build only; do not push to a connected device/emulator.
#   -DeviceSerial <s>  Target a specific ADB device serial (use: adb devices).

param(
    [switch]$Release,
    [switch]$NoDeploy,
    [string]$DeviceSerial = ""
)

$ErrorActionPreference = "Stop"
$Root    = Join-Path $PSScriptRoot "marathi_tts_mobile"
$GradleW = Join-Path $Root "gradlew.bat"

Write-Host ""
Write-Host "=== Marathi TTS Mobile ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Locate ADB (skip if -NoDeploy) ────────────────────────────────────────
$ADB = $null
if (-not $NoDeploy) {
    Write-Host "[1/4] Locating ADB..." -ForegroundColor Yellow

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
    Write-Host "[1/4] Skipping ADB check (-NoDeploy)" -ForegroundColor DarkGray
}

# ── 2. Check Java ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/4] Checking Java..." -ForegroundColor Yellow
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
Write-Host "[3/4] Building $buildVariant APK..." -ForegroundColor Yellow
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
    Write-Host "[4/4] Skipping deploy (-NoDeploy). Copy the APK manually:" -ForegroundColor DarkGray
    Write-Host "  $($ApkPath.FullName)" -ForegroundColor White
} else {
    Write-Host "[4/4] Deploying to device..." -ForegroundColor Yellow

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

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
