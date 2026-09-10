from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from core.security import security_manager
from services.parser import SoldsParserService
from bot.keyboards.main_menu import get_main_keyboard
from bot.user_state import app_state

router = Router()


def get_welcome_text(user_id: int) -> str:
    parser = SoldsParserService()
    venues = parser.load_venues()
    is_admin = security_manager.is_admin(user_id)
    role_badge = "👑 Администратор" if is_admin else "👤 Пользователь"

    from_label = app_state.from_date if app_state.from_date else "Все события"
    to_label = app_state.to_date if app_state.to_date else "Все события"

    text = (
        f"👋 <b>POSNext Solds Parser Bot</b>\n\n"
        f"Ваш статус: {role_badge}\n"
        f"🏛 Загружено площадок: <b>{len(venues)}</b> шт. (файл <code>venues.txt</code>)\n\n"
        f"<b>Текущие параметры фильтрации:</b>\n"
        f"• Дата 'От': <code>{from_label}</code>\n"
        f"• Дата 'До': <code>{to_label}</code>\n"
        f"• Минимально Sold: <b>{app_state.min_solds}</b>\n"
        f"• Метрика Active On Hand: <i>листинги с тегами R, Drop, Jump (On Hand)</i>\n\n"
        f"Выберите действие ниже:"
    )
    return text


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_admin = security_manager.is_admin(message.from_user.id)
    text = get_welcome_text(message.from_user.id)
    await message.answer(text, reply_markup=get_main_keyboard(is_admin), parse_mode="HTML")


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = security_manager.is_admin(callback.from_user.id)
    text = get_welcome_text(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=get_main_keyboard(is_admin), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_main_keyboard(is_admin), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def callback_cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = security_manager.is_admin(callback.from_user.id)
    text = "Действие отменено.\n\n" + get_welcome_text(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=get_main_keyboard(is_admin), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_main_keyboard(is_admin), parse_mode="HTML")
    await callback.answer()
