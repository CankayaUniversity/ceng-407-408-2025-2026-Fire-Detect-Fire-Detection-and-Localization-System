# Flame Scope Backend

FastAPI + SQLAlchemy + JWT. Varsayılan veritabanı **SQLite** (geçici); ileride PostgreSQL'e dönülebilir.

## Kurulum

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Ortam

İsteğe bağlı `.env` (`.env.example` örnek alınabilir):

- Varsayılan: **SQLite** kullanılır (`sqlite+aiosqlite:///./flamescope.db`), ek ayar gerekmez.
- `SECRET_KEY`: JWT imzası (üretimde mutlaka değiştirin).
- İleride PostgreSQL: `DATABASE_URL=postgresql+asyncpg://...` ve `DATABASE_URL_SYNC=postgresql://...` tanımlayın.

## Veritabanı (SQLite)

Ek kurulum yok. İlk çalıştırmada `flamescope.db` oluşturulur (backend klasöründe).

Test verileri (4 kullanıcı + 2 kamera + 2 incident):

```bash
cd backend
python -m scripts.seed_test_data
```

Oluşturulan hesaplar: `admin@flamescope.com` / `Admin123`, `manager@flamescope.com` / `Manager123`, `employee@flamescope.com` / `Employee123`, `fire@flamescope.com` / `Fire123`.

## Backend'i çalıştırma

**Tüm komutlar `backend` klasöründe, sanal ortam aktifken çalıştırılmalı.**

```bash
cd c:\Users\bulent\Desktop\flamescope\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000  
Döküman: http://localhost:8000/docs

## Endpoint özeti

| Method | Path | Açıklama | Yetki |
|--------|------|----------|--------|
| POST | /auth/login | Giriş, token döner | - |
| GET | /me | Giriş yapan kullanıcı | JWT |
| GET | /cameras | Kamera listesi (stream bilgisi role göre) | JWT |
| POST | /cameras | Kamera ekle | ADMIN |
| GET | /incidents | Incident listesi (EMPLOYEE/FIRE_RESPONSE sadece CONFIRMED) | JWT |
| GET | /incidents/{id} | Incident detay | JWT |
| POST | /incidents/detected | Yangın tespit (detector) | X-Detector-API-Key (opsiyonel) |
| POST | /incidents/{id}/confirm | Doğrula | ADMIN, MANAGER |
| POST | /incidents/{id}/dismiss | Reddet | ADMIN, MANAGER |
