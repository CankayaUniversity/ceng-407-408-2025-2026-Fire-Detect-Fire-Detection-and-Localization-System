"""
Veritabanındaki kullanıcıları listeler. Backend klasöründen: python -m scripts.list_users
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import async_session_maker, init_db
from app.models.user import User
from sqlalchemy import select


async def main():
    await init_db()
    async with async_session_maker() as db:
        result = await db.execute(select(User).order_by(User.id))
        users = result.scalars().all()
    if not users:
        print("Veritabanında kullanıcı yok. Önce: python -m scripts.seed_test_data")
        return
    print("Oluşturulan kullanıcılar (login için email + TEST_USERS içindeki şifre):")
    for u in users:
        print(f"  id={u.id}  email={u.email}  role={u.role.value}")


if __name__ == "__main__":
    asyncio.run(main())
