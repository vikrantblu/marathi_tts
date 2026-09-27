# run_mobile_tests.ps1 - Build, install, and run Test Dashboard on device
param(
    [switch]$SkipBuild,
    [int]$Timeout = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PKG           = "com.marathitts.mobile"
$MAIN_ACTIVITY = "$PKG/.MainActivity"
$MOBILE_DIR    = "$PSScriptRoot\marathi_tts_mobile"
$SEP           = "-" * 72

# Locate ADB
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
$adb = if ($adbCmd) { $adbCmd.Source } else {
    @(
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        "$env:ANDROID_HOME\platform-tools\adb.exe",
        "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe",
        $(if ($env:SystemDrive) { "$env:SystemDrive\Android\Sdk\platform-tools\adb.exe" })
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

if (-not $adb) { Write-Error "adb.exe not found." }
Write-Host "[adb] $adb" -ForegroundColor DarkGray

# Check device
$devList = & $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\bdevice\b" }
if (-not $devList) { Write-Error "No Android device connected." }
$serial = ($devList -split "\s+")[0]
Write-Host "[device] $serial" -ForegroundColor Cyan

# Build
if (-not $SkipBuild) {
    Write-Host "`n[build] Running assembleDebug..." -ForegroundColor Yellow
    Push-Location $MOBILE_DIR
    try {
        & .\gradlew.bat assembleDebug --quiet
        if ($LASTEXITCODE -ne 0) { throw "Gradle build failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
    Write-Host "[build] Done." -ForegroundColor Green
}

# Install
$apk = Get-ChildItem "$MOBILE_DIR\app\build\outputs\apk\debug\*.apk" |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $apk) { Write-Error "No debug APK found." }
Write-Host "`n[install] $($apk.Name)" -ForegroundColor Yellow
& $adb -s $serial install -r $apk.FullName | Out-Null
Write-Host "[install] Done." -ForegroundColor Green

# Clear logcat + kill old instance
& $adb -s $serial logcat -c
& $adb -s $serial shell am force-stop $PKG | Out-Null
Start-Sleep -Milliseconds 800

# Launch with autoRun intent
Write-Host "[launch] Starting TestDashboard with autoRun=true..." -ForegroundColor Yellow
& $adb -s $serial shell am start -n $MAIN_ACTIVITY --es navigate_to testDashboard --ez auto_run true | Out-Null
Write-Host "[launch] Done. Streaming logcat..." -ForegroundColor Green
Write-Host $SEP -ForegroundColor DarkGray

# Stream logcat via background job
$passCount = 0
$failCount = 0
$logLines  = [System.Collections.Generic.List[string]]::new()
$startTime = Get-Date

$job = Start-Job -ScriptBlock {
    param($adbExe, $deviceSerial)
    & $adbExe -s $deviceSerial logcat -v time "TestDashboard:D" "MainActivity:I" "PythonBridge:W" "*:S"
} -ArgumentList $adb, $serial

try {
    while ($true) {
        $lines = Receive-Job $job 2>$null
        foreach ($line in $lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $logLines.Add($line)

            if ($line -match "\[T\d{2}\] PASS") {
                Write-Host "  $line" -ForegroundColor Green
            } elseif ($line -match "\[T\d{2}\] FAIL") {
                Write-Host "  $line" -ForegroundColor Red
            } elseif ($line -match "Starting|autoRun|Ready|ALL done") {
                Write-Host "  $line" -ForegroundColor Cyan
            } else {
                Write-Host "  $line" -ForegroundColor DarkGray
            }

            if ($line -match "ALL done") { break }
        }
        if ($lines -match "ALL done") { break }
        if (((Get-Date) - $startTime).TotalSeconds -gt $Timeout) {
            Write-Host "`n[timeout] ${Timeout}s reached." -ForegroundColor Yellow
            break
        }
        Start-Sleep -Milliseconds 400
    }
} finally {
    Stop-Job  $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}

# Tally
$passCount = @($logLines | Where-Object { $_ -match "\[T\d{2}\] PASS" }).Count
$failCount = @($logLines | Where-Object { $_ -match "\[T\d{2}\] FAIL" }).Count
$total     = $passCount + $failCount

Write-Host $SEP -ForegroundColor DarkGray
Write-Host "MOBILE RESULTS  total=$total  PASS=$passCount  FAIL=$failCount"
if ($failCount -gt 0) { Write-Host "FAILED tests:" -ForegroundColor Red }
$logLines | Where-Object { $_ -match "\[T\d{2}\] FAIL" } | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }

# Save log
$ts  = (Get-Date).ToString("yyyyMMdd_HHmmss")
$log = "$PSScriptRoot\marathi_tts_mobile\test_run_$ts.log"
$logLines | Set-Content $log -Encoding UTF8
Write-Host "[log] $log" -ForegroundColor DarkGray

if ($failCount -gt 0) { exit 1 }
elseif ($total -eq 0) { Write-Host "[WARN] No results captured." -ForegroundColor Yellow; exit 2 }
else { Write-Host "[ALL PASS]" -ForegroundColor Green; exit 0 }
