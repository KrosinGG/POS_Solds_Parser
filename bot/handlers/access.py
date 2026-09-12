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
        await callback.answer("Только главный администратор имеет доступ к этому разделу", show_alert=True)
        return

    users_count = len(security_manager.get_allowed_users())
    text = (
        "👥 <b>УПРАВЛЕНИЕ ДОСТУПОМ ПОЛЬЗОВАТЕЛЕЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Авторизовано пользователей: <b>{users_count} чел.</b>\n\n"
        "Здесь вы можете добавить или удалить Telegram ID коллег, которым разрешено использовать парсер."
    )
    await callback.message.edit_text(text, reply_markup=get_access_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "list_users")
async def callback_list_users(callback: CallbackQuery):
    if not security_manager.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    users_detailed = security_manager.get_users_detailed()
    user_blocks = []

    for idx, u in enumerate(users_detailed, start=1):
        uid = u["user_id"]
        is_adm = security_manager.is_admin(uid)
        role_title = "👑 <b>Главный администратор</b>" if is_adm else "👤 <b>Доверенный пользователь</b>"

        # Имя и фамилия
        f_name = u.get("first_name", "").strip()
        l_name = u.get("last_name", "").strip()
        full_name = f"{f_name} {l_name}".strip() if (f_name or l_name) else "<i>(будет определено при входе)</i>"

        # Юзернейм
        username = u.get("username", "").strip()
        username_str = f"@{username}" if username else "<i>не указан</i>"

        block = (
            f"<b>{idx}.</b> {role_title}\n"
            f"   👤 Имя / Фамилия: <b>{full_name}</b>\n"
            f"   🏷 Юзернейм: <b>{username_str}</b>\n"
            f"   🆔 Telegram ID: <code>{uid}</code>"
        )
        user_blocks.append(block)

    users_text = "\n\n".join(user_blocks) if user_blocks else "Список пуст."
    text = (
        f"👥 <b>СПИСОК АВТОРИЗОВАННЫХ ПОЛЬЗОВАТЕЛЕЙ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{users_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Всего пользователей: <b>{len(users_detailed)}</b>"
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
        "➕ <b>ДОБАВЛЕНИЕ НОВОГО ПОЛЬЗОВАТЕЛЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Отправьте числовой <b>Telegram ID</b> пользователя (например, <code>987654321</code>):\n\n"
        "💡 <i>Узнать свой Telegram ID пользователь может в боте @userinfobot</i>"
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

    # Пробуем запросить данные профиля через Telegram API
    first_name = ""
    last_name = ""
    username = ""
    try:
        chat = await message.bot.get_chat(new_uid)
        first_name = chat.first_name or ""
        last_name = chat.last_name or ""
        username = chat.username or ""
    except Exception:
        pass

    success = security_manager.add_user(
        user_id=new_uid,
        first_name=first_name,
        last_name=last_name,
        username=username
    )
    await state.clear()

    full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else "Ожидает первого входа"
    username_display = f"@{username}" if username else "Не указан"

    if success:
        result_msg = (
            f"✅ <b>Пользователь успешно добавлен!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Имя / Фамилия: <b>{full_name}</b>\n"
            f"🏷 Юзернейм: <b>{username_display}</b>\n"
            f"🆔 Telegram ID: <code>{new_uid}</code>"
        )
    else:
        result_msg = f"ℹ️ Пользователь с Telegram ID <code>{new_uid}</code> уже имеет доступ."

    await message.answer(result_msg, parse_mode="HTML")

    text = (
        "👥 <b>УПРАВЛЕНИЕ ДОСТУПОМ ПОЛЬЗОВАТЕЛЕЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите действие ниже:"
    )
    await message.answer(text, reply_markup=get_access_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "remove_user")
async def callback_remove_user(callback: CallbackQuery, state: FSMContext):
    if not security_manager.is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return

    await state.set_state(AccessStates.waiting_for_remove_user_id)
    text = (
        "➖ <b>ОТЗЫВ ДОСТУПА ПОЛЬЗОВАТЕЛЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Отправьте числовой <b>Telegram ID</b>, у которого нужно отозвать доступ к боту:"
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

    text = (
        "👥 <b>УПРАВЛЕНИЕ ДОСТУПОМ ПОЛЬЗОВАТЕЛЕЙ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите действие ниже:"
    )
    await message.answer(text, reply_markup=get_access_keyboard(), parse_mode="HTML")
