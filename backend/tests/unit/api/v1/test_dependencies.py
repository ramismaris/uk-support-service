from unittest.mock import MagicMock

import pytest

from src.api.v1.dependencies import require_admin, require_staff
from src.core.constants import UserRole
from src.core.exceptions import ForbiddenException


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.ADMIN])
async def test_require_staff_allows_staff(role: UserRole):
    user = MagicMock(role=role)

    assert await require_staff(user) is user


async def test_require_staff_rejects_client():
    with pytest.raises(ForbiddenException):
        await require_staff(MagicMock(role=UserRole.CLIENT))


async def test_require_admin_allows_admin():
    user = MagicMock(role=UserRole.ADMIN)

    assert await require_admin(user) is user


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.CLIENT])
async def test_require_admin_rejects_non_admin(role: UserRole):
    with pytest.raises(ForbiddenException):
        await require_admin(MagicMock(role=role))
