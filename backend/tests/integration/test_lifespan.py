from unittest.mock import patch

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
