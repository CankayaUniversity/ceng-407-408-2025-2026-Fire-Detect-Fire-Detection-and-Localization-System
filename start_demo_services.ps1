param(
    [string]$Root = "C:\Flamescope\FireDetect"
)

$ErrorActionPreference = "Stop"

$LogDir = Join-Path $Root ".codex-runtime-logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Start-DemoProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$LogName
    )

    $out = Join-Path $LogDir "$LogName.out.log"
    $err = Join-Path $LogDir "$LogName.err.log"
    $process = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $out `
        -RedirectStandardError $err `
        -WindowStyle Hidden `
        -PassThru
    Write-Host "$Name started. PID=$($process.Id)"
}

Write-Host "Starting FlameScope demo services..."

Start-DemoProcess `
    -Name "Backend" `
    -FilePath "python" `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000") `
    -WorkingDirectory (Join-Path $Root "backend") `
    -LogName "backend"

Start-Sleep -Seconds 3

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Write-Host "Backend health check OK."
} catch {
    Write-Host "Backend health check did not respond yet. Check $LogDir\backend.err.log if it stays down."
}

Write-Host "Starting RTSP/HLS webcam bridge..."
& powershell -ExecutionPolicy Bypass -File (Join-Path $Root "detector\rtsp_server\start_rtsp.ps1") -RtspPort 8555 -HlsPort 8888 -Background

Start-Sleep -Seconds 3

Write-Host "Configuring Computer Webcam stream for detector..."
Push-Location (Join-Path $Root "backend")
python -m scripts.setup_demo_camera --rtsp-url "rtsp://127.0.0.1:8555/webcam"
Pop-Location

Start-DemoProcess `
    -Name "Detector" `
    -FilePath "python" `
    -ArgumentList @("-m", "src.main") `
    -WorkingDirectory (Join-Path $Root "detector") `
    -LogName "detector"

Write-Host ""
Write-Host "Ready for demo:"
Write-Host "Backend docs: http://localhost:8000/docs"
Write-Host "Webcam HLS:   http://127.0.0.1:8888/webcam/index.m3u8"
Write-Host "Emulator API host should be: 10.0.2.2"
Write-Host "Logs: $LogDir"
