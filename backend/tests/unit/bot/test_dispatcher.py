from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot import dispatcher


async def test_stop_bot_closes_session_when_polling_failed():
    bot = MagicMock()
    bot.close_session = AsyncMock()

    with (
        patch.object(dispatcher, "Bot", return_value=bot),
        patch.object(
            dispatcher.dp,
            "start_polling",
            new=AsyncMock(side_effect=RuntimeError("polling failed")),
        ),
        patch.object(dispatcher.dp, "stop_polling", new=AsyncMock()),
    ):
        await dispatcher.start_bot()

        task = dispatcher._polling_task
        assert task is not None
        with pytest.raises(RuntimeError, match="polling failed"):
            await task

        await dispatcher.stop_bot()

    bot.close_session.assert_awaited_once()
    assert dispatcher._bot is None
    assert dispatcher._polling_task is None
