from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import Role


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Role = Role.EMPLOYEE


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: Role
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserMe(BaseModel):
    id: int
    full_name: str
    email: str
    role: Role
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserResponse]
