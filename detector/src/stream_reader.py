from __future__ import annotations

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
            cap = cv2.VideoCapture(src)

        self.cap = cap

        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source}")

    def frames(self) -> Generator[Tuple[int, "cv2.Mat"], None, None]:
        index = 0
        while True:
            ok, frame = self.cap.read()
            if not ok or frame is None:
                break
            yield index, frame
            index += 1

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()


