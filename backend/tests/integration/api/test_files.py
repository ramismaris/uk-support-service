from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import build_file_url, sign_file_link
from src.main import app
from src.providers.factory import get_storage_provider
from src.providers.local_storage_provider import LocalStorageProvider
from src.services.file_service import FileService


@pytest.fixture
def storage(tmp_path) -> LocalStorageProvider:
    provider = LocalStorageProvider(str(tmp_path))
    app.dependency_overrides[get_storage_provider] = lambda: provider
    return provider


async def test_download_by_signed_link(
    client: AsyncClient, db: AsyncSession, storage: LocalStorageProvider
):
    file = await FileService(db, storage).save(b"hello", "image/png", original_name="a.png")

    resp = await client.get(build_file_url(file.id, datetime.now(UTC)))

    assert resp.status_code == 200
    assert resp.content == b"hello"
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["cache-control"] == "private, max-age=3600"
    assert resp.headers["content-security-policy"] == (
        "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    )
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["content-disposition"] == "inline"


async def test_html_file_is_served_as_attachment(
    client: AsyncClient, db: AsyncSession, storage: LocalStorageProvider
):
    file = await FileService(db, storage).save(
        b"<script>alert(1)</script>", "text/html", original_name="страница.html"
    )

    resp = await client.get(build_file_url(file.id, datetime.now(UTC)))

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    assert resp.headers["content-disposition"] == (
        "attachment; filename*=UTF-8''%D1%81%D1%82%D1%80%D0%B0%D0%BD%D0%B8%D1%86%D0%B0.html"
    )
    assert resp.headers["x-content-type-options"] == "nosniff"


async def test_image_is_served_inline(
    client: AsyncClient, db: AsyncSession, storage: LocalStorageProvider
):
    file = await FileService(db, storage).save(b"img", "image/jpeg", original_name="photo.jpg")

    resp = await client.get(build_file_url(file.id, datetime.now(UTC)))

    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == "inline"


async def test_tampered_signature_returns_403(
    client: AsyncClient, db: AsyncSession, storage: LocalStorageProvider
):
    file = await FileService(db, storage).save(b"hello", "image/png")
    expires_at = int((datetime.now(UTC) + timedelta(minutes=30)).timestamp())
    sig = sign_file_link(file.id, expires_at)
    tampered = ("0" if sig[0] != "0" else "1") + sig[1:]

    resp = await client.get(f"/api/v1/files/{file.id}", params={"exp": expires_at, "sig": tampered})

    assert resp.status_code == 403


async def test_expired_link_returns_403(
    client: AsyncClient, db: AsyncSession, storage: LocalStorageProvider
):
    file = await FileService(db, storage).save(b"hello", "image/png")
    past = datetime.now(UTC) - timedelta(hours=2)

    resp = await client.get(build_file_url(file.id, past))

    assert resp.status_code == 403


async def test_valid_link_for_missing_file_returns_404(
    client: AsyncClient, storage: LocalStorageProvider
):
    resp = await client.get(build_file_url(999_999, datetime.now(UTC)))

    assert resp.status_code == 404
