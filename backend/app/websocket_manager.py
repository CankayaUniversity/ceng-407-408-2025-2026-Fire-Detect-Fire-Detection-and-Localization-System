"""
WebSocket connection manager for real-time fire alerts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

from app.models.user import Role

logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    ws: WebSocket
    user_id: int
    role: Role


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[ClientConnection] = []

    async def connect(self, ws: WebSocket, user_id: int, role: Role) -> None:
        await ws.accept()
        self._connections.append(ClientConnection(ws=ws, user_id=user_id, role=role))
        logger.info(
            "WS client connected. user_id=%s role=%s total=%d",
            user_id,
            role.value,
            len(self._connections),
        )

    def disconnect(self, ws: WebSocket) -> None:
        self._connections = [conn for conn in self._connections if conn.ws is not ws]
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, data: dict[str, Any]) -> None:
        await self.send_to_roles(data, None)

    async def send_to_roles(self, data: dict[str, Any], roles: set[Role] | None) -> None:
        dead: list[WebSocket] = []
        for conn in list(self._connections):
            if roles is not None and conn.role not in roles:
                continue
            try:
                await conn.ws.send_json(data)
            except Exception:
                dead.append(conn.ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
