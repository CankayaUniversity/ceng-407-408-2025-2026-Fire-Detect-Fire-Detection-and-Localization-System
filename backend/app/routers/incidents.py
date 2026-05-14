import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import PurePath, PureWindowsPath

from app.config import get_settings
from app.database.session import async_session_maker, get_db
from app.auth.dependencies import get_current_user, require_roles, verify_detector_api_key
from app.models.user import User, Role
from app.models.incident import IncidentStatus
from app.schemas.incident import (
    IncidentCreateDetected,
    IncidentResponse,
    IncidentListResponse,
    ResponseUpdateRequest,
    SafetyReportRequest,
)
from app.services.incident_service import IncidentService
from app.services.camera_service import CameraService
from app.websocket_manager import manager
from app.models.incident_update import IncidentResponseUpdate, IncidentSafetyReport

router = APIRouter(prefix="/incidents", tags=["incidents"])


async def _auto_escalate_if_unanswered(incident_id: int, delay_seconds: int) -> None:
    await asyncio.sleep(delay_seconds)
    async with async_session_maker() as db:
        await IncidentService.auto_confirm_if_pending(
            db,
            incident_id,
            reason="timeout",
            target_roles=set(Role),
        )
        await db.commit()


def _normalize_snapshot_url(snapshot_url: str | None) -> str | None:
    if not snapshot_url:
        return None

    value = snapshot_url.strip()
    if not value:
        return None

    if value.startswith(("http://", "https://", "/snapshots/")):
        return value

    normalized = value.replace("\\", "/")
    if normalized.startswith("snapshots/") or "/snapshots/" in normalized:
        return f"/snapshots/{PurePath(normalized).name}"

    return f"/snapshots/{PureWindowsPath(value).name}"


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


@router.get("/analytics/summary")
async def incident_summary(
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    return await IncidentService.summary(db)


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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _detector_ok: None = Depends(verify_detector_api_key),
):
    camera = await CameraService.get_by_id(db, data.camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    snapshot_url = _normalize_snapshot_url(data.snapshot_url)
    incident = await IncidentService.create_detected(
        db,
        camera_id=data.camera_id,
        confidence=data.confidence,
        snapshot_url=snapshot_url,
    )
    incident = await IncidentService.get_by_id(db, incident.id)
    settings = get_settings()

    if data.confidence is not None and data.confidence >= settings.critical_risk_threshold:
        incident = await IncidentService.auto_confirm_if_pending(
            db,
            incident.id,
            reason="critical_risk",
            target_roles=set(Role),
        )
        incident = await IncidentService.get_by_id(db, incident.id)
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

    # Tüm bağlı mobil/web client'lara gerçek zamanlı bildirim gönder
    await manager.send_to_roles({
        "type": "fire_detected",
        "incident_id": incident.id,
        "camera_id": incident.camera_id,
        "camera_name": camera.name,
        "camera_location": camera.location,
        "confidence": data.confidence,
        "snapshot_url": snapshot_url,
        "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
    }, {Role.ADMIN, Role.MANAGER})

    should_auto_escalate = (
        data.confidence is not None
        and data.confidence >= settings.auto_escalation_risk_threshold
    )
    if settings.auto_escalation_seconds > 0 and should_auto_escalate:
        background_tasks.add_task(
            _auto_escalate_if_unanswered,
            incident.id,
            settings.auto_escalation_seconds,
        )

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


@router.post("/{incident_id}/safety-report")
async def submit_safety_report(
    incident_id: int,
    data: SafetyReportRequest,
    current_user: User = Depends(require_roles(Role.EMPLOYEE)),
    db: AsyncSession = Depends(get_db),
):
    incident = await IncidentService.get_by_id(db, incident_id)
    if not incident or incident.status != IncidentStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    report = IncidentSafetyReport(
        incident_id=incident_id,
        user_id=current_user.id,
        status=data.status,
    )
    db.add(report)
    await db.flush()
    return {"status": "ok", "safety_status": data.status.value}


@router.post("/{incident_id}/response-update")
async def submit_response_update(
    incident_id: int,
    data: ResponseUpdateRequest,
    current_user: User = Depends(require_roles(Role.FIRE_RESPONSE_UNIT)),
    db: AsyncSession = Depends(get_db),
):
    incident = await IncidentService.get_by_id(db, incident_id)
    if not incident or incident.status != IncidentStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    update = IncidentResponseUpdate(
        incident_id=incident_id,
        user_id=current_user.id,
        status=data.status,
    )
    db.add(update)
    await db.flush()
    return {"status": "ok", "response_status": data.status.value}
