from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="▶️ Запустить парсинг", callback_data="run_parser")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки фильтров", callback_data="open_settings"),
            InlineKeyboardButton(text="🏛 Список площадок", callback_data="venues_page:1")
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
    from_label = f"✅ {from_date}" if from_date else "❌ Все события"
    to_label = f"✅ {to_date}" if to_date else "❌ Все события"

    buttons = [
        [
            InlineKeyboardButton(text=f"📅 Дата «От»: {from_label}", callback_data="set_from_date")
        ],
        [
            InlineKeyboardButton(text=f"📅 Дата «До»: {to_label}", callback_data="set_to_date")
        ],
        [
            InlineKeyboardButton(text=f"🔥 Порог Sold: от {min_solds} шт.", callback_data="set_min_solds")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить все фильтры", callback_data="reset_filters")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_venues_pagination_keyboard(
    current_page: int,
    total_pages: int
) -> InlineKeyboardMarkup:
    buttons = []

    # Навигационная строка пагинации
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"venues_page:{current_page - 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="▫️", callback_data="noop"))

    nav_row.append(InlineKeyboardButton(text=f"📄 {current_page} / {total_pages}", callback_data="noop"))

    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"venues_page:{current_page + 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="▫️", callback_data="noop"))

    buttons.append(nav_row)

    # Кнопка скачивания файла
    buttons.append([
        InlineKeyboardButton(text="📥 Скачать venues.txt", callback_data="download_venues_file")
    ])

    # Кнопка возврата
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_access_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="add_user"),
            InlineKeyboardButton(text="➖ Удалить пользователя", callback_data="remove_user")
        ],
        [
            InlineKeyboardButton(text="📋 Список пользователей", callback_data="list_users")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")
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
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=target)]
        ]
    )
