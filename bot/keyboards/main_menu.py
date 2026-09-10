from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🚀 Запустить парсинг", callback_data="run_parser")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки фильтров", callback_data="open_settings"),
            InlineKeyboardButton(text="📁 Список венью", callback_data="view_venues")
        ]
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="👥 Управление доступом", callback_data="open_access")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_keyboard(
    from_date: Optional[str],
    to_date: Optional[str],
    min_solds: int
) -> InlineKeyboardMarkup:
    from_label = from_date if from_date else "Не задано (Все)"
    to_label = to_date if to_date else "Не задано (Все)"

    buttons = [
        [
            InlineKeyboardButton(text=f"📅 Дата 'От': {from_label}", callback_data="set_from_date")
        ],
        [
            InlineKeyboardButton(text=f"📅 Дата 'До': {to_label}", callback_data="set_to_date")
        ],
        [
            InlineKeyboardButton(text=f"🔥 Мин. Sold: {min_solds}", callback_data="set_min_solds")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить фильтры", callback_data="reset_filters")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_access_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="➕ Добавить Telegram ID", callback_data="add_user"),
            InlineKeyboardButton(text="➖ Удалить Telegram ID", callback_data="remove_user")
        ],
        [
            InlineKeyboardButton(text="📋 Список пользователей", callback_data="list_users")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )


def get_back_keyboard(target: str = "back_to_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=target)]
        ]
    )
