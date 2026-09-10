from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from services.parser import parse_user_date
from bot.keyboards.main_menu import get_settings_keyboard, get_cancel_keyboard
from bot.states.settings import FilterStates
from bot.user_state import app_state

router = Router()


def get_settings_text() -> str:
    from_lbl = app_state.from_date if app_state.from_date else "Не задано (Все события)"
    to_lbl = app_state.to_date if app_state.to_date else "Не задано (Все события)"

    text = (
        f"⚙️ <b>Настройки параметров парсера</b>\n\n"
        f"• <b>Дата 'От':</b> <code>{from_lbl}</code>\n"
        f"• <b>Дата 'До':</b> <code>{to_lbl}</code>\n"
        f"• <b>Минимум Sold:</b> <b>{app_state.min_solds}</b> шт.\n\n"
        f"Нажмите на соответствующую кнопку для изменения:"
    )
    return text


@router.callback_query(F.data == "open_settings")
async def callback_open_settings(callback: CallbackQuery):
    text = get_settings_text()
    markup = get_settings_keyboard(app_state.from_date, app_state.to_date, app_state.min_solds)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "set_from_date")
async def callback_set_from_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterStates.waiting_for_from_date)
    text = (
        "📅 <b>Введите начальную дату</b>\n\n"
        "Формат: <code>MM.DD.YY</code> (например, <code>10.16.26</code>).\n"
        "<i>Все шоу до этой даты будут пропущены.</i>\n\n"
        "Для сброса (без ограничений) отправьте <code>-</code> или <code>все</code>."
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(FilterStates.waiting_for_from_date)
async def process_from_date(message: Message, state: FSMContext):
    text = message.text.strip()
    if text in ["-", "все", "all", "0"]:
        app_state.from_date = None
        await state.clear()
        await message.answer("✅ Фильтр начальной даты сброшен (все события).")
    else:
        parsed = parse_user_date(text)
        if not parsed:
            await message.answer(
                "❌ Неверный формат даты! Введите дату в формате <code>10.16.26</code> или отправьте <code>-</code> для сброса:",
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            return
        app_state.from_date = text
        await state.clear()
        await message.answer(f"✅ Установлена дата 'От': <code>{text}</code> ({parsed.strftime('%d.%m.%Y')})", parse_mode="HTML")

    msg_text = get_settings_text()
    markup = get_settings_keyboard(app_state.from_date, app_state.to_date, app_state.min_solds)
    await message.answer(msg_text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data == "set_to_date")
async def callback_set_to_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterStates.waiting_for_to_date)
    text = (
        "📅 <b>Введите конечную дату</b>\n\n"
        "Формат: <code>MM.DD.YY</code> (например, <code>11.20.26</code>).\n"
        "<i>Все шоу после этой даты будут пропущены.</i>\n\n"
        "Для сброса (до бесконечности) отправьте <code>-</code> или <code>все</code>."
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(FilterStates.waiting_for_to_date)
async def process_to_date(message: Message, state: FSMContext):
    text = message.text.strip()
    if text in ["-", "все", "all", "0"]:
        app_state.to_date = None
        await state.clear()
        await message.answer("✅ Фильтр конечной даты сброшен (все события).")
    else:
        parsed = parse_user_date(text)
        if not parsed:
            await message.answer(
                "❌ Неверный формат даты! Введите дату в формате <code>MM.DD.YY</code> или отправьте <code>-</code> для сброса:",
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            return
        app_state.to_date = text
        await state.clear()
        await message.answer(f"✅ Установлена дата 'До': <code>{text}</code> ({parsed.strftime('%d.%m.%Y')})", parse_mode="HTML")

    msg_text = get_settings_text()
    markup = get_settings_keyboard(app_state.from_date, app_state.to_date, app_state.min_solds)
    await message.answer(msg_text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data == "set_min_solds")
async def callback_set_min_solds(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FilterStates.waiting_for_min_solds)
    text = (
        "🔥 <b>Введите минимальное количество Sold</b>\n\n"
        "Например, <code>10</code>.\n"
        "<i>Шоу, у которых меньше этого количества солдов, будут проигнорированы.</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(FilterStates.waiting_for_min_solds)
async def process_min_solds(message: Message, state: FSMContext):
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите целое неотрицательное число (например, 10):", reply_markup=get_cancel_keyboard())
        return

    app_state.min_solds = val
    await state.clear()
    await message.answer(f"✅ Установлен порог солдов: <b>{val}</b>", parse_mode="HTML")

    msg_text = get_settings_text()
    markup = get_settings_keyboard(app_state.from_date, app_state.to_date, app_state.min_solds)
    await message.answer(msg_text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data == "reset_filters")
async def callback_reset_filters(callback: CallbackQuery):
    app_state.reset()
    text = "🔄 Фильтры сброшены к значениям по умолчанию.\n\n" + get_settings_text()
    markup = get_settings_keyboard(app_state.from_date, app_state.to_date, app_state.min_solds)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer("Сброшено")
