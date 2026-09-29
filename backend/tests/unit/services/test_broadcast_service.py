import asyncio
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.config import settings
from src.core.constants import BroadcastStatus
from src.core.exceptions import AppException, ConflictException, MessengerException
from src.core.texts import (
    BROADCAST_IN_PROGRESS,
    BROADCAST_NO_RECIPIENTS,
    BROADCAST_PHOTO_UNAVAILABLE,
    BUILDING_NOT_FOUND,
)
from src.providers.messenger_provider import OutgoingFile
from src.services.broadcast_service import BroadcastService
from src.services.notification_service import MAIN_MENU_ROW

RATE = 4


def _active_building() -> MagicMock:
    building = MagicMock()
    building.is_active = True
    return building


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    monkeypatch.setattr(settings, "broadcast_rate_per_second", RATE)

    db = AsyncMock()
    messenger = AsyncMock()
    storage = MagicMock()

    admin = MagicMock()
    admin.id = 42
    author = MagicMock()
    author.id = 42

    broadcast = MagicMock()
    broadcast.id = 7
    broadcast.text = "Уважаемые жильцы"
    broadcast.file_id = None

    broadcasts = MagicMock()
    broadcasts.create = AsyncMock(return_value=broadcast)
    broadcasts.get_by_id = AsyncMock(return_value=broadcast)
    broadcasts.list = AsyncMock(return_value=[])
    broadcasts.count = AsyncMock(return_value=0)
    broadcasts.save_progress = AsyncMock()
    broadcasts.finish = AsyncMock()

    buildings = MagicMock()
    buildings.list_by_ids = AsyncMock(return_value=[])

    users = MagicMock()
    users.list_broadcast_recipients = AsyncMock(return_value=[101, 102])

    files = MagicMock()
    files.get_by_id = AsyncMock()

    file_service = MagicMock()
    file_service.get_max_token = AsyncMock(return_value="tok")

    content = MagicMock()
    content.ensure_content_image = AsyncMock()

    with ExitStack() as stack:
        stack.enter_context(
            patch("src.services.broadcast_service.BroadcastRepository", return_value=broadcasts)
        )
        stack.enter_context(
            patch("src.services.broadcast_service.BuildingRepository", return_value=buildings)
        )
        stack.enter_context(
            patch("src.services.broadcast_service.UserRepository", return_value=users)
        )
        stack.enter_context(
            patch("src.services.broadcast_service.FileRepository", return_value=files)
        )
        stack.enter_context(
            patch("src.services.broadcast_service.FileService", return_value=file_service)
        )
        stack.enter_context(
            patch("src.services.broadcast_service.ContentService", return_value=content)
        )
        run_bg = stack.enter_context(patch("src.services.broadcast_service.run_in_background"))
        run_broadcast = stack.enter_context(
            patch(
                "src.services.broadcast_service.run_broadcast",
                new=MagicMock(return_value="broadcast-coroutine"),
            )
        )
        sleep = stack.enter_context(
            patch(
                "src.services.broadcast_service.asyncio.sleep",
                new_callable=AsyncMock,
            )
        )
        service = BroadcastService(db, messenger, storage)

        yield SimpleNamespace(
            db=db,
            messenger=messenger,
            storage=storage,
            admin=admin,
            broadcast=broadcast,
            broadcasts=broadcasts,
            buildings=buildings,
            users=users,
            files=files,
            file_service=file_service,
            content=content,
            run_bg=run_bg,
            run_broadcast=run_broadcast,
            sleep=sleep,
            service=service,
        )


async def test_send_text_only_uses_menu_button_and_markdown(env: SimpleNamespace) -> None:
    await env.service.send(env.broadcast.id, [101, 102, 103])

    assert env.messenger.send_message.await_count == 3
    for awaited in env.messenger.send_message.await_args_list:
        assert awaited.args == (awaited.args[0], "Уважаемые жильцы")
        assert awaited.kwargs == {"buttons": [MAIN_MENU_ROW], "files": None, "markdown": True}
    assert [awaited.args[0] for awaited in env.messenger.send_message.await_args_list] == [
        101,
        102,
        103,
    ]
    env.broadcasts.finish.assert_awaited_once_with(env.broadcast.id, BroadcastStatus.DONE)


async def test_send_with_photo_passes_token_and_mime(env: SimpleNamespace) -> None:
    env.broadcast.file_id = 5
    file = MagicMock()
    file.max_token = "tok-photo"
    file.mime = "image/jpeg"
    env.files.get_by_id.return_value = file

    await env.service.send(env.broadcast.id, [101])

    env.files.get_by_id.assert_awaited_once_with(5)
    assert env.messenger.send_message.await_args.kwargs["files"] == [
        OutgoingFile("tok-photo", "image/jpeg")
    ]


async def test_send_without_stored_token_sends_no_files(env: SimpleNamespace) -> None:
    env.broadcast.file_id = 5
    file = MagicMock()
    file.max_token = None
    file.mime = "image/jpeg"
    env.files.get_by_id.return_value = file

    await env.service.send(env.broadcast.id, [101])

    assert env.messenger.send_message.await_args.kwargs["files"] is None


async def test_send_counts_delivered_and_failed_and_finishes(env: SimpleNamespace) -> None:
    env.messenger.send_message.side_effect = [
        None,
        MessengerException(),
        None,
        MessengerException(),
    ]

    await env.service.send(env.broadcast.id, [101, 102, 103, 104])

    assert env.messenger.send_message.await_count == 4
    env.broadcasts.save_progress.assert_awaited_once_with(
        env.broadcast.id, delivered_count=2, failed_count=2
    )
    env.broadcasts.finish.assert_awaited_once_with(env.broadcast.id, BroadcastStatus.DONE)
    assert env.db.commit.await_count == 1


async def test_send_paces_between_recipients(env: SimpleNamespace) -> None:
    await env.service.send(env.broadcast.id, [101, 102, 103])

    assert env.sleep.await_args_list == [call(1 / RATE), call(1 / RATE)]


async def test_send_saves_progress_every_ten(env: SimpleNamespace) -> None:
    recipients = list(range(1, 26))

    await env.service.send(env.broadcast.id, recipients)

    # Saved at 10, 20 and at the end; nothing between.
    assert env.broadcasts.save_progress.await_count == 3
    assert env.db.commit.await_count == 3
    env.broadcasts.finish.assert_awaited_once_with(env.broadcast.id, BroadcastStatus.DONE)


async def test_send_unexpected_error_marks_interrupted(env: SimpleNamespace) -> None:
    env.messenger.send_message.side_effect = [None, None, RuntimeError("boom")]

    await env.service.send(env.broadcast.id, [101, 102, 103])

    env.db.rollback.assert_awaited_once()
    env.broadcasts.save_progress.assert_awaited_once_with(
        env.broadcast.id, delivered_count=2, failed_count=0
    )
    env.broadcasts.finish.assert_awaited_once_with(env.broadcast.id, BroadcastStatus.INTERRUPTED)
    assert env.db.commit.await_count == 1


async def test_send_cancellation_propagates_and_does_not_touch_status(
    env: SimpleNamespace,
) -> None:
    env.messenger.send_message.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await env.service.send(env.broadcast.id, [101, 102])

    env.broadcasts.finish.assert_not_awaited()
    env.broadcasts.save_progress.assert_not_awaited()
    env.db.rollback.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_count_audience_returns_recipient_count(env: SimpleNamespace) -> None:
    env.buildings.list_by_ids.return_value = [_active_building(), _active_building()]
    env.users.list_broadcast_recipients.return_value = [101, 102, 103]

    count = await env.service.count_audience([3, 3, 4])

    assert count == 3
    env.buildings.list_by_ids.assert_awaited_once_with([3, 4])
    env.users.list_broadcast_recipients.assert_awaited_once_with([3, 4])
    env.broadcasts.create.assert_not_awaited()


async def test_count_audience_all_buildings_skips_lookup(env: SimpleNamespace) -> None:
    count = await env.service.count_audience(None)

    assert count == 2
    env.buildings.list_by_ids.assert_not_awaited()
    env.users.list_broadcast_recipients.assert_awaited_once_with(None)


async def test_count_audience_unknown_building_rejected(env: SimpleNamespace) -> None:
    env.buildings.list_by_ids.return_value = []

    with pytest.raises(AppException) as exc:
        await env.service.count_audience([5])

    assert exc.value.status_code == 400
    assert exc.value.message == BUILDING_NOT_FOUND
    env.users.list_broadcast_recipients.assert_not_awaited()


async def test_count_audience_inactive_building_rejected(env: SimpleNamespace) -> None:
    building = MagicMock()
    building.is_active = False
    env.buildings.list_by_ids.return_value = [building]

    with pytest.raises(AppException) as exc:
        await env.service.count_audience([5])

    assert exc.value.status_code == 400
    env.users.list_broadcast_recipients.assert_not_awaited()


async def test_create_success_schedules_the_job(env: SimpleNamespace) -> None:
    env.broadcast.id = 77
    env.broadcast.author = env.admin
    buildings = [_active_building(), _active_building()]
    env.buildings.list_by_ids.return_value = buildings
    env.users.list_broadcast_recipients.return_value = [101, 102]

    result = await env.service.create(env.admin, "  Текст  ", None, [3, 3, 4])

    assert result is env.broadcast
    env.buildings.list_by_ids.assert_awaited_once_with([3, 4])
    env.users.list_broadcast_recipients.assert_awaited_once_with([3, 4])
    env.broadcasts.create.assert_awaited_once_with(
        author_id=env.admin.id,
        text="  Текст  ",
        file_id=None,
        recipients_total=2,
        buildings=buildings,
    )
    env.db.commit.assert_awaited_once()
    env.run_broadcast.assert_called_once_with(env.broadcast.id, [101, 102])
    env.run_bg.assert_called_once_with(
        env.run_broadcast.return_value, name=f"broadcast-{env.broadcast.id}"
    )
    env.broadcasts.finish.assert_not_awaited()


async def test_create_no_recipients_rejected_before_saving(env: SimpleNamespace) -> None:
    env.users.list_broadcast_recipients.return_value = []

    with pytest.raises(AppException) as exc:
        await env.service.create(env.admin, "Текст", None, None)

    assert exc.value.status_code == 400
    assert exc.value.message == BROADCAST_NO_RECIPIENTS
    env.broadcasts.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_unknown_building_rejected(env: SimpleNamespace) -> None:
    env.buildings.list_by_ids.return_value = []

    with pytest.raises(AppException) as exc:
        await env.service.create(env.admin, "Текст", None, [5])

    assert exc.value.status_code == 400
    env.users.list_broadcast_recipients.assert_not_awaited()
    env.broadcasts.create.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_inactive_building_rejected(env: SimpleNamespace) -> None:
    building = MagicMock()
    building.is_active = False
    env.buildings.list_by_ids.return_value = [building]

    with pytest.raises(AppException) as exc:
        await env.service.create(env.admin, "Текст", None, [5])

    assert exc.value.status_code == 400
    assert exc.value.message == BUILDING_NOT_FOUND
    env.users.list_broadcast_recipients.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_rejects_file_that_is_not_content_image(env: SimpleNamespace) -> None:
    env.content.ensure_content_image.side_effect = AppException("Фото не найдено", status_code=400)

    with pytest.raises(AppException) as exc:
        await env.service.create(env.admin, "Текст", 5, None)

    assert exc.value.status_code == 400
    env.users.list_broadcast_recipients.assert_not_awaited()
    env.broadcasts.create.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_upload_failure_propagates_before_saving(env: SimpleNamespace) -> None:
    env.file_service.get_max_token.side_effect = MessengerException()

    with pytest.raises(MessengerException):
        await env.service.create(env.admin, "Текст", 5, None)

    env.broadcasts.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_photo_read_failure_is_a_bad_request(env: SimpleNamespace) -> None:
    env.file_service.get_max_token.side_effect = OSError("gone")

    with pytest.raises(AppException) as exc:
        await env.service.create(env.admin, "Текст", 5, None)

    assert exc.value.status_code == 400
    assert exc.value.message == BROADCAST_PHOTO_UNAVAILABLE
    env.broadcasts.create.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_second_sending_conflicts(env: SimpleNamespace) -> None:
    env.broadcasts.create.side_effect = IntegrityError("insert", {}, Exception("unique"))

    with pytest.raises(ConflictException) as exc:
        await env.service.create(env.admin, "Текст", None, None)

    assert exc.value.status_code == 409
    assert exc.value.message == BROADCAST_IN_PROGRESS
    env.db.rollback.assert_awaited_once()
    env.db.commit.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_with_photo_caches_token_before_insert(env: SimpleNamespace) -> None:
    photo = MagicMock()
    env.content.ensure_content_image.return_value = photo
    env.file_service.get_max_token.return_value = None

    await env.service.create(env.admin, "Текст", 5, None)

    env.content.ensure_content_image.assert_awaited_once_with(5)
    env.file_service.get_max_token.assert_awaited_once_with(photo, env.messenger)
    env.broadcasts.create.assert_awaited_once_with(
        author_id=env.admin.id,
        text="Текст",
        file_id=5,
        recipients_total=2,
        buildings=[],
    )
    env.run_bg.assert_called_once()
