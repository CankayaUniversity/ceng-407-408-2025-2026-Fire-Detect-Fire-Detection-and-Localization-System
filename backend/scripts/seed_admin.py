"""
Create an initial ADMIN user. Run once after DB is up.
Usage: python -m scripts.seed_admin
"""
import asyncio
import os
import sys

# Add parent so app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database.session import async_session_maker
from app.models.user import User, Role
from app.auth.password import hash_password


async def main():
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.role == Role.ADMIN).limit(1))
        if result.scalar_one_or_none():
            print("Admin user already exists.")
            return
        admin = User(
            full_name="Admin",
            email="admin@flamescope.local",
            password_hash=hash_password("admin123"),
            role=Role.ADMIN,
        )
        db.add(admin)
        await db.commit()
        print("Admin user created: admin@flamescope.local / admin123")


if __name__ == "__main__":
    asyncio.run(main())
