import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, event: dict) -> None:
        for websocket in list(self._connections):
            try:
                await websocket.send_json(event)
            except Exception:  # noqa: BLE001 - a broken socket fails in arbitrary ways
                logger.debug("WebSocket broadcast failed, dropping the connection")
                self.disconnect(websocket)


ws_manager = ConnectionManager()
