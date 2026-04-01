from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.auth.dependencies import get_current_user, require_roles, verify_detector_api_key
from app.models.user import User, Role
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse, CameraListResponse
from app.services.camera_service import CameraService

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("/detector-list")
async def list_cameras_for_detector(
    db: AsyncSession = Depends(get_db),
    _ok: None = Depends(verify_detector_api_key),
):
    """
    Detector servisinin kamera listesini çekmesi için endpoint.
    JWT gerektirmez — detector API key ile (ya da key yoksa herkese açık).
    Döner: [{"id": 1, "name": "...", "rtsp_url": "rtsp://..."}]
    """
    cameras = await CameraService.list_cameras(db)
    return {
        "cameras": [
            {"id": c.id, "name": c.name, "location": c.location, "rtsp_url": c.rtsp_url}
            for c in cameras
            if c.rtsp_url  # sadece RTSP URL'i olanları ver
        ]
    }


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


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    camera = await CameraService.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return CameraResponse(
        id=camera.id,
        name=camera.name,
        location=camera.location,
        rtsp_url=camera.rtsp_url,
        created_at=camera.created_at,
    )


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    data: CameraUpdate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    camera = await CameraService.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    if data.name is not None:
        camera.name = data.name
    if data.location is not None:
        camera.location = data.location
    if data.rtsp_url is not None:
        camera.rtsp_url = data.rtsp_url
    await db.flush()
    await db.refresh(camera)
    return CameraResponse(
        id=camera.id,
        name=camera.name,
        location=camera.location,
        rtsp_url=camera.rtsp_url,
        created_at=camera.created_at,
    )


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
