from maxapi.types import CallbackButton, LinkButton

from src.bot.keyboards import (
    MENU_EMERGENCY,
    MENU_MAIN,
    MENU_PAYMENT,
    MENU_SERVICES,
    back_keyboard,
    main_menu_keyboard,
    payment_keyboard,
)
from src.schemas.content import PaymentContent


def test_main_menu_has_one_button_per_row_in_order():
    rows = main_menu_keyboard().payload.buttons

    assert [len(row) for row in rows] == [1, 1, 1]
    assert [row[0].text for row in rows] == [
        "Аварийные службы",
        "Услуги УК",
        "Оплата ЖКХ",
    ]
    assert all(isinstance(row[0], CallbackButton) for row in rows)
    assert [row[0].payload for row in rows] == [
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
