import asyncio
import logging

from src.core import background


async def test_run_in_background_runs_coroutine():
    done = asyncio.Event()

    async def work() -> None:
        done.set()

    task = background.run_in_background(work(), name="work")

    await asyncio.wait_for(done.wait(), timeout=1)
    await task


async def test_run_in_background_logs_exception_without_raising(caplog):
    async def boom() -> None:
        raise RuntimeError("background boom")

    with caplog.at_level(logging.ERROR, logger="src.core.background"):
        task = background.run_in_background(boom(), name="boom")
        await asyncio.wait([task])
        await asyncio.sleep(0)

    assert "background boom" in caplog.text
    assert task.exception() is not None


async def test_run_in_background_ignores_cancelled_task(caplog):
    async def forever() -> None:
        await asyncio.sleep(10)

    with caplog.at_level(logging.ERROR, logger="src.core.background"):
        task = background.run_in_background(forever(), name="forever")
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.wait([task])
        await asyncio.sleep(0)

    assert task.cancelled()
    assert caplog.text == ""


async def test_run_in_background_drops_reference_after_completion():
    async def work() -> None:
        return None

    task = background.run_in_background(work(), name="work")
    assert task in background._tasks

    await task
    await asyncio.sleep(0)

    assert task not in background._tasks
