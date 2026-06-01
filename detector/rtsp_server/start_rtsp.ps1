# Flame Scope - RTSP stream launcher
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start_rtsp.ps1 -RtspPort 8554 -HlsPort 8888

param(
    [int]$WebcamIndex = 0,
    [string]$WebcamName = "",
    [int]$Bitrate = 800,
    [int]$Width = 1280,
    [int]$Height = 720,
    [int]$Fps = 30,
    [int]$RtspPort = 8554,
    [int]$HlsPort = 8888,
    [switch]$Background
)

$ErrorActionPreference = "Stop"

$installDir = Join-Path $env:USERPROFILE "flamescope-rtsp"
$mediamtxExe = Join-Path $installDir "mediamtx\mediamtx.exe"
$mediamtxCfg = Join-Path $installDir "mediamtx\mediamtx.yml"
$ffmpegExe = Join-Path $installDir "ffmpeg\bin\ffmpeg.exe"

if (-not (Test-Path $mediamtxExe)) {
    Write-Host "[ERROR] MediaMTX not found. Run setup_rtsp_server.ps1 first." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $ffmpegExe)) {
    Write-Host "[ERROR] FFmpeg not found. Run setup_rtsp_server.ps1 first." -ForegroundColor Red
    exit 1
}

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
  lobby:
    source: publisher
  outdoor:
    source: publisher
"@
$configContent | Out-File -FilePath $mediamtxCfg -Encoding UTF8

$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notlike "*Loopback*" -and
    $_.InterfaceAlias -notlike "*Virtual*" -and
    $_.InterfaceAlias -notlike "*WSL*" -and
    $_.IPAddress -notlike "169.*"
} | Select-Object -First 1).IPAddress

if (-not $localIP) {
    $localIP = "127.0.0.1"
}

if (-not $WebcamName) {
    try {
        $WebcamName = (Get-PnpDevice -Class Camera -Status OK 2>$null | Select-Object -First 1).FriendlyName
    } catch {}
}

$cameraInput = if ($WebcamName) { "video=$WebcamName" } else { "video=@device_idx_$WebcamIndex" }
$cameraInputArg = if ($WebcamName) { "`"video=$WebcamName`"" } else { "video=@device_idx_$WebcamIndex" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Flame Scope - RTSP Stream" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  IP        : $localIP" -ForegroundColor Yellow
Write-Host "  Camera    : $cameraInput" -ForegroundColor Yellow
Write-Host "  RTSP URL  : rtsp://${localIP}:$RtspPort/webcam" -ForegroundColor Green
Write-Host "  HLS URL   : http://${localIP}:$HlsPort/webcam" -ForegroundColor Green
Write-Host "  Video     : ${Width}x${Height} @ ${Fps}fps, ${Bitrate}kbps" -ForegroundColor Gray
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$existingRtsp = Get-NetTCPConnection -LocalPort $RtspPort -State Listen -ErrorAction SilentlyContinue
if ($existingRtsp) {
    Write-Host "[ERROR] RTSP port $RtspPort is already in use." -ForegroundColor Red
    $existingRtsp | Select-Object LocalAddress,LocalPort,OwningProcess
    exit 1
}

$existingHls = Get-NetTCPConnection -LocalPort $HlsPort -State Listen -ErrorAction SilentlyContinue
if ($existingHls) {
    Write-Host "[ERROR] HLS port $HlsPort is already in use." -ForegroundColor Red
    $existingHls | Select-Object LocalAddress,LocalPort,OwningProcess
    exit 1
}

$mtxProc = Start-Process -FilePath $mediamtxExe `
    -ArgumentList "`"$mediamtxCfg`"" `
    -PassThru `
    -WindowStyle Hidden
Start-Sleep -Seconds 2

if ($mtxProc.HasExited) {
    Write-Host "[ERROR] MediaMTX failed to start." -ForegroundColor Red
    exit 1
}
Write-Host "[MediaMTX] Running, PID: $($mtxProc.Id)" -ForegroundColor Green

$ffmpegArgs = @(
    "-hide_banner",
    "-loglevel", "warning",
    "-f", "dshow",
    "-vcodec", "mjpeg",
    "-video_size", "${Width}x${Height}",
    "-framerate", "$Fps",
    "-i", $cameraInputArg,
    "-vcodec", "libx264",
    "-preset", "ultrafast",
    "-tune", "zerolatency",
    "-b:v", "${Bitrate}k",
    "-bufsize", "${Bitrate}k",
    "-pix_fmt", "yuv420p",
    "-g", "$($Fps * 2)",
    "-f", "rtsp",
    "-rtsp_transport", "tcp",
    "rtsp://localhost:$RtspPort/webcam"
)

if ($Background) {
    $ffmpegProc = Start-Process -FilePath $ffmpegExe `
        -ArgumentList $ffmpegArgs `
        -PassThru `
        -WindowStyle Hidden
    Start-Sleep -Seconds 2

    if ($ffmpegProc.HasExited) {
        if (-not $mtxProc.HasExited) {
            $mtxProc.Kill()
        }
        Write-Host "[ERROR] FFmpeg failed to start." -ForegroundColor Red
        exit 1
    }

    Write-Host "[FFmpeg] Running, PID: $($ffmpegProc.Id)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Stream is running in background." -ForegroundColor Green
    Write-Host "Stop it with: Stop-Process -Id $($ffmpegProc.Id),$($mtxProc.Id)" -ForegroundColor Gray
    exit 0
}

try {
    & $ffmpegExe @ffmpegArgs
} finally {
    if (-not $mtxProc.HasExited) {
        $mtxProc.Kill()
    }
}
