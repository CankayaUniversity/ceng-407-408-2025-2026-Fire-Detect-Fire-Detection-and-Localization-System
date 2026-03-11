# Flame Scope – Flutter Mobil Uygulama

## Gereksinimler

- **Flutter SDK** yüklü olmalı. [flutter.dev](https://flutter.dev) → indir, PATH’e ekle.
- Kontrol: `flutter doctor`

## Proje nerede?

Flutter projesi bu `mobile/` klasörünün **içinde** olmalı; yani:

- `mobile/pubspec.yaml`
- `mobile/lib/main.dart`

Eğer proje başka bir isimle (örn. `flamescope_app`) duruyorsa, o klasörü `mobile` içine taşıyın veya aşağıdaki komutlarda `mobile` yerine o klasör adını kullanın.

## Çalıştırma

### 1. Klasöre gir

```powershell
cd c:\Users\bulent\Desktop\flamescope-repo\mobile
```

### 2. Bağımlılıkları indir

```powershell
flutter pub get
```

### 3. API adresini ayarla (isteğe bağlı)

Backend farklı bir makinede veya portta çalışıyorsa, uygulama içinde base URL’i değiştir (örn. `lib/core/constants/api.dart` veya `.env` kullanıyorsanız orada). Varsayılan genelde `http://localhost:8000` veya emülatör için `http://10.0.2.2:8000` (Android) / `http://127.0.0.1:8000` (iOS).

### 4. Cihaz / emülatör seç ve çalıştır

```powershell
flutter devices
flutter run
```

Belirli cihaz için:

```powershell
flutter run -d chrome
flutter run -d windows
flutter run -d <device_id>
```

## Özet komutlar (backend açıkken)

```powershell
cd c:\Users\bulent\Desktop\flamescope-repo\mobile
flutter pub get
flutter run
```

## Sorun çıkarsa

- `flutter doctor` ile Flutter kurulumunu kontrol et.
- `pubspec.yaml` bu klasörde yoksa Flutter projesi yanlış yerde; doğru klasöre gidip aynı komutları orada çalıştır.
