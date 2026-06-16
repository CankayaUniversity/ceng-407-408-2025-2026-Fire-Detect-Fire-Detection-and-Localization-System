from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SafetyStatus(str, enum.Enum):
    SAFE = "SAFE"
    NEED_HELP = "NEED_HELP"


class ResponseStatus(str, enum.Enum):
    DISPATCHED = "DISPATCHED"
    ARRIVED = "ARRIVED"
    UNDER_CONTROL = "UNDER_CONTROL"


class IncidentSafetyReport(Base):
    __tablename__ = "incident_safety_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[SafetyStatus] = mapped_column(Enum(SafetyStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class IncidentResponseUpdate(Base):
    __tablename__ = "incident_response_updates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[ResponseStatus] = mapped_column(Enum(ResponseStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
