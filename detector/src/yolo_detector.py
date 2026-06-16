from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .detector import BaseFireDetector, DetectionResult

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - handled at runtime if dependency missing
    YOLO = None


@dataclass
class _InferenceRequest:
    frame: np.ndarray
    done: threading.Event = field(default_factory=threading.Event)
    result: DetectionResult | None = None
    error: Exception | None = None


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
        batch_size: int = 4,
        batch_wait_ms: int = 20,
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
        self._batch_size = max(1, int(batch_size))
        self._batch_wait_seconds = max(0.0, float(batch_wait_ms) / 1000.0)
        self._model = YOLO(str(self.model_path))
        self._positive_class_ids = self._resolve_positive_class_ids()
        self._request_queue: queue.Queue[_InferenceRequest] = queue.Queue()
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="yolo-inference-worker",
            daemon=True,
        )
        self._worker.start()

        logger.info(
            "YOLO detector ready. model=%s threshold=%.2f imgsz=%d batch_size=%d batch_wait_ms=%d positive_classes=%s",
            self.model_path,
            self._threshold,
            self._imgsz,
            self._batch_size,
            int(self._batch_wait_seconds * 1000),
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
            request = _InferenceRequest(frame=arr)
            self._request_queue.put(request)

            if not request.done.wait(timeout=30.0):
                logger.error("YOLO detector inference timed out")
                return DetectionResult(False, 0.0, 0.0, 0.0)

            if request.error:
                raise request.error

            return request.result or DetectionResult(False, 0.0, 0.0, 0.0)
        except Exception as e:
            logger.exception("YOLO detector inference failed: %s", e)
            return DetectionResult(False, 0.0, 0.0, 0.0)

    def _worker_loop(self) -> None:
        while True:
            first = self._request_queue.get()
            batch = [first]
            deadline = time.monotonic() + self._batch_wait_seconds

            while len(batch) < self._batch_size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    batch.append(self._request_queue.get(timeout=remaining))
                except queue.Empty:
                    break

            try:
                results = self._model.predict(
                    source=[request.frame for request in batch],
                    conf=self._threshold,
                    imgsz=self._imgsz,
                    verbose=False,
                    device="cpu",
                )
                if len(results) != len(batch):
                    raise RuntimeError(
                        f"YOLO returned {len(results)} result(s) for batch of {len(batch)} frame(s)"
                    )
                for request, result in zip(batch, results):
                    request.result = self._result_from_prediction(result, request.frame)
            except Exception as exc:
                logger.exception("YOLO batch inference failed: %s", exc)
                for request in batch:
                    request.error = exc
            finally:
                for request in batch:
                    request.done.set()

    def _result_from_prediction(self, result: Any, frame: np.ndarray) -> DetectionResult:
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return DetectionResult(False, 0.0, 0.0, 0.0)

        frame_h, frame_w = frame.shape[:2]
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
