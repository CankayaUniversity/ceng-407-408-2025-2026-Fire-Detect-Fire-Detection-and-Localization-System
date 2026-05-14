from pathlib import Path
import subprocess

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.auth.dependencies import get_current_user, require_roles, verify_detector_api_key
from app.models.user import User, Role
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse, CameraListResponse
from app.services.camera_service import CameraService

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _restart_lobby_demo_stream() -> dict[str, str]:
    project_root = Path(__file__).resolve().parents[3]
    video_path = project_root / "demo-videos" / "lobby_fire.mp4"
    ffmpeg_exe = Path.home() / "flamescope-rtsp" / "ffmpeg" / "bin" / "ffmpeg.exe"
    stdout_log = project_root / "detector" / "lobby_video_rtsp.log"
    stderr_log = project_root / "detector" / "lobby_video_rtsp.err.log"
    marker_path = project_root / "demo-videos" / "lobby_fire.restart"

    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lobby demo video not found: {video_path}",
        )
    if not ffmpeg_exe.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FFmpeg not found: {ffmpeg_exe}",
        )

    stopped_by_pid = False
    try:
        previous_pid = marker_path.read_text(encoding="utf-8").strip()
        if previous_pid.isdigit():
            result = subprocess.run(
                ["taskkill", "/PID", previous_pid, "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            stopped_by_pid = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        stopped_by_pid = False

    if not stopped_by_pid:
        stop_command = (
            "Get-CimInstance Win32_Process -Filter \"name = 'ffmpeg.exe'\" | "
            "Where-Object { $_.CommandLine -like '*lobby_fire.mp4*' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", stop_command],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )

    args = [
        str(ffmpeg_exe),
        "-hide_banner",
        "-loglevel",
        "warning",
        "-re",
        "-ss",
        "9",
        "-stream_loop",
        "-1",
        "-i",
        str(video_path),
        "-an",
        "-vf",
        "scale=1280:720",
        "-vcodec",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "zerolatency",
        "-g",
        "15",
        "-bf",
        "0",
        "-x264-params",
        "keyint=15:min-keyint=15:scenecut=0",
        "-pix_fmt",
        "yuv420p",
        "-f",
        "rtsp",
        "-rtsp_transport",
        "tcp",
        "rtsp://localhost:8555/lobby",
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with stdout_log.open("ab") as stdout, stderr_log.open("ab") as stderr:
        process = subprocess.Popen(
            args,
            stdout=stdout,
            stderr=stderr,
            creationflags=creationflags,
        )

    marker_path.write_text(
        str(process.pid),
        encoding="utf-8",
    )

    return {"status": "restarted", "pid": str(process.pid)}


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
    camera = await CameraService.get_by_id(
        db,
        camera_id,
        load_incidents=current_user.role == Role.MANAGER,
    )
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    show_stream = CameraService.can_see_stream(current_user.role, camera)
    return CameraResponse(
        id=camera.id,
        name=camera.name,
        location=camera.location,
        rtsp_url=camera.rtsp_url if show_stream else None,
        created_at=camera.created_at,
    )


@router.post("/{camera_id}/demo/restart-lobby")
async def restart_lobby_demo_stream(
    camera_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    camera = await CameraService.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    if "lobby" not in (camera.name or "").lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo restart is only available for Lobby Kamera",
        )
    return _restart_lobby_demo_stream()


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
