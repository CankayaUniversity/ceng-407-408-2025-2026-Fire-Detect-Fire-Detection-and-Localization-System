from __future__ import annotations

import threading
import time
from typing import Generator, Tuple
from urllib.parse import urlparse, urlunparse

import cv2
import os
import logging

logger = logging.getLogger(__name__)


def _replace_url_port(url: str, port: int) -> str | None:
    parsed = urlparse(url)
    if not parsed.hostname:
        return None

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth += f":{parsed.password}"
        auth += "@"

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{auth}{host}:{port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _hls_fallback_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "rtsp" or not parsed.hostname:
        return None

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    path = parsed.path or "/stream"
    if not path.endswith(".m3u8"):
        path = path.rstrip("/") + "/index.m3u8"
    return urlunparse(("http", f"{host}:8888", path, "", "", ""))


def _candidate_sources(source: str) -> list[str]:
    candidates = [source]
    if not source.lower().startswith("rtsp://"):
        return candidates

    parsed = urlparse(source)
    if parsed.port != 8554:
        rtsp_8554 = _replace_url_port(source, 8554)
        if rtsp_8554 and rtsp_8554 not in candidates:
            candidates.append(rtsp_8554)

    hls_url = _hls_fallback_url(source)
    if hls_url and hls_url not in candidates:
        candidates.append(hls_url)
    return candidates


class StreamReader:
    """
    Thin wrapper around OpenCV VideoCapture.

    Supports:
      - numeric string (\"0\", \"1\") for webcam index
      - RTSP URL
      - video file path
    """

    def __init__(self, source: str):
        self.source = source
        # Convert numeric source like "0" to int for webcam
        src = int(source) if source.isdigit() else source

        # On Windows, default backend (MSMF) can fail with -1072875772
        # when another app touched the camera. Try DirectShow first.
        is_windows = os.name == "nt"
        cap = None
        opened_source = src
        if is_windows and isinstance(src, int):
            cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = None

        if cap is None:
            candidate_sources = _candidate_sources(src) if isinstance(src, str) else [src]
            for candidate in candidate_sources:
                if isinstance(candidate, str) and candidate.lower().startswith("rtsp://"):
                    os.environ.setdefault(
                        "OPENCV_FFMPEG_CAPTURE_OPTIONS",
                        "rtsp_transport;tcp|fflags;nobuffer|max_delay;0",
                    )
                cap = cv2.VideoCapture(candidate)
                if cap.isOpened():
                    opened_source = candidate
                    if candidate != src:
                        logger.info("Opened fallback video source: %s -> %s", src, candidate)
                    break
                cap.release()
                cap = None

        self.cap = cap
        self.source = str(opened_source)
        self._is_stream = isinstance(opened_source, str) and opened_source.lower().startswith(("rtsp://", "http://", "https://"))
        self._lock = threading.Lock()
        self._latest_frame = None
        self._stopped = False
        self._reader_thread = None

        if self.cap is None or not self.cap.isOpened():
            tried = _candidate_sources(source) if isinstance(source, str) else [source]
            raise RuntimeError(f"Cannot open video source: {source}; tried: {tried}")

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if self._is_stream:
            self._reader_thread = threading.Thread(target=self._read_latest, daemon=True)
            self._reader_thread.start()

    def _read_latest(self) -> None:
        while not self._stopped:
            ok, frame = self.cap.read()
            if not ok or frame is None:
                time.sleep(0.02)
                continue
            with self._lock:
                self._latest_frame = frame

    def frames(self) -> Generator[Tuple[int, "cv2.Mat"], None, None]:
        index = 0
        if self._is_stream:
            while not self._stopped:
                with self._lock:
                    frame = None if self._latest_frame is None else self._latest_frame.copy()
                if frame is None:
                    time.sleep(0.02)
                    continue
                yield index, frame
                index += 1
                time.sleep(0.03)
            return

        while True:
            ok, frame = self.cap.read()
            if not ok or frame is None:
                break
            yield index, frame
            index += 1

    def release(self) -> None:
        self._stopped = True
        if self._reader_thread is not None and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()


