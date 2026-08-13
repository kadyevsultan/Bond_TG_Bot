import asyncio

from alembic import command
from sqlalchemy import create_engine, inspect, text

from bond_bot.config import settings
from bond_bot.infrastructure.database.models import Base
from bond_bot.infrastructure.database.session import _alembic_config, migrate


async def upgraded_schema(tmp_path, monkeypatch) -> dict[str, set[str]]:
    monkeypatch.setattr(settings, "db_path", tmp_path / "migrated.sqlite3")
    await asyncio.to_thread(migrate)

    engine = create_engine(settings.db_url.replace("+aiosqlite", ""))
    try:
        inspector = inspect(engine)
        return {
            table: {column["name"] for column in inspector.get_columns(table)}
            for table in inspector.get_table_names()
            if table != "alembic_version"
        }
    finally:
        engine.dispose()


async def test_migrations_build_the_same_schema_as_models(tmp_path, monkeypatch):
    actual = await upgraded_schema(tmp_path, monkeypatch)
    expected = {
        table.name: {column.name for column in table.columns}
        for table in Base.metadata.sorted_tables
    }
    assert actual == expected


async def test_migrations_are_idempotent(tmp_path, monkeypatch):
    await upgraded_schema(tmp_path, monkeypatch)
    await asyncio.to_thread(migrate)
    assert await upgraded_schema(tmp_path, monkeypatch)


async def test_migrations_keep_child_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", tmp_path / "with_rows.sqlite3")
    config = _alembic_config()

    await asyncio.to_thread(command.upgrade, config, "f06b7166ed1a")

    engine = create_engine(settings.db_url.replace("+aiosqlite", ""))
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO themes (name, is_builtin, owner_id) VALUES ('Еда', 1, NULL)")
            )
            connection.execute(text("INSERT INTO words (theme_id, text) VALUES (1, 'Нож')"))
            connection.execute(
                text("INSERT INTO similar_words (word_id, text) VALUES (1, 'Вилка')")
            )
    finally:
        engine.dispose()

    await asyncio.to_thread(command.upgrade, config, "head")

    engine = create_engine(settings.db_url.replace("+aiosqlite", ""))
    try:
        with engine.connect() as connection:
            counts = {
                table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                for table in ("themes", "words", "similar_words")
            }
    finally:
        engine.dispose()

    assert counts == {"themes": 1, "words": 1, "similar_words": 1}
