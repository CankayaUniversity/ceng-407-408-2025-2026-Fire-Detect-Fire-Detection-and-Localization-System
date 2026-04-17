from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.schemas.user import UserMe, FCMTokenUpdate
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

@router.post("/me/fcm-token")
async def update_fcm_token(
    data: FCMTokenUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user.fcm_token = data.fcm_token
    await db.commit()
    return {"status": "success"}
