# Flame Scope – Chat Geçmişi Özeti

Bu dosya, proje geliştirme sürecindeki önemli kararlar ve adımların özetidir. Chat kaybolursa buradan hatırlayabilirsin.

---

## Proje Yapısı

- **backend/** – FastAPI, SQLAlchemy, JWT, SQLite (veya PostgreSQL)
- **detector/** – Python, OpenCV, mock fire detection, backend’e POST /incidents/detected
- **mobile/** – (İsteğe bağlı) Flutter, role-based UI – repodan kaldırıldı

---

## Önemli Kararlar

1. **Veritabanı:** MVP için SQLite; ileride `.env` ile PostgreSQL’e geçilebilir.
2. **Auth:** passlib kaldırıldı, doğrudan **bcrypt** kullanılıyor (72 byte sınırı + truncate).
3. **Roller:** ADMIN, MANAGER, EMPLOYEE, FIRE_RESPONSE_UNIT. Stream yetkisi backend’de; EMPLOYEE/FIRE_RESPONSE_UNIT’e rtsp_url dönülmez.
4. **Detector:** Consecutive frame + cooldown ile duplicate incident azaltıldı; timezone-aware datetime kullanılıyor.

---

## Çalıştırma (PC yeniden açıldığında)

**Backend:**
```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Seed (ilk kez veya DB boşsa):**
```powershell
cd backend
.venv\Scripts\activate
python -m scripts.seed_test_data
```
Hesaplar: admin@flamescope.com / Admin123, manager@flamescope.com / Manager123, vb.

**Detector:**
```powershell
cd detector
.venv\Scripts\activate
python -m src.main
```

---

## GitHub Repo

- **URL:** https://github.com/CankayaUniversity/ceng-407-408-2025-2026-Fire-Detect-Fire-Detection-and-Localization-System
- Proje buraya push edildi; sonradan **mobile** klasörü repodan kaldırıldı (commit: "Remove mobile folder").
- Yerel kopya: `c:\Users\bulent\Desktop\flamescope-repo` (clone edilmiş hali).

---

## Chat’i Kaybetmemek İçin

1. **Bu dosyayı commit et:** Projede `CHAT_GECMISI_OZET.md` olarak duruyor; `git add` + `git commit` + `git push` ile repoda da saklanır.
2. **Cursor chat’i kapatma:** Aynı chat penceresini kapatmazsan geçmiş aynı kalır.
3. **Manuel yedek:** Önemli gördüğün cevapları kopyalayıp proje içinde bir `.md` dosyasına yapıştırabilirsin.
4. **Cursor transcript’ler:** Cursor bazen sohbetleri kendi klasöründe tutar; Cursor ayarlarından veya proje klasöründeki `.cursor` / agent-transcripts benzeri konumlara bakabilirsin.

---

*Son güncelleme: Bu sohbet özeti oluşturuldu.*
