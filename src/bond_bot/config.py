from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_ids(value: object) -> object:
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        return [int(part) for part in value.replace(";", ",").split(",") if part.strip()]
    return value


IdList = Annotated[list[int], NoDecode, BeforeValidator(_split_ids)]

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: IdList = Field(default_factory=list, alias="ADMIN_IDS")
    db_path: Path = Field(default=Path("data/bond_bot.sqlite3"), alias="DB_PATH")

    def is_admin(self, user_id: int | None) -> bool:
        return user_id is not None and user_id in set(self.admin_ids)

    @property
    def db_url(self) -> str:
        path = self.db_path
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{path}"


settings = Settings()  # type: ignore[call-arg]
