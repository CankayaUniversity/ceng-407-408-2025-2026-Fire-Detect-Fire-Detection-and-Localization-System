from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, Role
from app.auth.password import hash_password


class UserService:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_users(db: AsyncSession) -> list[User]:
        result = await db.execute(select(User).order_by(User.id))
        return list(result.scalars().all())

    @staticmethod
    async def create_user(
        db: AsyncSession,
        *,
        full_name: str,
        email: str,
        password: str,
        role: Role,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: int) -> User | None:
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return None
        user.is_active = False
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def reactivate_user(db: AsyncSession, user_id: int) -> User | None:
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return None
        user.is_active = True
        await db.flush()
        await db.refresh(user)
        return user
