import logging
from typing import Any

from maxapi.filters.middleware import BaseMiddleware, HandlerCallable
from maxapi.types import BotStarted, MessageCallback, MessageCreated, UpdateUnion, User

from src.db.session import AsyncSessionLocal
from src.services.user_service import UserService

logger = logging.getLogger(__name__)


def _get_user(event: UpdateUnion) -> User | None:
    if isinstance(event, MessageCreated):
        return event.message.sender
    if isinstance(event, BotStarted):
        return event.user
    if isinstance(event, MessageCallback):
        return event.callback.user
    return None


class UserSyncMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: HandlerCallable,
        event_object: UpdateUnion,
        data: dict[str, Any],
    ) -> Any:
        sender = _get_user(event_object)
        if sender is None:
            return await handler(event_object, data)

        async with AsyncSessionLocal() as db:
            user = await UserService(db).sync_from_max(
                max_user_id=sender.user_id,
                first_name=sender.first_name,
                last_name=sender.last_name,
                username=sender.username,
            )
            if user.is_blocked:
                logger.debug("Skipped update from blocked user max_user_id=%s", sender.user_id)
                return None

            data["db"] = db
            data["user"] = user
            return await handler(event_object, data)
