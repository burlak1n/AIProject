from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dao import UsersDAO
from app.api.schemas import GetUserDB
from app.api.models import User
from app.dao.session_maker import session_manager


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        user_schema = GetUserDB(telegram_id=event.from_user.id)
        async with session_manager.create_session() as session:
            user: User = await UsersDAO.find_one_or_none(session, user_schema)
        if not user:
            await event.answer("Вы не зарегистрированы, для начала работы введите /start")
            return
        data["user"] = user
        return await handler(event, data)