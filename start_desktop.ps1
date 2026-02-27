# Marathi TTS Desktop - Start Script (PowerShell)
# Usage: .\start_desktop.ps1 [-Setup] [-Release]
#
#   -Setup     Run Python setup_bridge.py first to install all Python deps
#   -Release   Build & run the fat JAR instead of Gradle run (slower start,
#              but no Gradle overhead after first build)

param(
    [switch]$Setup,
    [switch]$Release
)

$ErrorActionPreference = "Stop"

# Set console to UTF-8 so Devanagari characters render correctly in terminal output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$Root = Join-Path $PSScriptRoot "marathi_tts_desktop"
$PythonBridgeDir = Join-Path $Root "python_bridge"
$GradleW = Join-Path $Root "gradlew.bat"

Write-Host ""
Write-Host "=== Marathi TTS Desktop ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Locate Python ─────────────────────────────────────────────────────────
Write-Host "[1/4] Locating Python..." -ForegroundColor Yellow

# Prefer the web-app venv if it exists alongside this folder
$VenvPy = Resolve-Path (Join-Path $Root "..\marathi_tts_web\.venv\Scripts\python.exe") `
           -ErrorAction SilentlyContinue

if ($VenvPy) {
    $Python = $VenvPy.Path
    Write-Host "  Using web-app venv: $Python" -ForegroundColor DarkGray
} else {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    $Python = if ($pyCmd) { $pyCmd.Source } else { $null }
    if (-not $Python) {
        $py3Cmd = Get-Command python3 -ErrorAction SilentlyContinue
        $Python = if ($py3Cmd) { $py3Cmd.Source } else { $null }
    }
    if (-not $Python) {
        Write-Host "ERROR: Python not found. Install Python 3.10+ or create the web-app venv first." `
                   -ForegroundColor Red
        exit 1
    }
    Write-Host "  Using system Python: $Python" -ForegroundColor DarkGray
}

# Show version
& $Python --version

# ── 2. Optional Python dependency setup ──────────────────────────────────────
if ($Setup) {
    Write-Host ""
    Write-Host "[2/4] Running Python setup_bridge.py..." -ForegroundColor Yellow
    $setupScript = Join-Path $PythonBridgeDir "setup_bridge.py"
    if (-not (Test-Path $setupScript)) {
        Write-Host "  WARNING: setup_bridge.py not found, skipping." -ForegroundColor DarkYellow
    } else {
        & $Python $setupScript
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  WARNING: setup_bridge.py exited with code $LASTEXITCODE" `
                       -ForegroundColor DarkYellow
        } else {
            Write-Host "  Python dependencies ready." -ForegroundColor Green
        }
    }
} else {
    Write-Host "[2/4] Skipping Python setup (use -Setup flag to install/verify dependencies)" `
               -ForegroundColor DarkGray
}

# ── 3. Check Java ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[3/4] Checking Java..." -ForegroundColor Yellow
$javaCmd = Get-Command java -ErrorAction SilentlyContinue
$Java = if ($javaCmd) { $javaCmd.Source } else { $null }
if (-not $Java) {
    Write-Host "ERROR: Java not found. Install JDK 17+." -ForegroundColor Red
    exit 1
}
$javaVersion = & { $ErrorActionPreference = 'Continue'; java -version 2>&1 } | ForEach-Object { "$_" } | Select-String "version" | Select-Object -First 1
Write-Host "  $javaVersion" -ForegroundColor DarkGray

# Derive JAVA_HOME from the java executable so Gradle uses this JDK
$JavaHome = (Split-Path (Split-Path $Java))   # …\bin\java.exe → …\bin → …
$env:JAVA_HOME = $JavaHome
Write-Host "  JAVA_HOME set to: $JavaHome" -ForegroundColor DarkGray

# ── 4. Build & launch ─────────────────────────────────────────────────────────
Write-Host ""
if ($Release) {
    Write-Host "[4/4] Building fat JAR (release mode)..." -ForegroundColor Yellow
    Push-Location $Root
    & $GradleW fatJar
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Gradle fatJar failed." -ForegroundColor Red
        Pop-Location
        exit 1
    }
    # Find the built JAR
    $Jar = Get-ChildItem (Join-Path $Root "build\libs") -Filter "*-all.jar" |
           Sort-Object LastWriteTime -Descending |
           Select-Object -First 1
    Pop-Location
    if (-not $Jar) {
        Write-Host "ERROR: Could not find fat JAR in build/libs." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Launching JAR: $($Jar.Name)" -ForegroundColor Green
    # Pass python path so PythonBridge can locate interpreter
    $env:PYTHON_EXECUTABLE = $Python
    & java "-DPYTHON_EXECUTABLE=$Python" "-Dfile.encoding=UTF-8" "-Dstdout.encoding=UTF-8" "-Dstderr.encoding=UTF-8" -jar $Jar.FullName
} else {
    Write-Host "[4/4] Launching via Gradle run (dev mode)..." -ForegroundColor Yellow
    Write-Host "  (Use -Release flag for fat-JAR launch after first build)" -ForegroundColor DarkGray
    Push-Location $Root
    # Pass the python path as an environment variable picked up by PythonBridge
    $env:PYTHON_EXECUTABLE = $Python
    $env:PYTHON_PATH = $Python
    & $GradleW run
    $exitCode = $LASTEXITCODE
    Pop-Location
    if ($exitCode -ne 0) {
        Write-Host "ERROR: Application exited with code $exitCode" -ForegroundColor Red
        exit $exitCode
    }
}

Write-Host ""
Write-Host "Desktop app closed." -ForegroundColor Cyan
