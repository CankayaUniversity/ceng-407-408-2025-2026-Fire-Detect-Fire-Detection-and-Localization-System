from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
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
    async def create_user(
        db: AsyncSession,
        *,
        full_name: str,
        email: str,
        password: str,
        role: str,
    ) -> User:
        from app.models.user import Role as RoleEnum
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=RoleEnum(role),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user
