"""
WebSocket endpoint for real-time fire notifications.

Connection: ws://<host>/ws?token=<JWT>
After the client connects, the server pushes JSON messages when a fire incident is created.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.database.session import get_db
from app.models.user import User
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_incidents(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Real-time fire notification endpoint.
    Pushes incident updates to connected clients when fire is detected.
    """
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await websocket.close(code=1008, reason="User not found")
        return

    await manager.connect(websocket, user.id, user.role)
    try:
        while True:
            # Read client messages for ping/pong and keep the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WS error: %s", exc)
        manager.disconnect(websocket)
