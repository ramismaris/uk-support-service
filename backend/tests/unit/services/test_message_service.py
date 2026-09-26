from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.core.constants import ButtonType, SenderType, TicketStatus, TicketType
from src.core.exceptions import (
    AppException,
    ConflictException,
    MessengerException,
    NotFoundException,
)
from src.core.texts import (
    MESSAGE_FILES_MAX,
    MESSAGE_FILES_MIXED,
    MESSAGE_LIMIT,
    TICKET_CLOSED_FOR_CLIENT,
)
from src.providers.messenger_provider import Button, OutgoingFile
from src.services.message_service import MessageService, UploadedFile
from src.services.ticket_rules import OPEN_STATUSES, ToTicket

REPLY_BUTTON = Button("Ответить", ButtonType.CALLBACK, "chat:ticket:1042")


def _upload(data: bytes = b"data", mime: str = "image/webp", filename: str | None = "a.webp"):
    return UploadedFile(data=data, mime=mime, filename=filename)


@pytest.fixture
def env() -> SimpleNamespace:
    db = AsyncMock()
    db.add = MagicMock()
    messenger = AsyncMock()
    storage = MagicMock()
    storage.save = AsyncMock()
    storage.delete = AsyncMock()

    client = MagicMock()
    client.id = 1
    client.max_user_id = 555
    client.active_ticket_id = None
    client.first_name = "Мария"
    client.last_name = "Иванова"

    author = MagicMock()
    author.id = 9
    author.max_user_id = 999

    ticket = MagicMock()
    ticket.id = 1042
    ticket.status = TicketStatus.NEW
    ticket.type = TicketType.REQUEST
    ticket.client = client
    ticket.client_id = client.id
    ticket.status_message_max_id = "card-1"

    tickets = MagicMock()
    tickets.get_by_id = AsyncMock(return_value=ticket)
    tickets.get_by_id_for_update = AsyncMock(return_value=ticket)
    tickets.get_by_status_message_max_id = AsyncMock(return_value=None)
    tickets.list_by_client = AsyncMock(return_value=[])

    saved = MagicMock()
    saved.id = 77
    message = MagicMock()
    message.id = 77
    messages = MagicMock()
    messages.create = AsyncMock(return_value=message)
    messages.get_by_id = AsyncMock(return_value=saved)
    messages.get_by_max_message_id = AsyncMock(return_value=None)

    changes = MagicMock()
    changes.create = AsyncMock()

    file_service = MagicMock()
    file_service.check_data = MagicMock()
    file_service.get_unattached = AsyncMock(return_value=[])
    file_service.add = AsyncMock()

    notifications = MagicMock()
    notifications.update_status_card = AsyncMock()

    with ExitStack() as stack:
        stack.enter_context(
            patch("src.services.message_service.MessageRepository", return_value=messages)
        )
        stack.enter_context(
            patch("src.services.message_service.TicketRepository", return_value=tickets)
        )
        stack.enter_context(
            patch(
                "src.services.message_service.StatusChangeRepository",
                return_value=changes,
            )
        )
        stack.enter_context(
            patch("src.services.message_service.FileService", return_value=file_service)
        )
        stack.enter_context(
            patch(
                "src.services.message_service.NotificationService",
                return_value=notifications,
            )
        )
        run_bg = stack.enter_context(patch("src.services.message_service.run_in_background"))
        publish_message_created = stack.enter_context(
            patch(
                "src.services.message_service.publish_message_created",
                new_callable=AsyncMock,
            )
        )
        publish_ticket_updated = stack.enter_context(
            patch(
                "src.services.message_service.publish_ticket_updated",
                new_callable=AsyncMock,
            )
        )
        notify = MagicMock(return_value="notify-coroutine")
        stack.enter_context(
            patch(
                "src.services.message_service.notify_staff_about_client_message",
                new=notify,
            )
        )
        service = MessageService(db, messenger, storage)

        yield SimpleNamespace(
            db=db,
            messenger=messenger,
            storage=storage,
            client=client,
            author=author,
            ticket=ticket,
            tickets=tickets,
            message=message,
            saved=saved,
            messages=messages,
            changes=changes,
            file_service=file_service,
            notifications=notifications,
            run_bg=run_bg,
            publish_message_created=publish_message_created,
            publish_ticket_updated=publish_ticket_updated,
            notify=notify,
            service=service,
        )


def _assert_staff_nothing_sent_written(env: SimpleNamespace) -> None:
    env.messenger.upload_file.assert_not_awaited()
    env.messenger.send_message.assert_not_awaited()
    env.messages.create.assert_not_awaited()
    env.messages.get_by_id.assert_not_awaited()
    env.tickets.get_by_id_for_update.assert_not_awaited()
    env.changes.create.assert_not_awaited()
    env.file_service.add.assert_not_awaited()
    env.storage.save.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.publish_message_created.assert_not_awaited()
    env.publish_ticket_updated.assert_not_awaited()


def _assert_client_nothing_sent_written(env: SimpleNamespace) -> None:
    env.messages.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.run_bg.assert_not_called()
    env.notifications.update_status_card.assert_not_awaited()
    env.publish_message_created.assert_not_awaited()
    env.publish_ticket_updated.assert_not_awaited()


async def test_send_staff_message_text_only(env: SimpleNamespace) -> None:
    env.messenger.send_message.return_value = "mid-99"
    order: list[str] = []
    env.db.commit.side_effect = lambda: order.append("commit")
    env.publish_message_created.side_effect = lambda db, message_id: order.append("message")
    env.publish_ticket_updated.side_effect = lambda db, ticket_id: order.append("ticket")

    message = await env.service.send_staff_message(
        env.ticket.id, env.author, "  Мастер придёт завтра  ", []
    )

    assert message is env.saved
    env.messenger.upload_file.assert_not_awaited()
    env.messenger.send_message.assert_awaited_once_with(
        env.client.max_user_id,
        "💬 Заявка №1042\n\nМастер придёт завтра",
        buttons=[[REPLY_BUTTON]],
        files=[],
        markdown=False,
    )
    env.messages.create.assert_awaited_once_with(
        env.ticket.id,
        SenderType.STAFF,
        author_id=env.author.id,
        text="Мастер придёт завтра",
        max_message_id="mid-99",
    )
    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        TicketStatus.NEW,
        TicketStatus.IN_PROGRESS,
        changed_by_id=None,
    )
    assert env.ticket.status == TicketStatus.IN_PROGRESS
    assert env.ticket.assignee_id == env.author.id
    assert env.ticket.staff_seen_at is not None
    assert order == ["commit", "message", "ticket"]
    env.db.commit.assert_awaited_once()
    env.publish_message_created.assert_awaited_once_with(env.db, env.message.id)
    env.publish_ticket_updated.assert_awaited_once_with(env.db, env.ticket.id)
    env.notifications.update_status_card.assert_awaited_once_with(env.ticket)
    env.messages.get_by_id.assert_awaited_once_with(env.message.id)
    env.tickets.get_by_id_for_update.assert_awaited_once_with(env.ticket.id)


async def test_send_staff_message_with_files_uploads_and_links(env: SimpleNamespace) -> None:
    first = _upload(b"first", "image/webp", "one.webp")
    second = _upload(b"second", "image/png", None)
    file_one = MagicMock()
    file_two = MagicMock()
    env.file_service.add.side_effect = [file_one, file_two]
    env.messenger.upload_file.side_effect = ["tok-1", "tok-2"]
    env.messenger.send_message.return_value = "mid-100"

    await env.service.send_staff_message(env.ticket.id, env.author, "Фото", [first, second])

    assert env.messenger.upload_file.await_args_list == [
        call(b"first", "image/webp", "one.webp"),
        call(b"second", "image/png", None),
    ]
    assert env.messenger.send_message.await_args.kwargs["files"] == [
        OutgoingFile("tok-1", "image/webp"),
        OutgoingFile("tok-2", "image/png"),
    ]
    assert env.file_service.add.await_args_list == [
        call(b"first", "image/webp", "one.webp", ticket_id=env.ticket.id, message_id=77),
        call(b"second", "image/png", None, ticket_id=env.ticket.id, message_id=77),
    ]
    assert file_one.max_token == "tok-1"
    assert file_two.max_token == "tok-2"


async def test_send_staff_message_deletes_blobs_when_commit_fails(env: SimpleNamespace) -> None:
    first = _upload(b"first", "image/webp", "one.webp")
    second = _upload(b"second", "image/png", "two.png")
    file_one = MagicMock()
    file_one.storage_key = "files/one.webp"
    file_two = MagicMock()
    file_two.storage_key = "files/two.png"
    env.file_service.add.side_effect = [file_one, file_two]
    env.messenger.upload_file.side_effect = ["tok-1", "tok-2"]
    env.messenger.send_message.return_value = "mid-100"
    env.db.commit.side_effect = RuntimeError("commit down")

    with pytest.raises(RuntimeError):
        await env.service.send_staff_message(env.ticket.id, env.author, "Фото", [first, second])

    assert env.storage.delete.await_args_list == [
        call("files/one.webp"),
        call("files/two.png"),
    ]
    env.publish_message_created.assert_not_awaited()
    env.publish_ticket_updated.assert_not_awaited()


async def test_send_staff_message_normalizes_mime_and_filename(env: SimpleNamespace) -> None:
    upload = UploadedFile(data=b"x", mime="  IMAGE/PNG  ", filename="  ")
    env.messenger.upload_file.return_value = "tok"

    await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [upload])

    env.messenger.upload_file.assert_awaited_once_with(b"x", "image/png", None)


async def test_send_staff_message_with_noop_messenger(env: SimpleNamespace) -> None:
    env.messenger.upload_file.return_value = None
    env.messenger.send_message.return_value = None

    await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [_upload()])

    assert env.messenger.send_message.await_args.kwargs["files"] == []
    assert env.messages.create.await_args.kwargs["max_message_id"] is None
    env.file_service.add.assert_awaited_once()
    assert env.file_service.add.await_args.kwargs["message_id"] == 77
    assert env.file_service.add.return_value.max_token is None


async def test_send_staff_message_blank_without_files_rejected(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await env.service.send_staff_message(env.ticket.id, env.author, "   ", [])

    assert exc.value.status_code == 400
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_accepts_limit_length(env: SimpleNamespace) -> None:
    text = "а" * MESSAGE_LIMIT

    await env.service.send_staff_message(env.ticket.id, env.author, text, [])

    assert env.messages.create.await_args.kwargs["text"] == text


async def test_send_staff_message_rejects_over_limit(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await env.service.send_staff_message(
            env.ticket.id, env.author, "а" * (MESSAGE_LIMIT + 1), []
        )

    assert exc.value.status_code == 400
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_accepts_max_files(env: SimpleNamespace) -> None:
    uploads = [_upload() for _ in range(MESSAGE_FILES_MAX)]

    await env.service.send_staff_message(env.ticket.id, env.author, None, uploads)

    assert all(upload.mime == "image/webp" for upload in uploads)
    assert len(env.file_service.add.await_args_list) == MESSAGE_FILES_MAX


async def test_send_staff_message_accepts_single_document(env: SimpleNamespace) -> None:
    upload = _upload(b"%PDF-1.7", "application/pdf", "act.pdf")
    env.messenger.upload_file.return_value = "tok-pdf"

    await env.service.send_staff_message(env.ticket.id, env.author, "Документ", [upload])

    env.messenger.upload_file.assert_awaited_once_with(b"%PDF-1.7", "application/pdf", "act.pdf")
    env.file_service.add.assert_awaited_once()


async def test_send_staff_message_rejects_too_many_files(env: SimpleNamespace) -> None:
    uploads = [_upload() for _ in range(MESSAGE_FILES_MAX + 1)]

    with pytest.raises(AppException) as exc:
        await env.service.send_staff_message(env.ticket.id, env.author, None, uploads)

    assert exc.value.status_code == 400
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_rejects_document_with_photo(env: SimpleNamespace) -> None:
    uploads = [_upload(), _upload(b"%PDF", "application/pdf", "act.pdf")]

    with pytest.raises(AppException) as exc:
        await env.service.send_staff_message(env.ticket.id, env.author, "Микс", uploads)

    assert exc.value.status_code == 400
    assert exc.value.message == MESSAGE_FILES_MIXED
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_rejects_two_documents(env: SimpleNamespace) -> None:
    uploads = [
        _upload(b"%PDF", "application/pdf", "one.pdf"),
        _upload(b"%PDF", "application/pdf", "two.pdf"),
    ]

    with pytest.raises(AppException) as exc:
        await env.service.send_staff_message(env.ticket.id, env.author, "Два файла", uploads)

    assert exc.value.status_code == 400
    assert exc.value.message == MESSAGE_FILES_MIXED
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_rejects_empty_file(env: SimpleNamespace) -> None:
    env.file_service.check_data.side_effect = AppException("Файл пуст", status_code=400)

    with pytest.raises(AppException) as exc:
        await env.service.send_staff_message(env.ticket.id, env.author, None, [_upload(b"")])

    assert exc.value.status_code == 400
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_rejects_too_large_file(env: SimpleNamespace) -> None:
    env.file_service.check_data.side_effect = AppException("Файл слишком большой", status_code=413)

    with pytest.raises(AppException) as exc:
        await env.service.send_staff_message(env.ticket.id, env.author, None, [_upload(b"x")])

    assert exc.value.status_code == 413
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_missing_ticket_rejected(env: SimpleNamespace) -> None:
    env.tickets.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [])

    _assert_staff_nothing_sent_written(env)


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.CLOSED, id="closed"),
        pytest.param(TicketStatus.REJECTED, id="rejected"),
    ],
)
async def test_send_staff_message_closed_ticket_rejected(
    env: SimpleNamespace, status: TicketStatus
) -> None:
    env.ticket.status = status

    with pytest.raises(ConflictException) as exc:
        await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [])

    assert exc.value.status_code == 409
    _assert_staff_nothing_sent_written(env)


async def test_send_staff_message_upload_failure_propagates(env: SimpleNamespace) -> None:
    env.messenger.upload_file.side_effect = MessengerException()

    with pytest.raises(MessengerException):
        await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [_upload()])

    env.messenger.send_message.assert_not_awaited()
    env.messages.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.publish_message_created.assert_not_awaited()
    env.publish_ticket_updated.assert_not_awaited()


async def test_send_staff_message_send_failure_propagates(env: SimpleNamespace) -> None:
    env.messenger.send_message.side_effect = MessengerException()

    with pytest.raises(MessengerException):
        await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [])

    env.messages.create.assert_not_awaited()
    env.changes.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.publish_message_created.assert_not_awaited()
    env.publish_ticket_updated.assert_not_awaited()
    env.notifications.update_status_card.assert_not_awaited()


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.IN_PROGRESS, id="in-progress"),
        pytest.param(TicketStatus.WAITING_CLIENT, id="waiting-client"),
    ],
)
async def test_send_staff_message_keeps_status_without_transition(
    env: SimpleNamespace, status: TicketStatus
) -> None:
    env.ticket.status = status
    env.messenger.send_message.return_value = "mid-101"

    await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [])

    env.changes.create.assert_not_awaited()
    assert env.ticket.status == status
    assert env.ticket.staff_seen_at is not None
    env.notifications.update_status_card.assert_not_awaited()


async def test_send_staff_message_failed_card_still_returns(env: SimpleNamespace) -> None:
    env.notifications.update_status_card.side_effect = MessengerException()

    message = await env.service.send_staff_message(env.ticket.id, env.author, "Текст", [])

    assert message is env.saved
    env.db.commit.assert_awaited_once()


async def test_resolve_client_route_reply_to_staff_message(env: SimpleNamespace) -> None:
    message = MagicMock()
    message.ticket_id = 20
    env.messages.get_by_max_message_id.return_value = message
    env.tickets.list_by_client.return_value = [MagicMock(id=10), MagicMock(id=20)]
    env.client.active_ticket_id = 20

    with patch(
        "src.services.message_service.ticket_rules.route_client_message",
        return_value="route",
    ) as rule:
        result = await env.service.resolve_client_route(env.client, "mid-staff")

    assert result == "route"
    env.messages.get_by_max_message_id.assert_awaited_once_with("mid-staff")
    env.tickets.get_by_status_message_max_id.assert_not_awaited()
    env.tickets.list_by_client.assert_awaited_once_with(env.client.id, statuses=OPEN_STATUSES)
    rule.assert_called_once_with(20, 20, [10, 20])


async def test_resolve_client_route_returns_rule_result(env: SimpleNamespace) -> None:
    message = MagicMock()
    message.ticket_id = 20
    env.messages.get_by_max_message_id.return_value = message
    env.tickets.list_by_client.return_value = [MagicMock(id=10), MagicMock(id=20)]
    env.client.active_ticket_id = None

    result = await env.service.resolve_client_route(env.client, "mid-staff")

    assert result == ToTicket(ticket_id=20)


async def test_resolve_client_route_reply_to_status_card(env: SimpleNamespace) -> None:
    card_ticket = MagicMock()
    card_ticket.id = 30
    env.messages.get_by_max_message_id.return_value = None
    env.tickets.get_by_status_message_max_id.return_value = card_ticket

    with patch(
        "src.services.message_service.ticket_rules.route_client_message",
        return_value="route",
    ) as rule:
        result = await env.service.resolve_client_route(env.client, "mid-card")

    assert result == "route"
    env.tickets.get_by_status_message_max_id.assert_awaited_once_with("mid-card")
    assert rule.call_args.args[0] == 30


async def test_resolve_client_route_unknown_reply(env: SimpleNamespace) -> None:
    env.messages.get_by_max_message_id.return_value = None
    env.tickets.get_by_status_message_max_id.return_value = None

    with patch(
        "src.services.message_service.ticket_rules.route_client_message",
        return_value="route",
    ) as rule:
        await env.service.resolve_client_route(env.client, "mid-unknown")

    assert rule.call_args.args[0] is None


async def test_resolve_client_route_without_reply_skips_lookup(env: SimpleNamespace) -> None:
    with patch(
        "src.services.message_service.ticket_rules.route_client_message",
        return_value="route",
    ) as rule:
        await env.service.resolve_client_route(env.client, None)

    env.messages.get_by_max_message_id.assert_not_awaited()
    env.tickets.get_by_status_message_max_id.assert_not_awaited()
    assert rule.call_args.args[0] is None


async def test_add_client_message_text_and_photos(env: SimpleNamespace) -> None:
    first = MagicMock()
    second = MagicMock()
    env.file_service.get_unattached.return_value = [first, second]
    env.ticket.status = TicketStatus.IN_PROGRESS
    order: list[str] = []
    env.db.commit.side_effect = lambda: order.append("commit")
    env.publish_message_created.side_effect = lambda db, message_id: order.append("message")
    env.publish_ticket_updated.side_effect = lambda db, ticket_id: order.append("ticket")

    message = await env.service.add_client_message(
        env.client,
        env.ticket.id,
        text="  Вот фото  ",
        file_ids=[1, 2],
        max_message_id="mid-in",
    )

    assert message is env.message
    env.file_service.get_unattached.assert_awaited_once_with([1, 2])
    env.messages.create.assert_awaited_once_with(
        env.ticket.id,
        SenderType.CLIENT,
        author_id=env.client.id,
        text="Вот фото",
        max_message_id="mid-in",
    )
    assert first.ticket_id == env.ticket.id
    assert first.message_id == env.message.id
    assert second.ticket_id == env.ticket.id
    assert second.message_id == env.message.id
    assert env.ticket.last_client_message_at is not None
    assert env.client.active_ticket_id == env.ticket.id
    assert order == ["commit", "message", "ticket"]
    env.db.commit.assert_awaited_once()
    env.publish_message_created.assert_awaited_once_with(env.db, env.message.id)
    env.publish_ticket_updated.assert_awaited_once_with(env.db, env.ticket.id)
    env.run_bg.assert_called_once_with(
        env.notify.return_value, name=f"notify-client-message-{env.message.id}"
    )
    env.notify.assert_called_once_with(env.message.id)


async def test_add_client_message_duplicate_returns_existing(env: SimpleNamespace) -> None:
    existing = MagicMock()
    env.messages.get_by_max_message_id.return_value = existing

    message = await env.service.add_client_message(
        env.client,
        env.ticket.id,
        text="Привет",
        file_ids=[],
        max_message_id="mid-in",
    )

    assert message is existing
    env.messages.get_by_max_message_id.assert_awaited_once_with("mid-in")
    env.tickets.get_by_id_for_update.assert_not_awaited()
    env.messages.create.assert_not_awaited()
    env.db.commit.assert_not_awaited()
    env.publish_message_created.assert_not_awaited()
    env.publish_ticket_updated.assert_not_awaited()
    env.run_bg.assert_not_called()


async def test_add_client_message_foreign_ticket_rejected(env: SimpleNamespace) -> None:
    env.ticket.client_id = env.client.id + 1

    with pytest.raises(NotFoundException):
        await env.service.add_client_message(
            env.client, env.ticket.id, text="Привет", file_ids=[], max_message_id=None
        )

    env.file_service.get_unattached.assert_not_awaited()
    _assert_client_nothing_sent_written(env)


async def test_add_client_message_missing_ticket_rejected(env: SimpleNamespace) -> None:
    env.tickets.get_by_id_for_update.return_value = None

    with pytest.raises(NotFoundException):
        await env.service.add_client_message(
            env.client, 999, text="Привет", file_ids=[], max_message_id=None
        )

    _assert_client_nothing_sent_written(env)


async def test_add_client_message_closed_ticket_rejected(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.CLOSED

    with pytest.raises(ConflictException) as exc:
        await env.service.add_client_message(
            env.client, env.ticket.id, text="Привет", file_ids=[], max_message_id=None
        )

    assert exc.value.status_code == 409
    assert exc.value.message == TICKET_CLOSED_FOR_CLIENT.format(ticket_id=env.ticket.id)
    _assert_client_nothing_sent_written(env)


async def test_add_client_message_photo_error_rejected(env: SimpleNamespace) -> None:
    env.file_service.get_unattached.side_effect = AppException("Фото не найдено", status_code=400)

    with pytest.raises(AppException) as exc:
        await env.service.add_client_message(
            env.client, env.ticket.id, text="Привет", file_ids=[999], max_message_id=None
        )

    assert exc.value.status_code == 400
    _assert_client_nothing_sent_written(env)


async def test_add_client_message_blank_without_photos_rejected(env: SimpleNamespace) -> None:
    with pytest.raises(AppException) as exc:
        await env.service.add_client_message(
            env.client, env.ticket.id, text="   ", file_ids=[], max_message_id=None
        )

    assert exc.value.status_code == 400
    env.tickets.get_by_id_for_update.assert_not_awaited()
    _assert_client_nothing_sent_written(env)


async def test_add_client_message_waiting_client_transitions(env: SimpleNamespace) -> None:
    env.ticket.status = TicketStatus.WAITING_CLIENT

    await env.service.add_client_message(
        env.client, env.ticket.id, text="Уже сделали?", file_ids=[], max_message_id=None
    )

    env.changes.create.assert_awaited_once_with(
        env.ticket.id,
        TicketStatus.WAITING_CLIENT,
        TicketStatus.IN_PROGRESS,
        changed_by_id=None,
    )
    assert env.ticket.status == TicketStatus.IN_PROGRESS
    env.notifications.update_status_card.assert_awaited_once_with(env.ticket)


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(TicketStatus.NEW, id="new"),
        pytest.param(TicketStatus.IN_PROGRESS, id="in-progress"),
    ],
)
async def test_add_client_message_keeps_status(env: SimpleNamespace, status: TicketStatus) -> None:
    env.ticket.status = status

    await env.service.add_client_message(
        env.client, env.ticket.id, text="Ещё вопрос", file_ids=[], max_message_id=None
    )

    env.changes.create.assert_not_awaited()
    assert env.ticket.status == status
    env.notifications.update_status_card.assert_not_awaited()
