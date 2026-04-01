"""
DuckDuckGo + icrawler ile fire ve no_fire görüntüleri toplar.
API key gerektirmez.
"""
from __future__ import annotations
import os, random, sys, shutil
from pathlib import Path

TARGET_FIRE    = 1200
TARGET_NO_FIRE = 0   # CIFAR-10 ile zaten var (1500 adet)
random.seed(42)

FIRE_QUERIES = [
    "wildfire burning",
    "house fire flames",
    "forest fire inferno",
    "gas fire flame close",
    "structure fire firefighter",
    "campfire large flame",
    "building fire orange flame",
    "wildland fire smoke",
]

TRAIN_FIRE = Path("training/dataset/train/fire")
VAL_FIRE   = Path("training/dataset/val/fire")
TRAIN_FIRE.mkdir(parents=True, exist_ok=True)
VAL_FIRE.mkdir(parents=True, exist_ok=True)

print("\n" + "="*50)
print("  Fire Image Downloader (DuckDuckGo + icrawler)")
print("="*50 + "\n")

downloaded = 0

# ── Method 1: icrawler (BingImageCrawler) ─────────────────────
print("[1] icrawler BingImageCrawler deneniyor...")
try:
    from icrawler.builtin import BingImageCrawler, GoogleImageCrawler

    tmp_dir = Path("training/_fire_tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for query in FIRE_QUERIES:
        if downloaded >= TARGET_FIRE:
            break
        per_query = min(150, TARGET_FIRE // len(FIRE_QUERIES) + 30)
        crawler_dir = tmp_dir / query.replace(" ", "_")
        crawler_dir.mkdir(exist_ok=True)

        try:
            crawler = BingImageCrawler(
                storage={"root_dir": str(crawler_dir)},
                feeder_threads=1,
                parser_threads=1,
                downloader_threads=4,
            )
            crawler.crawl(
                keyword=query,
                max_num=per_query,
                min_size=(100, 100),
                file_idx_offset=0,
            )
        except Exception as e:
            print(f"  Bing hata '{query}': {e}")
            # Fallback to Google
            try:
                crawler = GoogleImageCrawler(
                    storage={"root_dir": str(crawler_dir)},
                    feeder_threads=1,
                    parser_threads=1,
                    downloader_threads=4,
                )
                crawler.crawl(keyword=query, max_num=per_query, min_size=(100, 100))
            except Exception as e2:
                print(f"  Google hata '{query}': {e2}")

        # Move to dataset
        imgs = list(crawler_dir.glob("*.jpg")) + list(crawler_dir.glob("*.jpeg")) + list(crawler_dir.glob("*.png"))
        for img in imgs:
            if downloaded >= TARGET_FIRE:
                break
            try:
                import cv2
                frame = cv2.imread(str(img))
                if frame is None or frame.shape[0] < 64:
                    continue
                # Resize if too large
                h, w = frame.shape[:2]
                if max(h, w) > 640:
                    s = 640 / max(h, w)
                    frame = cv2.resize(frame, (int(w*s), int(h*s)))
                val = random.random() < 0.15
                dst_dir = VAL_FIRE if val else TRAIN_FIRE
                dst = dst_dir / f"sc_{downloaded:05d}.jpg"
                cv2.imwrite(str(dst), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
                downloaded += 1
            except Exception:
                pass

        print(f"  '{query}': {len(imgs)} indirildi, toplam: {downloaded}")

    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)

except ImportError:
    print("  icrawler yok, atlanıyor.")

# ── Method 2: duckduckgo-search ───────────────────────────────
if downloaded < TARGET_FIRE:
    print(f"\n[2] duckduckgo-search ile {TARGET_FIRE - downloaded} fire görseli daha...")
    try:
        from duckduckgo_search import DDGS
        import urllib.request
        import numpy as np

        ddgs = DDGS()
        import cv2

        for query in FIRE_QUERIES:
            if downloaded >= TARGET_FIRE:
                break
            try:
                results = list(ddgs.images(
                    query,
                    max_results=100,
                    size="Medium",
                    type_image="photo",
                ))
                for r in results:
                    if downloaded >= TARGET_FIRE:
                        break
                    url = r.get("image", "")
                    if not url:
                        continue
                    try:
                        req = urllib.request.Request(
                            url,
                            headers={"User-Agent": "Mozilla/5.0"},
                        )
                        with urllib.request.urlopen(req, timeout=8) as resp:
                            data = resp.read()
                        arr = np.frombuffer(data, np.uint8)
                        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if img is None or img.shape[0] < 64:
                            continue
                        h, w = img.shape[:2]
                        if max(h, w) > 640:
                            s = 640 / max(h, w)
                            img = cv2.resize(img, (int(w*s), int(h*s)))
                        val = random.random() < 0.15
                        dst = (VAL_FIRE if val else TRAIN_FIRE) / f"ddg_{downloaded:05d}.jpg"
                        cv2.imwrite(str(dst), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
                        downloaded += 1
                    except Exception:
                        pass
                print(f"  '{query}': toplam={downloaded}")
            except Exception as e:
                print(f"  DDG hata '{query}': {e}")

    except ImportError:
        print("  duckduckgo-search yok.")

# ── Sonuç ─────────────────────────────────────────────────────
tf = len(list(TRAIN_FIRE.glob("*.jpg")))
vf = len(list(VAL_FIRE.glob("*.jpg")))
tn = len(list(Path("training/dataset/train/no_fire").glob("*.jpg")))
vn = len(list(Path("training/dataset/val/no_fire").glob("*.jpg")))

print(f"\n{'='*50}")
print(f"  Dataset:")
print(f"  train: fire={tf}, no_fire={tn}")
print(f"  val  : fire={vf}, no_fire={vn}")
print(f"  TOPLAM: {tf+tn+vf+vn}")
print(f"{'='*50}")

if tf + vf < 100:
    print("\n[HATA] Cok az fire goruntusu! Internet baglantisini kontrol et.")
    sys.exit(1)
print("\nEgitim: python -m training.train_fire_model --data-dir training/dataset --epochs 30")
