from __future__ import annotations

import threading
import time
from typing import Generator, Tuple

import cv2
import os


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
        if is_windows and isinstance(src, int):
            cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = None

        if cap is None:
            if isinstance(src, str) and src.lower().startswith("rtsp://"):
                os.environ.setdefault(
                    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
                    "rtsp_transport;tcp|fflags;nobuffer|max_delay;0",
                )
            cap = cv2.VideoCapture(src)

        self.cap = cap
        self._is_stream = isinstance(src, str) and src.lower().startswith(("rtsp://", "http://", "https://"))
        self._lock = threading.Lock()
        self._latest_frame = None
        self._stopped = False
        self._reader_thread = None

        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source}")

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


