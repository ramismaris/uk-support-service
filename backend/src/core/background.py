import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)

_tasks: set[asyncio.Task[None]] = set()


def _on_task_done(task: asyncio.Task[None]) -> None:
    _tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Background task %s failed", task.get_name(), exc_info=exc)


def run_in_background(coro: Coroutine[Any, Any, None], *, name: str) -> asyncio.Task[None]:
    task = asyncio.create_task(coro, name=name)
    _tasks.add(task)
    task.add_done_callback(_on_task_done)
    return task
