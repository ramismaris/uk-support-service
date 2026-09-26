import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Close codes of the WebSocket application range: the panel can tell why it was closed.
WS_UNAUTHORIZED = 4401
WS_FORBIDDEN = 4403


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self._connections[websocket] = user_id

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def broadcast(self, event: dict) -> None:
        for websocket in list(self._connections):
            try:
                await websocket.send_json(event)
            except Exception:  # noqa: BLE001 - a broken socket fails in arbitrary ways
                logger.debug("WebSocket broadcast failed, dropping the connection")
                self.disconnect(websocket)

    async def close_user(self, user_id: int, code: int) -> None:
        sockets = [websocket for websocket, uid in self._connections.items() if uid == user_id]
        for websocket in sockets:
            self.disconnect(websocket)
        for websocket in sockets:
            try:
                await websocket.close(code=code)
            except Exception:  # noqa: BLE001 - a broken socket fails in arbitrary ways
                logger.debug("WebSocket close failed for an already-closed connection")


ws_manager = ConnectionManager()
