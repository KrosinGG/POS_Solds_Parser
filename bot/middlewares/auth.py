from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from core.security import security_manager
from core.logger import logger


class AuthMiddleware(BaseMiddleware):
    """Middleware для строгой проверки доступа к боту по Telegram ID."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        user_id = user.id

        if not security_manager.is_allowed(user_id):
            logger.warning(f"Попытка несанкционированного доступа: user_id={user_id}, username={user.username}")
            denial_text = (
                f"⛔ <b>Доступ запрещен</b>\n\n"
                f"Ваш Telegram ID: <code>{user_id}</code>\n"
                f"Для получения доступа обратитесь к администратору."
            )
            if isinstance(event, Message):
                await event.answer(denial_text, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещен", show_alert=True)
                if event.message:
                    await event.message.answer(denial_text, parse_mode="HTML")
            return

        return await handler(event, data)
