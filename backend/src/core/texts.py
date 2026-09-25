from src.core.constants import TicketStatus, TicketType

START_TEXT = "Здравствуйте! Это бот управляющей компании.\nВыберите раздел в меню."

ID_TEXT = "Ваш max_user_id: {user_id}"

SECTION_EMPTY_TEXT = "Раздел пока не заполнен."

USE_MENU_TEXT = "Пожалуйста, воспользуйтесь меню."

OUTDATED_BUTTON_TEXT = "Кнопка устарела. Отправьте /start."

STATUS_LABELS: dict[TicketStatus, str] = {
    TicketStatus.NEW: "Принята",
    TicketStatus.IN_PROGRESS: "В работе",
    TicketStatus.WAITING_CLIENT: "Нужен ваш ответ",
    TicketStatus.CLOSED: "Закрыта",
    TicketStatus.REJECTED: "Отклонена",
}

STAFF_NEW_TICKET_BUTTON = "Открыть"

DESCRIPTION_MAX_LENGTH = 500

DESCRIPTION_REQUIRED = "Опишите проблему"
APARTMENT_INVALID = "Квартира — до 20 символов: буквы, цифры, пробел, «/», «.» и «-»"
CATEGORY_NOT_FOUND = "Категория не найдена"
BUILDING_NOT_FOUND = "Адрес не найден"
PHOTO_NOT_FOUND = "Фото не найдено"
PHOTO_ALREADY_ATTACHED = "Фото уже прикреплено"
PHOTOS_DUPLICATED = "Фото повторяются"
PHOTO_NOT_IMAGE = "Можно прикрепить только фото"


def format_address(building_address: str, apartment: str) -> str:
    return f"{building_address}, кв. {apartment}"


def shorten_description(description: str) -> str:
    if len(description) <= DESCRIPTION_MAX_LENGTH:
        return description
    return description[:DESCRIPTION_MAX_LENGTH] + "…"


def new_ticket_staff_text(
    *,
    ticket_id: int,
    ticket_type: TicketType,
    category_title: str | None,
    building_address: str | None,
    apartment: str | None,
    client_first_name: str,
    client_last_name: str | None,
    client_phone: str | None,
    photos_count: int,
    description: str,
) -> str:
    if ticket_type == TicketType.QUESTION:
        header = f"🆕 Вопрос №{ticket_id}"
    else:
        header = f"🆕 Заявка №{ticket_id}"
        if category_title:
            header += f" · {category_title}"

    lines = [header]
    if ticket_type == TicketType.REQUEST and building_address and apartment:
        lines.append(format_address(building_address, apartment))

    client_name = " ".join(part for part in (client_first_name, client_last_name) if part)
    if client_phone:
        client_name = f"{client_name}, {client_phone}"
    lines.append(client_name)

    if photos_count:
        lines.append(f"📎 Фото: {photos_count}")

    lines.append("")
    lines.append(shorten_description(description))
    return "\n".join(lines)
