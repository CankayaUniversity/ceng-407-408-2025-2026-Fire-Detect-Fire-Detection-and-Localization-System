from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.schemas.user import UserMe
from app.models.user import User

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserMe)
async def me(current_user: User = Depends(get_current_user)):
    return UserMe(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )
