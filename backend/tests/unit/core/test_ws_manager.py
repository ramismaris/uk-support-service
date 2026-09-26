from unittest.mock import AsyncMock

from src.core.ws_manager import ConnectionManager


def _ws() -> AsyncMock:
    return AsyncMock()


async def test_connect_accepts_and_broadcast_reaches_connection() -> None:
    manager = ConnectionManager()
    websocket = _ws()

    await manager.connect(websocket)
    await manager.broadcast({"type": "ticket_created"})

    websocket.accept.assert_awaited_once()
    websocket.send_json.assert_awaited_once_with({"type": "ticket_created"})


async def test_broadcast_sends_to_every_connection() -> None:
    manager = ConnectionManager()
    first = _ws()
    second = _ws()
    await manager.connect(first)
    await manager.connect(second)

    await manager.broadcast({"type": "ticket_updated"})

    first.send_json.assert_awaited_once_with({"type": "ticket_updated"})
    second.send_json.assert_awaited_once_with({"type": "ticket_updated"})


async def test_failing_connection_is_dropped_and_others_still_served() -> None:
    manager = ConnectionManager()
    failing = _ws()
    failing.send_json.side_effect = RuntimeError("closed")
    healthy = _ws()
    await manager.connect(failing)
    await manager.connect(healthy)

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
    await manager.connect(websocket)

    manager.disconnect(websocket)
    manager.disconnect(websocket)

    await manager.broadcast({"type": "ticket_created"})

    websocket.send_json.assert_not_awaited()
