from datetime import datetime
from pydantic import BaseModel
from app.models.incident import IncidentStatus
from app.models.incident_update import ResponseStatus, SafetyStatus


class IncidentCreateDetected(BaseModel):
    camera_id: int
    confidence: float | None = None
    snapshot_url: str | None = None


class IncidentSafetyReportResponse(BaseModel):
    user_id: int
    user_name: str
    status: SafetyStatus
    created_at: datetime


class IncidentResponseUpdateResponse(BaseModel):
    user_id: int
    user_name: str
    status: ResponseStatus
    created_at: datetime


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
    safety_reports: list[IncidentSafetyReportResponse] = []
    response_updates: list[IncidentResponseUpdateResponse] = []

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]


class SafetyReportRequest(BaseModel):
    status: SafetyStatus


class ResponseUpdateRequest(BaseModel):
    status: ResponseStatus
