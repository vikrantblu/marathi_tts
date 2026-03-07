# Marathi TTS - Start Server (PowerShell)
# Usage: .\start_server.ps1 [-Port 9000] [-WslPort 8888]
#
# Django runs inside WSL2 on WslPort. A TCP proxy on Windows forwards
# Port -> WslPort so that Chrome/Edge can reach the server (WSL2 mirrored
# networking ports are not always reachable from browsers directly).

param(
    [int]$Port    = 9000,   # Windows-side port (what you open in Chrome)
    [int]$WslPort = 8888    # WSL-side Django port
)

Write-Host ""
Write-Host "=== Marathi TTS Server ===" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Stop old processes ---
Write-Host "[1/5] Stopping old processes..." -ForegroundColor Yellow
wsl -d Ubuntu-22.04 -e bash -c "pkill -f 'manage.py runserver' 2>/dev/null"
Get-Process python -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'tcp_proxy' } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# --- Step 2: Start Django in WSL (background job, no extra window) ---
Write-Host "[2/5] Starting Django on WSL port $WslPort..." -ForegroundColor Yellow
$wslCmd = "cd /mnt/d/marathi_tts/marathi_tts_web && source /home/vicky/venv/bin/activate && export CUDA_VISIBLE_DEVICES=-1 TF_CPP_MIN_LOG_LEVEL=3 TRANSFORMERS_NO_TF=1 USE_TF=0 TRANSFORMERS_VERBOSITY=error && python manage.py runserver 0.0.0.0:${WslPort} --noreload"
$djangoJob = Start-Job -ScriptBlock {
    param($cmd)
    wsl -d Ubuntu-22.04 -- bash -c $cmd
} -ArgumentList $wslCmd

# --- Step 3: Wait for Django ---
Write-Host "[3/5] Waiting for Django to start..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $code = curl.exe -s -o NUL -w "%{http_code}" "http://127.0.0.1:${WslPort}/" 2>$null
        if ($code -and $code -ne "000") {
            $ready = $true
            break
        }
    } catch {}
    Write-Host "  Waiting... ($($i*2)s)" -ForegroundColor DarkGray
}
if (-not $ready) {
    Write-Host "ERROR: Django did not start in 60 seconds." -ForegroundColor Red
    # Show any errors from the job
    Receive-Job $djangoJob -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "  Django is ready." -ForegroundColor Green

# --- Step 4: Start TCP proxy (background job, no extra window) ---
Write-Host "[4/5] Starting TCP proxy (Windows :$Port -> WSL :$WslPort)..." -ForegroundColor Yellow
$proxyJob = Start-Job -ScriptBlock {
    param($p, $wp)
    python "d:\marathi_tts\marathi_tts_web\tcp_proxy.py" $p $wp
} -ArgumentList $Port, $WslPort
Start-Sleep -Seconds 1

# --- Step 5: Done ---
$url = "http://127.0.0.1:${Port}/marathi_tts/tts/"
Write-Host "[5/5] Server is running!" -ForegroundColor Green
Write-Host ""
Write-Host "  Portal URL:  $url" -ForegroundColor Cyan
Write-Host "  Django:      WSL 0.0.0.0:$WslPort" -ForegroundColor DarkGray
Write-Host "  TCP Proxy:   Windows 127.0.0.1:$Port -> 127.0.0.1:$WslPort" -ForegroundColor DarkGray
Write-Host ""

# Open browser (this is the only thing that should open externally)
Start-Process $url

Write-Host "Press Enter to stop all services..." -ForegroundColor DarkGray
Read-Host

# Cleanup — stop background jobs and WSL processes
Write-Host "Stopping services..." -ForegroundColor Yellow
Stop-Job $djangoJob  -ErrorAction SilentlyContinue
Stop-Job $proxyJob   -ErrorAction SilentlyContinue
Remove-Job $djangoJob -Force -ErrorAction SilentlyContinue
Remove-Job $proxyJob  -Force -ErrorAction SilentlyContinue
wsl -d Ubuntu-22.04 -e bash -c "pkill -f 'manage.py runserver' 2>/dev/null"
Get-Process python -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'tcp_proxy' } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "All services stopped." -ForegroundColor Yellow
