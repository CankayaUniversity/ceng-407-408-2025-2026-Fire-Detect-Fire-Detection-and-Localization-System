from datetime import datetime
from pydantic import BaseModel
from app.models.incident import IncidentStatus


class IncidentCreateDetected(BaseModel):
    camera_id: int
    confidence: float | None = None
    snapshot_url: str | None = None


class IncidentResponse(BaseModel):
    id: int
    camera_id: int
    camera_name: str | None = None
    camera_location: str | None = None
    rtsp_url: str | None = None  # Only for ADMIN or MANAGER with access; never for EMPLOYEE/FIRE_RESPONSE_UNIT
    status: IncidentStatus
    confidence: float | None = None
    snapshot_url: str | None = None
    detected_at: datetime
    confirmed_at: datetime | None = None
    confirmed_by: int | None = None

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]
