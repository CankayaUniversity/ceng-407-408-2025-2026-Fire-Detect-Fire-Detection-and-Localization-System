# Fire / no_fire model training

Bu klasör, CNNFireDetector için 2 sınıflı (fire / no_fire) MobileNetV2 transfer learning eğitimini içerir. Üretilen `fire_model.pt`, `detector/src/cnn_detector.py` ile uyumludur.

## Veri yapısı

Görselleri aşağıdaki gibi yerleştirin:

```
training/
  dataset/
    train/
      fire/      <- yangın içeren görseller
      no_fire/   <- yangın içermeyen görseller
    val/
      fire/
      no_fire/
```

Desteklenen formatlar: `.jpg`, `.jpeg`, `.png` vb. (PIL/torchvision ile açılabilen tüm formatlar).

## Sınıf eşlemesi (cnn_detector ile aynı)

- **0** = no_fire  
- **1** = fire  

Inference’da `probs[0][1]` yangın olasılığıdır.

## Eğitim çalıştırma

Detector kökünden (veya `training/` içinden):

```bash
cd detector
python -m training.train_fire_model --data-dir training/dataset --epochs 20 --output training/fire_model.pt
```

Sadece CPU kullanmak için:

```bash
python -m training.train_fire_model --data-dir training/dataset --device cpu --epochs 20
```

En iyi validation accuracy’ye sahip model `--output` ile verilen yola (varsayılan: `fire_model.pt`) kaydedilir. Inference tarafında bu dosyayı `CNNFireDetector(model_path="...")` ile kullanın.

## Opsiyonel bağımlılıklar

Eğitim için `torch` ve `torchvision` yeterlidir (detector `requirements.txt` içinde). İsterseniz ileride `tqdm` ekleyebilirsiniz.
