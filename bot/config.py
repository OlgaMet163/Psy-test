from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    database_path: Path = Field(default=Path("bot.db"), alias="DATABASE_PATH")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        settings = Settings()
        data_dir = settings.data_dir if settings.data_dir.is_absolute() else Path.cwd() / settings.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        if settings.database_path.is_absolute():
            db_path = settings.database_path
        else:
            db_path = data_dir / settings.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        settings.data_dir = data_dir
        settings.database_path = db_path
        return settings
    except ValidationError as exc:  # pragma: no cover - logging only
        raise RuntimeError(f"Configuration error: {exc}") from exc

