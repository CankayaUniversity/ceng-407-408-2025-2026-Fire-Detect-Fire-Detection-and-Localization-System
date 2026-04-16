# ============================================================
# Flame Scope — RTSP Yayın Başlatıcı
# 
# Arkadaşının bilgisayarında çalıştır:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\start_rtsp.ps1
#
# Gereksinim: setup_rtsp_server.ps1 daha önce çalıştırılmış olmalı.
# ============================================================

param(
    [int]$WebcamIndex = 0,
    [int]$Bitrate = 800,    # kbps
    [int]$Width = 1280,
    [int]$Height = 720,
    [int]$Fps = 25
)

$installDir  = "$env:USERPROFILE\flamescope-rtsp"
$mediamtxExe = "$installDir\mediamtx\mediamtx.exe"
$mediamtxCfg = "$installDir\mediamtx\mediamtx.yml"
$ffmpegExe   = "$installDir\ffmpeg\bin\ffmpeg.exe"

if (-not (Test-Path $mediamtxExe)) {
    Write-Host "[HATA] MediaMTX bulunamadi. Once setup_rtsp_server.ps1'i calistir." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $ffmpegExe)) {
    Write-Host "[HATA] FFmpeg bulunamadi. Once setup_rtsp_server.ps1'i calistir." -ForegroundColor Red
    exit 1
}

# ── Yerel IP ─────────────────────────────────────────────────
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notlike "*Loopback*" -and
    $_.InterfaceAlias -notlike "*Virtual*" -and
    $_.InterfaceAlias -notlike "*WSL*" -and
    $_.IPAddress -notlike "169.*"
} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Flame Scope — RTSP Yayini" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  IP         : $localIP" -ForegroundColor Yellow
Write-Host "  RTSP URL   : rtsp://${localIP}:8554/webcam" -ForegroundColor Green
Write-Host "  Cozunurluk : ${Width}x${Height} @ ${Fps}fps  ${Bitrate}kbps" -ForegroundColor Gray
Write-Host ""
Write-Host "  Bu URL'i detector .env dosyasina ekle:" -ForegroundColor Cyan
Write-Host "  DETECTOR_CAMERAS=[{""id"":1,""name"":""Arkadas Kamera"",""source"":""rtsp://${localIP}:8554/webcam""}]" -ForegroundColor White
Write-Host ""
Write-Host "  Durdurmak: Ctrl+C" -ForegroundColor Gray
Write-Host "================================================" -ForegroundColor Cyan

# ── Mevcut webcam'leri listele ────────────────────────────────
Write-Host ""
Write-Host "Mevcut DirectShow kameralari:" -ForegroundColor Yellow
& $ffmpegExe -list_devices true -f dshow -i dummy 2>&1 | Where-Object { $_ -match "video|audio|camera|webcam" }
Write-Host ""

# ── MediaMTX başlat ───────────────────────────────────────────
Write-Host "[1/2] MediaMTX RTSP server baslatiliyor..." -ForegroundColor Yellow
$mtxProc = Start-Process -FilePath $mediamtxExe `
    -ArgumentList $mediamtxCfg `
    -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 2

if ($mtxProc.HasExited) {
    Write-Host "[HATA] MediaMTX baslanamadi!" -ForegroundColor Red
    exit 1
}
Write-Host "  MediaMTX calisiyor (PID: $($mtxProc.Id))" -ForegroundColor Green

# ── FFmpeg: webcam → RTSP ─────────────────────────────────────
Write-Host "[2/2] FFmpeg webcam yayini baslatiliyor..." -ForegroundColor Yellow
Write-Host ""

try {
    # DirectShow: video cihazı index ile
    & $ffmpegExe `
        -f dshow `
        -video_size "${Width}x${Height}" `
        -framerate $Fps `
        -i "video=@device_idx_${WebcamIndex}" `
        -vcodec libx264 `
        -preset ultrafast `
        -tune zerolatency `
        -b:v "${Bitrate}k" `
        -bufsize "${Bitrate}k" `
        -pix_fmt yuv420p `
        -g $($Fps * 2) `
        -f rtsp `
        -rtsp_transport tcp `
        "rtsp://localhost:8554/webcam"
}
catch {
    Write-Host "[bilgi] Index ile baglanti basarisiz, isim ile deneniyor..." -ForegroundColor Yellow
    # Alternatif: ilk bulduğu webcam adıyla dene
    $webcamName = (Get-PnpDevice -Class Camera -Status OK 2>$null | Select-Object -First 1).FriendlyName
    if ($webcamName) {
        Write-Host "  Webcam: $webcamName"
        & $ffmpegExe `
            -f dshow `
            -video_size "${Width}x${Height}" `
            -framerate $Fps `
            -i "video=`"$webcamName`"" `
            -vcodec libx264 `
            -preset ultrafast `
            -tune zerolatency `
            -b:v "${Bitrate}k" `
            -bufsize "${Bitrate}k" `
            -pix_fmt yuv420p `
            -g $($Fps * 2) `
            -f rtsp `
            -rtsp_transport tcp `
            "rtsp://localhost:8554/webcam"
    }
}
finally {
    # Temizlik: MediaMTX'i kapat
    if (-not $mtxProc.HasExited) {
        $mtxProc.Kill()
    }
}
