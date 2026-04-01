from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights

from .detector import BaseFireDetector, DetectionResult

logger = logging.getLogger(__name__)

# ImageNet normalization (used by pretrained MobileNetV2)
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
INPUT_SIZE = 224

# Default threshold — overridden by training metadata JSON if present
FIRE_CONFIDENCE_THRESHOLD = 0.55

# Class index for fire in 2-class setup: 0 = no_fire, 1 = fire
FIRE_CLASS_INDEX = 1

# ── HSV renk filtresi sabitleri ────────────────────────────────────────────────
# Kızıl/turuncu/sarı tonlar (yangın renkleri)
_HSV_FIRE_LOWER1 = np.array([0,   80, 100], dtype=np.uint8)   # kırmızı-turuncu (düşük hue)
_HSV_FIRE_UPPER1 = np.array([35, 255, 255], dtype=np.uint8)
_HSV_FIRE_LOWER2 = np.array([160, 80, 100], dtype=np.uint8)   # kırmızı (yüksek hue - sarmalanmış)
_HSV_FIRE_UPPER2 = np.array([180, 255, 255], dtype=np.uint8)

# Bir frame'in "yangın renkli" sayılması için gereken minimum piksel oranı
# Gerçek yangın / alev → genellikle %2+ piksel
# Normal oda / yüz / bilgisayar ekranı → genellikle <%1
_MIN_FIRE_PIXEL_RATIO = 0.06   # %6 — gerçek alev net görülmeli, cilt tonu/ışık filtre edilmeli


def _build_model(num_classes: int = 2) -> nn.Module:
    """
    MobileNetV2 with pretrained ImageNet backbone.
    Classifier head matches train_fire_model.py build_model().
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
    return model


def _load_threshold_from_metadata(model_path: Path) -> float:
    """
    Load recommended threshold from training metadata JSON if it exists.
    Falls back to FIRE_CONFIDENCE_THRESHOLD if not found.
    """
    meta_path = model_path.with_suffix(".json")
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            thresh = float(meta.get("recommended_threshold", FIRE_CONFIDENCE_THRESHOLD))
            logger.info("CNN detector: using threshold %.2f from %s", thresh, meta_path)
            return thresh
        except Exception as e:
            logger.warning("CNN detector: could not read metadata %s: %s", meta_path, e)
    return FIRE_CONFIDENCE_THRESHOLD


def _has_fire_colors(arr: np.ndarray) -> tuple[bool, float]:
    """
    HSV renk analizi ile frame'de yangın renginin olup olmadığını kontrol eder.
    Kızıl / turuncu / sarı yüksek doygunluklu pikselleri sayar.
    Döndürür: (yeterli_renk_var_mı, oran)
    """
    try:
        hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, _HSV_FIRE_LOWER1, _HSV_FIRE_UPPER1)
        mask2 = cv2.inRange(hsv, _HSV_FIRE_LOWER2, _HSV_FIRE_UPPER2)
        fire_pixels = int(cv2.countNonZero(mask1)) + int(cv2.countNonZero(mask2))
        total_pixels = arr.shape[0] * arr.shape[1]
        ratio = fire_pixels / max(total_pixels, 1)
        return ratio >= _MIN_FIRE_PIXEL_RATIO, ratio
    except Exception:
        return True, 0.0  # hata durumunda CNN'e bırak


def _preprocess_frame(frame: np.ndarray) -> torch.Tensor:
    """
    BGR -> RGB, resize 224x224, normalize, to tensor with batch dim.
    Returns tensor of shape (1, 3, 224, 224) on CPU, float32.
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE))
    tensor = torch.from_numpy(resized).permute(2, 0, 1).float().div(255.0)
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    normalized = (tensor - mean) / std
    return normalized.unsqueeze(0)


class CNNFireDetector(BaseFireDetector):
    """
    PyTorch CNN fire detector — MobileNetV2 + 2-class head (no_fire / fire).
    CPU inference. Threshold auto-loaded from training metadata JSON.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        threshold: float | None = None,
    ) -> None:
        self._device = torch.device("cpu")
        self.model_path = Path(model_path) if model_path else None
        self._model = self._load_model()
        # Prefer explicit threshold, then metadata JSON, then default
        if threshold is not None:
            self._threshold = threshold
        elif self.model_path:
            self._threshold = _load_threshold_from_metadata(self.model_path)
        else:
            self._threshold = FIRE_CONFIDENCE_THRESHOLD
        logger.info("CNN detector ready. threshold=%.2f", self._threshold)

    def _load_model(self) -> nn.Module:
        """Build model and load weights from disk if available."""
        model = _build_model(num_classes=2)
        if self.model_path and self.model_path.exists():
            try:
                state = torch.load(self.model_path, map_location="cpu", weights_only=True)
                model.load_state_dict(state, strict=True)
                logger.info("CNN detector: loaded weights from %s", self.model_path)
            except Exception as e:
                logger.warning(
                    "CNN detector: failed to load weights from %s: %s — random head (will not detect fire correctly)",
                    self.model_path, e,
                )
        else:
            logger.warning(
                "CNN detector: model file not found (%s). "
                "Train a model first: python -m training.train_fire_model",
                self.model_path,
            )
        model.to(self._device)
        model.eval()
        return model

    def detect(self, frame: Any) -> DetectionResult:
        if frame is None:
            return DetectionResult(False, 0.0, 0.0, 0.0)
        if self._model is None:
            return DetectionResult(False, 0.0, 0.0, 0.0)
        try:
            arr = np.asarray(frame)

            # 1) Siyah / sinyal-yok frame filtresi
            mean_brightness = float(arr.mean())
            std_brightness = float(arr.std())
            if mean_brightness < 8.0 or std_brightness < 5.0:
                return DetectionResult(False, 0.0, 0.0, 0.0)

            # 2) HSV renk ön filtresi — CNN'den önce ucuz kontrol
            has_colors, color_ratio = _has_fire_colors(arr)
            if not has_colors:
                logger.debug("HSV filtresi: yangın rengi yok (oran=%.3f) → atlandı", color_ratio)
                return DetectionResult(False, 0.0, 0.0, 0.0)

            batch = _preprocess_frame(arr)
            batch = batch.to(self._device)
            with torch.no_grad():
                logits = self._model(batch)
            probs = torch.softmax(logits, dim=1)
            fire_prob = probs[0][FIRE_CLASS_INDEX].item()
            has_fire = fire_prob >= self._threshold
            return DetectionResult(
                has_fire=has_fire,
                confidence=fire_prob,
                fire_ratio=fire_prob,
                largest_blob_ratio=0.0,
            )
        except Exception as e:
            logger.exception("CNN detector inference failed: %s", e)
            return DetectionResult(False, 0.0, 0.0, 0.0)
