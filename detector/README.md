# Flame Scope Detector (MVP)

Python/OpenCV tabanlı basit bir detector servisi.

## Amaç

- Webcam, RTSP veya video dosyasından görüntü almak
- Mock (heuristic) fire detection ile olası yangın tespit etmek
- Yangın tespit edildiğinde backend'e `POST /incidents/detected` çağrısı yapmak
- Aynı kameradan sürekli incident oluşturmamak için cooldown uygulamak
- Snapshot (anlık görüntü) kaydetmek

## Kurulum

```bash
cd detector
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Konfigürasyon

`src/config.py` içinde `Settings` modeli tanımlıdır. Ortam değişkenleri veya `.env` ile override edebilirsin:

- `BACKEND_BASE_URL` (varsayılan: `http://localhost:8000`)
- `DETECTOR_API_KEY` (opsiyonel, backend bunu doğruluyorsa)
- `SNAPSHOT_DIR` (varsayılan: `../snapshots`)
- `PUBLIC_SNAPSHOT_BASE_URL` (opsiyonel, backend statik dosya sunuyorsa)
- `COOLDOWN_SECONDS` (varsayılan: `60`)
- `DETECTOR_CAMERAS` (JSON string, örn: `[{"id":1,"name":"Webcam","source":"0"}]`)

Varsayılan konfigürasyon tek bir webcam kaynağı (`source="0"`) ile çalışır.

## Çalıştırma

```bash
cd detector
.venv\Scripts\activate
python -m src.main
```

Backend zaten `http://localhost:8000` altında çalışıyor olmalıdır (bkz. `../backend`).

## Dosya yapısı

```text
detector/
├── requirements.txt
├── README.md
├── snapshots/               # Kaydedilen jpeg snapshot'lar
└── src/
    ├── __init__.py
    ├── config.py            # Settings + camera list
    ├── stream_reader.py     # OpenCV VideoCapture wrapper
    ├── detector.py          # MockFireDetector (heuristic)
    ├── notifier.py          # BackendNotifier (POST /incidents/detected)
    └── main.py              # Çoklu kamera döngüsü + cooldown
```

## Notlar

- `MockFireDetector` gerçek bir model yerine çok basit bir HSV/renk tabanlı heuristik kullanır. İleride gerçek bir CNN / model ile `detect(frame) -> DetectionResult` arayüzü korunarak değiştirilebilir.
- Cooldown mekanizması kamera başına son incident zamanını hafızada tutar ve belirtilen süre içinde yeni incident göndermeyi engeller.
- Snapshot yolu backend'e `snapshot_url` olarak gönderilir; backend bu alanı sadece göstermek/incelemek için kullanır.

