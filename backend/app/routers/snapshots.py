from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth.dependencies import verify_detector_api_key
from app.config import get_settings

router = APIRouter(prefix="/snapshots", tags=["snapshots"])
logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
}


@router.post("/upload")
async def upload_snapshot(
    image: UploadFile = File(...),
    camera_id: int | None = Form(default=None),
    _detector_ok: None = Depends(verify_detector_api_key),
):
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase storage is not configured",
        )

    content_type = image.content_type or "application/octet-stream"
    extension = _ALLOWED_CONTENT_TYPES.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG snapshots are supported",
        )

    content = await image.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Snapshot is empty")

    max_bytes = settings.snapshot_upload_max_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Snapshot exceeds {settings.snapshot_upload_max_mb} MB",
        )

    base_url = settings.supabase_url.rstrip("/")
    bucket = settings.supabase_storage_bucket.strip("/")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    camera_segment = f"camera_{camera_id}" if camera_id is not None else "unknown_camera"
    object_path = f"incidents/{camera_segment}/{timestamp}_{uuid.uuid4().hex}{extension}"
    encoded_path = quote(object_path, safe="/")

    upload_url = f"{base_url}/storage/v1/object/{bucket}/{encoded_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    try:
        response = requests.post(
            upload_url,
            data=content,
            headers=headers,
            timeout=settings.supabase_upload_timeout_seconds,
        )
    except requests.RequestException as exc:
        logger.error("Supabase snapshot upload failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase snapshot upload failed",
        ) from exc

    if response.status_code >= 300:
        logger.error("Supabase snapshot upload rejected (%s): %s", response.status_code, response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase snapshot upload rejected",
        )

    public_url = f"{base_url}/storage/v1/object/public/{bucket}/{encoded_path}"
    return {"snapshot_url": public_url, "object_path": object_path}
