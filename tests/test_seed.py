import json

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bond_bot.infrastructure.database import seed
from bond_bot.infrastructure.database.models import Base, SimilarWord, Theme, Word
from bond_bot.infrastructure.database.repository import ThemeRepository
from bond_bot.infrastructure.database.seed import _sync_theme, seed_builtin_themes

WORDS = [
    {"text": "Нож", "similar": ["Вилка", "Ложка"]},
    {"text": "Чайник", "similar": ["Кастрюля"]},
]


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as opened:
        yield opened
    await engine.dispose()


async def words_of(session, name: str) -> dict[str, set[str]]:
    theme = await session.scalar(select(Theme).where(Theme.name == name))
    result = {}
    for word in await session.scalars(select(Word).where(Word.theme_id == theme.id)):
        similar = await session.scalars(
            select(SimilarWord.text).where(SimilarWord.word_id == word.id)
        )
        result[word.text] = set(similar)
    return result


async def test_sync_creates_theme_with_words(session):
    await _sync_theme(session, "Кухня", WORDS)
    assert await words_of(session, "Кухня") == {"Нож": {"Вилка", "Ложка"}, "Чайник": {"Кастрюля"}}


async def test_sync_is_idempotent(session):
    await _sync_theme(session, "Кухня", WORDS)
    await _sync_theme(session, "Кухня", WORDS)
    assert len(await words_of(session, "Кухня")) == 2
    assert await words_of(session, "Кухня") == {"Нож": {"Вилка", "Ложка"}, "Чайник": {"Кастрюля"}}


async def test_sync_adds_new_words_and_similar(session):
    await _sync_theme(session, "Кухня", WORDS)
    await _sync_theme(
        session,
        "Кухня",
        [
            {"text": "Нож", "similar": ["Вилка", "Ложка", "Ножницы"]},
            {"text": "Чайник", "similar": ["Кастрюля"]},
            {"text": "Тарелка", "similar": ["Блюдце"]},
        ],
    )
    assert await words_of(session, "Кухня") == {
        "Нож": {"Вилка", "Ложка", "Ножницы"},
        "Чайник": {"Кастрюля"},
        "Тарелка": {"Блюдце"},
    }


async def test_sync_removes_words_missing_from_json(session):
    await _sync_theme(session, "Кухня", WORDS)
    await _sync_theme(session, "Кухня", [{"text": "Нож", "similar": ["Вилка"]}])
    assert await words_of(session, "Кухня") == {"Нож": {"Вилка"}}


async def test_sync_leaves_no_orphan_similar_after_word_removal(session):
    await _sync_theme(session, "Кухня", WORDS)
    await _sync_theme(session, "Кухня", [{"text": "Нож", "similar": ["Вилка", "Ложка"]}])
    remaining = await session.scalars(select(SimilarWord.text))
    assert set(remaining) == {"Вилка", "Ложка"}


async def test_sync_skips_theme_edited_by_admin(session):
    await _sync_theme(session, "Кухня", WORDS)
    theme = await session.scalar(select(Theme).where(Theme.source_name == "Кухня"))
    theme.is_customized = True
    session.add(Word(theme_id=theme.id, text="Половник"))
    await session.flush()

    await _sync_theme(session, "Кухня", [{"text": "Нож", "similar": ["Вилка"]}])

    words = await words_of(session, "Кухня")
    assert "Половник" in words
    assert set(words) == {"Нож", "Чайник", "Половник"}


async def test_sync_finds_renamed_theme_by_source_name(session):
    await _sync_theme(session, "Кухня", WORDS)
    theme = await session.scalar(select(Theme).where(Theme.source_name == "Кухня"))
    theme.name = "Кухня и еда"
    theme.is_customized = True
    await session.flush()

    await _sync_theme(session, "Кухня", WORDS)

    names = [t.name for t in await session.scalars(select(Theme))]
    assert names == ["Кухня и еда"]


async def test_seed_does_not_resurrect_deleted_theme(session, tmp_path, monkeypatch):
    payload = {"name": "Кухня", "words": WORDS}
    (tmp_path / "kitchen.json").write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
    monkeypatch.setattr(seed, "THEMES_DIR", tmp_path)

    await seed_builtin_themes(session)
    theme = await session.scalar(select(Theme).where(Theme.source_name == "Кухня"))
    await ThemeRepository(session).delete_theme(theme)

    await seed_builtin_themes(session)

    assert theme.is_deleted
    assert await ThemeRepository(session).builtin() == []
    assert len(await words_of(session, "Кухня")) == 2


async def test_restored_theme_syncs_with_json_again(session, tmp_path, monkeypatch):
    payload = {"name": "Кухня", "words": WORDS}
    (tmp_path / "kitchen.json").write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
    monkeypatch.setattr(seed, "THEMES_DIR", tmp_path)

    await seed_builtin_themes(session)
    repo = ThemeRepository(session)
    theme = await session.scalar(select(Theme).where(Theme.source_name == "Кухня"))
    await repo.delete_theme(theme)
    await repo.restore_theme(theme)

    payload["words"] = WORDS + [{"text": "Тарелка", "similar": ["Блюдце"]}]
    (tmp_path / "kitchen.json").write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
    await seed_builtin_themes(session)

    assert set(await words_of(session, "Кухня")) == {"Нож", "Чайник", "Тарелка"}
