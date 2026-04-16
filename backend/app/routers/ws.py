"""
WebSocket endpoint — gerçek zamanlı yangın bildirimleri.

Bağlantı: ws://<host>/ws?token=<JWT>
Client bağlandıktan sonra yangın olayı oluşunca sunucu JSON push eder.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_incidents(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """
    Gerçek zamanlı yangın bildirimi endpoint'i.
    Yangın tespit edildiğinde tüm bağlı client'lara push gönderilir.
    """
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await manager.connect(websocket)
    try:
        while True:
            # Ping/pong için client mesajlarını oku (bağlantıyı canlı tutar)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WS error: %s", exc)
        manager.disconnect(websocket)
