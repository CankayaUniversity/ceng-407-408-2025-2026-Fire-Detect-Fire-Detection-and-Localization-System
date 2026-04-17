from pydantic import BaseModel
from datetime import datetime

class NotificationBase(BaseModel):
    incident_id: int | None = None
    message: str
    is_read: bool = False

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
