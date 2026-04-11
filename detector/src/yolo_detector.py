from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from .detector import BaseFireDetector, DetectionResult

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - handled at runtime if dependency missing
    YOLO = None


class YOLOFireDetector(BaseFireDetector):
    """
    YOLO-based fire detector.

    Any detection whose class name contains "fire" or "smoke" can trigger an incident.
    The detector returns the max confidence among relevant boxes and uses the largest
    relevant box area as a lightweight proxy for fire_ratio / largest_blob_ratio.
    """

    def __init__(
        self,
        model_path: str | Path,
        confidence_threshold: float = 0.4,
        imgsz: int = 512,
    ) -> None:
        if YOLO is None:
            raise RuntimeError(
                "ultralytics is not installed. Install it in detector/.venv first: "
                "python -m pip install ultralytics"
            )

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise RuntimeError(f"YOLO model file not found: {self.model_path}")

        self._threshold = confidence_threshold
        self._imgsz = imgsz
        self._model = YOLO(str(self.model_path))
        self._positive_class_ids = self._resolve_positive_class_ids()

        logger.info(
            "YOLO detector ready. model=%s threshold=%.2f imgsz=%d positive_classes=%s",
            self.model_path,
            self._threshold,
            self._imgsz,
            sorted(self._positive_class_ids),
        )

    def _resolve_positive_class_ids(self) -> set[int]:
        names = getattr(self._model.model, "names", None) or getattr(self._model, "names", None) or {}
        positive_ids: set[int] = set()

        if isinstance(names, list):
            items = enumerate(names)
        else:
            items = names.items()

        for idx, name in items:
            name_str = str(name).strip().lower()
            if "fire" in name_str or "smoke" in name_str:
                positive_ids.add(int(idx))

        if not positive_ids:
            logger.warning(
                "YOLO detector: could not infer fire/smoke classes from model names=%s. "
                "Falling back to all classes.",
                names,
            )
            if isinstance(names, list):
                positive_ids = {int(i) for i, _ in enumerate(names)}
            else:
                positive_ids = {int(i) for i in names.keys()}

        return positive_ids

    def detect(self, frame: Any) -> DetectionResult:
        if frame is None:
            return DetectionResult(False, 0.0, 0.0, 0.0)

        try:
            arr = np.asarray(frame)
            results = self._model.predict(
                source=arr,
                conf=self._threshold,
                imgsz=self._imgsz,
                verbose=False,
                device="cpu",
            )
            if not results:
                return DetectionResult(False, 0.0, 0.0, 0.0)

            result = results[0]
            boxes = getattr(result, "boxes", None)
            if boxes is None or len(boxes) == 0:
                return DetectionResult(False, 0.0, 0.0, 0.0)

            frame_h, frame_w = arr.shape[:2]
            frame_area = max(frame_h * frame_w, 1)

            max_conf = 0.0
            largest_ratio = 0.0
            positive_count = 0

            xyxy = boxes.xyxy.cpu().numpy()
            conf = boxes.conf.cpu().numpy()
            cls = boxes.cls.cpu().numpy().astype(int)

            for box, score, class_id in zip(xyxy, conf, cls):
                if int(class_id) not in self._positive_class_ids:
                    continue

                positive_count += 1
                max_conf = max(max_conf, float(score))
                x1, y1, x2, y2 = box
                box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                largest_ratio = max(largest_ratio, box_area / frame_area)

            if positive_count == 0:
                return DetectionResult(False, 0.0, 0.0, 0.0)

            return DetectionResult(
                has_fire=max_conf >= self._threshold,
                confidence=max_conf,
                fire_ratio=largest_ratio,
                largest_blob_ratio=largest_ratio,
            )
        except Exception as e:
            logger.exception("YOLO detector inference failed: %s", e)
            return DetectionResult(False, 0.0, 0.0, 0.0)
