import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import PurePath, PureWindowsPath

from app.config import get_settings
from app.database.session import async_session_maker, get_db
from app.auth.dependencies import get_current_user, require_roles, verify_detector_api_key
from app.models.user import User, Role
from app.models.incident import IncidentStatus
from app.models.notification import Notification
from app.schemas.incident import (
    IncidentCreateDetected,
    IncidentResponse,
    IncidentListResponse,
    IncidentResponseUpdateResponse,
    IncidentSafetyReportResponse,
    ResponseUpdateRequest,
    SafetyReportRequest,
)
from app.services.incident_service import IncidentService
from app.services.camera_service import CameraService
from app.websocket_manager import manager
from app.models.incident_update import IncidentResponseUpdate, IncidentSafetyReport

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _camera_label(incident) -> str:
    if not incident.camera:
        return "Unknown Camera"
    location = f" - {incident.camera.location}" if incident.camera.location else ""
    return f"{incident.camera.name}{location}"


def _safety_status_label(status_value: str) -> str:
    return {
        "SAFE": "I am safe",
        "NEED_HELP": "I need help",
    }.get(status_value, status_value.replace("_", " ").title())


def _response_status_label(status_value: str) -> str:
    return {
        "DISPATCHED": "Dispatched",
        "ARRIVED": "Arrived on scene",
        "UNDER_CONTROL": "Under control",
    }.get(status_value, status_value.replace("_", " ").title())


async def _notify_admin_manager_update(
    db: AsyncSession,
    *,
    incident,
    actor: User,
    title: str,
    message: str,
    event_type: str,
    status_value: str,
) -> None:
    result = await db.execute(
        select(User).where(
            User.role.in_([Role.ADMIN, Role.MANAGER]),
            User.is_active.is_(True),
        )
    )
    target_users = result.scalars().all()
    for user in target_users:
        db.add(Notification(user_id=user.id, incident_id=incident.id, message=message))

    await db.flush()
    await manager.send_to_roles(
        {
            "type": "ops_update",
            "event_type": event_type,
            "incident_id": incident.id,
            "camera_id": incident.camera_id,
            "camera_name": incident.camera.name if incident.camera else None,
            "camera_location": incident.camera.location if incident.camera else None,
            "actor_name": actor.full_name,
            "status": status_value,
            "title": title,
            "message": message,
        },
        {Role.ADMIN, Role.MANAGER},
    )


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


async def _incident_to_response(
    incident,
    current_user: User,
    db: AsyncSession | None = None,
    *,
    include_updates: bool = False,
) -> IncidentResponse:
    can_stream = IncidentService.can_see_stream_for_incident(current_user.role, incident)
    camera = incident.camera
    safety_reports: list[IncidentSafetyReportResponse] = []
    response_updates: list[IncidentResponseUpdateResponse] = []

    if include_updates and db is not None:
        safety_result = await db.execute(
            select(IncidentSafetyReport, User)
            .join(User, User.id == IncidentSafetyReport.user_id)
            .where(IncidentSafetyReport.incident_id == incident.id)
            .order_by(IncidentSafetyReport.created_at.desc())
        )
        safety_reports = [
            IncidentSafetyReportResponse(
                user_id=user.id,
                user_name=user.full_name,
                status=report.status,
                created_at=report.created_at,
            )
            for report, user in safety_result.all()
        ]

        response_result = await db.execute(
            select(IncidentResponseUpdate, User)
            .join(User, User.id == IncidentResponseUpdate.user_id)
            .where(IncidentResponseUpdate.incident_id == incident.id)
            .order_by(IncidentResponseUpdate.created_at.desc())
        )
        response_updates = [
            IncidentResponseUpdateResponse(
                user_id=user.id,
                user_name=user.full_name,
                status=update.status,
                created_at=update.created_at,
            )
            for update, user in response_result.all()
        ]

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
        safety_reports=safety_reports,
        response_updates=response_updates,
    )


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    incidents = await IncidentService.list_incidents(db, role=current_user.role)
    items = [await _incident_to_response(i, current_user) for i in incidents]
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
    include_updates = current_user.role in (Role.ADMIN, Role.MANAGER)
    return await _incident_to_response(
        incident,
        current_user,
        db,
        include_updates=include_updates,
    )


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
    await IncidentService.dispatch_detected_alert(db, incident)

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
    return await _incident_to_response(incident, current_user, db, include_updates=True)


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
    include_updates = current_user.role in (Role.ADMIN, Role.MANAGER)
    return await _incident_to_response(
        incident,
        current_user,
        db,
        include_updates=include_updates,
    )


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
    status_label = _safety_status_label(data.status.value)
    message = (
        f"Employee feedback: {current_user.full_name} reported \"{status_label}\" "
        f"for {_camera_label(incident)}."
    )
    await _notify_admin_manager_update(
        db,
        incident=incident,
        actor=current_user,
        title="Employee Safety Feedback",
        message=message,
        event_type="safety_report",
        status_value=data.status.value,
    )
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
    status_label = _response_status_label(data.status.value)
    message = (
        f"Fire response update: {current_user.full_name} marked \"{status_label}\" "
        f"for {_camera_label(incident)}."
    )
    await _notify_admin_manager_update(
        db,
        incident=incident,
        actor=current_user,
        title="Fire Response Update",
        message=message,
        event_type="response_update",
        status_value=data.status.value,
    )
    return {"status": "ok", "response_status": data.status.value}
