"""
Evaluate the runtime CNN detector on a labeled dataset.

Supports either:
  1) training/dataset/<split>/fire and training/dataset/<split>/no_fire
  2) <dataset-root>/fire and <dataset-root>/no_fire

This evaluates the deployed inference path in src/cnn_detector.py, including
its dark-frame checks and HSV prefilter, so the results match runtime behavior
more closely than training-only metrics.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

from src.cnn_detector import CNNFireDetector, _has_fire_colors

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
NO_FIRE = 0
FIRE = 1


@dataclass
class SamplePrediction:
    path: str
    label: int
    confidence: float
    predicted: int
    dark_rejected: bool
    hsv_rejected: bool


class Metrics:
    def __init__(self) -> None:
        self.tp = 0
        self.fp = 0
        self.tn = 0
        self.fn = 0

    def update(self, predicted: int, label: int) -> None:
        if predicted == FIRE and label == FIRE:
            self.tp += 1
        elif predicted == FIRE and label == NO_FIRE:
            self.fp += 1
        elif predicted == NO_FIRE and label == NO_FIRE:
            self.tn += 1
        else:
            self.fn += 1

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total else 0.0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p = self.precision
        r = self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def as_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "tn": self.tn,
            "fn": self.fn,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


def resolve_dataset_root(data_dir: Path, split: str, dataset_root: str | None) -> Path:
    if dataset_root:
        root = Path(dataset_root)
    else:
        root = data_dir / split

    fire_dir = root / "fire"
    no_fire_dir = root / "no_fire"
    if not fire_dir.is_dir() or not no_fire_dir.is_dir():
        raise FileNotFoundError(
            f"Expected dataset folders:\n  {fire_dir}\n  {no_fire_dir}"
        )
    return root


def list_images(folder: Path) -> list[Path]:
    return sorted(
        [
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        ]
    )


def analyze_frame(arr: np.ndarray) -> tuple[bool, bool]:
    mean_brightness = float(arr.mean())
    std_brightness = float(arr.std())
    dark_rejected = mean_brightness < 8.0 or std_brightness < 5.0
    has_fire_colors, _ = _has_fire_colors(arr)
    hsv_rejected = not has_fire_colors
    return dark_rejected, hsv_rejected


def evaluate_predictions(
    predictions: list[SamplePrediction],
    threshold: float,
) -> tuple[Metrics, list[SamplePrediction], list[SamplePrediction]]:
    metrics = Metrics()
    false_positives: list[SamplePrediction] = []
    false_negatives: list[SamplePrediction] = []

    for pred in predictions:
        predicted = FIRE if pred.confidence >= threshold else NO_FIRE
        metrics.update(predicted, pred.label)
        if predicted == FIRE and pred.label == NO_FIRE:
            false_positives.append(
                SamplePrediction(
                    path=pred.path,
                    label=pred.label,
                    confidence=pred.confidence,
                    predicted=predicted,
                    dark_rejected=pred.dark_rejected,
                    hsv_rejected=pred.hsv_rejected,
                )
            )
        elif predicted == NO_FIRE and pred.label == FIRE:
            false_negatives.append(
                SamplePrediction(
                    path=pred.path,
                    label=pred.label,
                    confidence=pred.confidence,
                    predicted=predicted,
                    dark_rejected=pred.dark_rejected,
                    hsv_rejected=pred.hsv_rejected,
                )
            )

    false_positives.sort(key=lambda item: item.confidence, reverse=True)
    false_negatives.sort(key=lambda item: item.confidence)
    return metrics, false_positives, false_negatives


def sweep_thresholds(
    predictions: list[SamplePrediction],
    min_recall: float,
) -> tuple[dict, dict]:
    best_f1 = {"threshold": 0.5, "f1": -1.0, "precision": 0.0, "recall": 0.0}
    best_min_recall = {"threshold": 0.5, "f1": -1.0, "precision": 0.0, "recall": 0.0}

    for raw in range(5, 96):
        threshold = raw / 100.0
        metrics, _, _ = evaluate_predictions(predictions, threshold)
        if metrics.f1 > best_f1["f1"]:
            best_f1 = {
                "threshold": threshold,
                "f1": metrics.f1,
                "precision": metrics.precision,
                "recall": metrics.recall,
            }
        if metrics.recall >= min_recall and metrics.f1 > best_min_recall["f1"]:
            best_min_recall = {
                "threshold": threshold,
                "f1": metrics.f1,
                "precision": metrics.precision,
                "recall": metrics.recall,
            }

    return best_f1, best_min_recall


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Flame Scope CNN detector")
    parser.add_argument("--data-dir", type=str, default="training/dataset")
    parser.add_argument("--split", type=str, default="test", help="test | val | train")
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help="Alternative folder containing fire/ and no_fire/ directly",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="training/fire_model.pt",
        help="Path to .pt weights file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Override threshold. Default: detector metadata or built-in default",
    )
    parser.add_argument(
        "--min-recall",
        type=float,
        default=0.90,
        help="Recall floor for recommended threshold sweep",
    )
    parser.add_argument(
        "--max-mistakes",
        type=int,
        default=20,
        help="How many false positives/negatives to include in the JSON report",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional report output path",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    dataset_root = resolve_dataset_root(data_dir, args.split, args.dataset_root)
    fire_paths = list_images(dataset_root / "fire")
    no_fire_paths = list_images(dataset_root / "no_fire")

    if not fire_paths and not no_fire_paths:
        raise FileNotFoundError(
            f"No image files found under {dataset_root}. "
            "Expected files with extensions like .jpg, .png, or .webp."
        )

    detector = CNNFireDetector(model_path=args.model_path, threshold=args.threshold)
    threshold = float(getattr(detector, "_threshold", 0.5))

    print("\n============================================================")
    print("  Flame Scope - CNN Evaluation")
    print(f"  Dataset   : {dataset_root.resolve()}")
    print(f"  Model     : {Path(args.model_path).resolve()}")
    print(f"  Threshold : {threshold:.2f}")
    print(f"  Fire imgs : {len(fire_paths)}")
    print(f"  No-fire   : {len(no_fire_paths)}")
    print("============================================================\n")

    predictions: list[SamplePrediction] = []
    unreadable = 0

    for label, paths in ((FIRE, fire_paths), (NO_FIRE, no_fire_paths)):
        for path in paths:
            arr = cv2.imread(str(path))
            if arr is None:
                unreadable += 1
                continue
            dark_rejected, hsv_rejected = analyze_frame(arr)
            result = detector.detect(arr)
            predictions.append(
                SamplePrediction(
                    path=str(path),
                    label=label,
                    confidence=float(result.confidence),
                    predicted=FIRE if result.confidence >= threshold else NO_FIRE,
                    dark_rejected=dark_rejected,
                    hsv_rejected=hsv_rejected,
                )
            )

    metrics, false_positives, false_negatives = evaluate_predictions(predictions, threshold)
    best_f1, best_min_recall = sweep_thresholds(predictions, args.min_recall)

    fire_count = sum(1 for item in predictions if item.label == FIRE)
    no_fire_count = sum(1 for item in predictions if item.label == NO_FIRE)
    dark_reject_fire = sum(1 for item in predictions if item.label == FIRE and item.dark_rejected)
    hsv_reject_fire = sum(1 for item in predictions if item.label == FIRE and item.hsv_rejected)
    dark_reject_total = sum(1 for item in predictions if item.dark_rejected)
    hsv_reject_total = sum(1 for item in predictions if item.hsv_rejected)

    print("Current-threshold metrics")
    print(
        f"  acc={metrics.accuracy:.4f}  prec={metrics.precision:.4f}  "
        f"rec={metrics.recall:.4f}  f1={metrics.f1:.4f}"
    )
    print(
        f"  TP={metrics.tp}  FP={metrics.fp}  TN={metrics.tn}  FN={metrics.fn}"
    )
    print()
    print("Threshold sweep")
    print(
        f"  best_f1_threshold={best_f1['threshold']:.2f}  "
        f"f1={best_f1['f1']:.4f}  prec={best_f1['precision']:.4f}  "
        f"rec={best_f1['recall']:.4f}"
    )
    if best_min_recall["f1"] >= 0:
        print(
            f"  best_threshold_with_recall>={args.min_recall:.2f} -> "
            f"{best_min_recall['threshold']:.2f}  "
            f"f1={best_min_recall['f1']:.4f}  prec={best_min_recall['precision']:.4f}  "
            f"rec={best_min_recall['recall']:.4f}"
        )
    else:
        print(f"  no threshold reached recall>={args.min_recall:.2f}")
    print()
    print("Prefilter diagnostics")
    print(
        f"  dark_rejected={dark_reject_total}/{len(predictions)}  "
        f"hsv_rejected={hsv_reject_total}/{len(predictions)}"
    )
    print(
        f"  fire_dark_rejected={dark_reject_fire}/{fire_count or 1}  "
        f"fire_hsv_rejected={hsv_reject_fire}/{fire_count or 1}"
    )
    if unreadable:
        print(f"  unreadable_images={unreadable}")

    report = {
        "dataset_root": str(dataset_root.resolve()),
        "model_path": str(Path(args.model_path).resolve()),
        "image_counts": {"fire": fire_count, "no_fire": no_fire_count},
        "threshold": threshold,
        "current_metrics": metrics.as_dict(),
        "best_f1_threshold": best_f1,
        "best_min_recall_threshold": best_min_recall,
        "diagnostics": {
            "unreadable_images": unreadable,
            "dark_rejected_total": dark_reject_total,
            "hsv_rejected_total": hsv_reject_total,
            "fire_dark_rejected": dark_reject_fire,
            "fire_hsv_rejected": hsv_reject_fire,
        },
        "false_positives": [asdict(item) for item in false_positives[: args.max_mistakes]],
        "false_negatives": [asdict(item) for item in false_negatives[: args.max_mistakes]],
    }

    output_json = Path(args.output_json) if args.output_json else dataset_root / "evaluation_report.json"
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to: {output_json.resolve()}")


if __name__ == "__main__":
    main()
