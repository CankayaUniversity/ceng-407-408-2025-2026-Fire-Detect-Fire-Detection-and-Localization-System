from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentStatus
from app.models.user import Role


class IncidentService:
    @staticmethod
    async def create_detected(
        db: AsyncSession,
        *,
        camera_id: int,
        confidence: float | None = None,
        snapshot_url: str | None = None,
    ) -> Incident:
        incident = Incident(
            camera_id=camera_id,
            status=IncidentStatus.DETECTED,
            confidence=confidence,
            snapshot_url=snapshot_url,
        )
        db.add(incident)
        await db.flush()
        await db.refresh(incident)
        return incident

    @staticmethod
    async def get_by_id(db: AsyncSession, incident_id: int) -> Incident | None:
        result = await db.execute(
            select(Incident)
            .options(selectinload(Incident.camera))
            .where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_incidents(
        db: AsyncSession,
        *,
        role: Role,
    ) -> list[Incident]:
        q = select(Incident).options(selectinload(Incident.camera)).order_by(Incident.detected_at.desc())
        if role in (Role.EMPLOYEE, Role.FIRE_RESPONSE_UNIT):
            q = q.where(Incident.status == IncidentStatus.CONFIRMED)
        result = await db.execute(q)
        return list(result.unique().scalars().all())

    @staticmethod
    async def summary(db: AsyncSession) -> dict:
        total = await db.scalar(select(func.count(Incident.id)))
        detected = await db.scalar(select(func.count(Incident.id)).where(Incident.status == IncidentStatus.DETECTED))
        confirmed = await db.scalar(select(func.count(Incident.id)).where(Incident.status == IncidentStatus.CONFIRMED))
        dismissed = await db.scalar(select(func.count(Incident.id)).where(Incident.status == IncidentStatus.DISMISSED))
        avg_risk = await db.scalar(select(func.avg(Incident.confidence)).where(Incident.confidence.is_not(None)))
        return {
            "total": total or 0,
            "detected": detected or 0,
            "confirmed": confirmed or 0,
            "dismissed": dismissed or 0,
            "average_risk": float(avg_risk) if avg_risk is not None else None,
        }

    @staticmethod
    def can_see_stream_for_incident(role: Role, incident: Incident) -> bool:
        if role == Role.ADMIN:
            return True
        if role == Role.MANAGER and incident.status in (IncidentStatus.DETECTED, IncidentStatus.CONFIRMED):
            return True
        return False

    @staticmethod
    async def dispatch_detected_alert(db: AsyncSession, incident: Incident) -> None:
        from app.models.notification import Notification
        from app.models.user import User
        from app.services.push_service import send_push_notification
        from app.websocket_manager import manager

        target_roles = {Role.ADMIN, Role.MANAGER}
        result = await db.execute(
            select(User).where(
                User.role.in_(list(target_roles)),
                User.is_active.is_(True),
            )
        )
        target_users = result.scalars().all()

        camera_name = incident.camera.name if incident.camera else "Unknown Camera"
        camera_location = incident.camera.location if incident.camera else None
        location_text = f" - {camera_location}" if camera_location else ""
        risk_text = f" Risk score: {round(incident.confidence * 100)}%." if incident.confidence is not None else ""
        message = f"Fire or smoke detected: {camera_name}{location_text}.{risk_text} Please review the alarm."

        event_data = {
            "type": "fire_detected",
            "incident_id": incident.id,
            "camera_id": incident.camera_id,
            "camera_name": camera_name,
            "camera_location": camera_location,
            "confidence": incident.confidence,
            "snapshot_url": incident.snapshot_url,
            "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
        }

        for user in target_users:
            db.add(Notification(user_id=user.id, incident_id=incident.id, message=message))
            send_push_notification(
                user,
                title="FlameScope Detection Alert",
                body=message,
                data=event_data,
            )

        await db.flush()
        await manager.send_to_roles(event_data, target_roles)

    @staticmethod
    async def confirm(db: AsyncSession, incident_id: int, user_id: int) -> Incident | None:
        return await IncidentService._confirm(
            db,
            incident_id,
            confirmed_by=user_id,
            reason="manager",
            target_roles={Role.EMPLOYEE, Role.FIRE_RESPONSE_UNIT},
        )

    @staticmethod
    async def auto_confirm_if_pending(
        db: AsyncSession,
        incident_id: int,
        *,
        reason: str,
        target_roles: set[Role] | None = None,
    ) -> Incident | None:
        return await IncidentService._confirm(
            db,
            incident_id,
            confirmed_by=None,
            reason=reason,
            target_roles=target_roles or set(Role),
        )

    @staticmethod
    async def _confirm(
        db: AsyncSession,
        incident_id: int,
        *,
        confirmed_by: int | None,
        reason: str,
        target_roles: set[Role],
    ) -> Incident | None:
        incident = await IncidentService.get_by_id(db, incident_id)
        if not incident or incident.status != IncidentStatus.DETECTED:
            return None

        incident.status = IncidentStatus.CONFIRMED
        incident.confirmed_at = datetime.now(timezone.utc)
        incident.confirmed_by = confirmed_by
        await db.flush()
        await db.refresh(incident)

        await IncidentService._dispatch_confirmed_alert(
            db,
            incident,
            reason=reason,
            target_roles=target_roles,
        )
        return incident

    @staticmethod
    async def _dispatch_confirmed_alert(
        db: AsyncSession,
        incident: Incident,
        *,
        reason: str,
        target_roles: set[Role],
    ) -> None:
        from app.models.notification import Notification
        from app.models.user import User
        from app.services.push_service import send_push_notification
        from app.websocket_manager import manager

        result = await db.execute(
            select(User).where(
                User.role.in_(list(target_roles)),
                User.is_active.is_(True),
            )
        )
        target_users = result.scalars().all()

        camera_name = incident.camera.name if incident.camera else "Unknown Camera"
        camera_location = incident.camera.location if incident.camera else None
        location_text = f" - {camera_location}" if camera_location else ""
        risk_text = f" Risk score: {round(incident.confidence * 100)}%." if incident.confidence is not None else ""
        reason_text = {
            "manager": "Confirmed by manager",
            "critical_risk": "Automatically escalated due to critical risk level",
            "timeout": "Automatically escalated because no manager response was received",
        }.get(reason, "Emergency alarm confirmed")
        message = (
            f"{reason_text}: {camera_name}{location_text}."
            f"{risk_text} Please follow the nearest safe exit instructions."
        )

        for user in target_users:
            db.add(Notification(user_id=user.id, incident_id=incident.id, message=message))
            send_push_notification(
                user,
                title="FlameScope Emergency",
                body=message,
                data={
                    "type": "fire_confirmed",
                    "incident_id": incident.id,
                    "camera_id": incident.camera_id,
                    "camera_name": camera_name,
                    "camera_location": camera_location,
                    "confidence": incident.confidence,
                    "snapshot_url": incident.snapshot_url,
                    "confirmed_at": incident.confirmed_at.isoformat() if incident.confirmed_at else None,
                    "confirmation_reason": reason,
                },
            )

        await db.flush()

        await manager.send_to_roles({
            "type": "fire_confirmed",
            "incident_id": incident.id,
            "camera_id": incident.camera_id,
            "camera_name": camera_name,
            "camera_location": camera_location,
            "confidence": incident.confidence,
            "snapshot_url": incident.snapshot_url,
            "confirmed_at": incident.confirmed_at.isoformat() if incident.confirmed_at else None,
            "message": message,
            "confirmation_reason": reason,
        }, target_roles)

    @staticmethod
    async def dismiss(db: AsyncSession, incident_id: int) -> Incident | None:
        incident = await IncidentService.get_by_id(db, incident_id)
        if not incident or incident.status != IncidentStatus.DETECTED:
            return None
        incident.status = IncidentStatus.DISMISSED
        await db.flush()
        await db.refresh(incident)
        return incident
