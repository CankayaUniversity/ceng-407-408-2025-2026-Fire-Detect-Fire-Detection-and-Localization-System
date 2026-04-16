"""
Gerçek indoor/outdoor sahneleri no_fire olarak indir.
CIFAR-10 yerine gerçek yüksek çözünürlüklü görseller kullanmak
false positive'leri dramatik şekilde azaltır.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from icrawler.builtin import BingImageCrawler

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "dataset" / "train" / "no_fire"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Kategori başına kaç görsel
PER_QUERY = 120

# Gerçek kamera görüntüsüne benzer no_fire sahneleri
# Özellikle dikkat edilmesi gerekenler:
#   - Warm/orange lighting (false positive kaynağı)
#   - Gece görüntüleri, lambalar
#   - Insan ciltleri (kızıl ton)
QUERIES = [
    # İç mekan / ofis / ev
    "office interior daytime",
    "living room interior",
    "kitchen interior",
    "bedroom interior photo",
    "corridor hallway indoor",
    "lobby interior building",
    "warehouse empty interior",

    # Dış mekan / sokak
    "street city daytime",
    "parking lot surveillance camera",
    "outdoor park daytime",
    "road highway traffic",

    # Kritik false positive kaynakları — mutlaka dahil et
    "warm orange lighting room interior",
    "sunset orange sky outdoor",
    "candle light warm room no fire",      # alev var ama az
    "led orange light room ambiance",
    "sunset golden hour indoor window",
    "desk lamp warm light office",
    "restaurant warm lighting interior",
    "neon sign night city street",

    # Ekranlar (arkadaşın ekranı false positive yapabilir)
    "computer monitor screen room",
    "television room interior dark",

    # İnsan / yüz (cilt tonu HSV filtresi tetikliyor)
    "people office work indoor",
    "security camera view hallway",
]

print(f"no_fire klasoru: {OUT_DIR}")
print(f"Hedef: {len(QUERIES)} sorgu x {PER_QUERY} = ~{len(QUERIES)*PER_QUERY} gorsel")

existing = len(list(OUT_DIR.glob("*.jpg"))) + len(list(OUT_DIR.glob("*.png")))
print(f"Mevcut gorsel: {existing}")

for i, query in enumerate(QUERIES, 1):
    safe = query.replace(" ", "_").replace("/", "_")[:40]
    tmp = ROOT / "_tmp_nofire" / safe
    tmp.mkdir(parents=True, exist_ok=True)

    print(f"\n[{i}/{len(QUERIES)}] '{query}' indiriliyor...")
    try:
        crawler = BingImageCrawler(storage={"root_dir": str(tmp)})
        crawler.crawl(keyword=query, max_num=PER_QUERY, min_size=(100, 100))
    except Exception as e:
        print(f"  HATA: {e}")
        continue

    # Görselleri hedef klasöre taşı, benzersiz isim ver
    moved = 0
    before = len(list(OUT_DIR.glob("*")))
    for f in tmp.iterdir():
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            dest = OUT_DIR / f"{safe}_{f.name}"
            if not dest.exists():
                shutil.copy2(f, dest)
                moved += 1
    print(f"  Eklendi: {moved} gorsel  (toplam: {before + moved})")
    shutil.rmtree(tmp, ignore_errors=True)

total = len(list(OUT_DIR.glob("*.jpg"))) + len(list(OUT_DIR.glob("*.png")))
print(f"\nno_fire toplam gorsel: {total}")
print("Bitti.")
