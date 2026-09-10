from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from core.security import security_manager
from bot.keyboards.main_menu import get_access_keyboard, get_cancel_keyboard, get_back_keyboard
from bot.states.settings import AccessStates

router = Router()


@router.callback_query(F.data == "open_access")
async def callback_open_access(callback: CallbackQuery):
    if not security_manager.is_admin(callback.from_user.id):
        await callback.answer("Только администратор имеет доступ к этому разделу", show_alert=True)
        return

    text = (
        "👥 <b>Управление доступом пользователей</b>\n\n"
        "Здесь вы можете добавить Telegram ID коллег, которым будет разрешен доступ к боту и парсеру."
    )
    await callback.message.edit_text(text, reply_markup=get_access_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "list_users")
async def callback_list_users(callback: CallbackQuery):
    if not security_manager.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    users = security_manager.get_allowed_users()
    lines = []
    for uid in users:
        badge = " (👑 Главный администратор)" if security_manager.is_admin(uid) else ""
        lines.append(f"• <code>{uid}</code>{badge}")

    users_text = "\n".join(lines) if lines else "Список пуст."
    text = (
        f"📋 <b>Список авторизованных Telegram ID:</b>\n\n"
        f"{users_text}\n\n"
        f"Всего пользователей: <b>{len(users)}</b>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("open_access"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "add_user")
async def callback_add_user(callback: CallbackQuery, state: FSMContext):
    if not security_manager.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await state.set_state(AccessStates.waiting_for_add_user_id)
    text = (
        "➕ <b>Добавление пользователя</b>\n\n"
        "Отправьте числовой <b>Telegram ID</b> пользователя (например, <code>987654321</code>):\n"
        "<i>Узнать свой ID пользователь может в боте @userinfobot</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AccessStates.waiting_for_add_user_id)
async def process_add_user(message: Message, state: FSMContext):
    if not security_manager.is_admin(message.from_user.id):
        return

    try:
        new_uid = int(message.text.strip())
        if new_uid <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректный числовой Telegram ID (только цифры):", reply_markup=get_cancel_keyboard())
        return

    success = security_manager.add_user(new_uid)
    await state.clear()

    if success:
        await message.answer(f"✅ Пользователь с Telegram ID <code>{new_uid}</code> успешно добавлен в список разрешенных!", parse_mode="HTML")
    else:
        await message.answer(f"ℹ️ Пользователь с Telegram ID <code>{new_uid}</code> уже есть в списке разрешенных.", parse_mode="HTML")

    text = "👥 <b>Управление доступом пользователей</b>"
    await message.answer(text, reply_markup=get_access_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "remove_user")
async def callback_remove_user(callback: CallbackQuery, state: FSMContext):
    if not security_manager.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await state.set_state(AccessStates.waiting_for_remove_user_id)
    text = (
        "➖ <b>Удаление пользователя</b>\n\n"
        "Отправьте числовой <b>Telegram ID</b>, у которого нужно отозвать доступ:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(AccessStates.waiting_for_remove_user_id)
async def process_remove_user(message: Message, state: FSMContext):
    if not security_manager.is_admin(message.from_user.id):
        return

    try:
        rem_uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный числовой Telegram ID:", reply_markup=get_cancel_keyboard())
        return

    success = security_manager.remove_user(rem_uid)
    await state.clear()

    if success:
        await message.answer(f"✅ Доступ для Telegram ID <code>{rem_uid}</code> успешно отозван.", parse_mode="HTML")
    else:
        await message.answer(f"❌ Не удалось удалить <code>{rem_uid}</code> (пользователь не найден или является главным администратором).", parse_mode="HTML")

    text = "👥 <b>Управление доступом пользователей</b>"
    await message.answer(text, reply_markup=get_access_keyboard(), parse_mode="HTML")
