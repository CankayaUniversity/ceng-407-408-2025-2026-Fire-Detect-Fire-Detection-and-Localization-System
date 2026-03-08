from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import requests

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


class BackendNotifier:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.backend_base_url.rstrip("/")
        self.endpoint = self.base_url + self.settings.incidents_detected_path

        # Ensure snapshot directory exists
        snapshot_dir = Path(self.settings.snapshot_dir)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir = snapshot_dir

    def _save_snapshot(self, camera_id: int, frame) -> str:
        """
        Save frame as JPEG image and return local path.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"camera_{camera_id}_{timestamp}.jpg"
        path = self.snapshot_dir / filename
        ok = cv2.imwrite(str(path), frame)
        if not ok:
            logger.warning("Failed to write snapshot to %s", path)
        return str(path)

    def _build_snapshot_url(self, local_path: str) -> str:
        """
        Build snapshot_url to send to backend.

        For MVP we simply send the local path. If public_snapshot_base_url
        is configured, we send that URL instead.
        """
        if self.settings.public_snapshot_base_url:
            base = self.settings.public_snapshot_base_url.rstrip("/")
            filename = os.path.basename(local_path)
            return f"{base}/{filename}"
        return local_path

    def send_incident(self, camera_id: int, frame, confidence: float) -> None:
        snapshot_path = self._save_snapshot(camera_id, frame)
        snapshot_url = self._build_snapshot_url(snapshot_path)

        payload = {
            "camera_id": camera_id,
            "confidence": round(float(confidence), 3),
            "snapshot_url": snapshot_url,
        }

        headers = {"Content-Type": "application/json"}
        if self.settings.detector_api_key:
            headers["X-Detector-API-Key"] = self.settings.detector_api_key

        try:
            resp = requests.post(self.endpoint, json=payload, headers=headers, timeout=5)
            if resp.status_code in (200, 201):
                logger.info(
                    "Incident sent for camera_id=%s (confidence=%.2f, snapshot=%s)",
                    camera_id,
                    confidence,
                    snapshot_url,
                )
            elif resp.status_code >= 300:
                logger.warning(
                    "Backend rejected incident (status=%s): %s", resp.status_code, resp.text
                )
        except requests.RequestException as exc:
            logger.error("Error sending incident to backend: %s", exc)


