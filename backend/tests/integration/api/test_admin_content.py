import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ContentKey, SenderType, TicketStatus, TicketType, UserRole
from src.core.security import hash_token
from src.core.texts import CONTENT_IMAGE_FORMAT, CONTENT_IMAGE_NOT_FOUND
from src.main import app
from src.models.file import File
from src.providers.factory import get_storage_provider
from src.providers.local_storage_provider import LocalStorageProvider
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.content_block_repository import ContentBlockRepository
from src.repositories.message_repository import MessageRepository
from src.repositories.ticket_repository import TicketRepository
from src.repositories.user_repository import UserRepository
from src.services.file_service import FileService

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
GIF = b"GIF89a\x00\x00"

FILE_URL_PATTERN = re.compile(r"^/api/v1/files/\d+\?exp=\d+&sig=[0-9a-f]{64}$")

BLOCKS = {
    ContentKey.WELCOME: {"text": "Здравствуйте", "file_id": None},
    ContentKey.EMERGENCY: {"text": "Аварийная служба"},
    ContentKey.SERVICES: {"text": "Услуги УК"},
    ContentKey.PAYMENT: {
        "text": "Оплата",
        "url": "https://example.com/pay",
        "button_text": "Оплатить",
    },
    ContentKey.CONTACTS: {
        "text": "Контакты",
        "phones": [{"title": "Диспетчерская", "phone": "+7 (800) 000-00-01"}],
    },
    ContentKey.THEME: {
        "company_name": "УК «Наш дом»",
        "primary_color": "#1E88E5",
        "logo_file_id": None,
    },
}


@pytest.fixture
def storage(tmp_path) -> LocalStorageProvider:
    provider = LocalStorageProvider(str(tmp_path))
    app.dependency_overrides[get_storage_provider] = lambda: provider
    return provider


async def _issue_token(db: AsyncSession, user) -> str:
    token = f"admin-content-token-{user.id}"
    await AuthTokenRepository(db).create(
        user.id, hash_token(token), datetime.now(UTC) + timedelta(days=1)
    )
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def base(db: AsyncSession) -> SimpleNamespace:
    users = UserRepository(db)
    client = await users.create(max_user_id=3000003, first_name="Мария")
    manager = await users.create(max_user_id=3000002, first_name="Игорь", role=UserRole.MANAGER)
    admin = await users.create(max_user_id=3000001, first_name="Анна", role=UserRole.ADMIN)
    blocked = await users.create(max_user_id=3000004, first_name="Пётр", role=UserRole.ADMIN)
    blocked.is_blocked = True

    client_token = await _issue_token(db, client)
    manager_token = await _issue_token(db, manager)
    admin_token = await _issue_token(db, admin)
    blocked_token = await _issue_token(db, blocked)
    await db.commit()

    return SimpleNamespace(
        client=client,
        manager=manager,
        admin=admin,
        blocked=blocked,
        client_token=client_token,
        manager_token=manager_token,
        admin_token=admin_token,
        blocked_token=blocked_token,
    )


@pytest.fixture
async def content_image(db: AsyncSession, storage: LocalStorageProvider) -> File:
    return await FileService(db, storage).save_image(PNG, "welcome.png")


async def _seed_blocks(db: AsyncSession) -> None:
    repository = ContentBlockRepository(db)
    for key, data in BLOCKS.items():
        await repository.create(key, data)
    await db.commit()


async def _stored(db: AsyncSession, key: ContentKey):
    db.expunge_all()
    return await ContentBlockRepository(db).get(key)


def _png_file() -> dict:
    return {"file": ("logo.png", PNG, "image/png")}


def _multipart(filename: str, data: bytes) -> tuple[bytes, dict[str, str]]:
    # httpx rejects a NUL in a multipart filename, so the body is built by hand.
    boundary = "nultestboundary"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return head + data + tail, headers


async def test_get_content_returns_all_blocks(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _seed_blocks(db)

    resp = await client.get("/api/v1/admin/content", headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["welcome"] == {"text": "Здравствуйте", "file_id": None, "file_url": None}
    assert body["emergency"] == {"text": "Аварийная служба"}
    assert body["services"] == {"text": "Услуги УК"}
    assert body["payment"] == {
        "text": "Оплата",
        "url": "https://example.com/pay",
        "button_text": "Оплатить",
    }
    assert body["contacts"] == {
        "text": "Контакты",
        "phones": [{"title": "Диспетчерская", "phone": "+7 (800) 000-00-01"}],
    }
    assert body["theme"] == {
        "company_name": "УК «Наш дом»",
        "primary_color": "#1E88E5",
        "logo_file_id": None,
        "logo_url": None,
    }


async def test_get_content_broken_block_is_null(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _seed_blocks(db)
    broken = await ContentBlockRepository(db).get(ContentKey.WELCOME)
    assert broken is not None
    broken.data = {"text": ""}
    await db.commit()

    resp = await client.get("/api/v1/admin/content", headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["welcome"] is None
    assert body["emergency"] == {"text": "Аварийная служба"}
    assert body["services"] == {"text": "Услуги УК"}


async def test_get_content_returns_signed_file_links(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    welcome_file = await FileService(db, storage).save_image(PNG, "welcome.png")
    logo_file = await FileService(db, storage).save_image(JPEG, "logo.jpg")
    await _seed_blocks(db)
    repository = ContentBlockRepository(db)
    welcome = await repository.get(ContentKey.WELCOME)
    assert welcome is not None
    welcome.data = {**welcome.data, "file_id": welcome_file.id}
    theme = await repository.get(ContentKey.THEME)
    assert theme is not None
    theme.data = {**theme.data, "logo_file_id": logo_file.id}
    await db.commit()

    resp = await client.get("/api/v1/admin/content", headers=_auth(base.admin_token))

    assert resp.status_code == 200
    body = resp.json()
    assert FILE_URL_PATTERN.match(body["welcome"]["file_url"])
    assert FILE_URL_PATTERN.match(body["theme"]["logo_url"])

    download = await client.get(body["welcome"]["file_url"])
    assert download.status_code == 200
    assert download.content == PNG


SIMPLE_PUT_CASES = [
    pytest.param(
        "/api/v1/admin/content/emergency",
        {"text": "  Пожар  "},
        ContentKey.EMERGENCY,
        {"text": "Пожар"},
        id="emergency",
    ),
    pytest.param(
        "/api/v1/admin/content/services",
        {"text": "  Услуги  "},
        ContentKey.SERVICES,
        {"text": "Услуги"},
        id="services",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {
            "text": "  Оплата  ",
            "url": "https://example.com/pay",
            "button_text": "  Оплатить  ",
        },
        ContentKey.PAYMENT,
        {"text": "Оплата", "url": "https://example.com/pay", "button_text": "Оплатить"},
        id="payment",
    ),
    pytest.param(
        "/api/v1/admin/content/contacts",
        {
            "text": "  Контакты  ",
            "phones": [{"title": "  Диспетчерская  ", "phone": "  +7  "}],
        },
        ContentKey.CONTACTS,
        {"text": "Контакты", "phones": [{"title": "Диспетчерская", "phone": "+7"}]},
        id="contacts",
    ),
]


@pytest.mark.parametrize(("path", "payload", "key", "expected"), SIMPLE_PUT_CASES)
async def test_put_simple_creates_missing_block(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    path: str,
    payload: dict,
    key: ContentKey,
    expected: dict,
) -> None:
    resp = await client.put(path, json=payload, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    assert resp.json() == expected
    stored = await _stored(db, key)
    assert stored is not None
    assert stored.data == expected
    assert stored.updated_by_id == base.admin.id


@pytest.mark.parametrize(("path", "payload", "key", "expected"), SIMPLE_PUT_CASES)
async def test_put_simple_updates_existing_block(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    path: str,
    payload: dict,
    key: ContentKey,
    expected: dict,
) -> None:
    await _seed_blocks(db)

    resp = await client.put(path, json=payload, headers=_auth(base.admin_token))

    assert resp.status_code == 200
    stored = await _stored(db, key)
    assert stored is not None
    assert stored.data == expected
    assert stored.updated_by_id == base.admin.id


async def test_put_welcome_creates_block_with_photo(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    content_image: File,
) -> None:
    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "  Привет  ", "file_id": content_image.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "Привет"
    assert body["file_id"] == content_image.id
    assert body["file_url"].startswith(f"/api/v1/files/{content_image.id}?")
    stored = await _stored(db, ContentKey.WELCOME)
    assert stored is not None
    assert stored.data == {"text": "Привет", "file_id": content_image.id}
    assert stored.updated_by_id == base.admin.id


async def test_put_welcome_updates_existing_block(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    content_image: File,
) -> None:
    await _seed_blocks(db)

    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "Новое приветствие", "file_id": content_image.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    stored = await _stored(db, ContentKey.WELCOME)
    assert stored is not None
    assert stored.data == {"text": "Новое приветствие", "file_id": content_image.id}
    assert stored.updated_by_id == base.admin.id


async def test_put_theme_creates_block_with_logo(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    content_image: File,
) -> None:
    resp = await client.put(
        "/api/v1/admin/content/theme",
        json={
            "company_name": "  УК  ",
            "primary_color": "#ABCDEF",
            "logo_file_id": content_image.id,
        },
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["company_name"] == "УК"
    assert body["primary_color"] == "#ABCDEF"
    assert body["logo_file_id"] == content_image.id
    assert body["logo_url"].startswith(f"/api/v1/files/{content_image.id}?")
    stored = await _stored(db, ContentKey.THEME)
    assert stored is not None
    assert stored.data == {
        "company_name": "УК",
        "primary_color": "#ABCDEF",
        "logo_file_id": content_image.id,
    }
    assert stored.updated_by_id == base.admin.id


INVALID_BODIES = [
    pytest.param(
        "/api/v1/admin/content/welcome",
        {"text": "   ", "file_id": 1},
        id="welcome-blank",
    ),
    pytest.param(
        "/api/v1/admin/content/welcome",
        {"text": "x" * 3001, "file_id": 1},
        id="welcome-too-long",
    ),
    pytest.param(
        "/api/v1/admin/content/welcome",
        {"text": "Привет"},
        id="welcome-without-file",
    ),
    pytest.param(
        "/api/v1/admin/content/welcome",
        {"text": "Привет", "file_id": 0},
        id="welcome-file-zero",
    ),
    pytest.param(
        "/api/v1/admin/content/welcome",
        {"text": "Привет", "file_id": 2**63},
        id="welcome-file-too-big",
    ),
    pytest.param(
        "/api/v1/admin/content/emergency",
        {"text": "   "},
        id="emergency-blank",
    ),
    pytest.param(
        "/api/v1/admin/content/emergency",
        {"text": "x" * 3001},
        id="emergency-too-long",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "javascript:alert(1)", "button_text": "ОК"},
        id="payment-javascript",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "ftp://x", "button_text": "ОК"},
        id="payment-ftp",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "example.com", "button_text": "ОК"},
        id="payment-without-scheme",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "https://example.com/a b", "button_text": "ОК"},
        id="payment-url-with-space",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "https://example.com/pay", "button_text": "x" * 65},
        id="payment-button-too-long",
    ),
    pytest.param(
        "/api/v1/admin/content/contacts",
        {"text": "Контакты", "phones": [{"title": "Д", "phone": "1"}] * 11},
        id="contacts-eleven-phones",
    ),
    pytest.param(
        "/api/v1/admin/content/contacts",
        {"text": "Контакты", "phones": [{"title": "x" * 51, "phone": "1"}]},
        id="contacts-title-too-long",
    ),
    pytest.param(
        "/api/v1/admin/content/theme",
        {"company_name": "УК", "primary_color": "red"},
        id="theme-color-name",
    ),
    pytest.param(
        "/api/v1/admin/content/theme",
        {"company_name": "УК", "primary_color": "#12345"},
        id="theme-color-short",
    ),
    pytest.param(
        "/api/v1/admin/content/theme",
        {"company_name": "УК", "primary_color": "#GGGGGG"},
        id="theme-color-bad-hex",
    ),
    pytest.param(
        "/api/v1/admin/content/theme",
        {"company_name": "УК", "primary_color": "#1E88E5", "logo_file_id": 0},
        id="theme-logo-zero",
    ),
    pytest.param(
        "/api/v1/admin/content/theme",
        {"company_name": "УК", "primary_color": "#1E88E5", "logo_file_id": 2**63},
        id="theme-logo-too-big",
    ),
]


@pytest.mark.parametrize(("path", "payload"), INVALID_BODIES)
async def test_put_invalid_body_returns_422(
    client: AsyncClient, base: SimpleNamespace, path: str, payload: dict
) -> None:
    resp = await client.put(path, json=payload, headers=_auth(base.admin_token))

    assert resp.status_code == 422


NUL_BODIES = [
    pytest.param(
        "/api/v1/admin/content/emergency",
        {"text": "a\x00b"},
        ContentKey.EMERGENCY,
        id="emergency-text",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "https://example.com/a\x00b", "button_text": "ОК"},
        ContentKey.PAYMENT,
        id="payment-url",
    ),
    pytest.param(
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "https://example.com/pay", "button_text": "a\x00b"},
        ContentKey.PAYMENT,
        id="payment-button-text",
    ),
    pytest.param(
        "/api/v1/admin/content/contacts",
        {"text": "Контакты", "phones": [{"title": "a\x00b", "phone": "+7"}]},
        ContentKey.CONTACTS,
        id="contacts-title",
    ),
    pytest.param(
        "/api/v1/admin/content/theme",
        {"company_name": "a\x00b", "primary_color": "#1E88E5"},
        ContentKey.THEME,
        id="theme-company-name",
    ),
]


@pytest.mark.parametrize(("path", "payload", "key"), NUL_BODIES)
async def test_put_nul_returns_422_and_keeps_block(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    path: str,
    payload: dict,
    key: ContentKey,
) -> None:
    await _seed_blocks(db)

    resp = await client.put(path, json=payload, headers=_auth(base.admin_token))

    assert resp.status_code == 422
    stored = await _stored(db, key)
    assert stored is not None
    assert stored.data == BLOCKS[key]


async def _create_question_ticket(db: AsyncSession, base: SimpleNamespace):
    ticket = await TicketRepository(db).create(
        type=TicketType.QUESTION,
        status=TicketStatus.NEW,
        client_id=base.client.id,
        description="Вопрос",
    )
    await db.commit()
    return ticket


async def test_put_welcome_unknown_file_returns_400(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "Привет", "file_id": 999999},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": CONTENT_IMAGE_NOT_FOUND}
    assert await _stored(db, ContentKey.WELCOME) is None


async def test_put_welcome_ticket_photo_returns_400(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    ticket = await _create_question_ticket(db, base)
    file = await FileService(db, storage).save(
        PNG, "image/png", original_name="photo.png", ticket_id=ticket.id
    )

    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "Привет", "file_id": file.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": CONTENT_IMAGE_NOT_FOUND}
    assert await _stored(db, ContentKey.WELCOME) is None


async def test_put_welcome_message_file_returns_400(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    ticket = await _create_question_ticket(db, base)
    message = await MessageRepository(db).create(
        ticket.id, SenderType.CLIENT, author_id=base.client.id, text="Фото"
    )
    await db.commit()
    file = await FileService(db, storage).save(
        PNG,
        "image/png",
        original_name="photo.png",
        ticket_id=ticket.id,
        message_id=message.id,
    )

    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "Привет", "file_id": file.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": CONTENT_IMAGE_NOT_FOUND}
    assert await _stored(db, ContentKey.WELCOME) is None


async def test_put_welcome_pdf_content_file_returns_400(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    file = await FileService(db, storage).save(
        b"%PDF-1.7", "application/pdf", original_name="act.pdf"
    )

    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "Привет", "file_id": file.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": CONTENT_IMAGE_NOT_FOUND}
    assert await _stored(db, ContentKey.WELCOME) is None


async def test_put_welcome_valid_image_succeeds(
    client: AsyncClient, base: SimpleNamespace, content_image: File
) -> None:
    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "Привет", "file_id": content_image.id},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 200


async def test_put_theme_unknown_logo_returns_400(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    resp = await client.put(
        "/api/v1/admin/content/theme",
        json={"company_name": "УК", "primary_color": "#1E88E5", "logo_file_id": 999999},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": CONTENT_IMAGE_NOT_FOUND}
    assert await _stored(db, ContentKey.THEME) is None


async def test_put_does_not_overwrite_on_file_error(
    client: AsyncClient, db: AsyncSession, base: SimpleNamespace
) -> None:
    await _seed_blocks(db)

    resp = await client.put(
        "/api/v1/admin/content/welcome",
        json={"text": "Новое", "file_id": 999999},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    stored = await _stored(db, ContentKey.WELCOME)
    assert stored is not None
    assert stored.data == BLOCKS[ContentKey.WELCOME]


async def test_upload_png_creates_content_file(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    resp = await client.post(
        "/api/v1/admin/content/images", files=_png_file(), headers=_auth(base.admin_token)
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["mime"] == "image/png"
    assert body["size"] == len(PNG)
    assert body["original_name"] == "logo.png"

    db.expire_all()
    file = await db.get(File, body["id"])
    assert file is not None
    assert file.ticket_id is None
    assert file.message_id is None

    download = await client.get(body["url"])
    assert download.status_code == 200
    assert download.content == PNG


async def test_upload_jpeg_creates_content_file(
    client: AsyncClient, base: SimpleNamespace, storage: LocalStorageProvider
) -> None:
    resp = await client.post(
        "/api/v1/admin/content/images",
        files={"file": ("photo.jpg", JPEG, "application/octet-stream")},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 201
    assert resp.json()["mime"] == "image/jpeg"


async def test_upload_text_as_image_returns_400(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.post(
        "/api/v1/admin/content/images",
        files={"file": ("a.png", b"not an image", "image/png")},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": CONTENT_IMAGE_FORMAT}


async def test_upload_gif_returns_400(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.post(
        "/api/v1/admin/content/images",
        files={"file": ("a.gif", GIF, "image/gif")},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": CONTENT_IMAGE_FORMAT}


async def test_upload_empty_file_returns_400(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.post(
        "/api/v1/admin/content/images",
        files={"file": ("a.png", b"", "image/png")},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 400


async def test_upload_too_large_returns_413(
    client: AsyncClient,
    base: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.services.file_service.MAX_FILE_SIZE", 8)
    monkeypatch.setattr("src.api.v1.admin.content.MAX_FILE_SIZE", 8)

    resp = await client.post(
        "/api/v1/admin/content/images",
        files={"file": ("big.png", b"0123456789", "image/png")},
        headers=_auth(base.admin_token),
    )

    assert resp.status_code == 413


async def test_upload_nul_filename_is_normalized(
    client: AsyncClient,
    db: AsyncSession,
    base: SimpleNamespace,
    storage: LocalStorageProvider,
) -> None:
    body, extra_headers = _multipart("a\x00b.png", PNG)

    resp = await client.post(
        "/api/v1/admin/content/images",
        content=body,
        headers={**_auth(base.admin_token), **extra_headers},
    )

    assert resp.status_code == 201
    assert resp.json()["original_name"] == "ab.png"

    db.expire_all()
    file = await db.get(File, resp.json()["id"])
    assert file is not None
    assert file.original_name == "ab.png"


async def test_upload_without_file_returns_422(client: AsyncClient, base: SimpleNamespace) -> None:
    resp = await client.post("/api/v1/admin/content/images", headers=_auth(base.admin_token))

    assert resp.status_code == 422


ADMIN_ROUTES = [
    pytest.param("GET", "/api/v1/admin/content", None, None, id="get"),
    pytest.param(
        "PUT",
        "/api/v1/admin/content/welcome",
        {"text": "Привет", "file_id": 1},
        None,
        id="welcome",
    ),
    pytest.param("PUT", "/api/v1/admin/content/emergency", {"text": "Пожар"}, None, id="emergency"),
    pytest.param("PUT", "/api/v1/admin/content/services", {"text": "Услуги"}, None, id="services"),
    pytest.param(
        "PUT",
        "/api/v1/admin/content/payment",
        {"text": "Оплата", "url": "https://example.com", "button_text": "ОК"},
        None,
        id="payment",
    ),
    pytest.param(
        "PUT",
        "/api/v1/admin/content/contacts",
        {"text": "Контакты", "phones": []},
        None,
        id="contacts",
    ),
    pytest.param(
        "PUT",
        "/api/v1/admin/content/theme",
        {"company_name": "УК", "primary_color": "#1E88E5"},
        None,
        id="theme",
    ),
    pytest.param("POST", "/api/v1/admin/content/images", None, _png_file(), id="images"),
]


async def _request(
    client: AsyncClient,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
    files: dict | None = None,
):
    if method == "GET":
        return await client.get(path, headers=headers)
    if method == "PUT":
        return await client.put(path, json=payload, headers=headers)
    return await client.post(path, files=files, headers=headers)


@pytest.mark.parametrize(("method", "path", "payload", "files"), ADMIN_ROUTES)
async def test_admin_content_requires_token(
    client: AsyncClient, method: str, path: str, payload: dict | None, files: dict | None
) -> None:
    resp = await _request(client, method, path, payload=payload, files=files)

    assert resp.status_code == 401


@pytest.mark.parametrize("role", ["client", "manager"])
@pytest.mark.parametrize(("method", "path", "payload", "files"), ADMIN_ROUTES)
async def test_admin_content_forbidden_for_non_admin(
    client: AsyncClient,
    base: SimpleNamespace,
    role: str,
    method: str,
    path: str,
    payload: dict | None,
    files: dict | None,
) -> None:
    token = base.client_token if role == "client" else base.manager_token

    resp = await _request(client, method, path, headers=_auth(token), payload=payload, files=files)

    assert resp.status_code == 403


@pytest.mark.parametrize(("method", "path", "payload", "files"), ADMIN_ROUTES)
async def test_admin_content_forbidden_for_blocked_admin(
    client: AsyncClient,
    base: SimpleNamespace,
    method: str,
    path: str,
    payload: dict | None,
    files: dict | None,
) -> None:
    resp = await _request(
        client, method, path, headers=_auth(base.blocked_token), payload=payload, files=files
    )

    assert resp.status_code == 403
