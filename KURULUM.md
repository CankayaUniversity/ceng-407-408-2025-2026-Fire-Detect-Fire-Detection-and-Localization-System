# Yerel çalıştırma (hızlı rehber)

Projeyi klonladıktan sonra backend + PostgreSQL + (isteğe bağlı) Flutter mobil ile ayağa kaldırmak için özet adımlar.

## Gereksinimler

- Docker Desktop (PostgreSQL için)
- Python **3.12** (Windows’ta `python` bazen MSYS’yi gösterir; tam yol veya `py -3.12` kullanın)
- Flutter SDK + Android SDK (mobil için)

## 1. Veritabanı (Docker)

Depo kökünde:

```powershell
docker compose up -d
```

`localhost:5432`, kullanıcı/şifre/DB: `postgres` / `postgres` / `flamescope` (`docker-compose.yml` ile uyumlu).

## 2. Backend

```powershell
cd backend
copy .env.example .env
```

`.env` içinde **SQLite değil**, PostgreSQL satırlarını kullanın:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flamescope
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/flamescope
SECRET_KEY=uretim-disi-guclu-bir-deger
```

İsteğe bağlı: `backend` klasörüne Firebase Admin JSON dosyasını `firebase-adminsdk.json` adıyla koyun (push bildirimleri). Bu dosya `.gitignore` içindedir, repoya eklemeyin.

Bağımlılık ve sunucu:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

İlk çalıştırmada tablolar oluşur. Test verisi için **yeni bir terminal**:

```powershell
cd backend
python -m scripts.seed_test_data
```

API: `http://localhost:8000/docs` — örnek giriş: `admin@flamescope.com` / `Admin123`.

### Detector webhook (PowerShell, UTF-8 gövde)

`DETECTOR_API_KEY` tanımlıysa aşağıdaki `$headers` satırını ekleyin.

```powershell
cd backend
$body = '{"camera_id":1,"confidence":0.95,"snapshot_url":"test.jpg"}'
Invoke-RestMethod -Uri "http://localhost:8000/incidents/detected" -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

## 3. Flutter mobil

```powershell
cd mobile
flutter pub get
```

`lib/core/constants/api_constants.dart` içinde **`kLanIp`**: Android emülatörde `10.0.2.2`, fiziksel telefonda bilgisayarın yerel IP’si.

```powershell
flutter devices
flutter run -d <cihaz_id>
```

Android derlemesi için `android/app/build.gradle.kts` içinde NDK 27, `minSdk >= 23`, core library desugaring ayarlıdır; ilk derleme uzun sürebilir.

Detay: `backend/README.md`, `mobile/README.md`, `ARCHITECTURE.md`.
