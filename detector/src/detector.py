from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    has_fire: bool
    confidence: float
    fire_ratio: float  # ratio of fire pixels
    largest_blob_ratio: float  # ratio of largest contour to frame (for logging)


class MockFireDetector:
    """
    MVP fire detector.

    - HSV-based fire-like pixel ratio + configurable thresholds.
    - Filters out very small regions (largest blob must exceed min_fire_area_ratio).
    - Returns has_fire only when confidence >= confidence_threshold.
    """

    def __init__(
        self,
        fire_threshold: float = 0.02,
        min_fire_area_ratio: float = 0.005,
        confidence_threshold: float = 0.25,
    ):
        self.fire_threshold = fire_threshold
        self.min_fire_area_ratio = min_fire_area_ratio
        self.confidence_threshold = confidence_threshold

    def detect(self, frame) -> DetectionResult:
        if frame is None:
            return DetectionResult(False, 0.0, 0.0, 0.0)

        # Downscale for speed
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        # Rough range for fire-like colors (orange / yellow)
        lower = np.array([10, 100, 150])  # H, S, V
        upper = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)

        total_pixels = mask.size
        fire_pixels = np.count_nonzero(mask)
        ratio = fire_pixels / float(total_pixels) if total_pixels else 0.0
        confidence = float(min(1.0, ratio / 0.1))

        # Largest connected "fire" region (filter tiny speckles)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        largest_area = max((cv2.contourArea(c) for c in contours), default=0)
        largest_blob_ratio = largest_area / float(total_pixels) if total_pixels else 0.0

        # Require: enough pixels, enough confidence, and blob not too small
        has_fire = (
            ratio >= self.fire_threshold
            and confidence >= self.confidence_threshold
            and largest_blob_ratio >= self.min_fire_area_ratio
        )

        if ratio >= self.fire_threshold or largest_blob_ratio >= self.min_fire_area_ratio:
            logger.debug(
                "detect: fire_ratio=%.4f largest_blob_ratio=%.4f confidence=%.2f -> %s",
                ratio,
                largest_blob_ratio,
                confidence,
                "FIRE" if has_fire else "no_fire (threshold or size filter)",
            )

        return DetectionResult(
            has_fire=has_fire,
            confidence=confidence,
            fire_ratio=ratio,
            largest_blob_ratio=largest_blob_ratio,
        )
