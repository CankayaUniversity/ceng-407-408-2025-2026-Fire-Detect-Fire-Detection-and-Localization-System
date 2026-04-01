"""
Train klasöründeki görsellerin %20'sini val'a taşır.
fire ve no_fire için ayrı ayrı çalışır.
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).parent
DATA = ROOT / "dataset"

VAL_RATIO = 0.20


def split_class(cls: str) -> None:
    train_dir = DATA / "train" / cls
    val_dir   = DATA / "val"   / cls
    val_dir.mkdir(parents=True, exist_ok=True)

    exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = [f for f in train_dir.iterdir() if f.suffix.lower() in exts]

    # Zaten val'da olanları say
    existing_val = len([f for f in val_dir.iterdir() if f.suffix.lower() in exts])

    # Ne kadar daha gerekiyor
    total_needed_val = int((len(files) + existing_val) * VAL_RATIO)
    to_move = max(0, total_needed_val - existing_val)

    print(f"\n[{cls}]")
    print(f"  Train: {len(files)}  Val (mevcut): {existing_val}  Taşınacak: {to_move}")

    if to_move == 0:
        print("  Val zaten yeterli.")
        return

    selected = random.sample(files, min(to_move, len(files)))
    moved = 0
    for f in selected:
        dest = val_dir / f.name
        if not dest.exists():
            shutil.move(str(f), dest)
            moved += 1
    print(f"  Taşındı: {moved} gorsel")
    remaining = len([x for x in train_dir.iterdir() if x.suffix.lower() in exts])
    print(f"  Train kalan: {remaining}  Val toplam: {existing_val + moved}")


print("=== Dataset hazırlama ===")
for cls in ["fire", "no_fire"]:
    train_dir = DATA / "train" / cls
    if train_dir.exists():
        split_class(cls)
    else:
        print(f"\n[{cls}] train klasörü yok, atlandı: {train_dir}")

print("\nBitti.")
for split in ["train", "val"]:
    for cls in ["fire", "no_fire"]:
        d = DATA / split / cls
        if d.exists():
            n = len([f for f in d.iterdir() if f.suffix.lower() in {".jpg",".jpeg",".png",".webp"}])
            print(f"  {split}/{cls}: {n}")
