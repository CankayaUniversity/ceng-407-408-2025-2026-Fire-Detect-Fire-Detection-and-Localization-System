"""
Fire / no_fire binary classifier — Flame Scope CNNFireDetector.

MobileNetV2 transfer learning with two-stage fine-tuning.
Output compatible with detector/src/cnn_detector.py.
Class mapping: 0 = no_fire, 1 = fire.

Usage:
    cd detector
    python -m training.train_fire_model --data-dir training/dataset --epochs 30
    python -m training.train_fire_model --data-dir training/dataset --epochs 30 --device cpu
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights

# ── Class mapping (must match detector/src/cnn_detector.py) ──────────────────
NO_FIRE_INDEX = 0
FIRE_INDEX = 1
CLASS_NAMES = ("no_fire", "fire")
NUM_CLASSES = 2

# ── ImageNet normalization ────────────────────────────────────────────────────
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
INPUT_SIZE = 224


# ─────────────────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────────────────

def build_model(num_classes: int = NUM_CLASSES, freeze_backbone: bool = True) -> nn.Module:
    """
    MobileNetV2 with pretrained ImageNet backbone.
    Stage-1: backbone frozen, only classifier trains.
    Stage-2: full fine-tuning with lower LR.
    """
    weights = MobileNet_V2_Weights.DEFAULT
    model = mobilenet_v2(weights=weights)
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(model.last_channel, 256),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.2),
        nn.Linear(256, num_classes),
    )
    if freeze_backbone:
        for name, param in model.named_parameters():
            if "classifier" not in name:
                param.requires_grad = False
    return model


def unfreeze_backbone(model: nn.Module) -> None:
    """Unfreeze all layers for stage-2 fine-tuning."""
    for param in model.parameters():
        param.requires_grad = True
    print("  [fine-tune] All layers unfrozen for stage-2.")


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────

def get_dataloaders(
    data_dir: Path,
    batch_size: int = 32,
    num_workers: int = 0,
    use_weighted_sampler: bool = True,
) -> tuple[DataLoader, DataLoader]:
    """
    Expects:
        data_dir/train/fire/
        data_dir/train/no_fire/
        data_dir/val/fire/
        data_dir/val/no_fire/

    ImageFolder sorts alphabetically: fire=0, no_fire=1.
    target_transform=lambda x: 1-x  →  fire=1, no_fire=0.
    """
    # ── Training augmentation (aggressive for fire recognition) ──────────────
    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomResizedCrop(INPUT_SIZE, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.1),
        transforms.RandomRotation(15),
        transforms.ColorJitter(
            brightness=0.4,   # fire changes brightness significantly
            contrast=0.4,
            saturation=0.4,
            hue=0.05,
        ),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        transforms.RandomErasing(p=0.1, scale=(0.02, 0.1)),
    ])

    # ── Validation: clean, deterministic ─────────────────────────────────────
    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    train_root = data_dir / "train"
    val_root = data_dir / "val"
    for p in (train_root, val_root):
        if not p.is_dir():
            raise FileNotFoundError(
                f"Missing: {p}\n"
                "Expected: data_dir/train/fire/, data_dir/train/no_fire/, "
                "data_dir/val/fire/, data_dir/val/no_fire/"
            )

    # target_transform: fire=0→1, no_fire=1→0
    flip = lambda x: 1 - x
    train_ds = ImageFolder(str(train_root), transform=train_transform, target_transform=flip)
    val_ds   = ImageFolder(str(val_root),   transform=val_transform,   target_transform=flip)

    n_fire     = sum(1 for _, y in train_ds if y == FIRE_INDEX)
    n_no_fire  = sum(1 for _, y in train_ds if y == NO_FIRE_INDEX)
    n_total    = len(train_ds)
    print(f"  Train: {n_total} images  (fire={n_fire}, no_fire={n_no_fire})")
    print(f"  Val:   {len(val_ds)} images")

    train_loader_kwargs: dict = dict(
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=False,
    )

    if use_weighted_sampler and n_fire > 0 and n_no_fire > 0:
        # Oversample minority class so each batch sees balanced fire/no_fire
        class_weight = [
            n_total / (NUM_CLASSES * n_no_fire),  # no_fire weight
            n_total / (NUM_CLASSES * n_fire),      # fire weight
        ]
        sample_weights = [class_weight[label] for _, label in train_ds]
        sampler = WeightedRandomSampler(sample_weights, num_samples=n_total, replacement=True)
        train_loader = DataLoader(train_ds, sampler=sampler, **train_loader_kwargs)
        print(f"  WeightedRandomSampler: fire_w={class_weight[1]:.3f}, no_fire_w={class_weight[0]:.3f}")
    else:
        train_loader = DataLoader(train_ds, shuffle=True, **train_loader_kwargs)

    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    return train_loader, val_loader


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

class Metrics:
    """Binary metrics focused on fire (positive) class."""

    def __init__(self):
        self.tp = self.fp = self.tn = self.fn = 0
        self.total_loss = 0.0
        self.n = 0

    def update(self, preds: torch.Tensor, targets: torch.Tensor, loss: float, batch_size: int):
        self.total_loss += loss * batch_size
        self.n += batch_size
        fire = (preds == FIRE_INDEX)
        gt   = (targets == FIRE_INDEX)
        self.tp += (fire & gt).sum().item()
        self.fp += (fire & ~gt).sum().item()
        self.tn += (~fire & ~gt).sum().item()
        self.fn += (~fire & gt).sum().item()

    @property
    def loss(self) -> float:
        return self.total_loss / self.n if self.n else 0.0

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.n if self.n else 0.0

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def summary(self) -> str:
        return (
            f"loss={self.loss:.4f}  acc={self.accuracy:.4f}  "
            f"prec={self.precision:.4f}  rec={self.recall:.4f}  f1={self.f1:.4f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Train / Validate loops
# ─────────────────────────────────────────────────────────────────────────────

def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: Optional[torch.optim.Optimizer],
    device: torch.device,
) -> Metrics:
    training = optimizer is not None
    model.train() if training else model.eval()
    metrics = Metrics()

    from tqdm import tqdm
    ctx = torch.enable_grad() if training else torch.no_grad()
    with ctx:
        for inputs, targets in tqdm(loader, leave=False, desc="train" if training else "val "):
            inputs, targets = inputs.to(device), targets.to(device)
            if training:
                optimizer.zero_grad()
            logits = model(inputs)
            loss = criterion(logits, targets)
            if training:
                loss.backward()
                optimizer.step()
            preds = logits.argmax(dim=1)
            metrics.update(preds, targets, loss.item(), inputs.size(0))

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Threshold tuning
# ─────────────────────────────────────────────────────────────────────────────

@torch.no_grad()
def find_best_threshold(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    min_recall: float = 0.90,
) -> float:
    """
    Sweep sigmoid threshold from 0.3..0.9 and pick highest F1 with recall >= min_recall.
    Fire is safety-critical → we require high recall (few missed fires).
    """
    model.eval()
    all_probs: list[float] = []
    all_labels: list[int] = []
    for inputs, targets in loader:
        inputs = inputs.to(device)
        logits = model(inputs)
        probs = torch.softmax(logits, dim=1)[:, FIRE_INDEX]
        all_probs.extend(probs.cpu().tolist())
        all_labels.extend(targets.tolist())

    best_thresh = 0.5
    best_f1 = -1.0
    for t_int in range(30, 91, 2):
        t = t_int / 100.0
        tp = fp = fn = tn = 0
        for prob, label in zip(all_probs, all_labels):
            pred = 1 if prob >= t else 0
            if pred == 1 and label == 1: tp += 1
            elif pred == 1 and label == 0: fp += 1
            elif pred == 0 and label == 1: fn += 1
            else: tn += 1
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        prec   = tp / (tp + fp) if (tp + fp) else 0.0
        f1     = 2 * prec * recall / (prec + recall) if (prec + recall) else 0.0
        if recall >= min_recall and f1 > best_f1:
            best_f1 = f1
            best_thresh = t

    print(f"  Best threshold (recall≥{min_recall}): {best_thresh:.2f}  (f1={best_f1:.4f})")
    return best_thresh


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Train fire/no_fire classifier — Flame Scope")
    parser.add_argument("--data-dir",      type=str,   default="training/dataset", help="Root with train/ and val/")
    parser.add_argument("--epochs",        type=int,   default=30,    help="Total epochs (stage1 + stage2)")
    parser.add_argument("--stage1-epochs", type=int,   default=10,    help="Epochs with frozen backbone")
    parser.add_argument("--batch-size",    type=int,   default=32,    help="Batch size")
    parser.add_argument("--lr1",           type=float, default=1e-3,  help="LR for stage-1 (classifier only)")
    parser.add_argument("--lr2",           type=float, default=1e-4,  help="LR for stage-2 (full fine-tune)")
    parser.add_argument("--output",        type=str,   default="training/fire_model.pt", help="Best model output path")
    parser.add_argument("--device",        type=str,   default=None,  help="cpu | cuda (default: auto)")
    parser.add_argument("--num-workers",   type=int,   default=0,     help="DataLoader workers (0=main thread)")
    parser.add_argument("--no-weighted-sampler", action="store_true", help="Disable WeightedRandomSampler")
    parser.add_argument("--min-recall",    type=float, default=0.90,  help="Min fire recall for threshold tuning")
    args = parser.parse_args()

    data_dir    = Path(args.data_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"\n{'='*60}")
    print(f"  Flame Scope — Fire Detection Training")
    print(f"  Device : {device}")
    print(f"  Data   : {data_dir.resolve()}")
    print(f"  Output : {output_path.resolve()}")
    print(f"  Epochs : {args.epochs} (stage1={args.stage1_epochs}, stage2={args.epochs - args.stage1_epochs})")
    print(f"{'='*60}\n")

    # ── Data ─────────────────────────────────────────────────────────────────
    train_loader, val_loader = get_dataloaders(
        data_dir,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        use_weighted_sampler=not args.no_weighted_sampler,
    )

    # ── Focal-like loss: weight fire class higher ─────────────────────────────
    # fire miss >> no_fire false alarm in safety systems
    fire_weight = torch.tensor([1.0, 2.5], device=device)
    criterion = nn.CrossEntropyLoss(weight=fire_weight)

    # ── Stage 1: frozen backbone ──────────────────────────────────────────────
    print(f"\n--- Stage 1 (frozen backbone, {args.stage1_epochs} epochs) ---")
    model = build_model(freeze_backbone=True).to(device)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"  Trainable params: {trainable:,} / {total:,}")

    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr1, weight_decay=1e-4,
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=args.stage1_epochs, eta_min=args.lr1 / 10)

    best_f1   = -1.0
    best_meta: dict = {}

    for epoch in range(1, args.stage1_epochs + 1):
        t0 = time.time()
        tr = run_epoch(model, train_loader, criterion, optimizer, device)
        va = run_epoch(model, val_loader,   criterion, None,      device)
        scheduler.step()
        elapsed = time.time() - t0
        print(
            f"  Ep {epoch:02d}/{args.stage1_epochs}  "
            f"train [{tr.summary()}]  "
            f"val [{va.summary()}]  {elapsed:.1f}s"
        )
        if va.f1 > best_f1:
            best_f1 = va.f1
            torch.save(model.state_dict(), output_path)
            best_meta = {"epoch": epoch, "stage": 1, "val_f1": va.f1, "val_recall": va.recall, "val_acc": va.accuracy}
            print(f"    ✓ New best f1={best_f1:.4f} → saved to {output_path}")

    # ── Stage 2: full fine-tuning ─────────────────────────────────────────────
    stage2_epochs = args.epochs - args.stage1_epochs
    if stage2_epochs > 0:
        print(f"\n--- Stage 2 (full fine-tune, {stage2_epochs} epochs) ---")
        # Load best stage-1 weights, then unfreeze
        model.load_state_dict(torch.load(output_path, map_location=device, weights_only=True))
        unfreeze_backbone(model)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"  Trainable params: {trainable:,} / {total:,}")

        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr2, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=stage2_epochs, eta_min=args.lr2 / 20)

        for epoch in range(1, stage2_epochs + 1):
            t0 = time.time()
            tr = run_epoch(model, train_loader, criterion, optimizer, device)
            va = run_epoch(model, val_loader,   criterion, None,      device)
            scheduler.step()
            elapsed = time.time() - t0
            print(
                f"  Ep {epoch:02d}/{stage2_epochs}  "
                f"train [{tr.summary()}]  "
                f"val [{va.summary()}]  {elapsed:.1f}s"
            )
            if va.f1 > best_f1:
                best_f1 = va.f1
                torch.save(model.state_dict(), output_path)
                best_meta = {"epoch": args.stage1_epochs + epoch, "stage": 2, "val_f1": va.f1, "val_recall": va.recall, "val_acc": va.accuracy}
                print(f"    ✓ New best f1={best_f1:.4f} → saved to {output_path}")

    # ── Threshold tuning on best model ───────────────────────────────────────
    print(f"\n--- Threshold tuning (min_recall={args.min_recall}) ---")
    model.load_state_dict(torch.load(output_path, map_location=device, weights_only=True))
    best_thresh = find_best_threshold(model, val_loader, device, min_recall=args.min_recall)

    # ── Save metadata ─────────────────────────────────────────────────────────
    meta = {
        **best_meta,
        "recommended_threshold": best_thresh,
        "class_names": list(CLASS_NAMES),
        "fire_class_index": FIRE_INDEX,
        "input_size": INPUT_SIZE,
    }
    meta_path = output_path.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2))

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Training complete.")
    print(f"  Best model  : {output_path}")
    print(f"  Metadata    : {meta_path}")
    print(f"  Best val F1 : {best_f1:.4f}")
    print(f"  Threshold   : {best_thresh:.2f}  (use FIRE_CONFIDENCE_THRESHOLD in cnn_detector.py)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
