from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import secrets

from app.database.session import get_db
from app.auth.jwt import create_access_token
from app.auth.password import verify_password
from app.services.user_service import UserService
from app.models.refresh_token import RefreshToken
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await UserService.get_by_email(db, data.email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    
    token = create_access_token(subject=user.id)
    
    refresh_token_string = secrets.token_urlsafe(32)
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    new_rt = RefreshToken(user_id=user.id, token=refresh_token_string, expires_at=refresh_expire)
    db.add(new_rt)
    await db.commit()
    
    return TokenResponse(access_token=token, refresh_token=refresh_token_string)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == data.refresh_token))
    rt = result.scalar_one_or_none()
    
    # Ensure token handles datetimes seamlessly for timezone correctness
    now_utc = datetime.now(timezone.utc)
    
    if not rt or rt.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
    rt_expires_at = rt.expires_at
    if rt_expires_at.tzinfo is None:
        rt_expires_at = rt_expires_at.replace(tzinfo=timezone.utc)
        
    if rt_expires_at < now_utc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
        
    # Standard logic to only rotate the access token and retain existing valid refresh token
    new_access_token = create_access_token(subject=rt.user_id)
    return TokenResponse(access_token=new_access_token, refresh_token=rt.token)

@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == data.refresh_token))
    rt = result.scalar_one_or_none()
    
    if rt:
        rt.revoked = True
        await db.commit()
        
    return {"message": "Logged out successfully"}
