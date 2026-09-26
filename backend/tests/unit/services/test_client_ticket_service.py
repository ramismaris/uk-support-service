from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.constants import TicketStatus, TicketType
from src.core.exceptions import (
    AppException,
    ConflictException,
    MessengerException,
    NotFoundException,
)
from src.core.texts import DESCRIPTION_LIMIT, MY_TICKETS_LIMIT
from src.services import ticket_rules
from src.services.client_ticket_service import (
    MY_TICKETS_CLOSED_STATUSES,
    ClientTicketService,
    validate_description,
)
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

    changes = MagicMock()
    changes.create = AsyncMock()

    category = MagicMock()
    category.id = 7
    category.is_active = True
    categories = MagicMock()
    categories.get_by_id = AsyncMock(return_value=category)
    categories.list_active = AsyncMock(return_value=[category])

    building = MagicMock()
    building.id = 8
    building.is_active = True
    buildings = MagicMock()
    buildings.get_by_id = AsyncMock(return_value=building)
    buildings.list_active = AsyncMock(return_value=[building])

    residence = MagicMock()
    residence.id = 3
    residence.user_id = 1
    residence.building_id = building.id
    residence.apartment = "45"
    residence.is_primary = True
    residences = MagicMock()
    residences.get = AsyncMock(return_value=None)
    residences.get_by_id = AsyncMock(return_value=None)
    residences.list_by_user = AsyncMock(return_value=[])
    residences.create = AsyncMock(return_value=residence)

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
                "src.services.client_ticket_service.ResidenceRepository",
                return_value=residences,
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
        service.file_service.get_unattached = AsyncMock(return_value=[])

        yield SimpleNamespace(
            db=db,
            messenger=messenger,
            storage=storage,
            tickets=tickets,
            ticket=ticket,
            file_service=service.file_service,
            changes=changes,
            category=category,
            categories=categories,
            building=building,
            buildings=buildings,
            residence=residence,
            residences=residences,
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


def test_validate_description_accepts_limit_length() -> None:
    value = "a" * DESCRIPTION_LIMIT

    assert validate_description(value) == value


def test_validate_description_strips() -> None:
    assert validate_description("  Течёт кран  ") == "Течёт кран"


def test_validate_description_rejects_over_limit() -> None:
    with pytest.raises(AppException) as exc:
        validate_description("a" * (DESCRIPTION_LIMIT + 1))

    assert exc.value.status_code == 400


def test_validate_description_rejects_blank() -> None:
    with pytest.raises(AppException) as exc:
        validate_description("   ")

    assert exc.value.status_code == 400


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
    env.file_service.get_unattached.return_value = [photo_one, photo_two]
    order: list[str] = []
    env.db.commit.side_effect = lambda: order.append("commit")
    env.notifications.send_status_card.side_effect = lambda ticket: order.append("card")

    ticket = await _request(env, photo_ids=[1, 2])

    assert ticket is env.ticket
    env.file_service.get_unattached.assert_awaited_once_with([1, 2])
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


async def test_too_long_description_rejected_writes_nothing(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await _request(env, description="a" * (DESCRIPTION_LIMIT + 1))

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
    env.file_service.get_unattached.side_effect = AppException("Фото не найдено", status_code=400)

    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[999])

    assert exc.value.status_code == 400
    env.file_service.get_unattached.assert_awaited_once_with([999])
    _assert_no_writes(env)


async def test_attached_photo_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.file_service.get_unattached.side_effect = AppException(
        "Фото уже прикреплено", status_code=400
    )

    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[5])

    assert exc.value.status_code == 400
    env.file_service.get_unattached.assert_awaited_once_with([5])
    _assert_no_writes(env)


async def test_photo_attached_to_message_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.file_service.get_unattached.side_effect = AppException(
        "Фото уже прикреплено", status_code=400
    )

    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[5])

    assert exc.value.status_code == 400
    env.file_service.get_unattached.assert_awaited_once_with([5])
    _assert_no_writes(env)


async def test_duplicate_photos_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.file_service.get_unattached.side_effect = AppException("Фото повторяются", status_code=400)

    with pytest.raises(AppException) as exc:
        await _request(env, photo_ids=[5, 5])

    assert exc.value.status_code == 400
    env.file_service.get_unattached.assert_awaited_once_with([5, 5])
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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("79161234567", "+79161234567"),
        ("+7 (916) 123-45-67", "+79161234567"),
        ("89161234567", "+79161234567"),
    ],
)
async def test_set_phone_normalizes(env: SimpleNamespace, raw: str, expected: str) -> None:
    await env.service.set_phone(env.client, raw)

    assert env.client.phone == expected
    env.db.commit.assert_awaited_once()


@pytest.mark.parametrize("raw", ["12345", "не телефон", "", "+7"])
async def test_set_phone_invalid_rejected(env: SimpleNamespace, raw: str) -> None:
    with pytest.raises(AppException) as exc:
        await env.service.set_phone(env.client, raw)

    assert exc.value.status_code == 400
    env.db.commit.assert_not_awaited()


async def test_add_residence_first_is_primary(env: SimpleNamespace) -> None:
    env.residences.list_by_user.return_value = []
    env.residence.is_primary = True

    residence = await env.service.add_residence(env.client, env.building.id, " 45 ")

    env.residences.create.assert_awaited_once_with(
        env.client.id, env.building.id, "45", is_primary=True
    )
    env.db.commit.assert_awaited_once()
    assert residence is env.residence


async def test_add_residence_second_is_not_primary(env: SimpleNamespace) -> None:
    env.residences.list_by_user.return_value = [env.residence]

    await env.service.add_residence(env.client, env.building.id, "45")

    assert env.residences.create.await_args.kwargs["is_primary"] is False


async def test_add_residence_existing_returned_without_write(env: SimpleNamespace) -> None:
    existing = MagicMock()
    env.residences.get.return_value = existing

    residence = await env.service.add_residence(env.client, env.building.id, "45")

    assert residence is existing
    env.residences.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_add_residence_inactive_building_rejected(env: SimpleNamespace) -> None:
    env.building.is_active = False

    with pytest.raises(NotFoundException):
        await env.service.add_residence(env.client, env.building.id, "45")

    env.residences.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_add_residence_bad_apartment_rejected(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await env.service.add_residence(env.client, env.building.id, "   ")

    assert exc.value.status_code == 400
    env.residences.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()


async def test_get_residence_returns_own(env: SimpleNamespace) -> None:
    own = MagicMock()
    own.user_id = env.client.id
    env.residences.get_by_id.return_value = own

    assert await env.service.get_residence(env.client, 5) is own


async def test_get_residence_of_another_client_rejected(env: SimpleNamespace) -> None:
    foreign = MagicMock()
    foreign.user_id = env.client.id + 1
    env.residences.get_by_id.return_value = foreign

    with pytest.raises(NotFoundException):
        await env.service.get_residence(env.client, 5)


async def test_get_residence_missing_rejected(env: SimpleNamespace) -> None:
    env.residences.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await env.service.get_residence(env.client, 5)


async def test_lists_delegate_to_repositories(env: SimpleNamespace) -> None:
    assert await env.service.list_categories() == [env.category]
    assert await env.service.list_buildings() == [env.building]
    env.residences.list_by_user.return_value = [env.residence]

    assert await env.service.list_residences(env.client) == [env.residence]
    env.residences.list_by_user.assert_awaited_once_with(env.client.id)


async def _question(env: SimpleNamespace, **overrides):
    params = {
        "description": "Как передать показания?",
        "photo_ids": [],
    }
    params.update(overrides)
    return await env.service.create_question(env.client, **params)


async def test_create_question_happy_path(env: SimpleNamespace) -> None:
    photo = MagicMock()
    photo.id = 1
    photo.ticket_id = None
    photo.message_id = None
    env.file_service.get_unattached.return_value = [photo]
    order: list[str] = []
    env.db.commit.side_effect = lambda: order.append("commit")
    env.notifications.send_status_card.side_effect = lambda ticket: order.append("card")

    ticket = await _question(env, photo_ids=[1])

    assert ticket is env.ticket
    env.file_service.get_unattached.assert_awaited_once_with([1])
    env.tickets.create.assert_awaited_once_with(
        type=TicketType.QUESTION,
        status=TicketStatus.NEW,
        client_id=env.client.id,
        description="Как передать показания?",
        category_id=None,
        building_id=None,
        apartment=None,
        contact_phone=env.client.phone,
        preferred_time=None,
    )
    assert env.ticket.client is env.client
    assert env.ticket.category is None
    assert env.ticket.building is None
    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        None,
        TicketStatus.NEW,
        changed_by_id=env.client.id,
    )
    assert photo.ticket_id == env.ticket.id
    assert env.client.active_ticket_id == env.ticket.id
    assert order == ["commit", "card"]
    env.notifications.send_status_card.assert_awaited_once_with(env.ticket)
    env.notify.assert_called_once_with(env.ticket.id)
    env.run_bg.assert_called_once_with(
        env.notify.return_value, name=f"notify-staff-{env.ticket.id}"
    )
    env.categories.get_by_id.assert_not_awaited()
    env.buildings.get_by_id.assert_not_awaited()


async def test_create_question_without_phone_stores_none(env: SimpleNamespace) -> None:
    env.client.phone = None

    await _question(env)

    assert env.tickets.create.await_args.kwargs["contact_phone"] is None


async def test_question_blank_description_rejected_writes_nothing(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await _question(env, description="   ")

    assert exc.value.status_code == 400
    _assert_no_writes(env)


async def test_question_too_long_description_rejected_writes_nothing(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await _question(env, description="a" * (DESCRIPTION_LIMIT + 1))

    assert exc.value.status_code == 400
    _assert_no_writes(env)


async def test_question_unknown_photo_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.file_service.get_unattached.side_effect = AppException("Фото не найдено", status_code=400)

    with pytest.raises(AppException) as exc:
        await _question(env, photo_ids=[999])

    assert exc.value.status_code == 400
    env.file_service.get_unattached.assert_awaited_once_with([999])
    _assert_no_writes(env)


async def test_question_duplicate_photos_rejected_writes_nothing(env: SimpleNamespace) -> None:
    env.file_service.get_unattached.side_effect = AppException("Фото повторяются", status_code=400)

    with pytest.raises(AppException) as exc:
        await _question(env, photo_ids=[5, 5])

    assert exc.value.status_code == 400
    env.file_service.get_unattached.assert_awaited_once_with([5, 5])
    _assert_no_writes(env)


def _ticket(ticket_id: int, client_id: int, status: TicketStatus) -> MagicMock:
    ticket = MagicMock()
    ticket.id = ticket_id
    ticket.client_id = client_id
    ticket.status = status
    return ticket


async def test_set_active_ticket_own_open(env: SimpleNamespace) -> None:
    ticket = _ticket(1042, env.client.id, TicketStatus.IN_PROGRESS)
    env.tickets.get_by_id = AsyncMock(return_value=ticket)

    result = await env.service.set_active_ticket(env.client, 1042)

    assert result is ticket
    assert env.client.active_ticket_id == 1042
    env.db.commit.assert_awaited_once()


async def test_set_active_ticket_foreign_rejected(env: SimpleNamespace) -> None:
    ticket = _ticket(1042, env.client.id + 1, TicketStatus.NEW)
    env.tickets.get_by_id = AsyncMock(return_value=ticket)

    with pytest.raises(NotFoundException):
        await env.service.set_active_ticket(env.client, 1042)

    env.db.commit.assert_not_awaited()


async def test_set_active_ticket_missing_rejected(env: SimpleNamespace) -> None:
    env.tickets.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await env.service.set_active_ticket(env.client, 1042)

    env.db.commit.assert_not_awaited()


async def test_set_active_ticket_closed_rejected(env: SimpleNamespace) -> None:
    ticket = _ticket(1042, env.client.id, TicketStatus.CLOSED)
    env.tickets.get_by_id = AsyncMock(return_value=ticket)

    with pytest.raises(ConflictException) as exc:
        await env.service.set_active_ticket(env.client, 1042)

    assert exc.value.status_code == 409
    assert str(ticket.id) in exc.value.message
    env.db.commit.assert_not_awaited()


async def test_list_open_tickets_delegates_with_open_statuses(env: SimpleNamespace) -> None:
    ticket = _ticket(1042, env.client.id, TicketStatus.WAITING_CLIENT)
    env.tickets.list_by_client = AsyncMock(return_value=[ticket])

    result = await env.service.list_open_tickets(env.client)

    assert result == [ticket]
    env.tickets.list_by_client.assert_awaited_once_with(
        env.client.id, statuses=ticket_rules.OPEN_STATUSES
    )


async def test_list_tickets_returns_open_then_closed(env: SimpleNamespace) -> None:
    open_ticket = _ticket(1042, env.client.id, TicketStatus.IN_PROGRESS)
    closed_ticket = _ticket(1030, env.client.id, TicketStatus.CLOSED)
    env.tickets.list_by_client = AsyncMock(side_effect=[[open_ticket], [closed_ticket]])

    result = await env.service.list_tickets(env.client)

    assert result == [open_ticket, closed_ticket]
    first, second = env.tickets.list_by_client.await_args_list
    assert first.args == (env.client.id,)
    assert first.kwargs == {
        "statuses": ticket_rules.OPEN_STATUSES,
        "limit": MY_TICKETS_LIMIT,
    }
    assert second.args == (env.client.id,)
    assert second.kwargs == {
        "statuses": MY_TICKETS_CLOSED_STATUSES,
        "limit": MY_TICKETS_LIMIT - 1,
    }


async def test_list_tickets_reduces_closed_limit_by_open_count(env: SimpleNamespace) -> None:
    open_tickets = [_ticket(1000 + index, env.client.id, TicketStatus.NEW) for index in range(4)]
    env.tickets.list_by_client = AsyncMock(side_effect=[open_tickets, []])

    await env.service.list_tickets(env.client)

    assert env.tickets.list_by_client.await_args_list[1].kwargs["limit"] == MY_TICKETS_LIMIT - 4


async def test_list_tickets_skips_closed_when_open_fills_limit(env: SimpleNamespace) -> None:
    open_tickets = [
        _ticket(1000 + index, env.client.id, TicketStatus.NEW) for index in range(MY_TICKETS_LIMIT)
    ]
    env.tickets.list_by_client = AsyncMock(return_value=open_tickets)

    result = await env.service.list_tickets(env.client)

    assert result == open_tickets
    env.tickets.list_by_client.assert_awaited_once_with(
        env.client.id, statuses=ticket_rules.OPEN_STATUSES, limit=MY_TICKETS_LIMIT
    )


async def test_get_ticket_returns_own(env: SimpleNamespace) -> None:
    ticket = _ticket(1042, env.client.id, TicketStatus.IN_PROGRESS)
    env.tickets.get_by_id = AsyncMock(return_value=ticket)

    assert await env.service.get_ticket(env.client, 1042) is ticket


async def test_get_ticket_of_another_client_rejected(env: SimpleNamespace) -> None:
    ticket = _ticket(1042, env.client.id + 1, TicketStatus.NEW)
    env.tickets.get_by_id = AsyncMock(return_value=ticket)

    with pytest.raises(NotFoundException):
        await env.service.get_ticket(env.client, 1042)


async def test_get_ticket_missing_rejected(env: SimpleNamespace) -> None:
    env.tickets.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(NotFoundException):
        await env.service.get_ticket(env.client, 1042)


async def test_get_ticket_returns_own_closed(env: SimpleNamespace) -> None:
    ticket = _ticket(1042, env.client.id, TicketStatus.CLOSED)
    env.tickets.get_by_id = AsyncMock(return_value=ticket)

    assert await env.service.get_ticket(env.client, 1042) is ticket
