"""
Periodically fetches the camera list from the backend.
Starts and stops one worker thread per camera.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

import requests

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


class CameraEntry:
    def __init__(self, camera_id: int, name: str, rtsp_url: str):
        self.camera_id = camera_id
        self.name = name
        self.rtsp_url = rtsp_url

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CameraEntry):
            return False
        return self.camera_id == other.camera_id and self.rtsp_url == other.rtsp_url

    def __repr__(self) -> str:
        return f"Camera(id={self.camera_id}, name={self.name!r}, rtsp={self.rtsp_url!r})"


class DynamicCameraManager:
    """
    Watches the backend camera list and starts a worker for newly added cameras.
    Restarts the worker when a camera RTSP URL changes.
    """

    def __init__(
        self,
        backend_url: str,
        api_key: str | None,
        thread_factory: Callable[[CameraEntry], threading.Thread],
    ):
        self._backend_url = backend_url.rstrip("/")
        self._api_key = api_key
        self._factory = thread_factory
        self._active: dict[int, tuple[CameraEntry, threading.Thread]] = {}
        self._stop_flags: dict[int, threading.Event] = {}
        self._lock = threading.Lock()

    def _fetch_cameras(self) -> list[CameraEntry] | None:
        url = f"{self._backend_url}/cameras/detector-list"
        headers = {}
        if self._api_key:
            headers["X-Detector-API-Key"] = self._api_key
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    CameraEntry(c["id"], c["name"], c["rtsp_url"])
                    for c in data.get("cameras", [])
                    if c.get("rtsp_url")
                ]
            logger.warning("Could not fetch backend camera list: HTTP %s", resp.status_code)
        except Exception as exc:
            logger.warning("Could not connect to backend: %s", exc)
        return None

    def _start_camera(self, entry: CameraEntry) -> None:
        stop_event = threading.Event()
        self._stop_flags[entry.camera_id] = stop_event
        thread = self._factory(entry)
        thread.daemon = True
        thread.start()
        self._active[entry.camera_id] = (entry, thread)
        logger.info("Camera thread started: %s", entry)

    def _stop_camera(self, camera_id: int) -> None:
        flag = self._stop_flags.pop(camera_id, None)
        if flag:
            flag.set()
        self._active.pop(camera_id, None)
        logger.info("Camera thread stopped: id=%d", camera_id)

    def sync(self) -> None:
        """Synchronize with the backend: start new cameras and refresh changed or stopped workers."""
        entries = self._fetch_cameras()
        if entries is None:
            return

        new_map = {e.camera_id: e for e in entries}

        with self._lock:
            for cid in list(self._active):
                current_entry, thread = self._active[cid]
                new_entry = new_map.get(cid)
                if new_entry is None:
                    logger.info("Camera removed from backend: %s", current_entry)
                    self._stop_camera(cid)
                elif new_entry != current_entry:
                    logger.info(
                        "Camera updated (%s -> %s); restarting worker",
                        current_entry.rtsp_url,
                        new_entry.rtsp_url,
                    )
                    self._stop_camera(cid)
                elif not thread.is_alive():
                    logger.warning("Camera thread stopped unexpectedly; restarting: %s", current_entry)
                    self._active.pop(cid, None)

            for cid, entry in new_map.items():
                if cid not in self._active:
                    self._start_camera(entry)

    def run_loop(self) -> None:
        """Called from the main thread and synchronizes forever."""
        logger.info("CameraManager started (poll=%ds)", POLL_INTERVAL)
        while True:
            self.sync()
            time.sleep(POLL_INTERVAL)
