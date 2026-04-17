from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentStatus
from app.models.camera import Camera
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
    def can_see_stream_for_incident(role: Role, incident: Incident) -> bool:
        """Include rtsp_url for this incident only if user may stream."""
        if role == Role.ADMIN:
            return True
        if role == Role.MANAGER and incident.status in (IncidentStatus.DETECTED, IncidentStatus.CONFIRMED):
            return True
        return False

    @staticmethod
    async def confirm(db: AsyncSession, incident_id: int, user_id: int) -> Incident | None:
        incident = await IncidentService.get_by_id(db, incident_id)
        if not incident or incident.status != IncidentStatus.DETECTED:
            return None
        incident.status = IncidentStatus.CONFIRMED
        incident.confirmed_at = datetime.now(timezone.utc)
        incident.confirmed_by = user_id
        await db.flush()
        await db.refresh(incident)

        from app.models.user import User
        from app.models.notification import Notification
        
        # Fetch target users and dispatch alerts
        result = await db.execute(
            select(User).where(User.role.in_([Role.EMPLOYEE, Role.FIRE_RESPONSE_UNIT]))
        )
        target_users = result.scalars().all()
        
        camera_name = incident.camera.name if incident.camera else "Unknown Camera"
        message = f"🚨 FIRE CONFIRMED at {camera_name}. Please follow safety instructions and proceed to the nearest exit immediately!"
        
        for u in target_users:
            notif = Notification(user_id=u.id, incident_id=incident.id, message=message)
            db.add(notif)
            
            if u.fcm_token:
                try:
                    from firebase_admin import messaging
                    msg = messaging.Message(
                        notification=messaging.Notification(
                            title="🔥 Flame Scope Alert",
                            body=message,
                        ),
                        token=u.fcm_token,
                    )
                    messaging.send(msg)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"FCM send failed for user {u.id}: {e}")
            
        await db.flush()
        
        from app.websocket_manager import manager
        await manager.broadcast({
            "type": "fire_confirmed",
            "incident_id": incident.id,
            "camera_name": camera_name,
            "message": message
        })
        
        return incident

    @staticmethod
    async def dismiss(db: AsyncSession, incident_id: int) -> Incident | None:
        incident = await IncidentService.get_by_id(db, incident_id)
        if not incident or incident.status != IncidentStatus.DETECTED:
            return None
        incident.status = IncidentStatus.DISMISSED
        await db.flush()
        await db.refresh(incident)
        return incident
