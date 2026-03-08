"""
Test verileri oluşturur: 4 kullanıcı, 2 kamera, 2 incident.
Kullanım: backend klasöründen: python -m scripts.seed_test_data
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database.session import async_session_maker, init_db
from app.models.user import User, Role
from app.models.camera import Camera
from app.models.incident import Incident, IncidentStatus
from app.auth.password import hash_password


TEST_USERS = [
    {"email": "admin@flamescope.com", "password": "Admin123", "full_name": "Admin User", "role": Role.ADMIN},
    {"email": "manager@flamescope.com", "password": "Manager123", "full_name": "Manager User", "role": Role.MANAGER},
    {"email": "employee@flamescope.com", "password": "Employee123", "full_name": "Employee User", "role": Role.EMPLOYEE},
    {"email": "fire@flamescope.com", "password": "Fire123", "full_name": "Fire Response Unit", "role": Role.FIRE_RESPONSE_UNIT},
]

TEST_CAMERAS = [
    {"name": "Lobby Kamera", "location": "Giriş Katı", "rtsp_url": "rtsp://192.168.1.100:554/stream1"},
    {"name": "Depo Kamera", "location": "Depo Bölümü", "rtsp_url": "rtsp://192.168.1.101:554/stream1"},
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


async def main():
    await init_db()
    async with async_session_maker() as db:
        # 1. Kullanıcılar
        print("Kullanıcılar oluşturuluyor...")
        users = []
        for data in TEST_USERS:
            u = await ensure_user(db, data)
            users.append(u)
            print(f"  - {data['email']} ({data['role'].value})")
        await db.flush()

        # 2. Kameralar (yoksa ekle)
        result = await db.execute(select(Camera).where(Camera.name == TEST_CAMERAS[0]["name"]))
        if result.scalar_one_or_none():
            print("Kameralar zaten mevcut, atlanıyor.")
        else:
            print("Kameralar oluşturuluyor...")
            c1 = Camera(**TEST_CAMERAS[0])
            c2 = Camera(**TEST_CAMERAS[1])
            db.add_all([c1, c2])
            await db.flush()
            print(f"  - {c1.name} ({c1.location})")
            print(f"  - {c2.name} ({c2.location})")

        # 3. Incident örnekleri (yoksa ekle)
        result = await db.execute(select(Camera).order_by(Camera.id))
        cameras = list(result.scalars().all())
        if len(cameras) < 2:
            print("En az 2 kamera gerekli; önce kameraları oluşturun.")
            await db.rollback()
            return

        result = await db.execute(select(Incident).limit(1))
        if result.scalar_one_or_none():
            print("Incident'ler zaten mevcut, atlanıyor.")
        else:
            print("Incident örnekleri oluşturuluyor...")
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
            print(f"  - Incident 1: {cameras[0].name} — DETECTED (confidence 0.92)")
            print(f"  - Incident 2: {cameras[1].name} — CONFIRMED (confidence 0.88)")

        await db.commit()
        print("\nTest verileri hazır.")
        print("\nGiriş bilgileri:")
        for d in TEST_USERS:
            print(f"  {d['email']} / {d['password']}")


if __name__ == "__main__":
    asyncio.run(main())
