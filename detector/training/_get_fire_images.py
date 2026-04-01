"""
Open Images V7 üzerinden yangın sınıfı görüntülerini indirir.
Auth gerektirmez — Google Cloud Storage public bucket.
"""
from __future__ import annotations
import csv, io, json, os, random, sys, time, urllib.request, urllib.parse
from pathlib import Path

import cv2
import numpy as np

OUT_FIRE     = Path("training/dataset/train/fire")
OUT_FIRE_VAL = Path("training/dataset/val/fire")
OUT_FIRE.mkdir(parents=True, exist_ok=True)
OUT_FIRE_VAL.mkdir(parents=True, exist_ok=True)

TARGET = 1200   # fire görüntüsü hedefi
VAL_RATIO = 0.15
random.seed(42)

# Open Images V7 — fire label = /m/03d1jx
FIRE_LABEL_NAME = "Fire"
FIRE_LABEL_ID   = "/m/03d1jx"

# ── 1. Validation bbox annotations CSV'sini indir ────────────
# Bu CSV, validation set'indeki tüm labelled görsellerin image_id'sini içerir
BBOX_CSV_URL = "https://storage.googleapis.com/openimages/v6/oidv6-class-descriptions.csv"
ANNOT_URLS   = [
    "https://storage.googleapis.com/openimages/v5/validation-annotations-bbox.csv",
    "https://storage.googleapis.com/openimages/v5/test-annotations-bbox.csv",
    "https://storage.googleapis.com/openimages/v6/oidv6-train-annotations-bbox.csv",  # large, try last
]
IMG_META_URLS = [
    "https://storage.googleapis.com/openimages/2018_04/validation/validation-images-boxable-google.csv",
    "https://storage.googleapis.com/openimages/2018_04/test/test-images-google.csv",
]

def fetch_url(url: str, timeout: int = 30) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FlameScopeDataset/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  [fetch err] {url[:60]}... : {e}")
        return None

def download_img(url: str, timeout: int = 15) -> np.ndarray | None:
    data = fetch_url(url, timeout)
    if not data:
        return None
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img

print("\n" + "="*55)
print("  Flame Scope — Fire Images (Open Images V7)")
print("="*55)

# ── 2. Validation image list ──────────────────────────────────
print("\n[1/3] Validation image listesi indiriliyor...")
img_url_map: dict[str, str] = {}  # image_id -> original_url
for meta_url in IMG_META_URLS:
    data = fetch_url(meta_url)
    if not data:
        continue
    lines = data.decode("utf-8", errors="ignore").splitlines()
    reader = csv.DictReader(lines)
    for row in reader:
        img_id = row.get("ImageID", "")
        url = row.get("OriginalURL", "")
        if img_id and url:
            img_url_map[img_id] = url
    if img_url_map:
        print(f"  {len(img_url_map)} görüntü URL'i yüklendi")
        break

# ── 3. Fire annotations ───────────────────────────────────────
print(f"\n[2/3] Fire label ({FIRE_LABEL_ID}) annotations indiriliyor...")
fire_ids: list[str] = []

for annot_url in ANNOT_URLS[:2]:  # ilk 2 (validation + test) yeter
    print(f"  {annot_url[-50:]}...")
    data = fetch_url(annot_url, timeout=60)
    if not data:
        continue
    lines = data.decode("utf-8", errors="ignore").splitlines()
    reader = csv.DictReader(lines)
    for row in reader:
        lbl = row.get("LabelName", "")
        if lbl == FIRE_LABEL_ID:
            img_id = row.get("ImageID", "")
            if img_id and img_id not in fire_ids:
                fire_ids.append(img_id)
    print(f"  Fire görüntü ID'si: {len(fire_ids)}")
    if len(fire_ids) >= TARGET * 2:
        break

if not fire_ids:
    print("  [bilgi] Open Images annotations bulunamadi, Wikimedia fallback...")
    # ── Fallback: bilinen Wikipedia yangın görselleri ──────────
    WIKI_FIRE_TITLES = [
        "File:WildFirePrevention.jpg", "File:Campfire.jpg",
        "File:House_fire_at_Spruce_St_Strathroy_Ontario.jpg",
        "File:USFS_Wildland_firefighter.jpg",
        "File:FireInNighttime.jpg", "File:Gas_flame.jpg",
        "File:Structure_fire_in_Ames,_Iowa.jpg",
        "File:Bonfire_at_Night.jpg", "File:Wildfire_in_Australia.jpg",
        "File:Aust_brushfire.jpg", "File:2020_Bobcat_Fire_nighttime.jpg",
    ]
    fire_direct_urls = []
    for title in WIKI_FIRE_TITLES:
        api = (f"https://commons.wikimedia.org/w/api.php?action=query"
               f"&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url&format=json")
        data = fetch_url(api, timeout=15)
        if data:
            d = json.loads(data)
            for page in d.get("query", {}).get("pages", {}).values():
                for ii in page.get("imageinfo", []):
                    u = ii.get("url", "")
                    if u and any(u.lower().endswith(e) for e in (".jpg", ".jpeg", ".png")):
                        fire_direct_urls.append(u)
    print(f"  Wikimedia fallback: {len(fire_direct_urls)} URL")

    saved = 0
    for url in fire_direct_urls:
        img = download_img(url)
        if img is not None and img.shape[0] >= 64:
            idx = saved
            if random.random() < VAL_RATIO:
                cv2.imwrite(str(OUT_FIRE_VAL / f"fb_{idx:04d}.jpg"), img)
            else:
                cv2.imwrite(str(OUT_FIRE / f"fb_{idx:04d}.jpg"), img)
            saved += 1
    print(f"  Kaydedildi: {saved}")
    sys.exit(0)

# ── 4. Görselleri indir ───────────────────────────────────────
print(f"\n[3/3] {min(len(fire_ids), TARGET)} fire görüntüsü indiriliyor...")
random.shuffle(fire_ids)
saved = 0
errors = 0

for img_id in fire_ids:
    if saved >= TARGET:
        break
    # URL arama sırası: img_url_map, sonra YFCC100M fallback, sonra OpenImages GCS
    url = img_url_map.get(img_id, "")
    if not url:
        # Try Open Images GCS thumbnail
        url = f"https://storage.googleapis.com/openimages/validation/{img_id}.jpg"

    img = download_img(url)
    if img is not None and img.shape[0] >= 64 and img.shape[1] >= 64:
        h, w = img.shape[:2]
        if max(h, w) > 640:
            s = 640 / max(h, w)
            img = cv2.resize(img, (int(w*s), int(h*s)))
        dst = OUT_FIRE_VAL if saved < int(TARGET * VAL_RATIO) else OUT_FIRE
        cv2.imwrite(str(dst / f"oi_{saved:05d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        saved += 1
        if saved % 50 == 0:
            print(f"  {saved}/{TARGET} indirildi")
    else:
        errors += 1

print(f"\n  Kaydedilen fire: train={len(list(OUT_FIRE.glob('*.jpg')))}, val={len(list(OUT_FIRE_VAL.glob('*.jpg')))}")
print(f"  Hata/skip: {errors}")

# ── Son kontrol ───────────────────────────────────────────────
tf  = len(list((Path("training/dataset/train/fire")).glob("*.jpg")))
tn  = len(list((Path("training/dataset/train/no_fire")).glob("*.jpg")))
vf  = len(list((Path("training/dataset/val/fire")).glob("*.jpg")))
vn  = len(list((Path("training/dataset/val/no_fire")).glob("*.jpg")))
print(f"\n{'='*55}")
print(f"  Dataset: train fire={tf} nf={tn} | val fire={vf} nf={vn}")
print(f"  TOPLAM: {tf+tn+vf+vn}")
print(f"{'='*55}")
