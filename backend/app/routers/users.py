"""
Admin-only user management: list and create users.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserResponse, UserListResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    users = await UserService.list_users(db)
    items = [
        UserResponse(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=u.role,
            is_active=getattr(u, "is_active", True),
            created_at=u.created_at,
        )
        for u in users
    ]
    return UserListResponse(users=items)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user. Admin only."""
    existing = await UserService.get_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    user = await UserService.create_user(
        db,
        full_name=data.full_name,
        email=data.email,
        password=data.password,
        role=data.role,
    )
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=getattr(user, "is_active", True),
        created_at=user.created_at,
    )


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user. Admin only. Cannot deactivate self or another admin."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    target = await UserService.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.role == Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate another admin",
        )
    if not getattr(target, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already deactivated",
        )
    user = await UserService.deactivate_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.patch("/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user(
    user_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Reactivate a user. Admin only."""
    target = await UserService.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if getattr(target, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active",
        )
    user = await UserService.reactivate_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
