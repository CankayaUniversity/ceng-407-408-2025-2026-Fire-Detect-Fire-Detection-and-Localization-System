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
        self.snapshot_upload_endpoint = self.base_url + self.settings.snapshot_upload_path

        snapshot_dir = Path(self.settings.snapshot_dir)
        if not snapshot_dir.is_absolute():
            detector_dir = Path(__file__).resolve().parents[1]
            snapshot_dir = detector_dir / snapshot_dir
        snapshot_dir = snapshot_dir.resolve()
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir = snapshot_dir

    def _save_snapshot(self, camera_id: int, frame) -> str:
        """
        Save frame as JPEG image and return local path.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"camera_{camera_id}_{timestamp}.jpg"
        path = self.snapshot_dir / filename
        ok = cv2.imwrite(str(path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not ok:
            logger.warning("Failed to write snapshot to %s", path)
        return str(path)

    def _build_snapshot_url(self, local_path: str) -> str:
        """
        Build snapshot_url to send to backend.

        By default the backend serves the repository-level snapshots folder at
        /snapshots, so send a URL path instead of a local filesystem path.
        """
        filename = os.path.basename(local_path)
        if self.settings.public_snapshot_base_url:
            base = self.settings.public_snapshot_base_url.rstrip("/")
            return f"{base}/{filename}"
        return f"/snapshots/{filename}"

    def _auth_headers(self) -> dict[str, str]:
        if not self.settings.detector_api_key:
            return {}
        return {"X-Detector-API-Key": self.settings.detector_api_key}

    def _upload_snapshot(self, camera_id: int, local_path: str) -> str | None:
        """
        Upload the snapshot through the backend so Supabase credentials stay server-side.
        """
        filename = os.path.basename(local_path)
        headers = self._auth_headers()
        try:
            with open(local_path, "rb") as image_file:
                resp = requests.post(
                    self.snapshot_upload_endpoint,
                    data={"camera_id": str(camera_id)},
                    files={"image": (filename, image_file, "image/jpeg")},
                    headers=headers,
                    timeout=self.settings.snapshot_upload_timeout_seconds,
                )
            if resp.status_code in (200, 201):
                snapshot_url = resp.json().get("snapshot_url")
                if snapshot_url:
                    return snapshot_url
                logger.warning("Snapshot upload response did not include snapshot_url: %s", resp.text)
            elif resp.status_code >= 300:
                logger.warning(
                    "Backend rejected snapshot upload (status=%s): %s",
                    resp.status_code,
                    resp.text,
                )
        except (OSError, ValueError, requests.RequestException) as exc:
            logger.warning("Snapshot upload failed; falling back to local URL: %s", exc)
        return None

    def send_incident(self, camera_id: int, frame, confidence: float) -> None:
        snapshot_path = self._save_snapshot(camera_id, frame)
        snapshot_url = self._upload_snapshot(camera_id, snapshot_path) or self._build_snapshot_url(snapshot_path)

        payload = {
            "camera_id": camera_id,
            "confidence": round(float(confidence), 3),
            "snapshot_url": snapshot_url,
        }

        headers = {"Content-Type": "application/json", **self._auth_headers()}

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


