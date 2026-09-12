import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.config import settings
from core.logger import logger


class SecurityManager:
    """Управление списком и профилями разрешенных пользователей Telegram."""

    def __init__(self, filepath: str = settings.ALLOWED_USERS_FILE_PATH):
        self.filepath = Path(filepath)
        self._users: Dict[int, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, int):
                                # Миграция старого формата (список int)
                                self._users[item] = {
                                    "user_id": item,
                                    "first_name": "",
                                    "last_name": "",
                                    "username": "",
                                    "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                            elif isinstance(item, dict) and "user_id" in item:
                                uid = int(item["user_id"])
                                self._users[uid] = {
                                    "user_id": uid,
                                    "first_name": item.get("first_name") or "",
                                    "last_name": item.get("last_name") or "",
                                    "username": item.get("username") or "",
                                    "added_at": item.get("added_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
            except Exception as e:
                logger.error(f"Ошибка при чтении {self.filepath}: {e}")
                self._users = {}

        # Главный администратор всегда должен быть в списке
        if settings.ADMIN_TELEGRAM_ID > 0:
            if settings.ADMIN_TELEGRAM_ID not in self._users:
                self._users[settings.ADMIN_TELEGRAM_ID] = {
                    "user_id": settings.ADMIN_TELEGRAM_ID,
                    "first_name": "Администратор",
                    "last_name": "",
                    "username": "",
                    "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

    def _save(self) -> None:
        try:
            users_list = list(self._users.values())
            # Сортируем: админ первый, остальные по id
            users_list.sort(key=lambda x: (0 if self.is_admin(x["user_id"]) else 1, x["user_id"]))
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(users_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении {self.filepath}: {e}")

    def is_allowed(self, user_id: int) -> bool:
        if settings.ADMIN_TELEGRAM_ID > 0 and user_id == settings.ADMIN_TELEGRAM_ID:
            return True
        return user_id in self._users

    def is_admin(self, user_id: int) -> bool:
        return settings.ADMIN_TELEGRAM_ID > 0 and user_id == settings.ADMIN_TELEGRAM_ID

    def add_user(
        self,
        user_id: int,
        first_name: str = "",
        last_name: str = "",
        username: str = ""
    ) -> bool:
        if user_id in self._users:
            # Обновляем инфо если передано
            if first_name or username:
                self._users[user_id]["first_name"] = first_name or self._users[user_id].get("first_name", "")
                self._users[user_id]["last_name"] = last_name or self._users[user_id].get("last_name", "")
                self._users[user_id]["username"] = username or self._users[user_id].get("username", "")
                self._save()
            return False

        self._users[user_id] = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save()
        logger.info(f"Добавлен разрешенный пользователь: {user_id} ({first_name} @{username})")
        return True

    def update_user_info(
        self,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> None:
        """Обновляет метаданные пользователя при его активности в боте."""
        if user_id not in self._users:
            return

        changed = False
        if first_name is not None and self._users[user_id].get("first_name") != first_name:
            self._users[user_id]["first_name"] = first_name
            changed = True
        if last_name is not None and self._users[user_id].get("last_name") != last_name:
            self._users[user_id]["last_name"] = last_name
            changed = True
        if username is not None and self._users[user_id].get("username") != username:
            self._users[user_id]["username"] = username
            changed = True

        if changed:
            self._save()

    def remove_user(self, user_id: int) -> bool:
        if settings.ADMIN_TELEGRAM_ID > 0 and user_id == settings.ADMIN_TELEGRAM_ID:
            # Нельзя удалить главного администратора
            return False
        if user_id in self._users:
            del self._users[user_id]
            self._save()
            logger.info(f"Удален пользователь: {user_id}")
            return True
        return False

    def get_allowed_users(self) -> List[int]:
        return sorted(list(self._users.keys()))

    def get_users_detailed(self) -> List[Dict[str, Any]]:
        result = list(self._users.values())
        result.sort(key=lambda x: (0 if self.is_admin(x["user_id"]) else 1, x["user_id"]))
        return result


security_manager = SecurityManager()
