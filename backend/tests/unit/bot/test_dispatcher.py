from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot import dispatcher
from src.bot.handlers.chat import router as chat_router
from src.bot.handlers.menu import router as menu_router
from src.bot.handlers.question import router as question_router
from src.bot.handlers.request_form import router as request_form_router
from src.bot.handlers.start import router as start_router


def test_routers_registered_in_order():
    assert dispatcher.dp.routers == [
        start_router,
        request_form_router,
        question_router,
        chat_router,
        menu_router,
    ]


def test_menu_router_registered_after_start_router():
    assert dispatcher.dp.routers.index(menu_router) > dispatcher.dp.routers.index(start_router)


def test_request_form_router_registered_before_menu_router():
    assert dispatcher.dp.routers.index(request_form_router) < dispatcher.dp.routers.index(
        menu_router
    )


def test_question_router_between_form_and_chat():
    assert dispatcher.dp.routers.index(question_router) > dispatcher.dp.routers.index(
        request_form_router
    )
    assert dispatcher.dp.routers.index(question_router) < dispatcher.dp.routers.index(chat_router)


def test_chat_router_between_question_and_menu():
    assert dispatcher.dp.routers.index(chat_router) > dispatcher.dp.routers.index(question_router)
    assert dispatcher.dp.routers.index(chat_router) < dispatcher.dp.routers.index(menu_router)


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
