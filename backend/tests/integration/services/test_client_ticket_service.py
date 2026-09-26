from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TicketStatus, TicketType
from src.repositories.building_repository import BuildingRepository
from src.repositories.category_repository import CategoryRepository
from src.repositories.file_repository import FileRepository
from src.repositories.status_change_repository import StatusChangeRepository
from src.repositories.user_repository import UserRepository
from src.services.client_ticket_service import ClientTicketService


async def test_create_request_end_to_end(db: AsyncSession) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000003, first_name="Мария", phone="+7 (900) 000-00-03")
    building = await BuildingRepository(db).create("ул. Ленина, 12")
    category = await CategoryRepository(db).create("Сантехника", 1)
    photo = await FileRepository(db).create(storage_key="files/a.webp", mime="image/webp", size=10)
    await db.commit()

    messenger = AsyncMock()
    messenger.send_message.return_value = "mid-42"
    service = ClientTicketService(db, messenger, MagicMock())

    with (
        patch("src.services.client_ticket_service.run_in_background") as run_bg,
        patch(
            "src.services.client_ticket_service.notify_staff_about_new_ticket",
            new=MagicMock(return_value="notify-coroutine"),
        ) as notify,
    ):
        ticket = await service.create_request(
            client,
            category_id=category.id,
            building_id=building.id,
            apartment="45",
            description="Течёт кран",
            preferred_time=None,
            photo_ids=[photo.id],
        )

    assert ticket.type == TicketType.REQUEST
    assert ticket.status == TicketStatus.NEW
    assert ticket.apartment == "45"
    assert ticket.contact_phone == "+7 (900) 000-00-03"
    assert ticket.status_message_max_id == "mid-42"

    history = await StatusChangeRepository(db).list_by_ticket(ticket.id)
    assert len(history) == 1
    assert history[0].from_status is None
    assert history[0].to_status == TicketStatus.NEW
    assert history[0].changed_by_id == client.id

    files = await FileRepository(db).list_by_ticket(ticket.id)
    assert [file.id for file in files] == [photo.id]

    user = await users.get_by_id(client.id)
    assert user is not None
    assert user.active_ticket_id == ticket.id

    messenger.send_message.assert_awaited_once()
    assert messenger.send_message.await_args.kwargs["markdown"] is True
    run_bg.assert_called_once_with(notify.return_value, name=f"notify-staff-{ticket.id}")


async def test_create_question_end_to_end(db: AsyncSession) -> None:
    users = UserRepository(db)
    client = await users.create(max_user_id=1000004, first_name="Пётр")
    photo = await FileRepository(db).create(storage_key="files/q.webp", mime="image/webp", size=10)
    await db.commit()

    messenger = AsyncMock()
    messenger.send_message.return_value = "mid-77"
    service = ClientTicketService(db, messenger, MagicMock())

    with (
        patch("src.services.client_ticket_service.run_in_background") as run_bg,
        patch(
            "src.services.client_ticket_service.notify_staff_about_new_ticket",
            new=MagicMock(return_value="notify-coroutine"),
        ) as notify,
    ):
        ticket = await service.create_question(
            client,
            description="Как передать показания?",
            photo_ids=[photo.id],
        )

    assert ticket.type == TicketType.QUESTION
    assert ticket.status == TicketStatus.NEW
    assert ticket.category_id is None
    assert ticket.building_id is None
    assert ticket.apartment is None
    assert ticket.contact_phone is None
    assert ticket.status_message_max_id == "mid-77"

    history = await StatusChangeRepository(db).list_by_ticket(ticket.id)
    assert len(history) == 1
    assert history[0].from_status is None
    assert history[0].to_status == TicketStatus.NEW
    assert history[0].changed_by_id == client.id

    files = await FileRepository(db).list_by_ticket(ticket.id)
    assert [file.id for file in files] == [photo.id]

    user = await users.get_by_id(client.id)
    assert user is not None
    assert user.active_ticket_id == ticket.id

    messenger.send_message.assert_awaited_once()
    run_bg.assert_called_once_with(notify.return_value, name=f"notify-staff-{ticket.id}")
