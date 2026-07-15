"""WebSocket connection manager with broadcast and heartbeat."""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from fastapi import WebSocket

from app.schemas.ws_message import EventType, WSMessage

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30  # seconds between PINGs
PONG_TIMEOUT = 10  # seconds to wait for PONG before disconnecting


@dataclass
class ConnectionInfo:
    """State for a single WebSocket connection."""

    email: str | None = None
    last_pong: float = field(default_factory=time.monotonic)


class WSConnectionManager:
    """Gerencia conexões WebSocket com broadcast e heartbeat."""

    def __init__(self, heartbeat_interval: int = HEARTBEAT_INTERVAL, pong_timeout: int = PONG_TIMEOUT) -> None:
        self._connections: dict[WebSocket, ConnectionInfo] = {}
        self._heartbeat_tasks: dict[WebSocket, asyncio.Task] = {}
        self._heartbeat_interval = heartbeat_interval
        self._pong_timeout = pong_timeout

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    async def connect(
        self, websocket: WebSocket, user_email: str | None = None
    ) -> None:
        await websocket.accept()
        self._connections[websocket] = ConnectionInfo(
            email=user_email, last_pong=time.monotonic()
        )
        task = asyncio.create_task(self._heartbeat_loop(websocket))
        self._heartbeat_tasks[websocket] = task
        logger.info(
            "WS connect: %s connections=%d",
            user_email or "anonymous",
            self.active_connections,
        )

    def disconnect(self, websocket: WebSocket) -> None:
        info = self._connections.pop(websocket, None)
        if info is not None:
            logger.info(
                "WS disconnect: %s connections=%d",
                info.email or "anonymous",
                self.active_connections,
            )
        task = self._heartbeat_tasks.pop(websocket, None)
        if task is not None:
            task.cancel()

    def record_pong(self, websocket: WebSocket) -> None:
        """Registra que recebemos PONG deste cliente."""
        info = self._connections.get(websocket)
        if info is not None:
            info.last_pong = time.monotonic()

    async def broadcast(self, message: WSMessage) -> None:
        """Envia mensagem para todas as conexões ativas."""
        payload = message.model_dump(mode="json")
        disconnected: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def send_personal(
        self, message: WSMessage, websocket: WebSocket
    ) -> None:
        """Envia mensagem para uma conexão específica."""
        payload = message.model_dump(mode="json")
        try:
            await websocket.send_json(payload)
        except Exception:
            self.disconnect(websocket)

    async def _heartbeat_loop(self, websocket: WebSocket) -> None:
        """Envia ping periódico e desconecta se não receber PONG."""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)

                info = self._connections.get(websocket)
                if info is None:
                    break

                before = info.last_pong

                ping = WSMessage(type=EventType.PING)
                try:
                    await websocket.send_json(ping.model_dump(mode="json"))
                except Exception:
                    self.disconnect(websocket)
                    break

                # Wait for client to respond with PONG (handled by main loop)
                await asyncio.sleep(self._pong_timeout)

                info = self._connections.get(websocket)
                if info is None:
                    break

                if info.last_pong == before:
                    logger.warning(
                        "WS heartbeat timeout — no PONG, disconnecting"
                    )
                    self.disconnect(websocket)
                    break
        except asyncio.CancelledError:
            pass

    async def shutdown(self) -> None:
        """Cleanup all connections on app shutdown."""
        for ws in list(self._connections.keys()):
            self.disconnect(ws)


# Singleton
manager = WSConnectionManager()
