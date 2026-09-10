from typing import Optional
from core.config import settings


class AppState:
    """Глобальное состояние параметров парсера для сессии бота."""

    def __init__(self):
        self.from_date: Optional[str] = settings.DEFAULT_FROM_DATE
        self.to_date: Optional[str] = settings.DEFAULT_TO_DATE
        self.min_solds: int = settings.DEFAULT_MIN_SOLDS
        self.is_scanning: bool = False

    def reset(self):
        self.from_date = settings.DEFAULT_FROM_DATE
        self.to_date = settings.DEFAULT_TO_DATE
        self.min_solds = settings.DEFAULT_MIN_SOLDS


app_state = AppState()
