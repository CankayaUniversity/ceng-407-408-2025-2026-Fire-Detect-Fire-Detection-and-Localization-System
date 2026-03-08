# Flame Scope Mobile

Role-based Flutter uygulaması. Backend: FastAPI (bkz. `../backend`).

## Gereksinimler

- Flutter SDK (PATH'ta)
- Backend çalışır durumda (varsayılan: `http://10.0.2.2:8000` emülatör için)

## Kurulum

```bash
cd mobile
flutter pub get
```

Platform klasörleri yoksa (ilk kez):

```bash
flutter create . --project-name flamescope
```

## Çalıştırma

```bash
flutter run
```

## API adresi

Emülatör: `lib/core/constants/api_constants.dart` içinde `kBaseUrl = 'http://10.0.2.2:8000'`.  
Fiziksel cihaz: Bilgisayarın yerel IP'si (örn. `http://192.168.1.10:8000`).

## Klasör yapısı

```
lib/
├── main.dart
├── core/
│   ├── api/           # Dio client
│   ├── auth/          # AuthService, token
│   ├── constants/     # API URL, roller, storage keys
│   ├── router/        # go_router, role-based redirect
│   └── theme/
├── features/
│   ├── auth/          # Login, Splash
│   ├── home/          # Admin, Manager, Employee, FireResponse home
│   ├── incidents/     # List, Detail (confirm/dismiss)
│   ├── cameras/       # Camera list (admin)
│   ├── stream/        # Live stream (admin/manager)
│   └── emergency/     # Acil durum bildirimleri
└── shared/
    └── models/        # User, Camera, Incident
```

## Roller

- **ADMIN:** Kameralar, incident listesi, canlı yayın.
- **MANAGER:** Incident listesi, detayda doğrula/reddet, ilgili incident için canlı yayın.
- **EMPLOYEE / FIRE_RESPONSE_UNIT:** Sadece acil durum bildirimleri (canlı yayın yok).
