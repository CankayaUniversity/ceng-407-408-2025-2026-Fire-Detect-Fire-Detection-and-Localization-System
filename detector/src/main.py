from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from .config import CameraConfig, get_settings
from .detector import MockFireDetector
from .notifier import BackendNotifier
from .stream_reader import StreamReader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("flamescope.detector")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def camera_loop(
    cam: CameraConfig,
    cooldown_seconds: int,
    consecutive_required: int,
    detector: MockFireDetector,
    notifier: BackendNotifier,
) -> None:
    """
    Per-camera loop: require N consecutive fire frames before sending incident;
    cooldown applies between incidents.
    """
    logger.info(
        "Starting camera loop for %s (source=%s, consecutive_frames=%d, cooldown=%ds)",
        cam.name,
        cam.source,
        consecutive_required,
        cooldown_seconds,
    )
    last_incident_at: datetime | None = None
    consecutive_fire_count = 0

    try:
        reader = StreamReader(cam.source)
    except RuntimeError as exc:
        logger.error("Camera %s could not be opened: %s", cam.name, exc)
        return

    try:
        for idx, frame in reader.frames():
            result = detector.detect(frame)
            if not result.has_fire:
                if consecutive_fire_count > 0:
                    logger.debug(
                        "[%s] Fire lost at frame %d (was %d/%d consecutive); resetting.",
                        cam.name,
                        idx,
                        consecutive_fire_count,
                        consecutive_required,
                    )
                consecutive_fire_count = 0
                time.sleep(0.05)
                continue

            consecutive_fire_count += 1
            logger.debug(
                "[%s] Frame %d: fire detected (%d/%d consecutive)",
                cam.name,
                idx,
                consecutive_fire_count,
                consecutive_required,
            )

            if consecutive_fire_count < consecutive_required:
                time.sleep(0.05)
                continue

            now = _utc_now()
            # Cooldown: do not send again until this time has passed
            next_allowed_at = (
                last_incident_at + timedelta(seconds=cooldown_seconds)
                if last_incident_at else None
            )
            if next_allowed_at is not None and now < next_allowed_at:
                remaining = (next_allowed_at - now).total_seconds()
                logger.info(
                    "[%s] Cooldown active: next incident allowed at %s (remaining %.1fs). Skipping.",
                    cam.name,
                    next_allowed_at.strftime("%H:%M:%SZ"),
                    remaining,
                )
                time.sleep(0.05)
                continue

            # Set cooldown before sending so duplicate is impossible even if send is slow or fails
            last_incident_at = now
            consecutive_fire_count = 0
            cooldown_until = now + timedelta(seconds=cooldown_seconds)
            logger.info(
                "[%s] Incident triggered at frame %d (confidence=%.2f). Sending to backend. Cooldown until %s (%.0fs).",
                cam.name,
                idx,
                result.confidence,
                cooldown_until.strftime("%Y-%m-%dT%H:%M:%SZ"),
                cooldown_seconds,
            )
            notifier.send_incident(cam.id, frame, result.confidence)
            logger.info(
                "[%s] Incident sent at %s; next allowed at %s.",
                cam.name,
                now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                cooldown_until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
    finally:
        reader.release()
        logger.info("Camera loop finished for %s", cam.name)


def main() -> None:
    settings = get_settings()
    detector = MockFireDetector(
        fire_threshold=settings.detection_fire_ratio_threshold,
        min_fire_area_ratio=settings.detection_min_fire_area_ratio,
        confidence_threshold=settings.detection_confidence_threshold,
    )
    notifier = BackendNotifier(settings=settings)

    threads: list[threading.Thread] = []
    for cam in settings.cameras:
        t = threading.Thread(
            target=camera_loop,
            args=(
                cam,
                settings.cooldown_seconds,
                settings.detection_consecutive_frames,
                detector,
                notifier,
            ),
            name=f"camera-{cam.id}",
            daemon=True,
        )
        threads.append(t)
        t.start()

    if not threads:
        logger.warning("No cameras configured; exiting.")
        return

    logger.info("Detector service started with %d camera(s). Press Ctrl+C to stop.", len(threads))
    try:
        # Keep main thread alive while camera threads run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")


if __name__ == "__main__":
    main()

