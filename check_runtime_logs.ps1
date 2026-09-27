param([switch]$Dump)

# Locate ADB dynamically
$adb = (Get-Command adb -ErrorAction SilentlyContinue)?.Source
if (-not $adb) {
    $sdkCandidates = @(
        $env:ANDROID_HOME,
        $env:ANDROID_SDK_ROOT,
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "Android\Sdk" }),
        $(if ($env:SystemDrive) { "$env:SystemDrive\Android\Sdk" }),
        "~/Android/Sdk"
    )
    foreach ($cand in $sdkCandidates) {
        if ($cand -and (Test-Path $cand)) {
            $candidateExe = Join-Path $cand "platform-tools\adb.exe"
            if (Test-Path $candidateExe) { $adb = $candidateExe; break }
            $candidateUnix = Join-Path $cand "platform-tools/adb"
            if (Test-Path $candidateUnix) { $adb = $candidateUnix; break }
        }
    }
}
if (-not $adb) { $adb = "adb" }

# Live-tail our app's logs only (filtered by tag).
# Press Ctrl+C to stop.
# Usage:
#   .\check_runtime_logs.ps1          → live tail (default)
#   .\check_runtime_logs.ps1 -Dump    → dump recent logs and exit

$tags = @(
    # Book reader
    "BookCameraActivity",
    "BookPageProcessor",
    "BookReaderFragment",
    "BookReaderViewModel",
    "PageEdgeDetector",
    "NativeImageOcr",
    # TTS & audio
    "TtsEngineManager",
    "AudioPlayerService",
    "SystemTtsEngine",
    # Python bridge
    "PythonBridge",
    "ChaquopyBridge",
    # Stotra
    "StotraRepository",
    "StotraFragment",
    "StotraViewModel",
    # Other screens
    "TtsFragment",
    "TtsViewModel",
    "EmotionFragment",
    "EmotionViewModel",
    "OcrFragment",
    "SttFragment",
    "CorrectionFragment",
    "WebFetchFragment",
    "PdfFragment",
    "ModiFragment",
    # TestDashboard
    "TestDashboard",
    # Generic app tags
    "MarathiTTS",
    "marathitts"
)

# Build logcat tag filter: "Tag:D Tag2:D ... *:S"
# *:S silences everything else
$filter = ($tags | ForEach-Object { "${_}:V" }) -join " "
$filter += " *:S"

if ($Dump) {
    Write-Host "=== Recent app logs (last 500 lines) ===" -ForegroundColor Cyan
    & $adb logcat -d -t 500 $filter 2>&1
} else {
    Write-Host "=== Live app logs -- Ctrl+C to stop ===" -ForegroundColor Cyan
    $watchList = $tags -join ", "
    Write-Host "Watching: $watchList" -ForegroundColor DarkGray
    Write-Host ""
    & $adb logcat $filter 2>&1
}
