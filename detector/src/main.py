from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from .camera_manager import CameraEntry, DynamicCameraManager
from .config import get_settings
from .detector import BaseFireDetector, MockFireDetector
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
    logger.info(
        "Kamera başlatıldı: %s  source=%s  consecutive=%d  cooldown=%ds",
        entry.name, entry.rtsp_url, consecutive_required, cooldown_seconds,
    )

    retry_idx = 0
    last_incident_at: datetime | None = None

    while True:
        consecutive_fire_count = 0

        # ── Bağlan ────────────────────────────────────────────────
        try:
            reader = StreamReader(entry.rtsp_url)
        except RuntimeError as exc:
            delay = _RETRY_DELAYS[min(retry_idx, len(_RETRY_DELAYS) - 1)]
            logger.warning(
                "Kamera açılamadı [%s]: %s — %ds sonra tekrar denenecek",
                entry.name, exc, delay,
            )
            retry_idx += 1
            time.sleep(delay)
            continue

        retry_idx = 0  # başarılı bağlantıda sayacı sıfırla
        logger.info("Kamera bağlandı: %s", entry.name)

        # ── Frame döngüsü ──────────────────────────────────────────
        try:
            for idx, frame in reader.frames():
                result = detector.detect(frame)
                if not result.has_fire:
                    consecutive_fire_count = 0
                    time.sleep(0.05)
                    continue

                consecutive_fire_count += 1
                logger.debug(
                    "[%s] Frame %d: fire (%.2f)  ardışık=%d/%d",
                    entry.name, idx, result.confidence,
                    consecutive_fire_count, consecutive_required,
                )

                if consecutive_fire_count < consecutive_required:
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
                logger.info(
                    "[%s] YANGIN TESPİT EDİLDİ! frame=%d  confidence=%.2f",
                    entry.name, idx, result.confidence,
                )
                notifier.send_incident(entry.camera_id, frame, result.confidence)

        except Exception as exc:
            logger.warning("[%s] Stream hatası: %s — yeniden bağlanılıyor", entry.name, exc)
        finally:
            reader.release()

        # Bağlantı koptu, kısa bekleyip yeniden bağlan
        delay = _RETRY_DELAYS[min(retry_idx, len(_RETRY_DELAYS) - 1)]
        logger.info("[%s] %ds sonra yeniden bağlanılıyor...", entry.name, delay)
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
