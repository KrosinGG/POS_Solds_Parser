import asyncio
import math
import time
from pathlib import Path
from typing import List
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from core.logger import logger
from services.exporter import ExcelExporter
from services.parser import SoldsParserService
from services.posnext.models import ParsedShow
from bot.keyboards.main_menu import (
    get_back_keyboard,
    get_main_keyboard,
    get_venues_pagination_keyboard
)
from core.security import security_manager
from bot.user_state import app_state

router = Router()

VENUES_PER_PAGE = 10


def make_progress_bar(current: int, total: int, length: int = 12) -> str:
    if total <= 0:
        return ""
    fraction = min(1.0, current / total)
    filled = int(fraction * length)
    bar = "█" * filled + "░" * (length - filled)
    percent = int(fraction * 100)
    return f"[{bar}] {percent}%"


@router.callback_query(F.data.startswith("venues_page:") | (F.data == "view_venues"))
async def callback_view_venues_page(callback: CallbackQuery):
    parser = SoldsParserService()
    venues = parser.load_venues()

    if not venues:
        text = (
            "⚠️ <b>Файл площадок пуст или не найден!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Убедитесь, что в корне проекта создан файл <code>venues.txt</code> с названиями площадок построчно."
        )
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("back_to_main"), parse_mode="HTML")
        await callback.answer()
        return

    # Определяем запрашиваемую страницу
    total_venues = len(venues)
    total_pages = max(1, math.ceil(total_venues / VENUES_PER_PAGE))

    page = 1
    if callback.data.startswith("venues_page:"):
        try:
            page = int(callback.data.split(":")[1])
        except (IndexError, ValueError):
            page = 1

    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * VENUES_PER_PAGE
    end_idx = min(start_idx + VENUES_PER_PAGE, total_venues)
    page_venues = venues[start_idx:end_idx]

    lines = [f"<b>{start_idx + i}.</b> {name}" for i, name in enumerate(page_venues, start=1)]
    venues_text = "\n".join(lines)

    text = (
        f"🏛 <b>СПИСОК ПЛОЩАДОК</b> (Стр. <b>{page}</b> из <b>{total_pages}</b>)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{venues_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Всего в базе: <b>{total_venues}</b> площадок\n"
        f"💡 <i>Используйте стрелки для перелистывания страниц:</i>"
    )

    markup = get_venues_pagination_keyboard(current_page=page, total_pages=total_pages)
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "download_venues_file")
async def callback_download_venues_file(callback: CallbackQuery):
    venues_path = Path("venues.txt")
    if not venues_path.exists():
        await callback.answer("Файл venues.txt не найден на сервере!", show_alert=True)
        return

    parser = SoldsParserService()
    venues = parser.load_venues()

    document = FSInputFile(str(venues_path), filename="venues.txt")
    await callback.message.answer_document(
        document=document,
        caption=f"📁 <b>Актуальный список театров и площадок</b>\nВсего записей: <b>{len(venues)}</b> шт.",
        parse_mode="HTML"
    )
    await callback.answer("Файл отправлен")


@router.callback_query(F.data == "run_parser")
async def callback_run_parser(callback: CallbackQuery):
    if app_state.is_scanning:
        await callback.answer("⏳ Парсинг уже запущен в фоновом режиме. Дождитесь окончания!", show_alert=True)
        return

    parser = SoldsParserService()
    venues = parser.load_venues()

    if not venues:
        await callback.message.answer(
            "❌ <b>Список венью пуст!</b> Заполните файл <code>venues.txt</code>.",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    app_state.is_scanning = True
    await callback.answer()

    total_venues = len(venues)
    last_update_time = time.time()

    from_lbl = f"✅ {app_state.from_date}" if app_state.from_date else "❌ Все события"
    to_lbl = f"✅ {app_state.to_date}" if app_state.to_date else "❌ Все события"

    # Стартовое сообщение прогресса
    status_msg = await callback.message.answer(
        f"🚀 <b>ЗАПУСК СКАНИРОВАНИЯ POSNEXT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛 Площадок к обработке: <b>{total_venues} шт.</b>\n"
        f"📅 Дата «От»: {from_lbl}\n"
        f"📅 Дата «До»: {to_lbl}\n"
        f"🔥 Порог Sold: <b>от {app_state.min_solds} шт.</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <i>Подключение к POSNext API и авторизация...</i>",
        parse_mode="HTML"
    )

    async def update_progress(idx: int, total: int, venue_name: str, match_count: int):
        nonlocal last_update_time
        now = time.time()
        # Троттлинг: обновляем сообщение не чаще 1 раза в 2.5 секунды во избежание 429 flood control
        if (now - last_update_time < 2.5) and (idx != total):
            return

        last_update_time = now
        bar = make_progress_bar(idx, total)
        text = (
            f"⚡ <b>СКАНИРОВАНИЕ И ОБХОД ПЛОЩАДОК</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Прогресс: <b>{idx}/{total}</b> {bar}\n"
            f"🏛 Текущая площадка: <code>{venue_name}</code>\n"
            f"🎯 Найдено подходящих шоу: <b>{match_count} шт.</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ <i>Пожалуйста, не перезапускайте бот...</i>"
        )
        try:
            await status_msg.edit_text(text, parse_mode="HTML")
        except Exception:
            pass

    try:
        all_shows, top_3 = await parser.run_scan(
            venues=venues,
            from_date_str=app_state.from_date,
            to_date_str=app_state.to_date,
            min_solds=app_state.min_solds,
            progress_callback=update_progress
        )

        # 1. Формируем сообщение с результатами и Топ-3
        if not all_shows:
            result_text = (
                f"🏁 <b>ПАРСИНГ ЗАВЕРШЕН!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏛 Обработано площадок: <b>{total_venues}</b>\n"
                f"ℹ️ <i>Подходящих шоу по заданным критериям (Sold ≥ {app_state.min_solds}) не найдено.</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await status_msg.edit_text(result_text, parse_mode="HTML")
            return

        # Генерация Excel отчета
        exporter = ExcelExporter()
        report_path = exporter.export(all_shows)

        medals = ["🥇", "🥈", "🥉"]
        top_lines = []
        for rank, s in enumerate(top_3, start=1):
            medal = medals[rank - 1] if rank <= 3 else f"#{rank}"
            venue_desc = f"{s.venue} ({s.city_state})" if s.city_state else s.venue
            top_lines.append(
                f"{medal} <b>{rank}. {s.event_name}</b>\n"
                f"   🏛 Площадка: <code>{venue_desc}</code>\n"
                f"   📅 Дата: <code>{s.event_datetime_str}</code>\n"
                f"   🔥 Sold: <b>{s.sold_count}</b> шт. | 🎟 Active On Hand: <b>{s.active_on_hand}</b> листингов"
            )

        top_3_block = "\n\n".join(top_lines)

        summary_text = (
            f"🏁 <b>ПАРСИНГ УСПЕШНО ЗАВЕРШЕН!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏛 Обработано площадок: <b>{total_venues} шт.</b>\n"
            f"🎯 Найдено подходящих шоу: <b>{len(all_shows)} шт.</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 <b>ТОП-3 ШОУ ПО КОЛИЧЕСТВУ СОЛДОВ:</b>\n\n"
            f"{top_3_block}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <i>Полная таблица со всеми {len(all_shows)} шоу прикреплена в файле ниже.</i>"
        )

        await status_msg.edit_text(summary_text, parse_mode="HTML")

        # 2. Отправляем Excel файл
        document = FSInputFile(str(report_path), filename=report_path.name)
        await callback.message.answer_document(
            document=document,
            caption=f"📈 <b>Итоговый отчет POSNext Solds</b>\n🎯 Найдено шоу: <b>{len(all_shows)}</b> | Порог Sold: <b>≥ {app_state.min_solds}</b>",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Критический сбой во время парсинга: {e}")
        await status_msg.edit_text(
            f"❌ <b>Произошла ошибка при выполнении парсинга:</b>\n<code>{e}</code>",
            parse_mode="HTML"
        )
    finally:
        app_state.is_scanning = False
