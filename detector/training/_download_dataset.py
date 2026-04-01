"""
Flame Scope — Dataset indirme scripti (Hugging Face kaynaklı).
HuggingFace'deki fire/no_fire dataset'ini indirir, train/val olarak düzenler.
"""
from __future__ import annotations
import os, sys, shutil, random
from pathlib import Path

OUT_DIR = Path("training/dataset")
random.seed(42)
VAL_RATIO = 0.15

def save_pil(img, path: Path):
    img.save(str(path), quality=90)

def split_and_save(images, label: str, out_dir: Path, tag: str):
    random.shuffle(images)
    n_val = max(1, int(len(images) * VAL_RATIO))
    val_imgs   = images[:n_val]
    train_imgs = images[n_val:]
    (out_dir / "train" / label).mkdir(parents=True, exist_ok=True)
    (out_dir / "val"   / label).mkdir(parents=True, exist_ok=True)
    for i, img in enumerate(train_imgs):
        save_pil(img, out_dir / "train" / label / f"{tag}_{i:05d}.jpg")
    for i, img in enumerate(val_imgs):
        save_pil(img, out_dir / "val" / label / f"{tag}_v{i:05d}.jpg")
    return len(train_imgs), len(val_imgs)

print("\n========================================")
print("  Flame Scope — Dataset İndirme")
print("========================================\n")

# ── 1. Hugging Face: keremberke/fire-detection-mini ──────────
print("[1/2] HuggingFace 'keremberke/fire-detection-mini' deneniyor...")
try:
    from datasets import load_dataset
    ds = load_dataset("keremberke/fire-detection-mini", name="full", trust_remote_code=True)
    print(f"  Yüklendi: {ds}")
    fire_images = []
    nofire_images = []
    for split in ds.values():
        for item in split:
            img = item["image"]
            lbl = item["labels"]
            if isinstance(lbl, list): lbl = lbl[0] if lbl else 0
            if lbl == 1 or (isinstance(lbl, str) and "fire" in lbl.lower()):
                fire_images.append(img)
            else:
                nofire_images.append(img)
    print(f"  fire={len(fire_images)}, no_fire={len(nofire_images)}")
    if fire_images and nofire_images:
        tr_f, va_f = split_and_save(fire_images, "fire", OUT_DIR, "hf1")
        tr_n, va_n = split_and_save(nofire_images, "no_fire", OUT_DIR, "hf1")
        print(f"  Kaydedildi: train fire={tr_f}, no_fire={tr_n} | val fire={va_f}, no_fire={va_n}")
except Exception as e:
    print(f"  [atlandı] {e}")

# ── 2. Hugging Face: pyronear/openfire ───────────────────────
print("\n[2/2] HuggingFace 'pyronear/openfire' deneniyor...")
try:
    from datasets import load_dataset
    ds2 = load_dataset("pyronear/openfire", trust_remote_code=True, split="train")
    fire2 = [item["image"] for item in ds2 if item.get("is_fire", 1) == 1]
    nofire2 = [item["image"] for item in ds2 if item.get("is_fire", 1) == 0]
    print(f"  fire={len(fire2)}, no_fire={len(nofire2)}")
    if fire2:
        tr_f, va_f = split_and_save(fire2[:3000], "fire", OUT_DIR, "pyr")
        print(f"  fire kaydedildi: train={tr_f}, val={va_f}")
    if nofire2:
        tr_n, va_n = split_and_save(nofire2[:3000], "no_fire", OUT_DIR, "pyr")
        print(f"  no_fire kaydedildi: train={tr_n}, val={va_n}")
except Exception as e:
    print(f"  [atlandı] {e}")

# ── Sonuç ─────────────────────────────────────────────────────
def count(p): return len(list(p.glob("*.jpg"))) if p.exists() else 0
tf = count(OUT_DIR/"train"/"fire");   tn = count(OUT_DIR/"train"/"no_fire")
vf = count(OUT_DIR/"val"/"fire");     vn = count(OUT_DIR/"val"/"no_fire")
total = tf + tn + vf + vn

print(f"\n{'='*40}")
print(f"  Dataset hazır:")
print(f"  train: fire={tf}, no_fire={tn}")
print(f"  val  : fire={vf}, no_fire={vn}")
print(f"  TOPLAM: {total} görüntü")
print(f"{'='*40}\n")

if total < 100:
    print("  [UYARI] Az görüntü var! Manuel dataset ekle:")
    print("  python -m training.prepare_dataset --extra-fire <klasör> --extra-no-fire <klasör> --skip-kaggle")
    sys.exit(1)
else:
    print("  Eğitime hazır!")
    print("  Komutu: python -m training.train_fire_model --data-dir training/dataset --epochs 30")
