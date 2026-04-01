from datetime import datetime
from pydantic import BaseModel


class CameraCreate(BaseModel):
    name: str
    location: str
    rtsp_url: str


class CameraUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    rtsp_url: str | None = None


class CameraResponse(BaseModel):
    id: int
    name: str
    location: str
    rtsp_url: str | None = None  # None when role cannot see stream (EMPLOYEE, FIRE_RESPONSE_UNIT)
    created_at: datetime

    class Config:
        from_attributes = True


class CameraListResponse(BaseModel):
    cameras: list[CameraResponse]
