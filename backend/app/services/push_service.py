from __future__ import annotations

import logging
from typing import Any

from app.models.user import User

logger = logging.getLogger(__name__)


def _stringify_data(data: dict[str, Any] | None) -> dict[str, str] | None:
    if not data:
        return None
    return {str(key): "" if value is None else str(value) for key, value in data.items()}


def send_push_notification(
    user: User,
    *,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> bool:
    if not user.fcm_token:
        return False

    try:
        from firebase_admin import messaging

        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=_stringify_data(data),
            android=messaging.AndroidConfig(priority="high"),
            token=user.fcm_token,
        )
        messaging.send(msg)
        return True
    except Exception as exc:
        logger.error("FCM send failed for user %s: %s", user.id, exc)
        return False
