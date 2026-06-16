"""
Create/update the local demo camera used by the detector.

Usage:
  python -m scripts.setup_demo_camera --host 192.168.1.35
  python -m scripts.setup_demo_camera --rtsp-url rtsp://192.168.1.35:8554/webcam
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.database.session import async_session_maker, init_db
from app.models.camera import Camera


def build_rtsp_url(host: str, port: int) -> str:
    return f"rtsp://{host}:{port}/webcam"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Flame Scope demo webcam.")
    parser.add_argument("--host", help="Computer LAN IP, e.g. 192.168.1.35")
    parser.add_argument("--port", type=int, default=8554, help="RTSP port, default: 8554")
    parser.add_argument("--rtsp-url", help="Full RTSP URL. Overrides --host/--port.")
    parser.add_argument("--name", default="Computer Webcam")
    parser.add_argument("--location", default="This Computer")
    args = parser.parse_args()

    if not args.rtsp_url and not args.host:
        parser.error("Provide --host or --rtsp-url")

    rtsp_url = args.rtsp_url or build_rtsp_url(args.host, args.port)

    await init_db()
    async with async_session_maker() as db:
        result = await db.execute(select(Camera).where(Camera.name == args.name))
        camera = result.scalar_one_or_none()

        if camera is None:
            camera = Camera(name=args.name, location=args.location, rtsp_url=rtsp_url)
            db.add(camera)
            action = "created"
        else:
            camera.location = args.location
            camera.rtsp_url = rtsp_url
            action = "updated"

        await db.commit()
        await db.refresh(camera)

    print(f"Demo camera {action}:")
    print(f"  id       : {camera.id}")
    print(f"  name     : {camera.name}")
    print(f"  location : {camera.location}")
    print(f"  rtsp_url : {camera.rtsp_url}")


if __name__ == "__main__":
    asyncio.run(main())
