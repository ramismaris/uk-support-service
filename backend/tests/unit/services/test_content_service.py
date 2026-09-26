import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.constants import ContentKey
from src.schemas.content import (
    ContactPhone,
    ContactsContent,
    EmergencyContent,
    PaymentContent,
    ServicesContent,
    WelcomeContent,
)
from src.services.content_service import ContentService


@pytest.fixture
def blocks_repo() -> MagicMock:
    repo = MagicMock()
    repo.get = AsyncMock()
    return repo


def _make_service(blocks_repo: MagicMock) -> ContentService:
    with patch("src.services.content_service.ContentBlockRepository", return_value=blocks_repo):
        return ContentService(MagicMock())


def _make_block(data: dict) -> MagicMock:
    block = MagicMock()
    block.data = data
    return block


@pytest.mark.parametrize(
    ("method", "key", "data", "expected"),
    [
        (
            "get_welcome",
            ContentKey.WELCOME,
            {"text": "Привет", "file_id": 7},
            WelcomeContent(text="Привет", file_id=7),
        ),
        (
            "get_emergency",
            ContentKey.EMERGENCY,
            {"text": "Аварийный текст"},
            EmergencyContent(text="Аварийный текст"),
        ),
        (
            "get_services",
            ContentKey.SERVICES,
            {"text": "Текст услуг"},
            ServicesContent(text="Текст услуг"),
        ),
        (
            "get_payment",
            ContentKey.PAYMENT,
            {"text": "Текст оплаты", "url": "https://pay.example", "button_text": "Оплатить"},
            PaymentContent(text="Текст оплаты", url="https://pay.example", button_text="Оплатить"),
        ),
        (
            "get_contacts",
            ContentKey.CONTACTS,
            {
                "text": "Свяжитесь с нами",
                "phones": [{"title": "Диспетчерская", "phone": "+7 (800) 000-00-01"}],
            },
            ContactsContent(
                text="Свяжитесь с нами",
                phones=[ContactPhone(title="Диспетчерская", phone="+7 (800) 000-00-01")],
            ),
        ),
    ],
)
async def test_getter_returns_validated_model(
    blocks_repo: MagicMock,
    method: str,
    key: ContentKey,
    data: dict,
    expected: object,
):
    blocks_repo.get.return_value = _make_block(data)

    result = await getattr(_make_service(blocks_repo), method)()

    blocks_repo.get.assert_awaited_once_with(key)
    assert result == expected


@pytest.mark.parametrize(
    "method",
    ["get_welcome", "get_emergency", "get_services", "get_payment", "get_contacts"],
)
async def test_getter_returns_none_when_block_missing(blocks_repo: MagicMock, method: str):
    blocks_repo.get.return_value = None

    assert await getattr(_make_service(blocks_repo), method)() is None


@pytest.mark.parametrize(
    "method",
    ["get_welcome", "get_emergency", "get_services", "get_payment", "get_contacts"],
)
async def test_getter_returns_none_and_logs_error_on_invalid_data(
    blocks_repo: MagicMock,
    caplog: pytest.LogCaptureFixture,
    method: str,
):
    blocks_repo.get.return_value = _make_block({})

    with caplog.at_level(logging.ERROR, logger="src.services.content_service"):
        result = await getattr(_make_service(blocks_repo), method)()

    assert result is None
    assert method.removeprefix("get_").upper() in caplog.text
    assert "ValidationError" in caplog.text
