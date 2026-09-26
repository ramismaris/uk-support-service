import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.constants import ContentKey
from src.core.exceptions import AppException
from src.core.texts import CONTENT_IMAGE_NOT_FOUND
from src.schemas.content import (
    ContactPhone,
    ContactsContent,
    EmergencyContent,
    PaymentContent,
    ServicesContent,
    ThemeContent,
    WelcomeContent,
    WelcomeContentUpdate,
)
from src.services.content_service import ContentService


@pytest.fixture
def blocks_repo() -> MagicMock:
    repo = MagicMock()
    repo.get = AsyncMock()
    repo.upsert = AsyncMock()
    return repo


@pytest.fixture
def files_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    return repo


def _make_service(
    blocks_repo: MagicMock,
    files_repo: MagicMock | None = None,
    db: AsyncMock | None = None,
) -> ContentService:
    if files_repo is None:
        files_repo = MagicMock()
        files_repo.get_by_id = AsyncMock()
    with (
        patch("src.services.content_service.ContentBlockRepository", return_value=blocks_repo),
        patch("src.services.content_service.FileRepository", return_value=files_repo),
    ):
        return ContentService(db if db is not None else AsyncMock())


def _make_block(data: dict) -> MagicMock:
    block = MagicMock()
    block.data = data
    return block


def _make_file(
    *,
    file_id: int = 1,
    ticket_id: int | None = None,
    message_id: int | None = None,
    mime: str = "image/png",
) -> MagicMock:
    file = MagicMock()
    file.id = file_id
    file.ticket_id = ticket_id
    file.message_id = message_id
    file.mime = mime
    return file


def _make_admin(admin_id: int = 42) -> MagicMock:
    admin = MagicMock()
    admin.id = admin_id
    return admin


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
        (
            "get_theme",
            ContentKey.THEME,
            {"company_name": "УК «Наш дом»", "primary_color": "#1E88E5", "logo_file_id": 5},
            ThemeContent(company_name="УК «Наш дом»", primary_color="#1E88E5", logo_file_id=5),
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
    [
        "get_welcome",
        "get_emergency",
        "get_services",
        "get_payment",
        "get_contacts",
        "get_theme",
    ],
)
async def test_getter_returns_none_when_block_missing(blocks_repo: MagicMock, method: str):
    blocks_repo.get.return_value = None

    assert await getattr(_make_service(blocks_repo), method)() is None


@pytest.mark.parametrize(
    "method",
    [
        "get_welcome",
        "get_emergency",
        "get_services",
        "get_payment",
        "get_contacts",
        "get_theme",
    ],
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


async def test_save_valid_image_stores_block(blocks_repo: MagicMock, files_repo: MagicMock) -> None:
    db = AsyncMock()
    files_repo.get_by_id.return_value = _make_file()
    admin = _make_admin()
    service = _make_service(blocks_repo, files_repo, db)
    content = WelcomeContentUpdate(text="  Привет  ", file_id=7)

    await service.save(ContentKey.WELCOME, content, admin)

    files_repo.get_by_id.assert_awaited_once_with(7)
    blocks_repo.upsert.assert_awaited_once_with(
        ContentKey.WELCOME, {"text": "Привет", "file_id": 7}, updated_by_id=admin.id
    )
    db.commit.assert_awaited_once()


@pytest.mark.parametrize(
    "file",
    [
        pytest.param(None, id="missing"),
        pytest.param(_make_file(ticket_id=99), id="ticket"),
        pytest.param(_make_file(message_id=99), id="message"),
        pytest.param(_make_file(mime="application/pdf"), id="pdf"),
    ],
)
async def test_save_rejects_file_that_is_not_content_image(
    blocks_repo: MagicMock, files_repo: MagicMock, file: MagicMock | None
) -> None:
    db = AsyncMock()
    files_repo.get_by_id.return_value = file
    service = _make_service(blocks_repo, files_repo, db)

    with pytest.raises(AppException) as exc_info:
        await service.save(
            ContentKey.WELCOME,
            WelcomeContentUpdate(text="Привет", file_id=7),
            _make_admin(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == CONTENT_IMAGE_NOT_FOUND
    blocks_repo.upsert.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_save_theme_without_logo_skips_file_lookup(
    blocks_repo: MagicMock, files_repo: MagicMock
) -> None:
    db = AsyncMock()
    admin = _make_admin()
    service = _make_service(blocks_repo, files_repo, db)

    await service.save(
        ContentKey.THEME,
        ThemeContent(company_name="УК «Наш дом»", primary_color="#1E88E5"),
        admin,
    )

    files_repo.get_by_id.assert_not_awaited()
    blocks_repo.upsert.assert_awaited_once_with(
        ContentKey.THEME,
        {"company_name": "УК «Наш дом»", "primary_color": "#1E88E5", "logo_file_id": None},
        updated_by_id=admin.id,
    )
    db.commit.assert_awaited_once()


async def test_save_block_without_file_skips_file_lookup(
    blocks_repo: MagicMock, files_repo: MagicMock
) -> None:
    db = AsyncMock()
    admin = _make_admin()
    service = _make_service(blocks_repo, files_repo, db)

    await service.save(ContentKey.EMERGENCY, EmergencyContent(text="Аварийная служба"), admin)

    files_repo.get_by_id.assert_not_awaited()
    blocks_repo.upsert.assert_awaited_once_with(
        ContentKey.EMERGENCY, {"text": "Аварийная служба"}, updated_by_id=admin.id
    )
    db.commit.assert_awaited_once()
