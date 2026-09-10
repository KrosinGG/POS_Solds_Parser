import asyncio
import time
from typing import List
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from core.logger import logger
from services.exporter import ExcelExporter
from services.parser import SoldsParserService
from services.posnext.models import ParsedShow
from bot.keyboards.main_menu import get_back_keyboard, get_main_keyboard
from core.security import security_manager
from bot.user_state import app_state

router = Router()


def make_progress_bar(current: int, total: int, length: int = 12) -> str:
    if total <= 0:
        return ""
    fraction = min(1.0, current / total)
    filled = int(fraction * length)
    bar = "█" * filled + "░" * (length - filled)
    percent = int(fraction * 100)
    return f"[{bar}] {percent}%"


@router.callback_query(F.data == "view_venues")
async def callback_view_venues(callback: CallbackQuery):
    parser = SoldsParserService()
    venues = parser.load_venues()

    if not venues:
        text = (
            "⚠️ <b>Файл площадок пуст или не найден!</b>\n\n"
            "Убедитесь, что в корне проекта создан файл <code>venues.txt</code> с названиями театров построчно."
        )
    else:
        preview = venues[:25]
        preview_lines = [f"{i}. {name}" for i, name in enumerate(preview, start=1)]
        venues_str = "\n".join(preview_lines)
        more = f"\n<i>... и еще {len(venues) - 25} площадок</i>" if len(venues) > 25 else ""

        text = (
            f"📁 <b>Список площадок (файл <code>venues.txt</code>):</b>\n\n"
            f"Всего загружено: <b>{len(venues)}</b> венью\n\n"
            f"{venues_str}{more}"
        )

    await callback.message.edit_text(text, reply_markup=get_back_keyboard("back_to_main"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "run_parser")
async def callback_run_parser(callback: CallbackQuery):
    if app_state.is_scanning:
        await callback.answer("⏳ Парсинг уже запущен в фоновом режиме. Дождитесь окончания!", show_alert=True)
        return

    parser = SoldsParserService()
    venues = parser.load_venues()

    if not venues:
        await callback.message.answer(
            "❌ <b>Список венью пуст!</b> Проверьте файл <code>venues.txt</code> в корне проекта.",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    app_state.is_scanning = True
    await callback.answer()

    total_venues = len(venues)
    last_update_time = time.time()

    # Стартовое сообщение прогресса
    status_msg = await callback.message.answer(
        f"🚀 <b>Запуск сканирования POSNext...</b>\n\n"
        f"🏛 Площадок к обработке: <b>{total_venues}</b>\n"
        f"⚙️ Фильтры: От <code>{app_state.from_date or 'Все'}</code> | До <code>{app_state.to_date or 'Все'}</code> | Sold ≥ <b>{app_state.min_solds}</b>\n\n"
        f"⏳ Подключение к POSNext API...",
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
            f"⚡ <b>Идет сбор данных POSNext...</b>\n\n"
            f"📊 Прогресс: <b>{idx}/{total}</b> {bar}\n"
            f"🏛 Текущая площадка: <code>{venue_name}</code>\n"
            f"🎯 Найдено подходящих шоу: <b>{match_count}</b> шт."
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
                f"🏁 <b>Парсинг завершен!</b>\n\n"
                f"🏛 Обработано площадок: <b>{total_venues}</b>\n"
                f"ℹ️ Подходящих шоу по заданным фильтрам (Sold ≥ {app_state.min_solds}) не найдено."
            )
            await status_msg.edit_text(result_text, parse_mode="HTML")
            return

        # Генерация Excel отчета
        exporter = ExcelExporter()
        report_path = exporter.export(all_shows)

        top_lines = []
        for rank, s in enumerate(top_3, start=1):
            venue_desc = f"{s.venue} ({s.city_state})" if s.city_state else s.venue
            top_lines.append(
                f"<b>{rank}. {s.event_name}</b>\n"
                f"   🏛 Площадка: <code>{venue_desc}</code>\n"
                f"   📅 Дата: <code>{s.event_datetime_str}</code>\n"
                f"   🔥 Sold: <b>{s.sold_count}</b> шт. | 🎟 Active On Hand: <b>{s.active_on_hand}</b> листингов"
            )

        top_3_block = "\n\n".join(top_lines)

        summary_text = (
            f"✅ <b>Парсинг успешно завершен!</b>\n\n"
            f"🏛 Обработано площадок: <b>{total_venues}</b> шт.\n"
            f"🎯 Всего найдено подходящих шоу: <b>{len(all_shows)}</b> шт.\n\n"
            f"🏆 <b>ТОП-3 ШОУ ПО КОЛИЧЕСТВУ СОЛДОВ:</b>\n\n"
            f"{top_3_block}\n\n"
            f"📊 <i>Полная таблица со всеми {len(all_shows)} шоу прикреплена в файле ниже.</i>"
        )

        await status_msg.edit_text(summary_text, parse_mode="HTML")

        # 2. Отправляем Excel файл
        document = FSInputFile(str(report_path), filename=report_path.name)
        await callback.message.answer_document(
            document=document,
            caption=f"📈 Отчет по солдам POSNext ({len(all_shows)} шоу, фильтр Sold ≥ {app_state.min_solds})"
        )

    except Exception as e:
        logger.error(f"Критический сбой во время парсинга: {e}")
        await status_msg.edit_text(
            f"❌ <b>Произошла ошибка при выполнении парсинга:</b>\n<code>{e}</code>",
            parse_mode="HTML"
        )
    finally:
        app_state.is_scanning = False
