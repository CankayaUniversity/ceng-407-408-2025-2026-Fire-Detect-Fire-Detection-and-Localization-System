# ============================================================
# Flame Scope — RTSP Server Kurulum Scripti (MediaMTX)
# 
# Arkadaşın bilgisayarında çalıştır:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup_rtsp_server.ps1
#
# Bu script:
#   1. MediaMTX (RTSP server) indirir
#   2. FFmpeg indirir (webcam→RTSP streaming için)
#   3. start_rtsp.ps1 scripti oluşturur
#   4. RTSP URL'i gösterir (Flame Scope'a gir)
# ============================================================

$ErrorActionPreference = "Stop"

$installDir = "$env:USERPROFILE\flamescope-rtsp"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Flame Scope — RTSP Server Kurulumu" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. MediaMTX ──────────────────────────────────────────────
$mediamtxUrl = "https://github.com/bluenviron/mediamtx/releases/download/v1.12.3/mediamtx_v1.12.3_windows_amd64.zip"
$mediamtxZip = "$installDir\mediamtx.zip"
$mediamtxDir = "$installDir\mediamtx"

if (-not (Test-Path "$mediamtxDir\mediamtx.exe")) {
    Write-Host "[1/3] MediaMTX indiriliyor..." -ForegroundColor Yellow
    curl.exe -L -o $mediamtxZip $mediamtxUrl
    New-Item -ItemType Directory -Force -Path $mediamtxDir | Out-Null
    Expand-Archive -Path $mediamtxZip -DestinationPath $mediamtxDir -Force
    Remove-Item $mediamtxZip -Force
    Write-Host "  MediaMTX kuruldu: $mediamtxDir" -ForegroundColor Green
} else {
    Write-Host "[1/3] MediaMTX zaten mevcut. Atlanıyor." -ForegroundColor Green
}

# ── 2. FFmpeg ─────────────────────────────────────────────────
$ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$ffmpegZip = "$installDir\ffmpeg.zip"
$ffmpegDir = "$installDir\ffmpeg"

if (-not (Test-Path "$ffmpegDir\bin\ffmpeg.exe")) {
    Write-Host "[2/3] FFmpeg indiriliyor (~80 MB)..." -ForegroundColor Yellow
    curl.exe -L -o $ffmpegZip $ffmpegUrl
    New-Item -ItemType Directory -Force -Path $ffmpegDir | Out-Null
    Write-Host "  FFmpeg ZIP açılıyor..."
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ffmpegZip, $ffmpegDir)
    # FFmpeg zip içinde bir alt klasör var, taşı
    $inner = Get-ChildItem $ffmpegDir -Directory | Select-Object -First 1
    if ($inner -and $inner.Name -ne "bin") {
        Get-ChildItem "$($inner.FullName)" | Move-Item -Destination $ffmpegDir -Force
        Remove-Item $inner.FullName -Recurse -Force
    }
    Remove-Item $ffmpegZip -Force
    Write-Host "  FFmpeg kuruldu: $ffmpegDir" -ForegroundColor Green
} else {
    Write-Host "[2/3] FFmpeg zaten mevcut. Atlanıyor." -ForegroundColor Green
}

# ── 3. MediaMTX config ────────────────────────────────────────
$configContent = @"
# Flame Scope MediaMTX Configuration
# Sadece gerekli ayarlar — webcam RTSP streaming

rtspAddress: :8554
rtpAddress: :8000
rtcpAddress: :8001
hlsAddress: :8888
webrtcAddress: :8889
srtAddress: :8890

logLevel: warn
logDestinations: [stdout]

readTimeout: 10s
writeTimeout: 10s
writeQueueSize: 512

paths:
  webcam:
    # Bu path'e FFmpeg push eder
    source: publisher
"@

$configPath = "$mediamtxDir\mediamtx.yml"
$configContent | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "[3/3] MediaMTX config oluşturuldu." -ForegroundColor Green

# ── 4. Webcam listesi (kullanıcıya göster) ────────────────────
Write-Host ""
Write-Host "Sistemdeki kameralar:" -ForegroundColor Cyan
try {
    $cameras = Get-PnpDevice -Class Camera -Status OK 2>$null
    if ($cameras) {
        $cameras | ForEach-Object { Write-Host "  → $($_.FriendlyName)" }
    }
} catch {
    Write-Host "  (kamera listesi alınamadı, directshow ile deneyecek)"
}

# ── 5. Başlatma scripti ───────────────────────────────────────
$startScript = @"
# Flame Scope — RTSP Yayın Başlatıcı
# Bu scripti arkadaşının bilgisayarında çalıştır.

`$mediamtxExe = "$mediamtxDir\mediamtx.exe"
`$ffmpegExe   = "$ffmpegDir\bin\ffmpeg.exe"
`$configFile  = "$configPath"

# Bilgisayarın yerel IP adresini al
`$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    `$_.InterfaceAlias -notlike "*Loopback*" -and
    `$_.InterfaceAlias -notlike "*Virtual*" -and
    `$_.IPAddress -notlike "169.*"
} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Flame Scope RTSP Server Baslatiliyor" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Yerel IP   : `$localIP" -ForegroundColor Yellow
Write-Host "  RTSP URL   : rtsp://`${localIP}:8554/webcam" -ForegroundColor Green
Write-Host ""
Write-Host "  Bu URL'i Flame Scope detector'a gir:" -ForegroundColor Cyan
Write-Host "  DETECTOR_CAMERAS='[{\"id\":1,\"name\":\"Arkadas Webcam\",\"source\":\"rtsp://`${localIP}:8554/webcam\"}]'" -ForegroundColor White
Write-Host ""
Write-Host "  Durdurmak icin: Ctrl+C" -ForegroundColor Gray
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# MediaMTX'i arka planda başlat
`$mtxJob = Start-Job -ScriptBlock {
    param(`$exe, `$cfg)
    & `$exe `$cfg
} -ArgumentList `$mediamtxExe, `$configFile

Start-Sleep -Seconds 2
Write-Host "[MediaMTX] RTSP server baslatildi (port 8554)" -ForegroundColor Green

# FFmpeg: webcam -> RTSP (index 0 = ilk webcam)
Write-Host "[FFmpeg] Webcam yayini baslatiliyor..." -ForegroundColor Yellow
Write-Host "  (Webcam index 0 kullaniliyor. Farkli webcam icin -i video='Webcam Adi' kullan)"
Write-Host ""

# DirectShow ile webcam al, RTSP'ye push et
& `$ffmpegExe ``
    -f dshow ``
    -i video="@device_pnp_\\\\?\\usb#vid_0000..." ``
    -vcodec libx264 ``
    -preset ultrafast ``
    -tune zerolatency ``
    -b:v 800k ``
    -f rtsp ``
    "rtsp://localhost:8554/webcam"
"@

$startScriptPath = "$installDir\start_rtsp.ps1"
$startScript | Out-File -FilePath $startScriptPath -Encoding UTF8

# ── 6. Webcam adını bul ve start_rtsp.ps1'i güncelle ─────────
$webcamName = ""
try {
    $webcamName = (Get-PnpDevice -Class Camera -Status OK 2>$null | Select-Object -First 1).FriendlyName
} catch {}

if ($webcamName) {
    # start_rtsp.ps1 içindeki placeholder'ı gerçek webcam adıyla değiştir
    (Get-Content $startScriptPath) -replace "@device_pnp_.*\.\.\.", $webcamName | Set-Content $startScriptPath
    (Get-Content $startScriptPath) -replace 'video="@device_pnp_.*?"', "video=`"$webcamName`"" | Set-Content $startScriptPath
    Write-Host ""
    Write-Host "  Tespit edilen webcam: $webcamName" -ForegroundColor Green
}

# ── 7. Son bilgi ──────────────────────────────────────────────
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notlike "*Loopback*" -and
    $_.InterfaceAlias -notlike "*Virtual*" -and
    $_.IPAddress -notlike "169.*"
} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Kurulum tamamlandi!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Sonraki adim — su scripti calistir:" -ForegroundColor Cyan
Write-Host "  .\start_rtsp.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  Tahmini RTSP URL:" -ForegroundColor Cyan
if ($localIP) {
    Write-Host "  rtsp://${localIP}:8554/webcam" -ForegroundColor Green
} else {
    Write-Host "  rtsp://<BILGISAYAR_IP>:8554/webcam" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  Kurulum klasoru: $installDir" -ForegroundColor Gray
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
