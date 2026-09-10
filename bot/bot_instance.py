from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from core.config import settings
from bot.middlewares.auth import AuthMiddleware
from bot.handlers import start, settings as settings_handlers, access, run


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация middleware строгой авторизации пользователей
    auth_middleware = AuthMiddleware()
    dp.message.outer_middleware(auth_middleware)
    dp.callback_query.outer_middleware(auth_middleware)

    # Регистрация маршрутов (хэндлеров)
    dp.include_router(start.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(access.router)
    dp.include_router(run.router)

    return bot, dp
