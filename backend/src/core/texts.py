from src.core.constants import DIRECTORY_ACTIVE_LIMIT, TicketStatus, TicketType

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
DESCRIPTION_LIMIT = 3000

DESCRIPTION_REQUIRED = "Опишите проблему"
DESCRIPTION_TOO_LONG = f"Описание — не больше {DESCRIPTION_LIMIT} символов"
APARTMENT_INVALID = "Квартира — до 20 символов: буквы, цифры, пробел, «/», «.» и «-»"
CATEGORY_NOT_FOUND = "Категория не найдена"
BUILDING_NOT_FOUND = "Адрес не найден"
PHOTO_NOT_FOUND = "Фото не найдено"
PHOTO_ALREADY_ATTACHED = "Фото уже прикреплено"
PHOTOS_DUPLICATED = "Фото повторяются"
PHOTO_NOT_IMAGE = "Можно прикрепить только фото"
PHONE_INVALID = "Проверьте номер телефона"
RESIDENCE_NOT_FOUND = "Адрес не найден"

# Chat

MESSAGE_LIMIT = 3000
MESSAGE_FILES_MAX = 10

MESSAGE_EMPTY = "Напишите сообщение или приложите файл"
MESSAGE_TOO_LONG = f"Сообщение — не больше {MESSAGE_LIMIT} символов"
MESSAGE_TOO_MANY_FILES = f"Можно приложить не больше {MESSAGE_FILES_MAX} файлов"
MESSAGE_FILES_MIXED = "В одном сообщении — до 10 фото или один документ"

TICKET_NOT_FOUND = "Обращение не найдено"
TICKET_CLOSED_FOR_STAFF = "Обращение закрыто — написать клиенту нельзя"
TICKET_CLOSED_FOR_CLIENT = "Обращение №{ticket_id} уже закрыто"
TICKET_REPLY_BUTTON = "Ответить"

# Status change, closing and rating
STATUS_COMMENT_LIMIT = 1000
STATUS_COMMENT_TOO_LONG = f"Комментарий — не больше {STATUS_COMMENT_LIMIT} символов"
REJECT_REASON_REQUIRED = "Укажите причину отклонения"
RATING_INVALID = "Оценка — от 1 до 5"
RATING_ONLY_CLOSED = "Оценить можно только закрытое обращение"

RESOLVED_YES_BUTTON = "Да"
RESOLVED_NO_BUTTON = "Нет"
STATUS_RESOLVED_QUESTION: dict[TicketType, str] = {
    TicketType.REQUEST: "Проблема решена?",
    TicketType.QUESTION: "Вопрос решён?",
}

RATE_PROMPT = "Оцените работу по {label} — от 1 до 5:"
RATE_THANKS = "Спасибо за оценку!"
REOPENED_TEXT = (
    "🟢 Статус {label}: В работе. Напишите, что осталось не так, — сообщение уйдёт сотруднику."
)

CHAT_SENT = "Сообщение добавлено к {label}."
CHAT_WRITE_PROMPT = "Напишите сообщение по {label}."
CHAT_WRITE_NOTIFICATION = "Пишите — сообщение уйдёт сотруднику"
CHAT_FINISH_CURRENT = "Сначала закончите или отмените текущее действие"
CHAT_UNSUPPORTED = "Пока я принимаю только текст и фото."
CHAT_PHOTOS_FAILED = "Часть фото не удалось добавить."
CHAT_PHOTOS_ALL_FAILED = "Не удалось получить фото. Попробуйте ещё раз."
CHAT_CHOOSE_TICKET = "К какой заявке относится сообщение?"
CHAT_OFFER_QUESTION = "Открытых заявок нет — оформить это как вопрос?"
CHAT_TEXT_REQUIRED = (
    "Сейчас у вас нет открытых заявок. Хотите спросить — напишите вопрос текстом, "
    "а если нужно сообщить о проблеме — нажмите «Подать заявку»."
)
CHAT_NOT_SENT = "Сообщение не отправлено."
QUESTION_SENT = "Вопрос №{ticket_id} отправлен."

CHAT_NEW_QUESTION_BUTTON = "Новый вопрос"
CHAT_YES_BUTTON = "Да"
CHAT_NO_BUTTON = "Нет"


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


def staff_message_client_text(
    *,
    ticket_id: int,
    ticket_type: TicketType,
    text: str | None,
) -> str:
    if ticket_type == TicketType.QUESTION:
        header = f"💬 Вопрос №{ticket_id}"
    else:
        header = f"💬 Заявка №{ticket_id}"

    if text is None:
        return header
    return f"{header}\n\n{text}"


def client_message_staff_text(
    *,
    ticket_id: int,
    ticket_type: TicketType,
    client_first_name: str,
    client_last_name: str | None,
    text: str | None,
    photos_count: int,
) -> str:
    if ticket_type == TicketType.QUESTION:
        header = f"💬 Вопрос №{ticket_id}"
    else:
        header = f"💬 Заявка №{ticket_id}"

    client_name = " ".join(part for part in (client_first_name, client_last_name) if part)
    lines = [f"{header} · {client_name}"]

    if photos_count:
        lines.append(f"📎 Фото: {photos_count}")

    if text is not None:
        lines.append("")
        lines.append(shorten_description(text))

    return "\n".join(lines)


def ticket_dative(ticket_type: TicketType, ticket_id: int) -> str:
    if ticket_type == TicketType.QUESTION:
        return f"вопросу №{ticket_id}"
    return f"заявке №{ticket_id}"


def ticket_genitive(ticket_type: TicketType, ticket_id: int) -> str:
    if ticket_type == TicketType.QUESTION:
        return f"вопроса №{ticket_id}"
    return f"заявки №{ticket_id}"


_STATUS_MESSAGE_ICONS: dict[TicketStatus, str] = {
    TicketStatus.IN_PROGRESS: "🟢",
    TicketStatus.WAITING_CLIENT: "🟡",
    TicketStatus.REJECTED: "🔴",
    TicketStatus.CLOSED: "🟢",
}


def status_message_text(
    ticket_type: TicketType,
    ticket_id: int,
    status: TicketStatus,
    comment: str | None,
) -> str:
    label = STATUS_LABELS[status]
    text = f"{_STATUS_MESSAGE_ICONS[status]} Статус {ticket_genitive(ticket_type, ticket_id)}: {label}."
    if status == TicketStatus.WAITING_CLIENT:
        text += " Напишите его в этот чат."
    elif status == TicketStatus.REJECTED:
        text += f"\nПричина: {comment}"
    elif status == TicketStatus.CLOSED:
        text += f"\n{STATUS_RESOLVED_QUESTION[ticket_type]}"
    return text


def reopened_staff_text(
    *,
    ticket_id: int,
    ticket_type: TicketType,
    client_first_name: str,
    client_last_name: str | None,
) -> str:
    if ticket_type == TicketType.QUESTION:
        header = f"🔄 Вопрос №{ticket_id}"
    else:
        header = f"🔄 Заявка №{ticket_id}"
    client_name = " ".join(part for part in (client_first_name, client_last_name) if part)
    return (
        f"{header} · {client_name}\n"
        "Клиент сообщил, что проблема не решена — обращение снова в работе."
    )


def ticket_button_label(ticket_type: TicketType, ticket_id: int, category_title: str | None) -> str:
    if ticket_type == TicketType.QUESTION:
        return f"№{ticket_id} · Вопрос"
    return f"№{ticket_id} · {category_title}"


# Client request form (bot)

FORM_START_BUTTON = "📝 Подать заявку"
FORM_CONTACT_BUTTON = "Поделиться контактом"
FORM_CANCEL_BUTTON = "Отменить"
FORM_ADDRESS_OK_BUTTON = "Верно"
FORM_ADDRESS_OTHER_BUTTON = "Другой адрес"
FORM_ADDRESS_ADD_BUTTON = "Добавить адрес"
FORM_PHOTOS_DONE_BUTTON = "Готово"
FORM_PHOTOS_SKIP_BUTTON = "Пропустить"
FORM_TIME_SKIP_BUTTON = "Пропустить"
FORM_SEND_BUTTON = "Отправить"

FORM_PHOTOS_MAX = 10

FORM_PHONE_PROMPT = (
    "Для решения проблемы нам может понадобиться ваш номер — укажите его кнопкой ниже."
)
FORM_PHONE_OWN_TEXT = "Нужен именно ваш номер — нажмите «Поделиться контактом»."
FORM_TEXT_ONLY = "Голосовые и файлы я пока не понимаю — напишите текстом."
FORM_CATEGORY_PROMPT = "Выберите категорию обращения."
FORM_ADDRESS_PROMPT = "Оформляем на адрес:\n{address}\n\nВсё верно?"
FORM_ADDRESS_OTHER_PROMPT = "Выберите адрес из списка или добавьте новый."
FORM_BUILDING_PROMPT = "Выберите ваш дом из списка ниже."
FORM_APARTMENT_PROMPT = "Напишите номер вашей квартиры."
# Max delivers a voice message to the bot as an empty update without a sender, so the bot cannot
# answer it: the prompts where the client types warn in advance.
FORM_DESCRIPTION_PROMPT = "Что произошло? Опишите проблему текстом — голосовые я пока не понимаю."
FORM_PHOTOS_PROMPT = (
    "Приложите фото, если есть — это поможет быстрее разобраться в проблеме (можно несколько).\n\n"
    "Нет фото? Нажмите «Пропустить»."
)
FORM_PHOTOS_ADDED = "Фото добавлено: {count}. Пришлите ещё или нажмите «Готово»."
FORM_PHOTOS_LIMIT = "Можно прикрепить не больше {max} фото. Добавлено: {count}."
FORM_PHOTO_FAILED = "Не удалось добавить фото. Добавлено: {count}."
FORM_TIME_PROMPT = "Когда вам удобно принять мастера?\n\nПока не знаете — нажмите «Пропустить»."
FORM_TIME_NOT_SET = "не указано"
FORM_CONFIRM_PROMPT = (
    "🔎 <b>Проверьте заявку</b>\n\n"
    "<b>Категория:</b> {category}\n"
    "<b>Адрес:</b> {address}\n"
    "<b>Описание:</b> {description}\n"
    "<b>Фото:</b> {photos}\n"
    "<b>Время:</b> {time}\n\n"
    "Отправляем?"
)
FORM_SENT = "Заявка №{ticket_id} отправлена."
FORM_CANCELLED = "Заявка отменена."

# Client menu (bot)

MAIN_MENU_BUTTON = "Главное меню"

MY_TICKETS_BUTTON = "📋 Мои заявки"
QUESTION_BUTTON = "💬 Задать вопрос"
PAYMENT_BUTTON = "💳 Оплата ЖКХ"
SERVICES_BUTTON = "🛠️ Услуги УК"
EMERGENCY_BUTTON = "🚨 Аварийные службы"

MY_TICKETS_LIMIT = 10
MY_TICKETS_TITLE = "Ваши заявки:"
MY_TICKETS_EMPTY = "Заявок пока нет. Если что-то случилось — нажмите «Подать заявку»."
MY_TICKETS_WRITE_BUTTON = "Написать по {label}"

QUESTION_SECTION_DEFAULT = "Есть вопрос? Напишите — ответим прямо здесь."
QUESTION_WRITE_BUTTON = "Написать вопрос"

QUESTION_PROMPT = (
    "Напишите вопрос одним сообщением — текстом, можно с фото. Голосовые я пока не понимаю."
)
QUESTION_TEXT_REQUIRED = "Напишите вопрос текстом — фото можно приложить к нему."
QUESTION_CANCELLED = "Вопрос не отправлен."

# Content (admin API)

CONTENT_IMAGE_FORMAT = "Нужна картинка в формате JPEG или PNG"
CONTENT_IMAGE_NOT_FOUND = "Фото не найдено — загрузите его заново"
THEME_NOT_SET = "Оформление не настроено"
TEXT_INVALID_CHARACTER = "Текст содержит недопустимый символ"

# Users (admin API)

USER_NOT_FOUND = "Пользователь не найден"
USER_CANNOT_CHANGE_SELF = "Нельзя снять права администратора с себя или заблокировать себя"
USER_CONFIG_ADMIN = (
    "Этот администратор задан в настройках сервера — понизить или заблокировать его нельзя"
)

# Broadcast (admin API)

BROADCAST_IN_PROGRESS = "Другая рассылка ещё отправляется — дождитесь её окончания"
BROADCAST_NO_RECIPIENTS = "Нет получателей: рассылка уходит жильцам, которые уже написали боту"
BROADCAST_PHOTO_UNAVAILABLE = "Не удалось получить фото — загрузите его заново"

# Directories (admin API)

DIRECTORY_NAME_MARKUP = "Без символов разметки: * _ ~ ^ + ` [ ] # >"
BUILDING_EXISTS = "Такой дом уже есть"
CATEGORY_EXISTS = "Такая категория уже есть"
BUILDINGS_LIMIT = (
    f"Включено уже {DIRECTORY_ACTIVE_LIMIT} домов — больше бот не покажет. "
    "Сначала отключите ненужный дом"
)
CATEGORIES_LIMIT = (
    f"Включено уже {DIRECTORY_ACTIVE_LIMIT} категорий — больше бот не покажет. "
    "Сначала отключите ненужную категорию"
)
BUILDING_LAST_ACTIVE = "Нельзя отключить последний дом: жилец не сможет указать адрес"
CATEGORY_LAST_ACTIVE = "Нельзя отключить последнюю категорию: жилец не сможет подать заявку"
CATEGORY_ORDER_STALE = "Список категорий изменился — обновите страницу"
