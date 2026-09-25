import asyncio
import logging
from contextlib import suppress

from maxapi import Bot, Dispatcher

from src.bot.handlers.menu import router as menu_router
from src.bot.handlers.start import router as start_router
from src.bot.middlewares import UserSyncMiddleware
from src.core.config import settings

logger = logging.getLogger(__name__)

dp = Dispatcher()
dp.register_outer_middleware(UserSyncMiddleware())
dp.include_routers(start_router, menu_router)

_bot: Bot | None = None
_polling_task: asyncio.Task[None] | None = None


def _on_polling_done(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Bot polling stopped with an error", exc_info=exc)


async def start_bot() -> None:
    global _bot, _polling_task

    _bot = Bot(token=settings.bot_token)
    _polling_task = asyncio.create_task(dp.start_polling(_bot))
    _polling_task.add_done_callback(_on_polling_done)


async def stop_bot() -> None:
    global _bot, _polling_task

    try:
        await dp.stop_polling()

        if _polling_task is not None:
            _polling_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await _polling_task
            _polling_task = None
    finally:
        if _bot is not None:
            await _bot.close_session()
            _bot = None
