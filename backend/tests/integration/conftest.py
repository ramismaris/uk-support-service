import os
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.models  # noqa: F401
from src.core.config import settings
from src.db.base import Base
from src.db.session import get_db
from src.main import app

_TEST_DB_HOST = os.getenv("TEST_DATABASE_HOST", "localhost")
_TEST_DB_NAME = f"{settings.database_name}_test"
_TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.database_user}:{settings.database_password}"
    f"@{_TEST_DB_HOST}:{settings.database_port}/{_TEST_DB_NAME}"
)
_ADMIN_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.database_user}:{settings.database_password}"
    f"@{_TEST_DB_HOST}:{settings.database_port}/postgres"
)

_engine = create_async_engine(_TEST_DATABASE_URL, echo=False)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)


async def _create_test_database() -> None:
    admin_engine = create_async_engine(_ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": _TEST_DB_NAME},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))
    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncIterator[None]:
    await _create_test_database()
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_db() -> AsyncIterator[None]:
    yield
    async with _SessionFactory() as session, session.begin():
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())


@pytest_asyncio.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with _SessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with _SessionFactory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
