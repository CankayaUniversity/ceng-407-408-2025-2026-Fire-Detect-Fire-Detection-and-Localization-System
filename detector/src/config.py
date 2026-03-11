from functools import lru_cache
from typing import List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class CameraConfig(BaseModel):
    """
    Simple camera definition for the detector.

    source:
      - "0", "1" ... -> webcam index
      - "rtsp://..." -> RTSP URL
      - "path/to/video.mp4" -> video file
    """

    id: int = Field(..., description="Camera id as known by backend")
    name: str = Field(..., description="Human readable name")
    source: str = Field(..., description="OpenCV VideoCapture source (index, RTSP, or file path)")


class Settings(BaseSettings):
    # Backend
    backend_base_url: str = "http://localhost:8000"
    detector_api_key: str | None = None

    # Where to POST incidents
    incidents_detected_path: str = "/incidents/detected"

    # Snapshots
    snapshot_dir: str = "../snapshots"
    # Optional public base URL if snapshots are served by backend (e.g. http://localhost:8000/static/)
    public_snapshot_base_url: str | None = None

    # Cameras to monitor
    # Example env: DETECTOR_CAMERAS='[{"id":1,"name":"Webcam","source":"0"}]'
    cameras: List[CameraConfig] = Field(
        default_factory=lambda: [CameraConfig(id=1, name="Default webcam", source="0")]
    )

    # Cooldown in seconds between incidents for same camera
    cooldown_seconds: int = 10

    # Detection tuning (reduce false alarms)
    detection_fire_ratio_threshold: float = 0.005  # min ratio of fire-like pixels to total
    detection_min_fire_area_ratio: float = 0.0  # min ratio of largest fire blob to total (filter tiny spots)
    detection_confidence_threshold: float = 0.1  # min confidence to count frame as "fire"
    detection_consecutive_frames: int = 2  # require this many consecutive fire frames before incident

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()


