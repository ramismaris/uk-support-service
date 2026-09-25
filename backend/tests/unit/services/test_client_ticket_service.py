from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.constants import TicketStatus, TicketType
from src.core.exceptions import AppException, MessengerException, NotFoundException
from src.services.client_ticket_service import ClientTicketService
from src.services.file_service import MAX_FILE_SIZE


@pytest.fixture
def env() -> SimpleNamespace:
    db = AsyncMock()
    db.add = MagicMock()
    messenger = AsyncMock()
    storage = MagicMock()
    storage.save = AsyncMock()
    storage.delete = AsyncMock()

    ticket = MagicMock()
    ticket.id = 1042
    tickets = MagicMock()
    tickets.create = AsyncMock(return_value=ticket)

    files = MagicMock()
    files.list_by_ids = AsyncMock(return_value=[])

    changes = MagicMock()
    changes.create = AsyncMock()

    category = MagicMock()
    category.id = 7
    category.is_active = True
    categories = MagicMock()
    categories.get_by_id = AsyncMock(return_value=category)

    building = MagicMock()
    building.id = 8
    building.is_active = True
    buildings = MagicMock()
    buildings.get_by_id = AsyncMock(return_value=building)

    notifications = MagicMock()
    notifications.send_status_card = AsyncMock()

    client = MagicMock()
    client.id = 1
    client.phone = "+7 (900) 000-00-03"
    client.active_ticket_id = None

    with ExitStack() as stack:
        stack.enter_context(
            patch("src.services.client_ticket_service.TicketRepository", return_value=tickets)
        )
        stack.enter_context(
            patch("src.services.client_ticket_service.FileRepository", return_value=files)
        )
        stack.enter_context(
            patch(
                "src.services.client_ticket_service.StatusChangeRepository",
                return_value=changes,
            )
        )
        stack.enter_context(
            patch(
                "src.services.client_ticket_service.CategoryRepository",
                return_value=categories,
            )
        )
        stack.enter_context(
            patch(
                "src.services.client_ticket_service.BuildingRepository",
                return_value=buildings,
            )
        )
        stack.enter_context(
            patch(
                "src.services.client_ticket_service.NotificationService",
                return_value=notifications,
            )
        )
        run_bg = stack.enter_context(patch("src.services.client_ticket_service.run_in_background"))
        notify = MagicMock(return_value="notify-coroutine")
        stack.enter_context(
            patch(
                "src.services.client_ticket_service.notify_staff_about_new_ticket",
                new=notify,
            )
        )
        service = ClientTicketService(db, messenger, storage)

        yield SimpleNamespace(
            db=db,
            messenger=messenger,
            storage=storage,
            tickets=tickets,
            ticket=ticket,
            files=files,
            changes=changes,
            category=category,
            categories=categories,
            building=building,
            buildings=buildings,
            notifications=notifications,
            client=client,
            run_bg=run_bg,
            notify=notify,
            service=service,
        )


async def _request(env: SimpleNamespace, **overrides):
    params = {
        "category_id": env.category.id,
        "building_id": env.building.id,
        "apartment": "45",
        "description": "Течёт кран",
        "preferred_time": "вечером",
        "photo_ids": [],
    }
    params.update(overrides)
    return await env.service.create_request(env.client, **params)


def _assert_no_writes(env: SimpleNamespace) -> None:
    env.tickets.create.assert_not_awaited()
    env.changes.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.notifications.send_status_card.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_create_request_happy_path(env: SimpleNamespace) -> None:
    photo_one = MagicMock()
    photo_one.id = 1
    photo_one.ticket_id = None
    photo_one.message_id = None
    photo_two = MagicMock()
    photo_two.id = 2
    photo_two.ticket_id = None
    photo_two.message_id = None
    env.files.list_by_ids.return_value = [photo_one, photo_two]
    order: list[str] = []
    env.db.commit.side_effect = lambda: order.append("commit")
    env.notifications.send_status_card.side_effect = lambda ticket: order.append("card")

    ticket = await _request(env, photo_ids=[1, 2])

    assert ticket is env.ticket
    env.files.list_by_ids.assert_awaited_once_with([1, 2])
    env.tickets.create.assert_awaited_once_with(
        type=TicketType.REQUEST,
        status=TicketStatus.NEW,
        client_id=env.client.id,
        description="Течёт кран",
        category_id=env.category.id,
        building_id=env.building.id,
        apartment="45",
        contact_phone=env.client.phone,
        preferred_time="вечером",
    )
    assert env.ticket.client is env.client
    assert env.ticket.category is env.category
    assert env.ticket.building is env.building
    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        None,
        TicketStatus.NEW,
        changed_by_id=env.client.id,
    )
    assert photo_one.ticket_id == env.ticket.id
    assert photo_two.ticket_id == env.ticket.id
    assert env.client.active_ticket_id == env.ticket.id
    assert order == ["commit", "card"]
    env.notifications.send_status_card.assert_awaited_once_with(env.ticket)
    env.notify.assert_called_once_with(env.ticket.id)
    env.run_bg.assert_called_once_with(
        env.notify.return_value, name=f"notify-staff-{env.ticket.id}"
    )


async def test_blank_description_rejected_writes_nothing(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await _request(env, description="   ")

    assert exc.value.status_code == 400
    _assert_no_writes(env)


async def test_blank_apartment_rejected_writes_nothing(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await _request(env, apartment="  ")

    assert exc.value.status_code == 400
    _assert_no_writes(env)


@pytest.mark.parametrize("value", ["12", "12А", "12/1", "офис 5"])
async def test_apartment_valid_values_are_stripped_and_accepted(
    env: SimpleNamespace, value: str
) -> None:
    await _request(env, apartment=f"  {value}  ")

    assert env.tickets.create.await_args.kwargs["apartment"] == value


@pytest.mark.parametrize("value", ["12*", "_12", "[12](x)", "1" * 21, "   "])
async def test_apartment_invalid_values_rejected_writes_nothing(
    env: SimpleNamespace, value: str
) -> None:
    with pytest.raises(AppException) as exc:
        await _request(env, apartment=value)

    assert exc.value.status_code == 400
    _assert_no_writes(env)


async def test_unknown_category_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.categories.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await _request(env)

    _assert_no_writes(env)


async def test_inactive_category_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.category.is_active = False

    with pytest.raises(NotFoundException):
        await _request(env)

    _assert_no_writes(env)


async def test_unknown_building_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.buildings.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await _request(env)

    _assert_no_writes(env)


async def test_inactive_building_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.building.is_active = False

    with pytest.raises(NotFoundException):
        await _request(env)

    _assert_no_writes(env)


async def test_unknown_photo_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.files.list_by_ids.return_value = []

    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[999])

    assert exc.value.status_code == 400
    _assert_no_writes(env)


async def test_attached_photo_rejected_writes_nothing(env: SimpleNamespace) -> None:
    attached = MagicMock()
    attached.id = 5
    attached.ticket_id = 99
    attached.message_id = None
    env.files.list_by_ids.return_value = [attached]

    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[5])

    assert exc.value.status_code == 400
    _assert_no_writes(env)


async def test_photo_attached_to_message_rejected_writes_nothing(env: SimpleNamespace) -> None:
    attached = MagicMock()
    attached.id = 5
    attached.ticket_id = None
    attached.message_id = 9
    env.files.list_by_ids.return_value = [attached]

    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[5])

    assert exc.value.status_code == 400
    _assert_no_writes(env)


async def test_duplicate_photos_rejected_writes_nothing(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[5, 5])

    assert exc.value.status_code == 400
    env.files.list_by_ids.assert_not_awaited()
    _assert_no_writes(env)


async def test_blank_preferred_time_becomes_none(env: SimpleNamespace) -> None:
    await _request(env, preferred_time="   ")

    assert env.tickets.create.await_args.kwargs["preferred_time"] is None


async def test_failed_status_card_still_returns_ticket_and_notifies_staff(
    env: SimpleNamespace,
) -> None:
    env.notifications.send_status_card.side_effect = MessengerException()

    ticket = await _request(env)

    assert ticket is env.ticket
    env.db.commit.assert_awaited_once()
    env.run_bg.assert_called_once_with(
        env.notify.return_value, name=f"notify-staff-{env.ticket.id}"
    )


async def test_save_photo_passes_max_file_size_and_saves_image(env: SimpleNamespace) -> None:
    env.messenger.download_file.return_value = (b"photo-bytes", "image/webp")

    photo = await env.service.save_photo("https://i.oneme.ru/i?r=abc")

    env.messenger.download_file.assert_awaited_once_with(
        "https://i.oneme.ru/i?r=abc", MAX_FILE_SIZE
    )
    assert photo.mime == "image/webp"
    assert photo.size == len(b"photo-bytes")
    env.storage.save.assert_awaited_once()


async def test_save_photo_rejects_non_image(env: SimpleNamespace) -> None:
    env.messenger.download_file.return_value = (b"data", "application/pdf")

    with pytest.raises(AppException) as exc:
        await env.service.save_photo("https://i.oneme.ru/i?r=abc")

    assert exc.value.status_code == 400
    env.storage.save.assert_not_awaited()


async def test_save_photo_lets_messenger_exception_through(env: SimpleNamespace) -> None:
    env.messenger.download_file.side_effect = MessengerException()

    with pytest.raises(MessengerException):
        await env.service.save_photo("https://i.oneme.ru/i?r=abc")
