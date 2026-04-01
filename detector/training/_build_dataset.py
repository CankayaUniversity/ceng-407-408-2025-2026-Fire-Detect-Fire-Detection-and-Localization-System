"""
Flame Scope — Auth gerektirmeyen dataset oluşturucu.

Fire:    Wikimedia Commons API + Open Images CSV (kamu malı görseller)
No-fire: CIFAR-10 (torchvision — otomatik indirir)

Çalıştır:
    cd detector
    python training/_build_dataset.py
"""
from __future__ import annotations
import io, json, os, random, sys, time, urllib.request
from pathlib import Path

import cv2
import numpy as np

OUT = Path("training/dataset")
random.seed(42)
VAL_RATIO = 0.15
TARGET_FIRE    = 1500   # toplam fire görüntüsü hedefi
TARGET_NO_FIRE = 1500   # toplam no_fire görüntüsü hedefi

# ── Wikimedia Commons: yüksek kaliteli yangın fotoğrafları ────
WIKIMEDIA_SEARCHES = [
    "wildfire flame", "house fire", "forest fire", "campfire flame",
    "gas flame", "fire burning", "structure fire"
]

def wikimedia_image_urls(search: str, limit: int = 50) -> list[str]:
    api = (
        "https://commons.wikimedia.org/w/api.php"
        f"?action=query&list=search&srsearch={urllib.parse.quote(search)}"
        f"&srnamespace=6&format=json&srlimit={limit}"
    )
    try:
        with urllib.request.urlopen(api, timeout=10) as r:
            data = json.loads(r.read())
        titles = [h["title"] for h in data["query"]["search"]]
        urls = []
        for title in titles:
            img_api = (
                "https://commons.wikimedia.org/w/api.php"
                f"?action=query&titles={urllib.parse.quote(title)}"
                "&prop=imageinfo&iiprop=url&format=json"
            )
            with urllib.request.urlopen(img_api, timeout=10) as r2:
                d2 = json.loads(r2.read())
            for page in d2["query"]["pages"].values():
                ii = page.get("imageinfo", [])
                if ii:
                    u = ii[0]["url"]
                    if any(u.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
                        urls.append(u)
            time.sleep(0.05)
        return urls
    except Exception as e:
        print(f"    [wikimedia err] {search}: {e}")
        return []

def download_image(url: str, timeout: int = 10):
    """Return numpy BGR image or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FlameScopeBot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None

def save_split(images: list, label: str, out_dir: Path, prefix: str):
    random.shuffle(images)
    n_val = max(1, int(len(images) * VAL_RATIO))
    for i, img in enumerate(images[n_val:]):
        p = out_dir / "train" / label / f"{prefix}_{i:05d}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    for i, img in enumerate(images[:n_val]):
        p = out_dir / "val" / label / f"{prefix}_{i:05d}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return len(images) - n_val, n_val

import urllib.parse

print("\n" + "="*50)
print("  Flame Scope — Dataset Build")
print("="*50)

# ─────────────────────────────────────────────────────────────
# 1. FIRE images — Wikimedia Commons
# ─────────────────────────────────────────────────────────────
print(f"\n[1/2] FIRE — Wikimedia Commons (hedef: {TARGET_FIRE})")
fire_imgs: list[np.ndarray] = []
all_fire_urls: list[str] = []

for search in WIKIMEDIA_SEARCHES:
    urls = wikimedia_image_urls(search, limit=40)
    all_fire_urls.extend(urls)
    print(f"  '{search}' -> {len(urls)} URL")

all_fire_urls = list(dict.fromkeys(all_fire_urls))  # deduplicate
random.shuffle(all_fire_urls)
print(f"  Toplam benzersiz URL: {len(all_fire_urls)}")

for i, url in enumerate(all_fire_urls):
    if len(fire_imgs) >= TARGET_FIRE:
        break
    img = download_image(url)
    if img is not None and img.shape[0] >= 64 and img.shape[1] >= 64:
        # Resize to reasonable size
        h, w = img.shape[:2]
        if max(h, w) > 512:
            scale = 512 / max(h, w)
            img = cv2.resize(img, (int(w*scale), int(h*scale)))
        fire_imgs.append(img)
    if (i+1) % 20 == 0:
        print(f"  İndirilen: {len(fire_imgs)}/{TARGET_FIRE} ({i+1}/{len(all_fire_urls)} URL)")

print(f"  Fire görüntüsü toplam: {len(fire_imgs)}")

if len(fire_imgs) < 50:
    print("  [UYARI] Yeterli fire görseli indirilemedi. İnternet bağlantısını kontrol et.")

if fire_imgs:
    tr, va = save_split(fire_imgs, "fire", OUT, "wk")
    print(f"  Kaydedildi: train={tr}, val={va}")

# ─────────────────────────────────────────────────────────────
# 2. NO-FIRE images — CIFAR-10 via torchvision
# ─────────────────────────────────────────────────────────────
print(f"\n[2/2] NO-FIRE — CIFAR-10 (hedef: {TARGET_NO_FIRE})")
try:
    from torchvision.datasets import CIFAR10
    import torchvision.transforms as T
    from PIL import Image

    transform = T.Compose([T.Resize(128), T.CenterCrop(128)])
    cifar = CIFAR10(root="training/_cifar_cache", train=True, download=True)
    print(f"  CIFAR-10 indirildi: {len(cifar)} görüntü")

    # CIFAR-10 sınıfları: airplane, automobile, bird, cat, deer, dog, frog, horse, ship, truck
    # Hepsi "no_fire" — ama "ship", "truck", "airplane" gibi outdoor + "cat", "dog" gibi indoor
    # Rastgele seç, dengeli
    nofire_imgs = []
    indices = list(range(len(cifar)))
    random.shuffle(indices)
    for idx in indices:
        if len(nofire_imgs) >= TARGET_NO_FIRE:
            break
        pil_img, _ = cifar[idx]
        pil_img = transform(pil_img).resize((128, 128))
        arr = np.array(pil_img)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        nofire_imgs.append(bgr)

    print(f"  No-fire görüntüsü: {len(nofire_imgs)}")
    tr, va = save_split(nofire_imgs, "no_fire", OUT, "cf")
    print(f"  Kaydedildi: train={tr}, val={va}")

except Exception as e:
    print(f"  [hata] CIFAR-10: {e}")

# ─────────────────────────────────────────────────────────────
# Özet
# ─────────────────────────────────────────────────────────────
def count(p: Path) -> int:
    return len(list(p.glob("*.jpg"))) if p.exists() else 0

tf = count(OUT/"train"/"fire");    tn = count(OUT/"train"/"no_fire")
vf = count(OUT/"val"/"fire");      vn = count(OUT/"val"/"no_fire")
total = tf + tn + vf + vn

print(f"\n{'='*50}")
print(f"  Dataset hazır:")
print(f"  train:  fire={tf},  no_fire={tn}")
print(f"  val  :  fire={vf},  no_fire={vn}")
print(f"  TOPLAM: {total} görüntü")
print(f"{'='*50}")

if total < 200:
    print("\n[UYARI] Çok az görüntü. Eğitim kaliteli olmayacak.")
    print("  Manuel ekle: python -m training.prepare_dataset --extra-fire <yol> --skip-kaggle")
    sys.exit(1)
else:
    print("\nEğitimi başlat:")
    print("  python -m training.train_fire_model --data-dir training/dataset --epochs 30")
