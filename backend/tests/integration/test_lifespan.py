from unittest.mock import AsyncMock, patch

import pytest

from src.core.config import settings
from src.main import app


async def test_lifespan_with_bot_off_does_not_start_bot():
    with (
        patch("src.main.start_bot") as start_bot_mock,
        patch("src.main.stop_bot") as stop_bot_mock,
    ):
        async with app.router.lifespan_context(app):
            pass

    start_bot_mock.assert_not_called()
    stop_bot_mock.assert_not_called()


async def test_lifespan_closes_messenger_provider_when_stop_bot_fails(monkeypatch):
    monkeypatch.setattr(settings, "bot_mode", "polling")

    with (
        patch("src.main.start_bot", new_callable=AsyncMock),
        patch(
            "src.main.stop_bot",
            new_callable=AsyncMock,
            side_effect=RuntimeError("stop failed"),
        ),
        patch("src.main.close_messenger_provider", new_callable=AsyncMock) as close_mock,
        pytest.raises(RuntimeError),
    ):
        async with app.router.lifespan_context(app):
            pass

    close_mock.assert_awaited_once()
