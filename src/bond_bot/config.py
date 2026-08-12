"""Конфигурация приложения, читается из .env."""

from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _empty_to_none(value: object) -> object:
    """Пустая строка в .env означает «не задано», а не ошибку разбора."""
    return None if value == "" else value


OptionalInt = Annotated[int | None, BeforeValidator(_empty_to_none)]

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_id: OptionalInt = Field(default=None, alias="ADMIN_ID")
    db_path: Path = Field(default=Path("data/bond_bot.sqlite3"), alias="DB_PATH")

    @property
    def db_url(self) -> str:
        path = self.db_path
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{path}"


settings = Settings()  # type: ignore[call-arg]
