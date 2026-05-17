"""
Create demo data: 4 users, 3 cameras, and 2 sample incidents.
Usage from the backend folder: python -m scripts.seed_test_data
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.auth.password import hash_password
from app.database.session import async_session_maker, init_db
from app.models.camera import Camera
from app.models.incident import Incident, IncidentStatus
from app.models.user import Role, User


TEST_USERS = [
    {"email": "admin@flamescope.com", "password": "Admin123", "full_name": "Admin User", "role": Role.ADMIN},
    {"email": "manager@flamescope.com", "password": "Manager123", "full_name": "Manager User", "role": Role.MANAGER},
    {"email": "employee@flamescope.com", "password": "Employee123", "full_name": "Employee User", "role": Role.EMPLOYEE},
    {"email": "fire@flamescope.com", "password": "Fire123", "full_name": "Fire Response Unit", "role": Role.FIRE_RESPONSE_UNIT},
]

TEST_CAMERAS = [
    {"name": "Lobby Camera", "location": "Entrance Floor", "rtsp_url": "rtsp://192.168.1.100:554/lobby"},
    {"name": "Computer Webcam", "location": "This Computer", "rtsp_url": "rtsp://192.168.1.100:8555/webcam"},
    {"name": "Outdoor Smoke Camera", "location": "Outdoor Area", "rtsp_url": "rtsp://192.168.1.100:8555/outdoor"},
]


async def ensure_user(db, data: dict) -> User:
    result = await db.execute(select(User).where(User.email == data["email"]))
    user = result.scalar_one_or_none()
    if user:
        user.password_hash = hash_password(data["password"])
        return user

    user = User(
        full_name=data["full_name"],
        email=data["email"],
        password_hash=hash_password(data["password"]),
        role=data["role"],
    )
    db.add(user)
    await db.flush()
    return user


async def main() -> None:
    await init_db()
    async with async_session_maker() as db:
        print("Creating users...")
        users = []
        for data in TEST_USERS:
            user = await ensure_user(db, data)
            users.append(user)
            print(f"  - {data['email']} ({data['role'].value})")
        await db.flush()

        result = await db.execute(select(Camera).where(Camera.name == TEST_CAMERAS[0]["name"]))
        if result.scalar_one_or_none():
            print("Cameras already exist, skipping.")
        else:
            print("Creating cameras...")
            cameras_to_add = [Camera(**data) for data in TEST_CAMERAS]
            db.add_all(cameras_to_add)
            await db.flush()
            for camera in cameras_to_add:
                print(f"  - {camera.name} ({camera.location})")

        result = await db.execute(select(Camera).order_by(Camera.id))
        cameras = list(result.scalars().all())
        if len(cameras) < 2:
            print("At least 2 cameras are required; create cameras first.")
            await db.rollback()
            return

        result = await db.execute(select(Incident).limit(1))
        if result.scalar_one_or_none():
            print("Incidents already exist, skipping.")
        else:
            print("Creating sample incidents...")
            manager = next((u for u in users if u.role == Role.MANAGER), users[0])
            now = datetime.utcnow()
            inc1 = Incident(
                camera_id=cameras[0].id,
                status=IncidentStatus.DETECTED,
                confidence=0.92,
                snapshot_url="https://example.com/snapshots/inc1.jpg",
                detected_at=now - timedelta(hours=1),
            )
            inc2 = Incident(
                camera_id=cameras[1].id,
                status=IncidentStatus.CONFIRMED,
                confidence=0.88,
                snapshot_url="https://example.com/snapshots/inc2.jpg",
                detected_at=now - timedelta(hours=3),
                confirmed_at=now - timedelta(hours=2, minutes=50),
                confirmed_by=manager.id,
            )
            db.add_all([inc1, inc2])
            await db.flush()
            print(f"  - Incident 1: {cameras[0].name} - DETECTED (confidence 0.92)")
            print(f"  - Incident 2: {cameras[1].name} - CONFIRMED (confidence 0.88)")

        await db.commit()
        print("\nTest data is ready.")
        print("\nLogin credentials:")
        for data in TEST_USERS:
            print(f"  {data['email']} / {data['password']}")


if __name__ == "__main__":
    asyncio.run(main())
