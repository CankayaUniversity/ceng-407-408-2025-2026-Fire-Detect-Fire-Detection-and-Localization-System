# Flame Scope — Model Eğitimi ve RTSP Test Kılavuzu

Bu kılavuz, gerçek yangın tespit modelini eğitmek ve arkadaşının webcam'ini RTSP kameraya dönüştürerek test etmek için adım adım rehberdir.

---

## İçindekiler
1. [Genel Akış](#1-genel-akış)
2. [Dataset Hazırlama](#2-dataset-hazırlama)
3. [Model Eğitimi](#3-model-eğitimi)
4. [Detector'ı CNN Moda Geçirme](#4-detectori-cnn-moda-geçirme)
5. [RTSP Test Kamerası (Arkadaş Webcam)](#5-rtsp-test-kamerası)
6. [Eğitim Parametreleri](#6-eğitim-parametreleri)
7. [Sorun Giderme](#7-sorun-giderme)

---

## 1. Genel Akış

```
Dataset İndir/Hazırla
        ↓
  Model Eğit (30-50 epoch)
        ↓
  fire_model.pt + fire_model.json
        ↓
  .env → DETECTOR_MODE=cnn + CNN_MODEL_PATH
        ↓
  Arkadaş: start_rtsp.ps1 çalıştır (RTSP URL al)
        ↓
  .env → DETECTOR_CAMERAS=[{..., "source":"rtsp://..."}]
        ↓
  python -m src.main  →  backend'e incident POST
```

---

## 2. Dataset Hazırlama

### Seçenek A — Otomatik (Kaggle)

```powershell
# 1. Kaggle API kurulumu
pip install kaggle

# 2. Kaggle token: https://www.kaggle.com → Account → API → Create New API Token
#    İndirilen kaggle.json'u buraya koy:
mkdir "$env:USERPROFILE\.kaggle"
copy kaggle.json "$env:USERPROFILE\.kaggle\kaggle.json"

# 3. Dataset indir ve hazırla
cd detector
python -m training.prepare_dataset --out training/dataset
```

İndirilecek datasetler:
- **phylake1337/fire-dataset** — ~755 fire, ~244 non_fire
- **crowdwork365/fire-vs-no-fire** — ~1800 fire, ~1800 non_fire

### Seçenek B — Manuel indirme

1. https://www.kaggle.com/datasets/phylake1337/fire-dataset → Download
2. ZIP'i aç → `fire_images/` ve `non_fire_images/` klasörleri çıkar

```powershell
cd detector
python -m training.prepare_dataset `
  --extra-fire    C:\path\to\fire_images `
  --extra-no-fire C:\path\to\non_fire_images `
  --skip-kaggle
```

### Seçenek C — D-Fire (En kapsamlı, ~42k görüntü)

```powershell
git clone https://github.com/gaiasd/DFireDataset.git
cd detector
python -m training.prepare_dataset `
  --extra-fire    ..\DFireDataset\train\fire `
  --extra-no-fire ..\DFireDataset\train\no_fire `
  --skip-kaggle
```

### Seçenek D — Kendi videondan frame çıkar

```powershell
cd detector

# Yangın videosundan (her 5 frame'de 1 kaydet)
python -m training.extract_frames `
  --video fire_video.mp4 `
  --out training/dataset/train/fire `
  --label fire --every 5

# Normal ortam videosundan
python -m training.extract_frames `
  --video normal_video.mp4 `
  --out training/dataset/train/no_fire `
  --label no_fire --every 10

# Canlı RTSP kameradan kayıt (60 saniyelik)
python -m training.extract_frames `
  --rtsp rtsp://192.168.1.10:8554/webcam `
  --out training/dataset/train/fire `
  --label fire --every 3 --duration 60
```

### Beklenen klasör yapısı

```
detector/training/dataset/
├── train/
│   ├── fire/       ← en az 500 görüntü önerilir
│   └── no_fire/    ← en az 500 görüntü önerilir
└── val/
    ├── fire/       ← ~100+ görüntü
    └── no_fire/    ← ~100+ görüntü
```

---

## 3. Model Eğitimi

### Gereksinimler

```powershell
cd detector
pip install torch torchvision  # CPU için yeterli
# veya CUDA için: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Eğitim başlat

```powershell
cd detector

# Temel (CPU, 30 epoch)
python -m training.train_fire_model --data-dir training/dataset --epochs 30

# Önerilen (2 aşamalı fine-tuning)
python -m training.train_fire_model `
  --data-dir training/dataset `
  --epochs 40 `
  --stage1-epochs 12 `
  --batch-size 32 `
  --output training/fire_model.pt

# GPU varsa
python -m training.train_fire_model `
  --data-dir training/dataset `
  --epochs 40 `
  --device cuda `
  --batch-size 64
```

### Eğitim çıktısı

```
detector/training/
├── fire_model.pt    ← model ağırlıkları
└── fire_model.json  ← metadata (threshold, val_f1, val_recall ...)
```

`fire_model.json` örneği:
```json
{
  "epoch": 35,
  "stage": 2,
  "val_f1": 0.9421,
  "val_recall": 0.9312,
  "val_acc": 0.9487,
  "recommended_threshold": 0.54,
  "fire_class_index": 1
}
```

### Ne zaman yeterli?

| Metrik | Minimum | İyi | Çok iyi |
|--------|---------|-----|---------|
| val_recall (yangın yakalama) | 0.85 | 0.92 | 0.97 |
| val_precision (false alarm) | 0.80 | 0.90 | 0.95 |
| val_f1 | 0.82 | 0.91 | 0.96 |

> Yangın sistemi için **recall önceliklidir** — yangını kaçırmak, yanlış alarm vermekten tehlikelidir.

---

## 4. Detector'ı CNN Moda Geçirme

```powershell
# detector/.env dosyası oluştur (yoksa)
cd detector
copy .env.example .env
```

`.env` içini düzenle:
```env
DETECTOR_MODE=cnn
CNN_MODEL_PATH=training/fire_model.pt
DETECTION_CONSECUTIVE_FRAMES=3
COOLDOWN_SECONDS=30

# Kamera (önce yerel webcam ile test et)
DETECTOR_CAMERAS=[{"id":1,"name":"Test","source":"0"}]
```

Test çalıştır:
```powershell
cd detector
python -m src.main
```

## 4.5. Modeli Test Dataseti Üzerinde Değerlendirme

Ayrı bir test split ile modelin false positive / false negative davranışını
ölçmek için şu yapıyı kullan:

```text
detector/training/dataset/
├── train/
├── val/
└── test/
    ├── fire/
    └── no_fire/
```

Değerlendirme script'i runtime'daki `CNNFireDetector` akışını kullanır.
Yani karanlık-frame filtresi ve HSV ön filtresi de sonuca dahildir.

```powershell
cd detector

# Ayrı test split varsa (önerilen)
python -m training.evaluate_fire_model `
  --data-dir training/dataset `
  --split test `
  --model-path training/fire_model.pt

# Henüz test split yoksa geçici olarak val split üzerinde
python -m training.evaluate_fire_model `
  --data-dir training/dataset `
  --split val `
  --model-path training/fire_model.pt
```

Threshold override örneği:

```powershell
python -m training.evaluate_fire_model `
  --data-dir training/dataset `
  --split test `
  --model-path training/fire_model.pt `
  --threshold 0.50
```

Script şunları raporlar:
- confusion matrix (`TP`, `FP`, `TN`, `FN`)
- accuracy / precision / recall / F1
- threshold sweep sonucu
- false positive ve false negative örnekleri
- HSV / dark-frame prefilter diagnostics

JSON raporu varsayılan olarak buraya yazar:

```text
training/dataset/<split>/evaluation_report.json
```

---

## 5. RTSP Test Kamerası

### Arkadaşının bilgisayarında (Windows)

```powershell
# 1. Kurulum scriptini indir/kopyala
#    detector/rtsp_server/setup_rtsp_server.ps1

# 2. PowerShell'i aç, scripti çalıştır:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_rtsp_server.ps1

# 3. Kurulum bittikten sonra yayını başlat:
.\start_rtsp.ps1

# Çıktıda şu görünür:
#   RTSP URL : rtsp://192.168.1.XXX:8554/webcam
```

### Senin bilgisayarında (Flame Scope detector)

`.env` dosyasını güncelle:
```env
DETECTOR_CAMERAS=[{"id":1,"name":"Arkadas Kamera","source":"rtsp://192.168.1.XXX:8554/webcam"}]
```

> ⚠️ IP adresini `start_rtsp.ps1` çıktısından al. Aynı ağda (Wi-Fi/ethernet) olmanız gerekir.

### Bağlantı testi

```powershell
# OpenCV ile test (Python):
cd detector
python -c "
import cv2
cap = cv2.VideoCapture('rtsp://192.168.1.XXX:8554/webcam')
ok, f = cap.read()
print('Bağlantı:', 'BAŞARILI' if ok else 'BAŞARISIZ', f.shape if ok else '')
cap.release()
"
```

### Alternatif RTSP yöntemleri

| Yöntem | Açıklama | Kurulum |
|--------|----------|---------|
| **MediaMTX + FFmpeg** (önerilen) | En kararlı, düşük gecikme | `setup_rtsp_server.ps1` |
| **IP Webcam** (Android) | Telefonu kamera yap | Play Store'dan yükle, URL al |
| **DroidCam** | Android/iPhone webcam | droidcam.en.uptodown.com |
| **VLC** | Basit ama yavaş | Media → Stream → RTSP |
| **OBS + obs-rtspserver** | Profesyonel | OBS + plugin |

---

## 6. Eğitim Parametreleri

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `--epochs` | 30 | Toplam epoch sayısı |
| `--stage1-epochs` | 10 | Dondurulmuş backbone epoch sayısı |
| `--batch-size` | 32 | Batch boyutu (GPU: 64 artır) |
| `--lr1` | 1e-3 | Stage-1 öğrenme hızı |
| `--lr2` | 1e-4 | Stage-2 fine-tune öğrenme hızı |
| `--min-recall` | 0.90 | Threshold tuning için minimum recall |
| `--no-weighted-sampler` | — | Sınıf dengeleme kapalı |

---

## 7. Sorun Giderme

### RTSP bağlanamıyor
- Aynı ağda mısınız? (`ping 192.168.1.XXX`)
- Windows Güvenlik Duvarı: 8554 portunu aç
  ```powershell
  New-NetFirewallRule -DisplayName "RTSP MediaMTX" -Direction Inbound -Protocol TCP -LocalPort 8554 -Action Allow
  ```
- VPN varsa kapat

### Model yükleme hatası
- `training/fire_model.pt` mevcut mu?
- `CNN_MODEL_PATH` doğru mu? (detector/ klasörüne göre relatif)

### Çok fazla false alarm (model eğitilmeden)
- `DETECTOR_MODE=mock` yerine `cnn` kullanın (model eğitildikten sonra)
- `DETECTION_CONSECUTIVE_FRAMES=5` artırın

### Düşük recall (yangın kaçırıyor)
- Eğitimde `--min-recall 0.95` ile daha düşük threshold seç
- Daha fazla yangın görüntüsü ekle ve yeniden eğit
- `DETECTION_CONSECUTIVE_FRAMES` değerini düşür
