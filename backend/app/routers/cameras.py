from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, Role
from app.schemas.camera import CameraCreate, CameraResponse, CameraListResponse
from app.services.camera_service import CameraService

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=CameraListResponse)
async def list_cameras(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    load_incidents = current_user.role == Role.MANAGER
    cameras = await CameraService.list_cameras(db, load_incidents=load_incidents)
    items = []
    for c in cameras:
        show_stream = CameraService.can_see_stream(current_user.role, c)
        items.append(
            CameraResponse(
                id=c.id,
                name=c.name,
                location=c.location,
                rtsp_url=c.rtsp_url if show_stream else None,
                created_at=c.created_at,
            )
        )
    return CameraListResponse(cameras=items)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    data: CameraCreate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    camera = await CameraService.create_camera(
        db, name=data.name, location=data.location, rtsp_url=data.rtsp_url
    )
    return CameraResponse(
        id=camera.id,
        name=camera.name,
        location=camera.location,
        rtsp_url=camera.rtsp_url,
        created_at=camera.created_at,
    )
