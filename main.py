import asyncio
from pathlib import Path
from core.config import settings
from core.logger import logger
from bot.bot_instance import create_bot_and_dispatcher


async def main():
    logger.info("========================================")
    logger.info("  POSNext Solds Parser & Telegram Bot   ")
    logger.info("========================================")

    # Валидация базовой конфигурации
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: Не задан TELEGRAM_BOT_TOKEN в файле .env!")
        logger.info("Создайте файл .env на основе .env.example и укажите TELEGRAM_BOT_TOKEN.")
        return

    if settings.ADMIN_TELEGRAM_ID <= 0:
        logger.warning("ВНИМАНИЕ: ADMIN_TELEGRAM_ID не задан в .env. Бот не сможет определить главного администратора.")

    # Проверка наличия директории отчетов
    Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)

    # Проверка наличия venues.txt
    venues_path = Path(settings.VENUES_FILE_PATH)
    if not venues_path.exists():
        logger.warning(f"Файл со списком венью {venues_path} не найден! Создан пустой файл шаблона.")
        venues_path.write_text("# Названия театров/площадок построчно\nWarner Theatre\n", encoding="utf-8")

    bot, dp = create_bot_and_dispatcher()

    logger.info("Успешная инициализация бота. Запуск long polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Работа бота завершена.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
