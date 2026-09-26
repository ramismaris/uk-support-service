from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UserRole
from src.core.exceptions import ForbiddenException, UnauthorizedException
from src.core.ws_manager import WS_FORBIDDEN, WS_UNAUTHORIZED, ws_manager
from src.db.session import get_db
from src.services.auth_service import AuthService

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def staff_websocket(
    websocket: WebSocket,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Query()] = None,
) -> None:
    if token is None:
        await _reject(websocket, WS_UNAUTHORIZED)
        return

    try:
        user = await AuthService(db).get_user_by_token(token)
    except UnauthorizedException:
        await _reject(websocket, WS_UNAUTHORIZED)
        return
    except ForbiddenException:
        await _reject(websocket, WS_FORBIDDEN)
        return

    if user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        await _reject(websocket, WS_FORBIDDEN)
        return

    # Do not keep a pooled connection idle inside a transaction while the panel is open.
    await db.close()

    await ws_manager.connect(websocket, user.id)
    try:
        while True:
            # Incoming frames are ignored; receiving only detects the disconnect.
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    finally:
        ws_manager.disconnect(websocket)


async def _reject(websocket: WebSocket, code: int) -> None:
    # Accept before closing so the client receives the application close code.
    await websocket.accept()
    await websocket.close(code=code)
