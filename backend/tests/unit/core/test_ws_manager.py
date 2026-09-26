from unittest.mock import AsyncMock

from src.core.ws_manager import WS_FORBIDDEN, ConnectionManager


def _ws() -> AsyncMock:
    return AsyncMock()


async def test_connect_accepts_and_broadcast_reaches_connection() -> None:
    manager = ConnectionManager()
    websocket = _ws()

    await manager.connect(websocket, user_id=1)
    await manager.broadcast({"type": "ticket_created"})

    websocket.accept.assert_awaited_once()
    websocket.send_json.assert_awaited_once_with({"type": "ticket_created"})


async def test_broadcast_sends_to_every_connection() -> None:
    manager = ConnectionManager()
    first = _ws()
    second = _ws()
    await manager.connect(first, user_id=1)
    await manager.connect(second, user_id=2)

    await manager.broadcast({"type": "ticket_updated"})

    first.send_json.assert_awaited_once_with({"type": "ticket_updated"})
    second.send_json.assert_awaited_once_with({"type": "ticket_updated"})


async def test_failing_connection_is_dropped_and_others_still_served() -> None:
    manager = ConnectionManager()
    failing = _ws()
    failing.send_json.side_effect = RuntimeError("closed")
    healthy = _ws()
    await manager.connect(failing, user_id=1)
    await manager.connect(healthy, user_id=2)

    await manager.broadcast({"type": "message_created"})

    failing.send_json.assert_awaited_once()
    healthy.send_json.assert_awaited_once_with({"type": "message_created"})

    failing.send_json.reset_mock()
    await manager.broadcast({"type": "ticket_updated"})

    failing.send_json.assert_not_awaited()
    assert healthy.send_json.await_count == 2


async def test_disconnect_is_idempotent() -> None:
    manager = ConnectionManager()
    websocket = _ws()
    await manager.connect(websocket, user_id=1)

    manager.disconnect(websocket)
    manager.disconnect(websocket)

    await manager.broadcast({"type": "ticket_created"})

    websocket.send_json.assert_not_awaited()


async def test_close_user_closes_only_that_users_sockets() -> None:
    manager = ConnectionManager()
    target = _ws()
    other = _ws()
    await manager.connect(target, user_id=1)
    await manager.connect(other, user_id=2)

    await manager.close_user(user_id=1, code=WS_FORBIDDEN)

    target.close.assert_awaited_once_with(code=WS_FORBIDDEN)
    other.close.assert_not_awaited()


async def test_closed_user_sockets_get_no_broadcast_but_others_do() -> None:
    manager = ConnectionManager()
    target = _ws()
    other = _ws()
    await manager.connect(target, user_id=1)
    await manager.connect(other, user_id=2)

    await manager.close_user(user_id=1, code=WS_FORBIDDEN)

    await manager.broadcast({"type": "ticket_created"})

    target.send_json.assert_not_awaited()
    other.send_json.assert_awaited_once_with({"type": "ticket_created"})


async def test_close_user_survives_a_failing_socket() -> None:
    manager = ConnectionManager()
    failing = _ws()
    failing.close.side_effect = RuntimeError("already closed")
    healthy = _ws()
    await manager.connect(failing, user_id=1)
    await manager.connect(healthy, user_id=1)

    await manager.close_user(user_id=1, code=WS_FORBIDDEN)

    failing.close.assert_awaited_once_with(code=WS_FORBIDDEN)
    healthy.close.assert_awaited_once_with(code=WS_FORBIDDEN)

    await manager.broadcast({"type": "ticket_created"})
    failing.send_json.assert_not_awaited()
    healthy.send_json.assert_not_awaited()
