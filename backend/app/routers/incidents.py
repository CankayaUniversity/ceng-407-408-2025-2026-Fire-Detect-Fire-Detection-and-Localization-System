from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.auth.dependencies import get_current_user, require_roles, verify_detector_api_key
from app.models.user import User, Role
from app.models.incident import IncidentStatus
from app.schemas.incident import (
    IncidentCreateDetected,
    IncidentResponse,
    IncidentListResponse,
)
from app.services.incident_service import IncidentService
from app.services.camera_service import CameraService

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _incident_to_response(incident, current_user: User) -> IncidentResponse:
    can_stream = IncidentService.can_see_stream_for_incident(current_user.role, incident)
    camera = incident.camera
    return IncidentResponse(
        id=incident.id,
        camera_id=incident.camera_id,
        camera_name=camera.name if camera else None,
        camera_location=camera.location if camera else None,
        rtsp_url=(camera.rtsp_url if camera and can_stream else None),
        status=incident.status,
        confidence=incident.confidence,
        snapshot_url=incident.snapshot_url,
        detected_at=incident.detected_at,
        confirmed_at=incident.confirmed_at,
        confirmed_by=incident.confirmed_by,
    )


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    incidents = await IncidentService.list_incidents(db, role=current_user.role)
    items = [_incident_to_response(i, current_user) for i in incidents]
    return IncidentListResponse(incidents=items)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    incident = await IncidentService.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if current_user.role in (Role.EMPLOYEE, Role.FIRE_RESPONSE_UNIT) and incident.status != IncidentStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return _incident_to_response(incident, current_user)


@router.post("/detected", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_detected_incident(
    data: IncidentCreateDetected,
    db: AsyncSession = Depends(get_db),
    _detector_ok: None = Depends(verify_detector_api_key),
):
    camera = await CameraService.get_by_id(db, data.camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    incident = await IncidentService.create_detected(
        db,
        camera_id=data.camera_id,
        confidence=data.confidence,
        snapshot_url=data.snapshot_url,
    )
    incident = await IncidentService.get_by_id(db, incident.id)
    # Response includes stream info (caller is detector; no role to hide)
    return IncidentResponse(
        id=incident.id,
        camera_id=incident.camera_id,
        camera_name=camera.name,
        camera_location=camera.location,
        rtsp_url=camera.rtsp_url,
        status=incident.status,
        confidence=incident.confidence,
        snapshot_url=incident.snapshot_url,
        detected_at=incident.detected_at,
        confirmed_at=incident.confirmed_at,
        confirmed_by=incident.confirmed_by,
    )


@router.post("/{incident_id}/confirm", response_model=IncidentResponse)
async def confirm_incident(
    incident_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    incident = await IncidentService.confirm(db, incident_id, current_user.id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident not found or not in DETECTED status",
        )
    incident = await IncidentService.get_by_id(db, incident.id)
    return _incident_to_response(incident, current_user)


@router.post("/{incident_id}/dismiss", response_model=IncidentResponse)
async def dismiss_incident(
    incident_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    incident = await IncidentService.dismiss(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident not found or not in DETECTED status",
        )
    incident = await IncidentService.get_by_id(db, incident.id)
    return _incident_to_response(incident, current_user)