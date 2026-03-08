# Flame Scope — Proje Mimarisi

Bu doküman, IP kamera yangın tespiti, olay yönetimi ve acil bildirim sistemi için önerilen klasör yapısı ve geliştirme sırasını açıklar.

---

## 1. Genel Mimari

```
flamescope/
├── backend/          # FastAPI REST API + WebSocket (stream yetkisi burada)
├── detector/         # Python: kamera okuma + OpenCV yangın tespiti
├── mobile/           # Flutter uygulama (admin/manager/employee/fire_response_unit)
├── docker-compose.yml
└── ARCHITECTURE.md
```

**Veri akışı (özet):**
- Kameralar → **detector** (RTSP/HTTP) → yangın tespiti → **backend** (incident oluşturma)
- **Backend** → JWT, roller, stream yetkisi, incident CRUD, bildirim tetikleme
- **Mobile** → Backend API + (gerekirse) push/WebSocket ile bildirim

---

## 2. Backend (FastAPI) Klasör Yapısı

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, CORS, router mount
│   ├── config.py               # Pydantic Settings (DB, JWT secret, detector URL)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # get_current_user, require_roles, get_db
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # tüm v1 router'ları toplar
│   │   │   ├── auth.py          # login, refresh, me
│   │   │   ├── users.py         # CRUD (admin), list
│   │   │   ├── cameras.py      # CRUD kameralar, list
│   │   │   ├── incidents.py    # list, get, confirm, false_alarm (manager)
│   │   │   ├── stream.py       # stream URL/token (yetki: admin her zaman, manager sadece aktif incident)
│   │   │   └── notifications.py # kullanıcının bildirimleri (employee, fire_response_unit)
│   │   └── webhooks.py         # detector’dan gelen yangın tespit webhook (internal)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py          # JWT create/verify, password hash
│   │   └── permissions.py      # role checks, stream permission logic
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User, Role enum
│   │   ├── camera.py            # Camera
│   │   ├── incident.py          # Incident (status: DETECTED, CONFIRMED, FALSE_ALARM)
│   │   └── notification.py     # Notification (user_id, incident_id, read)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── camera.py
│   │   ├── incident.py
│   │   └── notification.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── incident_service.py  # create_incident (webhook), confirm, false_alarm, notify
│   │   ├── notification_service.py  # push/email veya in-app; employee + fire_response_unit
│   │   └── stream_service.py    # stream yetki: admin vs manager (aktif incident)
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py           # AsyncSession, engine, get_db
│   │   └── base.py              # Base, metadata
│   │
│   └── migrations/             # Alembic
│       └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_incidents.py
│   └── test_stream_permissions.py
│
├── requirements.txt
├── Dockerfile
└── alembic.ini
```

**Önemli noktalar:**
- **Stream yetkisi:** `stream_service` veya `permissions.py` içinde: ADMIN → her zaman; MANAGER → sadece ilgili kamera için açık (DETECTED/CONFIRMED) incident varsa; EMPLOYEE/FIRE_RESPONSE_UNIT → 403.
- **Webhook:** Detector yangın tespit edince `POST /api/webhooks/fire-detected` gibi bir endpoint’e camera_id, snapshot_url, confidence gönderir; backend incident oluşturur (DETECTED).
- **Bildirim:** Manager CONFIRMED yaptığında `notification_service` ile Employee ve FireResponseUnit kullanıcılarına kayıt oluşturulur (ve gerekirse FCM/APNs entegrasyonu).

---

## 3. Detector (Python / OpenCV) Klasör Yapısı

```
detector/
├── src/
│   ├── __init__.py
│   ├── main.py                 # entry: config yükle, kamera listesi al (backend’den veya env), loop
│   ├── config.py               # BACKEND_URL, WEBHOOK_PATH, kamera kaynakları (RTSP/HTTP)
│   │
│   ├── capture/
│   │   ├── __init__.py
│   │   └── reader.py           # Kamera okuma (OpenCV VideoCapture), frame döndür
│   │
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── fire_detector.py    # OpenCV/renk + (isteğe) basit model; True/False + confidence
│   │   └── pipeline.py         # frame → fire_detector → yangın varsa backend’e webhook
│   │
│   └── client/
│       ├── __init__.py
│       └── backend_client.py   # HTTP client: get cameras, POST fire-detected (camera_id, frame/snapshot, confidence)
│
├── tests/
│   └── test_fire_detector.py
│
├── requirements.txt            # opencv-python, requests, pydantic
└── Dockerfile
```

**Akış:**
1. Backend’den (veya config’den) kamera listesi alınır (url, camera_id).
2. Her kamera için ayrı thread/process veya async loop ile frame alınır.
3. Her frame (veya N frame’de bir) `fire_detector` ile taranır.
4. Tespit varsa cooldown ile (aynı kamera için kısa sürede tekrar webhook atmamak) `backend_client.post_fire_detected(...)` çağrılır.

---

## 4. Mobile (Flutter) Klasör Yapısı

```
mobile/
├── lib/
│   ├── main.dart
│   ├── app.dart                # MaterialApp, theme, routes
│   │
│   ├── core/
│   │   ├── constants/
│   │   │   ├── api.dart        # base URL, endpoints
│   │   │   └── roles.dart      # role string’leri
│   │   ├── theme/
│   │   │   └── app_theme.dart
│   │   ├── router/
│   │   │   └── app_router.dart # go_router: login, role-based home, incident, stream, notifications
│   │   └── utils/
│   │       └── permission_utils.dart  # stream gösterilir mi (role + incident)
│   │
│   ├── data/
│   │   ├── api/
│   │   │   ├── api_client.dart     # Dio/http, interceptors (JWT)
│   │   │   ├── auth_api.dart
│   │   │   ├── cameras_api.dart
│   │   │   ├── incidents_api.dart
│   │   │   ├── stream_api.dart
│   │   │   └── notifications_api.dart
│   │   ├── models/
│   │   │   ├── user.dart
│   │   │   ├── camera.dart
│   │   │   ├── incident.dart
│   │   │   └── notification.dart
│   │   └── repositories/
│   │       ├── auth_repository.dart
│   │       ├── incident_repository.dart
│   │       └── notification_repository.dart
│   │
│   ├── domain/
│   │   └── entities/           # (isteğe) domain modelleri
│   │
│   ├── features/
│   │   ├── auth/
│   │   │   ├── login_screen.dart
│   │   │   └── ...
│   │   ├── home/
│   │   │   └── home_screen.dart   # role’e göre: admin dashboard, manager incidents, employee bilgi
│   │   ├── cameras/                # admin: list, add, edit
│   │   │   ├── camera_list_screen.dart
│   │   │   └── camera_form_screen.dart
│   │   ├── incidents/              # manager: list, detail, confirm/false_alarm
│   │   │   ├── incident_list_screen.dart
│   │   │   ├── incident_detail_screen.dart
│   │   │   └── (stream bu incident’e bağlı açılır)
│   │   ├── stream/                 # canlı görüntü (yetki kontrolü backend’de)
│   │   │   └── stream_screen.dart  # incident_id veya camera_id ile
│   │   ├── notifications/         # employee, fire_response_unit: liste, kaçış talimatları
│   │   │   ├── notification_list_screen.dart
│   │   │   └── notification_detail_screen.dart
│   │   └── fire_info/              # fire_response_unit: aktif yangın özeti
│   │       └── active_fires_screen.dart
│   │
│   └── shared/
│       ├── widgets/
│       │   ├── role_guard.dart      # role’e göre widget gösterme
│       │   └── loading_error.dart
│       └── providers/              # (Riverpod/Provider) auth, incidents, notifications
│
├── test/
├── pubspec.yaml
└── README.md
```

**Yetki özeti (UI):**
- **ADMIN:** Kamera yönetimi, tüm incident’ler, her zaman stream linki.
- **MANAGER:** Incident listesi → detay → “Canlı izle” (sadece o incident açıkken), Confirm / False alarm.
- **EMPLOYEE:** Sadece bildirimler ve kaçış talimatları; stream menüde yok.
- **FIRE_RESPONSE_UNIT:** Bildirimler + aktif yangın bilgisi; stream yok.

---

## 5. Geliştirme Sırası (Önerilen)

Aşamaları bağımsız modüller halinde ilerletmek için aşağıdaki sıra önerilir.

### Faz 1 — Backend temel
1. **Proje iskeleti:** `backend/` klasörü, `main.py`, `config.py`, `requirements.txt`.
2. **Veritabanı:** PostgreSQL, SQLAlchemy modelleri (User, Role enum, Camera, Incident, Notification), Alembic ilk migration.
3. **Auth:** JWT (access + refresh), login/refresh/me, `deps.py` (get_current_user, require_roles).
4. **Kullanıcı ve kamera CRUD:** Sadece ADMIN; users ve cameras endpoint’leri.

Bu fazda backend’i Postman/curl ile test edebilirsin.

### Faz 2 — Incident ve yetkiler
5. **Incident modeli ve API:** Status (DETECTED, CONFIRMED, FALSE_ALARM), manager’ın list/get/confirm/false_alarm.
6. **Webhook:** Detector’dan gelecek yangın tespit endpoint’i; incident oluşturma (DETECTED).
7. **Stream yetki servisi:** `stream_service` + endpoint: ADMIN her zaman izin; MANAGER sadece ilgili kamera için açık incident varken; diğer roller 403.
8. **Bildirim servisi:** Manager CONFIRMED yaptığında Employee ve FireResponseUnit için notification kaydı (in-app); isteğe FCM/APNs sonra eklenir.

### Faz 3 — Detector
9. **Detector iskeleti:** `config`, `backend_client` (kamera listesi + fire-detected webhook).
10. **Kamera okuma:** OpenCV ile tek bir RTSP/HTTP kaynağından frame alma.
11. **Yangın tespiti:** Basit renk/parlama kuralları veya küçük bir model; threshold ve cooldown.
12. **Çoklu kamera ve loop:** Backend’den kamera listesi alıp sırayla veya paralel işleme.

### Faz 4 — Mobil uygulama
13. **Flutter projesi ve API katmanı:** Dio, JWT interceptor, auth/cameras/incidents/stream/notifications API sınıfları.
14. **Auth ekranı ve token saklama:** Login, refresh, role’e göre yönlendirme.
15. **Admin:** Kamera listesi ve CRUD ekranları; stream’e her zaman erişim.
16. **Manager:** Incident listesi, detay, confirm/false alarm, “Canlı izle” butonu (stream yetkisi backend’de).
17. **Employee / Fire response unit:** Bildirim listesi, detay (kaçış talimatları); fire_response_unit için aktif yangın özeti.
18. **Stream ekranı:** Backend’den aldığın stream URL/token ile canlı görüntü (WebView veya video player).

### Faz 5 — Entegrasyon ve iyileştirmeler
19. **Docker:** backend, detector, PostgreSQL (ve isteğe Redis) için Dockerfile ve docker-compose.
20. **Push bildirimleri:** FCM/APNs entegrasyonu (backend’de tetikleme, mobilde token ve dinleyici).
21. **Test ve dokümantasyon:** API testleri, detector birim testleri, README ve ARCHITECTURE güncellemesi.

---

## 6. Özet Tablo

| Bileşen   | Teknoloji   | Sorumluluk |
|----------|-------------|-------------|
| Backend  | FastAPI     | Auth (JWT), roller, kamera/incident/notification CRUD, stream yetkisi, webhook, bildirim tetikleme |
| Detector | Python/OpenCV | Kamera okuma, yangın tespiti, backend’e fire-detected webhook |
| Mobile   | Flutter     | Role-based UI: admin (kameralar + stream), manager (incident + stream), employee/fire_response_unit (bildirimler) |
| DB       | PostgreSQL  | Users, cameras, incidents, notifications |

Bu yapı ile backend tek doğruluk kaynağı (stream yetkisi dahil) olur; detector sadece tespit ve webhook; mobil ise rolüne göre sadece erişebildiği API’leri kullanır.
