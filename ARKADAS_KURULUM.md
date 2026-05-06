# Arkadaslar Icin Hizli Kurulum

Bu rehber, projeyi temiz bir bilgisayarda yerel demo olarak calistirmak icindir. Gizli dosyalar (`.env`, veritabani, snapshot fotograflari, Firebase admin anahtari, build klasorleri) repoya konmaz; herkes kendi bilgisayarinda olusturur.

## 0. Klasor ve Gereksinimler

Projeyi Turkce karakter veya bosluk olmayan kisa bir yola koyun. OpenCV Windows'ta Turkce karakterli yollara snapshot yazamayabiliyor.

```powershell
C:\Flamescope\FireDetect
```

Gerekenler:

- Python 3.12
- Flutter SDK
- Android SDK
- Git
- Internet baglantisi

PostgreSQL/Docker sart degil. Varsayilan kurulum SQLite kullanir: `backend/flamescope.db`.

## 1. Backend

```powershell
cd "C:\Flamescope\FireDetect\backend"
copy .env.example .env
python -m pip install -r requirements.txt
python -m scripts.seed_test_data
```

Backend'i baslat:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Kontrol:

```text
http://localhost:8000/docs
```

Test kullanicilari:

```text
admin@flamescope.com / Admin123
manager@flamescope.com / Manager123
employee@flamescope.com / Employee123
fire@flamescope.com / Fire123
```

## 2. Bilgisayarin IP Adresini Bul

Fiziksel telefon ayni Wi-Fi/hotspot aginda olacak. Bilgisayarin Wi-Fi IP'sini bul:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
  $_.InterfaceAlias -notlike "*Loopback*" -and
  $_.InterfaceAlias -notlike "*Virtual*" -and
  $_.IPAddress -notlike "169.*"
} | Select-Object IPAddress,InterfaceAlias
```

Ornek IP:

```text
192.168.1.35
```

Asagidaki komutlarda bu IP'yi kendi IP'nizle degistirin.

## 3. Webcam RTSP Yayini

Ilk kez kurulum:

```powershell
cd "C:\Flamescope\FireDetect\detector\rtsp_server"
powershell -ExecutionPolicy Bypass -File .\setup_rtsp_server.ps1
```

Webcam yayinini baslat:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_rtsp.ps1 -RtspPort 8555 -HlsPort 8888 -Background
```

Script ekranda RTSP URL gosterir:

```text
rtsp://<BILGISAYAR_IP>:8555/webcam
```

## 4. Backend Kamera Kaydini Ayarla

Backend acikken yeni bir CMD ac:

```powershell
cd "C:\Flamescope\FireDetect\backend"
python -m scripts.setup_demo_camera --host <BILGISAYAR_IP>
```

Ornek:

```powershell
python -m scripts.setup_demo_camera --host 192.168.1.35
```

## 5. YOLO Detector

Ilk kez:

```powershell
cd "C:\Flamescope\FireDetect\detector"
copy .env.example .env
python -m pip install -r requirements.txt
```

`detector\.env` icinde snapshot URL'sini fiziksel telefon icin bilgisayar IP'sine cek:

```env
PUBLIC_SNAPSHOT_BASE_URL=http://<BILGISAYAR_IP>:8000/snapshots
```

Detector'i baslat:

```powershell
python -m src.main
```

Logda sunlari gormelisiniz:

```text
YOLO detector ready. model=training\best.pt
Detector servisi baslatildi. Backend: http://localhost:8000  Mod: yolo
Kamera baglandi: Bilgisayar Webcam
```

## 6. Mobil APK

Telefon ayni agda olmali. APK build ederken backend IP'sini `--dart-define` ile verin:

```powershell
cd "C:\Flamescope\FireDetect\mobile"
C:\flutter\bin\flutter.bat pub get
C:\flutter\bin\flutter.bat build apk --debug --dart-define=FLAMESCOPE_API_HOST=<BILGISAYAR_IP>
```

Ornek:

```powershell
C:\flutter\bin\flutter.bat build apk --debug --dart-define=FLAMESCOPE_API_HOST=192.168.1.35
```

APK:

```text
C:\Flamescope\FireDetect\mobile\build\app\outputs\flutter-apk\app-debug.apk
```

## 7. Demo Sirasinda Acik Kalacaklar

Uc ayri CMD yeterli:

```powershell
# Backend
cd "C:\Flamescope\FireDetect\backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
# RTSP webcam
cd "C:\Flamescope\FireDetect\detector\rtsp_server"
powershell -ExecutionPolicy Bypass -File .\start_rtsp.ps1 -RtspPort 8555 -HlsPort 8888 -Background
```

```powershell
# YOLO detector
cd "C:\Flamescope\FireDetect\detector"
python -m src.main
```

## 8. Hata Kontrolleri

Snapshot dosyasi olusuyor mu?

```powershell
dir "C:\Flamescope\FireDetect\snapshots"
```

Snapshot tarayicida aciliyor mu?

```text
http://<BILGISAYAR_IP>:8000/snapshots/<DOSYA_ADI>.jpg
```

Kamera kaydi dogru mu?

```powershell
cd "C:\Flamescope\FireDetect\backend"
python -m scripts.setup_demo_camera --host <BILGISAYAR_IP>
```

IP degisirse:

- `setup_demo_camera --host <YENI_IP>` tekrar calistirin.
- APK'yi yeni `--dart-define=FLAMESCOPE_API_HOST=<YENI_IP>` ile tekrar build edin.
- `detector\.env` icindeki `PUBLIC_SNAPSHOT_BASE_URL` hostunu guncelleyin.
