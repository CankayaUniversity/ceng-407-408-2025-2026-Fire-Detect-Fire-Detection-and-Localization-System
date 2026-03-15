from __future__ import annotations

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
FIRE_CONFIDENCE_THRESHOLD = 0.7

# Class index for fire in 2-class setup: 0 = no_fire, 1 = fire
FIRE_CLASS_INDEX = 1


def _build_model(num_classes: int = 2) -> nn.Module:
    """Build MobileNetV2 with pretrained backbone and 2-class classifier head."""
    weights = MobileNet_V2_Weights.DEFAULT
    model = mobilenet_v2(weights=weights)
    # Replace classifier: original last layer is Linear(1280, 1000)
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(model.last_channel, num_classes),
    )
    return model


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
    PyTorch CNN fire detector using MobileNetV2 (pretrained backbone)
    with a 2-class head (no_fire / fire). CPU inference only.
    """

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self._model = self._load_model()
        self._device = torch.device("cpu")

    def _load_model(self) -> nn.Module | None:
        """Build MobileNetV2 2-class model; load weights from disk if path exists."""
        model = _build_model(num_classes=2)
        if self.model_path and self.model_path.exists():
            try:
                state = torch.load(self.model_path, map_location="cpu", weights_only=True)
                model.load_state_dict(state, strict=True)
                logger.info("CNN detector: loaded weights from %s", self.model_path)
            except Exception as e:
                logger.warning("CNN detector: failed to load weights from %s: %s", self.model_path, e)
        else:
            logger.info(
                "CNN detector: no model path or file missing; using pretrained backbone + random 2-class head (no fire until trained)."
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
            batch = _preprocess_frame(np.asarray(frame))
            batch = batch.to(self._device)
            with torch.no_grad():
                logits = self._model(batch)
            probs = torch.softmax(logits, dim=1)
            fire_prob = probs[0][FIRE_CLASS_INDEX].item()
            has_fire = fire_prob >= FIRE_CONFIDENCE_THRESHOLD
            return DetectionResult(
                has_fire=has_fire,
                confidence=fire_prob,
                fire_ratio=fire_prob,
                largest_blob_ratio=0.0,
            )
        except Exception as e:
            logger.exception("CNN detector inference failed: %s", e)
            return DetectionResult(False, 0.0, 0.0, 0.0)
