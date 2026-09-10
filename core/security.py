import json
from pathlib import Path
from typing import Set
from core.config import settings
from core.logger import logger


class SecurityManager:
    """Управление списком разрешенных пользователей Telegram."""

    def __init__(self, filepath: str = settings.ALLOWED_USERS_FILE_PATH):
        self.filepath = Path(filepath)
        self._allowed_users: Set[int] = set()
        self._load()

    def _load(self) -> None:
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._allowed_users = set(int(uid) for uid in data)
            except Exception as e:
                logger.error(f"Ошибка при чтении {self.filepath}: {e}")
                self._allowed_users = set()

        # Always guarantee ADMIN_TELEGRAM_ID is in the allowed set if configured
        if settings.ADMIN_TELEGRAM_ID > 0:
            self._allowed_users.add(settings.ADMIN_TELEGRAM_ID)

    def _save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self._allowed_users)), f, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении {self.filepath}: {e}")

    def is_allowed(self, user_id: int) -> bool:
        if settings.ADMIN_TELEGRAM_ID > 0 and user_id == settings.ADMIN_TELEGRAM_ID:
            return True
        return user_id in self._allowed_users

    def is_admin(self, user_id: int) -> bool:
        return settings.ADMIN_TELEGRAM_ID > 0 and user_id == settings.ADMIN_TELEGRAM_ID

    def add_user(self, user_id: int) -> bool:
        if user_id in self._allowed_users:
            return False
        self._allowed_users.add(user_id)
        self._save()
        logger.info(f"Добавлен разрешенный пользователь: {user_id}")
        return True

    def remove_user(self, user_id: int) -> bool:
        if settings.ADMIN_TELEGRAM_ID > 0 and user_id == settings.ADMIN_TELEGRAM_ID:
            # Cannot remove primary admin
            return False
        if user_id in self._allowed_users:
            self._allowed_users.remove(user_id)
            self._save()
            logger.info(f"Удален пользователь: {user_id}")
            return True
        return False

    def get_allowed_users(self) -> list[int]:
        return sorted(list(self._allowed_users))


security_manager = SecurityManager()
