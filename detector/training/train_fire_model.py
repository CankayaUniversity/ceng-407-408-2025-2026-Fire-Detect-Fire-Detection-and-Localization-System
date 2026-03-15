"""
Fire / no_fire binary classifier training for Flame Scope CNNFireDetector.

MobileNetV2 transfer learning; output compatible with detector/src/cnn_detector.py.
Class mapping: 0 = no_fire, 1 = fire.

Usage (from detector repo root):
  cd detector
  python -m training.train_fire_model --data-dir training/dataset --epochs 20

Or from detector/training:
  python train_fire_model.py --data-dir dataset --epochs 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights

# Class mapping (must match detector/src/cnn_detector.py)
NO_FIRE_INDEX = 0
FIRE_INDEX = 1
CLASS_NAMES = ("no_fire", "fire")
NUM_CLASSES = 2

# ImageNet normalization (same as cnn_detector)
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
INPUT_SIZE = 224


def build_model(num_classes: int = NUM_CLASSES) -> nn.Module:
    """Same architecture as detector/src/cnn_detector.py _build_model()."""
    weights = MobileNet_V2_Weights.DEFAULT
    model = mobilenet_v2(weights=weights)
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(model.last_channel, num_classes),
    )
    return model


def get_dataloaders(
    data_dir: Path,
    batch_size: int = 32,
    num_workers: int = 0,
):
    """
    dataset/train and dataset/val must contain subdirs: fire/, no_fire/.
    ImageFolder sorts classes alphabetically -> fire=0, no_fire=1.
    We want 0=no_fire, 1=fire -> use target_transform to swap.
    """
    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomCrop(INPUT_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    val_transform = transforms.Compose([
        transforms.Resize(INPUT_SIZE),
        transforms.CenterCrop(INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    train_root = data_dir / "train"
    val_root = data_dir / "val"
    if not train_root.is_dir() or not val_root.is_dir():
        raise FileNotFoundError(
            f"Expected {train_root} and {val_root} with fire/ and no_fire/ subdirs."
        )

    # ImageFolder: sorted class names -> fire=0, no_fire=1. We need 0=no_fire, 1=fire.
    train_ds = ImageFolder(str(train_root), transform=train_transform, target_transform=lambda x: 1 - x)
    val_ds = ImageFolder(str(val_root), transform=val_transform, target_transform=lambda x: 1 - x)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=False,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=False,
    )
    return train_loader, val_loader


def train_epoch(model: nn.Module, loader: DataLoader, criterion: nn.Module, optimizer: torch.optim.Optimizer, device: torch.device) -> tuple[float, float]:
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0
    for inputs, targets in loader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        logits = model(inputs)
        loss = criterion(logits, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * inputs.size(0)
        pred = logits.argmax(dim=1)
        correct += (pred == targets).sum().item()
        total += targets.size(0)
    return total_loss / total, correct / total


@torch.no_grad()
def validate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    for inputs, targets in loader:
        inputs, targets = inputs.to(device), targets.to(device)
        logits = model(inputs)
        loss = criterion(logits, targets)
        total_loss += loss.item() * inputs.size(0)
        pred = logits.argmax(dim=1)
        correct += (pred == targets).sum().item()
        total += targets.size(0)
    return total_loss / total, correct / total


def main() -> None:
    parser = argparse.ArgumentParser(description="Train fire/no_fire classifier for CNNFireDetector")
    parser.add_argument("--data-dir", type=str, default="dataset", help="Root containing train/ and val/ with fire/ and no_fire/")
    parser.add_argument("--epochs", type=int, default=20, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--output", type=str, default="fire_model.pt", help="Output path for best model (state_dict)")
    parser.add_argument("--device", type=str, default=None, help="Device: cpu or cuda (default: auto)")
    parser.add_argument("--num-workers", type=int, default=0, help="DataLoader num_workers (0 for CPU-safe)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"Data directory not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"Device: {device}")
    print(f"Class mapping: 0 = {CLASS_NAMES[0]}, 1 = {CLASS_NAMES[1]}")

    train_loader, val_loader = get_dataloaders(data_dir, batch_size=args.batch_size, num_workers=args.num_workers)
    model = build_model().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    output_path = Path(args.output)
    best_val_acc = -1.0

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        print(
            f"Epoch {epoch}/{args.epochs}  train_loss={train_loss:.4f}  train_acc={train_acc:.4f}  "
            f"val_loss={val_loss:.4f}  val_acc={val_acc:.4f}"
        )
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), output_path)
            print(f"  -> best model saved to {output_path}")

    print(f"Done. Best val accuracy: {best_val_acc:.4f}. Model: {output_path}")


if __name__ == "__main__":
    main()
