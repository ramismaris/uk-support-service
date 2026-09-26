from src.core.constants import TicketType
from src.core.texts import (
    DESCRIPTION_MAX_LENGTH,
    client_message_staff_text,
    staff_message_client_text,
)


def test_staff_message_client_text_request() -> None:
    text = staff_message_client_text(
        ticket_id=1042,
        ticket_type=TicketType.REQUEST,
        text="Мастер придёт завтра в 10:00.",
    )

    assert text == "💬 Заявка №1042\n\nМастер придёт завтра в 10:00."


def test_staff_message_client_text_question() -> None:
    text = staff_message_client_text(
        ticket_id=1047,
        ticket_type=TicketType.QUESTION,
        text="Уточните, пожалуйста, номер подъезда.",
    )

    assert text == "💬 Вопрос №1047\n\nУточните, пожалуйста, номер подъезда."


def test_staff_message_client_text_without_text_is_header_only() -> None:
    text = staff_message_client_text(
        ticket_id=1042,
        ticket_type=TicketType.REQUEST,
        text=None,
    )

    assert text == "💬 Заявка №1042"


def test_client_message_staff_text_request_with_photos() -> None:
    text = client_message_staff_text(
        ticket_id=1042,
        ticket_type=TicketType.REQUEST,
        client_first_name="Мария",
        client_last_name="Иванова",
        text="Течёт кран на кухне.",
        photos_count=2,
    )

    assert text == ("💬 Заявка №1042 · Мария Иванова\n📎 Фото: 2\n\nТечёт кран на кухне.")


def test_client_message_staff_text_question_without_last_name() -> None:
    text = client_message_staff_text(
        ticket_id=1047,
        ticket_type=TicketType.QUESTION,
        client_first_name="Мария",
        client_last_name=None,
        text="Когда отключат воду?",
        photos_count=0,
    )

    assert text == "💬 Вопрос №1047 · Мария\n\nКогда отключат воду?"
    assert "📎" not in text


def test_client_message_staff_text_without_photos_omits_photo_line() -> None:
    text = client_message_staff_text(
        ticket_id=1042,
        ticket_type=TicketType.REQUEST,
        client_first_name="Мария",
        client_last_name="Иванова",
        text="Спасибо!",
        photos_count=0,
    )

    assert text == "💬 Заявка №1042 · Мария Иванова\n\nСпасибо!"


def test_client_message_staff_text_without_text_has_no_blank_line() -> None:
    text = client_message_staff_text(
        ticket_id=1042,
        ticket_type=TicketType.REQUEST,
        client_first_name="Мария",
        client_last_name="Иванова",
        text=None,
        photos_count=1,
    )

    assert text == "💬 Заявка №1042 · Мария Иванова\n📎 Фото: 1"
    assert not text.endswith("\n")


def test_client_message_staff_text_cuts_long_text() -> None:
    text = client_message_staff_text(
        ticket_id=1042,
        ticket_type=TicketType.REQUEST,
        client_first_name="Мария",
        client_last_name="Иванова",
        text="а" * (DESCRIPTION_MAX_LENGTH + 100),
        photos_count=0,
    )

    assert text.endswith("а" * DESCRIPTION_MAX_LENGTH + "…")
    assert "а" * (DESCRIPTION_MAX_LENGTH + 1) not in text
