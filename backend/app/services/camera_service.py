from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.camera import Camera
from app.models.user import Role
from app.models.incident import IncidentStatus


class CameraService:
    @staticmethod
    async def list_cameras(db: AsyncSession, load_incidents: bool = False) -> list[Camera]:
        q = select(Camera).order_by(Camera.id)
        if load_incidents:
            q = q.options(selectinload(Camera.incidents))
        result = await db.execute(q)
        return list(result.unique().scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, camera_id: int) -> Camera | None:
        result = await db.execute(select(Camera).where(Camera.id == camera_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_camera(
        db: AsyncSession,
        *,
        name: str,
        location: str,
        rtsp_url: str,
    ) -> Camera:
        camera = Camera(name=name, location=location, rtsp_url=rtsp_url)
        db.add(camera)
        await db.flush()
        await db.refresh(camera)
        return camera

    @staticmethod
    def can_see_stream(role: Role, camera: Camera) -> bool:
        """Whether to include rtsp_url in response. ADMIN always; MANAGER only if camera has DETECTED/CONFIRMED incident."""
        if role == Role.ADMIN:
            return True
        if role == Role.MANAGER and getattr(camera, "incidents", None):
            return any(
                i.status in (IncidentStatus.DETECTED, IncidentStatus.CONFIRMED)
                for i in camera.incidents
            )
        return False
