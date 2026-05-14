from __future__ import annotations

import logging
from pathlib import Path
import threading
import time
from datetime import datetime, timedelta, timezone

import cv2
import numpy as np

from .camera_manager import CameraEntry, DynamicCameraManager
from .config import get_settings
from .detector import BaseFireDetector, DetectionResult, MockFireDetector
from .notifier import BackendNotifier
from .stream_reader import StreamReader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("flamescope.detector")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


_RETRY_DELAYS = [5, 10, 20, 30, 60]  # bağlantı hatasında bekleme süreleri (sn)
_LOBBY_DEMO_WINDOW_SECONDS = 14
_LOBBY_DEMO_START_MS = 11000


def _is_lobby_demo_camera(entry: CameraEntry) -> bool:
    return "lobby" in (entry.name or "").lower()


def _is_webcam_demo_camera(entry: CameraEntry) -> bool:
    name = (entry.name or "").lower()
    return "webcam" in name or "bilgisayar" in name


def _lobby_demo_marker_mtime() -> float | None:
    marker_path = Path(__file__).resolve().parents[2] / "demo-videos" / "lobby_fire.restart"
    try:
        return marker_path.stat().st_mtime
    except OSError:
        return None


def _frame_for_detection(entry: CameraEntry, frame):
    return frame


def _lobby_demo_video_path() -> Path:
    return Path(__file__).resolve().parents[2] / "demo-videos" / "lobby_fire.mp4"


def _risk_score_from_fire_signal(
    flame_ratio: float,
    largest_blob_ratio: float,
    min_flame_ratio: float,
    min_blob_ratio: float,
) -> float:
    """
    Camera-calibrated risk score for early warning channels.

    This is not a neural-network probability. It turns the amount of flame-colored
    pixels and the size of the strongest continuous flame region into a stable
    0-1 score that is easy to explain in the demo.
    """
    flame_strength = max(0.0, (flame_ratio - min_flame_ratio) / max(min_flame_ratio, 1e-6))
    blob_strength = max(0.0, (largest_blob_ratio - min_blob_ratio) / max(min_blob_ratio, 1e-6))
    score = 0.62 + min(0.16, flame_strength * 0.08) + min(0.20, blob_strength * 0.10)
    return float(min(0.95, score))


def _detect_calibrated_early_flame(entry: CameraEntry, frame) -> DetectionResult | None:
    """
    Sabit demo kamerasi icin erken alev kanali.

    YOLO modeli bu NIST salon videosundaki ilk 3-5 saniyelik alev formunu gec yakaliyor.
    Kameraya ozel ROI ile lambayi/sag duvari disarida birakip, genis ve kalici alev rengi
    alanini yakalayarak erken alarm uretiriz. Gercek kurulumda bu ROI kamera kalibrasyonudur.
    """
    if not _is_lobby_demo_camera(entry):
        return None

    if frame is None:
        return None

    height, width = frame.shape[:2]
    if height <= 0 or width <= 0:
        return None

    y1 = int(height * 0.05)
    y2 = int(height * 0.85)
    x1 = 0
    x2 = int(width * 0.72)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    saturated_flame = cv2.inRange(
        hsv,
        np.array([0, 120, 160], dtype=np.uint8),
        np.array([35, 255, 255], dtype=np.uint8),
    )
    mask = saturated_flame

    kernel = np.ones((5, 5), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)

    total_pixels = mask.size
    flame_pixels = int(np.count_nonzero(mask))
    flame_ratio = flame_pixels / float(total_pixels) if total_pixels else 0.0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_area = max((cv2.contourArea(contour) for contour in contours), default=0.0)
    largest_blob_ratio = largest_area / float(total_pixels) if total_pixels else 0.0

    # Pre-fire lights stay around 0.02; the first usable flame frame appears near 0.028.
    min_flame_ratio = 0.025
    min_blob_ratio = 0.022
    has_fire = flame_ratio >= min_flame_ratio and largest_blob_ratio >= min_blob_ratio
    if not has_fire:
        return None

    confidence = _risk_score_from_fire_signal(
        flame_ratio,
        largest_blob_ratio,
        min_flame_ratio,
        min_blob_ratio,
    )
    logger.debug(
        "[%s] Erken alev kanali tetiklendi. flame_ratio=%.3f largest=%.3f confidence=%.2f",
        entry.name,
        flame_ratio,
        largest_blob_ratio,
        confidence,
    )
    return DetectionResult(True, confidence, flame_ratio, largest_blob_ratio)


def _detect_webcam_small_flame(entry: CameraEntry, frame) -> DetectionResult | None:
    """
    Webcam demo icin kucuk alev kanali.

    YOLO tavan lambasini/parlamayi zaman zaman yangin sanabiliyor; bu nedenle webcam
    demosunda ust bolgeyi disarida birakip yalniz alt/orta bolgede doygun alev rengi arariz.
    Cakmak/kagit demosunda alevi kameranin alt-orta kismina getirmek en stabil sonuc verir.
    """
    if not _is_webcam_demo_camera(entry):
        return None
    if frame is None:
        return None

    height, width = frame.shape[:2]
    if height <= 0 or width <= 0:
        return None

    y1 = int(height * 0.35)
    y2 = int(height * 0.95)
    x1 = int(width * 0.08)
    x2 = int(width * 0.92)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    orange_flame = cv2.inRange(
        hsv,
        np.array([0, 95, 145], dtype=np.uint8),
        np.array([42, 255, 255], dtype=np.uint8),
    )
    hot_yellow = cv2.inRange(
        hsv,
        np.array([12, 45, 215], dtype=np.uint8),
        np.array([48, 255, 255], dtype=np.uint8),
    )
    bright_flame_core = cv2.inRange(
        hsv,
        np.array([8, 20, 235], dtype=np.uint8),
        np.array([55, 220, 255], dtype=np.uint8),
    )
    mask = cv2.bitwise_or(orange_flame, hot_yellow)

    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)

    total_pixels = mask.size
    flame_ratio = np.count_nonzero(mask) / float(total_pixels) if total_pixels else 0.0
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_contour = max(contours, key=cv2.contourArea, default=None)
    largest_area = cv2.contourArea(largest_contour) if largest_contour is not None else 0.0
    largest_blob_ratio = largest_area / float(total_pixels) if total_pixels else 0.0
    core_ratio = np.count_nonzero(bright_flame_core) / float(total_pixels) if total_pixels else 0.0

    bbox = None
    core_in_blob_ratio = 0.0
    if largest_contour is not None:
        bx, by, bw, bh = cv2.boundingRect(largest_contour)
        bbox = (x1 + bx, y1 + by, bw, bh)
        blob_core = bright_flame_core[by:by + bh, bx:bx + bw]
        core_in_blob_ratio = (
            np.count_nonzero(blob_core) / float(max(1, bw * bh))
            if blob_core.size else 0.0
        )

    min_flame_ratio = 0.004
    min_blob_ratio = 0.0018
    has_bright_core = core_ratio >= 0.0006 or core_in_blob_ratio >= 0.018
    has_fire = (
        flame_ratio >= min_flame_ratio
        and largest_blob_ratio >= min_blob_ratio
        and has_bright_core
    )
    if not has_fire:
        return None

    confidence = _risk_score_from_fire_signal(
        flame_ratio,
        largest_blob_ratio,
        min_flame_ratio,
        min_blob_ratio,
    )
    logger.info(
        "[%s] Webcam kucuk alev kanali tetiklendi. flame_ratio=%.5f largest=%.5f core=%.5f blob_core=%.5f confidence=%.2f",
        entry.name,
        flame_ratio,
        largest_blob_ratio,
        core_ratio,
        core_in_blob_ratio,
        confidence,
    )
    return DetectionResult(True, confidence, flame_ratio, largest_blob_ratio, bbox)


def _snapshot_frame_for_incident(entry: CameraEntry, frame, result: DetectionResult):
    if not _is_webcam_demo_camera(entry) or not result.bbox:
        return frame

    height, width = frame.shape[:2]
    x, y, w, h = result.bbox
    cx = x + w / 2.0
    cy = y + h / 2.0

    crop_w = int(max(520, w * 7, h * 7 * 16 / 9))
    crop_w = min(width, crop_w)
    crop_h = int(crop_w * 9 / 16)
    if crop_h > height:
        crop_h = height
        crop_w = int(crop_h * 16 / 9)

    x1 = int(max(0, min(width - crop_w, cx - crop_w / 2)))
    y1 = int(max(0, min(height - crop_h, cy - crop_h / 2)))
    crop = frame[y1:y1 + crop_h, x1:x1 + crop_w]
    if crop.size == 0:
        return frame

    return cv2.resize(crop, (1280, 720), interpolation=cv2.INTER_CUBIC)


def _send_lobby_demo_incident(
    entry: CameraEntry,
    notifier: BackendNotifier,
    consecutive_required: int,
) -> bool:
    video_path = _lobby_demo_video_path()
    if not video_path.exists():
        logger.warning("[%s] Lobby demo video bulunamadi: %s", entry.name, video_path)
        return False

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("[%s] Lobby demo video acilamadi: %s", entry.name, video_path)
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_delay = 1.0 / max(1.0, min(fps, 30.0))
    cap.set(cv2.CAP_PROP_POS_MSEC, _LOBBY_DEMO_START_MS)
    max_frames = int(fps * 8)
    consecutive_fire_count = 0

    try:
        for idx in range(max_frames):
            ok, frame = cap.read()
            if not ok or frame is None:
                return False

            result = _detect_calibrated_early_flame(entry, frame)
            if not result or not result.has_fire:
                consecutive_fire_count = 0
                time.sleep(frame_delay)
                continue

            consecutive_fire_count += 1
            if consecutive_fire_count < consecutive_required:
                time.sleep(frame_delay)
                continue

            logger.info(
                "[%s] LOBBY DEMO YANGIN TESPİT EDİLDİ! local_frame=%d confidence=%.2f",
                entry.name,
                idx,
                result.confidence,
            )
            notifier.send_incident(entry.camera_id, frame, result.confidence)
            return True
    finally:
        cap.release()

    return False


def camera_loop(
    entry: CameraEntry,
    cooldown_seconds: int,
    consecutive_required: int,
    detector: BaseFireDetector,
    notifier: BackendNotifier,
) -> None:
    """
    Bir kamera için sürekli çalışan döngü. Bağlantı kesilince otomatik yeniden bağlanır.
    N ardışık fire frame → backend'e incident gönder → cooldown uygula.
    """
    effective_consecutive_required = consecutive_required

    logger.info(
        "Kamera başlatıldı: %s  source=%s  consecutive=%d  cooldown=%ds",
        entry.name, entry.rtsp_url, effective_consecutive_required, cooldown_seconds,
    )

    retry_idx = 0
    last_incident_at: datetime | None = None
    clear_frames_required = max(5, consecutive_required)
    last_lobby_demo_marker = _lobby_demo_marker_mtime() or 0.0

    if _is_lobby_demo_camera(entry):
        logger.info("[%s] Lobby demo modu: RTSP beklemeden restart marker izleniyor.", entry.name)
        while True:
            marker_mtime = _lobby_demo_marker_mtime()
            if marker_mtime and marker_mtime > last_lobby_demo_marker:
                last_lobby_demo_marker = marker_mtime
                _send_lobby_demo_incident(entry, notifier, consecutive_required)
            time.sleep(0.2)

    while True:
        consecutive_fire_count = 0
        consecutive_clear_count = clear_frames_required
        armed = True

        # ── Bağlan ────────────────────────────────────────────────
        try:
            reader = StreamReader(entry.rtsp_url)
        except RuntimeError as exc:
            delay = 0.5 if _is_lobby_demo_camera(entry) else _RETRY_DELAYS[min(retry_idx, len(_RETRY_DELAYS) - 1)]
            logger.warning(
                "Kamera açılamadı [%s]: %s — %.1fs sonra tekrar denenecek",
                entry.name, exc, delay,
            )
            retry_idx += 1
            time.sleep(delay)
            continue

        retry_idx = 0  # başarılı bağlantıda sayacı sıfırla
        logger.info("Kamera bağlandı: %s", entry.name)
        connection_started_at = time.time()
        warmup_frames = 20 if _is_lobby_demo_camera(entry) else 0

        # ── Frame döngüsü ──────────────────────────────────────────
        try:
            for idx, frame in reader.frames():
                if idx < warmup_frames:
                    time.sleep(0.05)
                    continue
                detection_frame = _frame_for_detection(entry, frame)
                if _is_webcam_demo_camera(entry):
                    result = _detect_webcam_small_flame(entry, detection_frame) or DetectionResult(False, 0.0, 0.0, 0.0)
                else:
                    result = detector.detect(detection_frame)
                    calibrated_result = _detect_calibrated_early_flame(entry, detection_frame)
                    if calibrated_result and calibrated_result.has_fire:
                        result = calibrated_result
                if not result.has_fire:
                    consecutive_fire_count = 0
                    consecutive_clear_count += 1
                    if not armed and consecutive_clear_count >= clear_frames_required:
                        armed = True
                        logger.info("[%s] Detector tekrar hazir.", entry.name)
                    time.sleep(0.05)
                    continue

                consecutive_clear_count = 0
                consecutive_fire_count += 1
                logger.debug(
                    "[%s] Frame %d: fire (%.2f)  ardışık=%d/%d",
                    entry.name, idx, result.confidence,
                    consecutive_fire_count, effective_consecutive_required,
                )

                if consecutive_fire_count < effective_consecutive_required:
                    time.sleep(0.05)
                    continue

                if not armed:
                    time.sleep(0.05)
                    continue

                now = _utc_now()
                next_allowed_at = (
                    last_incident_at + timedelta(seconds=cooldown_seconds)
                    if last_incident_at else None
                )
                if next_allowed_at and now < next_allowed_at:
                    remaining = (next_allowed_at - now).total_seconds()
                    logger.debug("[%s] Cooldown: %.1fs kaldı.", entry.name, remaining)
                    time.sleep(0.05)
                    continue

                last_incident_at = now
                consecutive_fire_count = 0
                armed = False
                logger.info(
                    "[%s] YANGIN TESPİT EDİLDİ! frame=%d  confidence=%.2f",
                    entry.name, idx, result.confidence,
                )
                snapshot_frame = _snapshot_frame_for_incident(entry, detection_frame, result)
                notifier.send_incident(entry.camera_id, snapshot_frame, result.confidence)

        except Exception as exc:
            logger.warning("[%s] Stream hatası: %s — yeniden bağlanılıyor", entry.name, exc)
        finally:
            reader.release()

        # Bağlantı koptu, kısa bekleyip yeniden bağlan
        delay = 0.5 if _is_lobby_demo_camera(entry) else _RETRY_DELAYS[min(retry_idx, len(_RETRY_DELAYS) - 1)]
        logger.info("[%s] %.1fs sonra yeniden bağlanılıyor...", entry.name, delay)
        retry_idx = min(retry_idx + 1, len(_RETRY_DELAYS) - 1)
        time.sleep(delay)


def main() -> None:
    settings = get_settings()

    # ── Detector seç ──────────────────────────────────────────
    mode = (settings.detector_mode or "mock").strip().lower()
    if mode == "cnn":
        from .cnn_detector import CNNFireDetector
        detector: BaseFireDetector = CNNFireDetector(
            model_path=settings.cnn_model_path,
            threshold=settings.cnn_threshold,
        )
        logger.info("CNN detector yüklendi. model=%s", settings.cnn_model_path or "(yok)")
    elif mode == "yolo":
        from .yolo_detector import YOLOFireDetector
        detector = YOLOFireDetector(
            model_path=settings.yolo_model_path,
            confidence_threshold=settings.yolo_confidence_threshold,
            imgsz=settings.yolo_imgsz,
        )
        logger.info("YOLO detector yüklendi. model=%s", settings.yolo_model_path or "(yok)")
    else:
        detector = MockFireDetector(
            fire_threshold=settings.detection_fire_ratio_threshold,
            min_fire_area_ratio=settings.detection_min_fire_area_ratio,
            confidence_threshold=settings.detection_confidence_threshold,
        )
        logger.info("Mock (HSV) detector kullanılıyor.")

    notifier = BackendNotifier(settings=settings)

    # ── Thread factory ─────────────────────────────────────────
    def make_thread(entry: CameraEntry) -> threading.Thread:
        return threading.Thread(
            target=camera_loop,
            args=(
                entry,
                settings.cooldown_seconds,
                settings.detection_consecutive_frames,
                detector,
                notifier,
            ),
            name=f"camera-{entry.camera_id}",
            daemon=True,
        )

    # ── Kamera yöneticisi ──────────────────────────────────────
    manager = DynamicCameraManager(
        backend_url=settings.backend_base_url,
        api_key=settings.detector_api_key,
        thread_factory=make_thread,
    )

    logger.info(
        "Detector servisi başlatıldı. Backend: %s  Mod: %s",
        settings.backend_base_url, mode,
    )
    logger.info("Backend'deki kameralar her %d saniyede otomatik yüklenir.", 30)

    try:
        # İlk sync hemen, sonra her 30 saniyede
        manager.run_loop()
    except KeyboardInterrupt:
        logger.info("Durduruldu.")


if __name__ == "__main__":
    main()
