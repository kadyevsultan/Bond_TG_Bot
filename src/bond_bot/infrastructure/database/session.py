from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bond_bot.config import settings

engine: AsyncEngine = create_async_engine(settings.db_url, echo=False)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", settings.db_url)
    return config


def _schema_predates_alembic() -> bool:
    sync_engine = create_engine(settings.db_url.replace("+aiosqlite", ""))
    try:
        with sync_engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            revision = MigrationContext.configure(connection).get_current_revision()
    finally:
        sync_engine.dispose()
    return "themes" in tables and revision is None


def migrate() -> None:
    config = _alembic_config()
    if _schema_predates_alembic():
        command.stamp(config, "head")
        return
    command.upgrade(config, "head")


async def init_db() -> None:
    await asyncio.to_thread(migrate)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
