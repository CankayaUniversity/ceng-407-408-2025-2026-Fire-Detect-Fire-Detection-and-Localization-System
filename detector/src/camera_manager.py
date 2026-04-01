"""
Backend'deki kamera listesini periyodik olarak çeker.
Her kamera için ayrı bir thread başlatır/durdurur.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

import requests

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # saniye


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
    Backend'i dinler; yeni kamera eklendiyse thread başlatır.
    Değişen RTSP URL'i olan kamera için eski thread'i durdurur, yenisini başlatır.
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
            logger.warning("Backend kamera listesi alınamadı: HTTP %s", resp.status_code)
        except Exception as exc:
            logger.warning("Backend'e bağlanılamadı: %s", exc)
        return None

    def _start_camera(self, entry: CameraEntry) -> None:
        stop_event = threading.Event()
        self._stop_flags[entry.camera_id] = stop_event
        t = self._factory(entry)
        t.daemon = True
        t.start()
        self._active[entry.camera_id] = (entry, t)
        logger.info("Kamera thread başlatıldı: %s", entry)

    def _stop_camera(self, camera_id: int) -> None:
        flag = self._stop_flags.pop(camera_id, None)
        if flag:
            flag.set()
        self._active.pop(camera_id, None)
        logger.info("Kamera thread durduruldu: id=%d", camera_id)

    def sync(self) -> None:
        """Backend ile senkronize et — yeni kameraları başlat, değişenleri/ölenlerini yenile."""
        entries = self._fetch_cameras()
        if entries is None:
            return

        new_map = {e.camera_id: e for e in entries}

        with self._lock:
            for cid in list(self._active):
                current_entry, thread = self._active[cid]
                new_entry = new_map.get(cid)
                if new_entry is None:
                    logger.info("Kamera kaldırıldı (backend'de yok): %s", current_entry)
                    self._stop_camera(cid)
                elif new_entry != current_entry:
                    logger.info(
                        "Kamera güncellendi (%s -> %s) — thread yenileniyor",
                        current_entry.rtsp_url,
                        new_entry.rtsp_url,
                    )
                    self._stop_camera(cid)
                elif not thread.is_alive():
                    # Thread beklenmedik şekilde öldü — yeniden başlat
                    logger.warning(
                        "Kamera thread'i durdu, yeniden başlatılıyor: %s", current_entry
                    )
                    self._active.pop(cid, None)

            # Yeni / yenilenen / yeniden başlatılacak kameraları başlat
            for cid, entry in new_map.items():
                if cid not in self._active:
                    self._start_camera(entry)

    def run_loop(self) -> None:
        """Ana thread'den çağrılır; sonsuza kadar senkronize eder."""
        logger.info("CameraManager başlatıldı (poll=%ds)", POLL_INTERVAL)
        while True:
            self.sync()
            time.sleep(POLL_INTERVAL)
