from types import SimpleNamespace

from maxapi.types import CallbackButton, LinkButton, RequestContactButton

from src.bot.keyboards import (
    CHAT_CANCEL,
    CHAT_CHOOSE_PREFIX,
    CHAT_QUESTION,
    FORM_ADDRESS_ADD,
    FORM_ADDRESS_OK,
    FORM_ADDRESS_OTHER,
    FORM_BUILDING_PREFIX,
    FORM_CANCEL,
    FORM_CATEGORY_PREFIX,
    FORM_PHOTOS_DONE,
    FORM_PHOTOS_SKIP,
    FORM_RESIDENCE_PREFIX,
    FORM_SEND,
    FORM_START,
    FORM_TIME_SKIP,
    MENU_EMERGENCY,
    MENU_MAIN,
    MENU_PAYMENT,
    MENU_QUESTION,
    MENU_SERVICES,
    MENU_TICKETS,
    QUESTION_CANCEL,
    QUESTION_WRITE,
    RATE_PREFIX,
    address_keyboard,
    back_keyboard,
    building_keyboard,
    cancel_keyboard,
    category_keyboard,
    choose_ticket_keyboard,
    confirm_keyboard,
    confirm_question_keyboard,
    contacts_keyboard,
    main_menu_keyboard,
    my_tickets_empty_keyboard,
    my_tickets_keyboard,
    payment_keyboard,
    phone_keyboard,
    photos_done_keyboard,
    photos_skip_keyboard,
    question_cancel_keyboard,
    rating_keyboard,
    residences_keyboard,
    time_keyboard,
)
from src.core.constants import CHAT_TICKET_PREFIX, TicketStatus, TicketType
from src.schemas.content import PaymentContent


def test_main_menu_has_one_button_per_row_in_order():
    rows = main_menu_keyboard().payload.buttons

    assert [len(row) for row in rows] == [1, 1, 1, 1, 1, 1]
    assert [row[0].text for row in rows] == [
        "Подать заявку",
        "Мои заявки",
        "Задать вопрос",
        "Аварийные службы",
        "Услуги УК",
        "Оплата ЖКХ",
    ]
    assert all(isinstance(row[0], CallbackButton) for row in rows)
    assert [row[0].payload for row in rows] == [
        FORM_START,
        MENU_TICKETS,
        MENU_QUESTION,
        MENU_EMERGENCY,
        MENU_SERVICES,
        MENU_PAYMENT,
    ]


def test_back_keyboard_has_main_menu_button():
    rows = back_keyboard().payload.buttons

    assert len(rows) == 1
    assert rows[0][0].text == "« В меню"
    assert rows[0][0].payload == MENU_MAIN


def test_payment_keyboard_has_link_then_back():
    content = PaymentContent(
        text="Оплатите услуги",
        url="https://pay.example/zhkh",
        button_text="Оплатить ЖКХ",
    )

    rows = payment_keyboard(content).payload.buttons

    assert len(rows) == 2
    link = rows[0][0]
    assert isinstance(link, LinkButton)
    assert link.text == "Оплатить ЖКХ"
    assert link.url == "https://pay.example/zhkh"
    assert rows[1][0].text == "« В меню"
    assert rows[1][0].payload == MENU_MAIN


def test_phone_keyboard_has_contact_then_cancel():
    rows = phone_keyboard().payload.buttons

    assert len(rows) == 2
    assert isinstance(rows[0][0], RequestContactButton)
    assert rows[0][0].text == "Поделиться контактом"
    assert rows[1][0].payload == FORM_CANCEL


def test_cancel_keyboard_has_only_cancel():
    rows = cancel_keyboard().payload.buttons

    assert len(rows) == 1
    assert rows[0][0].text == "Отменить"
    assert rows[0][0].payload == FORM_CANCEL


def test_category_keyboard_lists_categories_then_cancel():
    categories = [
        SimpleNamespace(id=1, title="Сантехника"),
        SimpleNamespace(id=2, title="Электрика"),
    ]

    rows = category_keyboard(categories).payload.buttons

    assert [row[0].text for row in rows] == ["Сантехника", "Электрика", "Отменить"]
    assert [row[0].payload for row in rows] == [
        f"{FORM_CATEGORY_PREFIX}1",
        f"{FORM_CATEGORY_PREFIX}2",
        FORM_CANCEL,
    ]


def test_address_keyboard_has_ok_other_cancel():
    rows = address_keyboard().payload.buttons

    assert [row[0].payload for row in rows] == [
        FORM_ADDRESS_OK,
        FORM_ADDRESS_OTHER,
        FORM_CANCEL,
    ]


def test_residences_keyboard_lists_options_then_add_and_cancel():
    rows = residences_keyboard([(5, "ул. Ленина, 1, кв. 2")]).payload.buttons

    assert [row[0].text for row in rows] == ["ул. Ленина, 1, кв. 2", "Добавить адрес", "Отменить"]
    assert rows[0][0].payload == f"{FORM_RESIDENCE_PREFIX}5"
    assert rows[1][0].payload == FORM_ADDRESS_ADD
    assert rows[2][0].payload == FORM_CANCEL


def test_building_keyboard_lists_buildings_then_cancel():
    buildings = [SimpleNamespace(id=9, address="ул. Ленина, 12")]

    rows = building_keyboard(buildings).payload.buttons

    assert [row[0].text for row in rows] == ["ул. Ленина, 12", "Отменить"]
    assert rows[0][0].payload == f"{FORM_BUILDING_PREFIX}9"


def test_photos_skip_keyboard_has_skip_then_cancel():
    rows = photos_skip_keyboard().payload.buttons

    assert [row[0].text for row in rows] == ["Пропустить", "Отменить"]
    assert [row[0].payload for row in rows] == [FORM_PHOTOS_SKIP, FORM_CANCEL]


def test_photos_done_keyboard_has_done_then_cancel():
    rows = photos_done_keyboard().payload.buttons

    assert [row[0].text for row in rows] == ["Готово", "Отменить"]
    assert [row[0].payload for row in rows] == [FORM_PHOTOS_DONE, FORM_CANCEL]


def test_time_keyboard_has_skip_then_cancel():
    rows = time_keyboard().payload.buttons

    assert [row[0].payload for row in rows] == [FORM_TIME_SKIP, FORM_CANCEL]


def test_confirm_keyboard_has_send_then_cancel():
    rows = confirm_keyboard().payload.buttons

    assert [row[0].payload for row in rows] == [FORM_SEND, FORM_CANCEL]


def _ticket(ticket_type: TicketType, ticket_id: int, category_title: str | None):
    category = None if category_title is None else SimpleNamespace(title=category_title)
    return SimpleNamespace(type=ticket_type, id=ticket_id, category=category)


def test_choose_ticket_keyboard_lists_tickets_then_question_then_cancel():
    tickets = [
        _ticket(TicketType.REQUEST, 1042, "Сантехника"),
        _ticket(TicketType.QUESTION, 1051, None),
    ]

    rows = choose_ticket_keyboard(tickets, with_question=True).payload.buttons

    assert [row[0].text for row in rows] == [
        "№1042 · Сантехника",
        "№1051 · Вопрос",
        "Новый вопрос",
        "Отменить",
    ]
    assert [row[0].payload for row in rows] == [
        f"{CHAT_CHOOSE_PREFIX}1042",
        f"{CHAT_CHOOSE_PREFIX}1051",
        CHAT_QUESTION,
        CHAT_CANCEL,
    ]


def test_choose_ticket_keyboard_without_question_has_no_question_row():
    tickets = [_ticket(TicketType.REQUEST, 1042, "Сантехника")]

    rows = choose_ticket_keyboard(tickets, with_question=False).payload.buttons

    assert [row[0].payload for row in rows] == [
        f"{CHAT_CHOOSE_PREFIX}1042",
        CHAT_CANCEL,
    ]


def test_confirm_question_keyboard_has_yes_then_no():
    rows = confirm_question_keyboard().payload.buttons

    assert [row[0].text for row in rows] == ["Да", "Нет"]
    assert [row[0].payload for row in rows] == [CHAT_QUESTION, CHAT_CANCEL]


def _status_ticket(
    ticket_type: TicketType,
    ticket_id: int,
    status: TicketStatus,
    category_title: str | None = None,
):
    category = None if category_title is None else SimpleNamespace(title=category_title)
    return SimpleNamespace(type=ticket_type, id=ticket_id, status=status, category=category)


def test_my_tickets_keyboard_offers_write_only_for_open_tickets():
    tickets = [
        _status_ticket(TicketType.REQUEST, 1042, TicketStatus.IN_PROGRESS, "Сантехника"),
        _status_ticket(TicketType.QUESTION, 1051, TicketStatus.NEW),
        _status_ticket(TicketType.REQUEST, 1030, TicketStatus.CLOSED, "Электрика"),
    ]

    rows = my_tickets_keyboard(tickets).payload.buttons

    assert [row[0].text for row in rows] == [
        "Написать по заявке №1042",
        "Написать по вопросу №1051",
        "« В меню",
    ]
    assert [row[0].payload for row in rows] == [
        f"{CHAT_TICKET_PREFIX}1042",
        f"{CHAT_TICKET_PREFIX}1051",
        MENU_MAIN,
    ]


def test_my_tickets_keyboard_without_open_tickets_has_only_back():
    tickets = [_status_ticket(TicketType.REQUEST, 1030, TicketStatus.REJECTED, "Электрика")]

    rows = my_tickets_keyboard(tickets).payload.buttons

    assert [row[0].payload for row in rows] == [MENU_MAIN]


def test_my_tickets_empty_keyboard_has_form_start_then_back():
    rows = my_tickets_empty_keyboard().payload.buttons

    assert [row[0].text for row in rows] == ["Подать заявку", "« В меню"]
    assert [row[0].payload for row in rows] == [FORM_START, MENU_MAIN]


def test_contacts_keyboard_has_write_question_then_back():
    rows = contacts_keyboard().payload.buttons

    assert [row[0].text for row in rows] == ["Написать вопрос", "« В меню"]
    assert [row[0].payload for row in rows] == [QUESTION_WRITE, MENU_MAIN]


def test_question_cancel_keyboard_has_cancel():
    rows = question_cancel_keyboard().payload.buttons

    assert [row[0].text for row in rows] == ["Отменить"]
    assert [row[0].payload for row in rows] == [QUESTION_CANCEL]


def test_rating_keyboard_has_scores_one_to_five_in_one_row():
    rows = rating_keyboard(1042).payload.buttons

    assert len(rows) == 1
    assert [button.text for button in rows[0]] == ["1", "2", "3", "4", "5"]
    assert [button.payload for button in rows[0]] == [
        f"{RATE_PREFIX}1042:1",
        f"{RATE_PREFIX}1042:2",
        f"{RATE_PREFIX}1042:3",
        f"{RATE_PREFIX}1042:4",
        f"{RATE_PREFIX}1042:5",
    ]
