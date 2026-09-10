from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    ADMIN_TELEGRAM_ID: int = 0

    # POSNext Credentials
    POSNEXT_EMAIL: str = ""
    POSNEXT_PASSWORD: str = ""

    # Optional manual token & session values
    POSNEXT_BEARER_TOKEN: Optional[str] = None
    POSNEXT_BID: Optional[str] = None
    POSNEXT_UID: Optional[str] = None

    # Parser Defaults
    VENUES_FILE_PATH: str = "venues.txt"
    DEFAULT_MIN_SOLDS: int = 10
    DEFAULT_FROM_DATE: Optional[str] = None
    DEFAULT_TO_DATE: Optional[str] = None
    HEADLESS: bool = True

    # File Paths
    SESSION_FILE_PATH: str = "session.json"
    ALLOWED_USERS_FILE_PATH: str = "allowed_users.json"
    REPORTS_DIR: str = "reports"


settings = Settings()
