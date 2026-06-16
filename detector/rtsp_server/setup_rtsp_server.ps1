# Flame Scope - RTSP server setup (MediaMTX + FFmpeg)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup_rtsp_server.ps1
#
# Installs tools under:
#   %USERPROFILE%\flamescope-rtsp

param(
    [int]$RtspPort = 8554,
    [int]$HlsPort = 8888
)

$ErrorActionPreference = "Stop"

$installDir = Join-Path $env:USERPROFILE "flamescope-rtsp"
$mediamtxDir = Join-Path $installDir "mediamtx"
$ffmpegDir = Join-Path $installDir "ffmpeg"

New-Item -ItemType Directory -Force -Path $installDir | Out-Null

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Flame Scope - RTSP Server Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$mediamtxUrl = "https://github.com/bluenviron/mediamtx/releases/download/v1.12.3/mediamtx_v1.12.3_windows_amd64.zip"
$mediamtxZip = Join-Path $installDir "mediamtx.zip"

if (-not (Test-Path (Join-Path $mediamtxDir "mediamtx.exe"))) {
    Write-Host "[1/3] Downloading MediaMTX..." -ForegroundColor Yellow
    curl.exe -L -o $mediamtxZip $mediamtxUrl
    New-Item -ItemType Directory -Force -Path $mediamtxDir | Out-Null
    Expand-Archive -Path $mediamtxZip -DestinationPath $mediamtxDir -Force
    Remove-Item $mediamtxZip -Force
    Write-Host "  MediaMTX installed: $mediamtxDir" -ForegroundColor Green
} else {
    Write-Host "[1/3] MediaMTX already installed." -ForegroundColor Green
}

$ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$ffmpegZip = Join-Path $installDir "ffmpeg.zip"

if (-not (Test-Path (Join-Path $ffmpegDir "bin\ffmpeg.exe"))) {
    Write-Host "[2/3] Downloading FFmpeg..." -ForegroundColor Yellow
    curl.exe -L -o $ffmpegZip $ffmpegUrl
    New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ffmpegZip, $ffmpegDir)

    $inner = Get-ChildItem $ffmpegDir -Directory | Select-Object -First 1
    if ($inner -and $inner.Name -ne "bin") {
        Get-ChildItem $inner.FullName | Move-Item -Destination $ffmpegDir -Force
        Remove-Item $inner.FullName -Recurse -Force
    }

    Remove-Item $ffmpegZip -Force
    Write-Host "  FFmpeg installed: $ffmpegDir" -ForegroundColor Green
} else {
    Write-Host "[2/3] FFmpeg already installed." -ForegroundColor Green
}

$configPath = Join-Path $mediamtxDir "mediamtx.yml"
$configContent = @"
# Flame Scope MediaMTX configuration

rtspAddress: :$RtspPort
rtpAddress: :8000
rtcpAddress: :8001
hlsAddress: :$HlsPort
webrtcAddress: :8889
srtAddress: :8890

logLevel: warn
logDestinations: [stdout]

readTimeout: 10s
writeTimeout: 10s
writeQueueSize: 512

paths:
  webcam:
    source: publisher
"@

$configContent | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "[3/3] MediaMTX config written: $configPath" -ForegroundColor Green

$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notlike "*Loopback*" -and
    $_.InterfaceAlias -notlike "*Virtual*" -and
    $_.InterfaceAlias -notlike "*WSL*" -and
    $_.IPAddress -notlike "169.*"
} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "Available cameras:" -ForegroundColor Cyan
try {
    $cameras = Get-PnpDevice -Class Camera -Status OK 2>$null
    if ($cameras) {
        $cameras | ForEach-Object { Write-Host "  - $($_.FriendlyName)" }
    } else {
        Write-Host "  No PnP camera found. FFmpeg DirectShow listing may still find one."
    }
} catch {
    Write-Host "  Camera list could not be read."
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Setup complete" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Start stream:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\start_rtsp.ps1 -RtspPort $RtspPort -HlsPort $HlsPort" -ForegroundColor White
Write-Host ""
if ($localIP) {
    Write-Host "  RTSP URL: rtsp://${localIP}:$RtspPort/webcam" -ForegroundColor Green
    Write-Host "  HLS URL : http://${localIP}:$HlsPort/webcam" -ForegroundColor Green
} else {
    Write-Host "  RTSP URL: rtsp://<PC_IP>:$RtspPort/webcam" -ForegroundColor Yellow
    Write-Host "  HLS URL : http://<PC_IP>:$HlsPort/webcam" -ForegroundColor Yellow
}
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
