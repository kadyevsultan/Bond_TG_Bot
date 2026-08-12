import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bond_bot.infrastructure.database.models import Base
from bond_bot.infrastructure.database.repository import DuplicateError, ThemeRepository
from bond_bot.infrastructure.database.seed import seed_builtin_themes

OWNER = 1055275164


@pytest_asyncio.fixture
async def repo():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield ThemeRepository(session)
    await engine.dispose()


async def test_create_theme_with_words_and_similar(repo):
    theme = await repo.create("Кухня", owner_id=OWNER)
    word = await repo.add_word(theme, "Нож")
    await repo.add_similar(word, "Вилка")
    await repo.add_similar(word, "Ложка")

    snapshot = await repo.snapshot(theme.id)
    assert snapshot.name == "Кухня"
    assert snapshot.cards[0].text == "Нож"
    assert set(snapshot.cards[0].similar) == {"Вилка", "Ложка"}


async def test_duplicate_theme_name_is_rejected(repo):
    await repo.create("Кухня", owner_id=OWNER)
    with pytest.raises(DuplicateError):
        await repo.create("Кухня", owner_id=OWNER)


async def test_same_name_allowed_for_different_owners(repo):
    await repo.create("Кухня", owner_id=OWNER)
    other = await repo.create("Кухня", owner_id=OWNER + 1)
    assert other.id


async def test_duplicate_word_is_rejected(repo):
    theme = await repo.create("Кухня", owner_id=OWNER)
    await repo.add_word(theme, "Нож")
    with pytest.raises(DuplicateError):
        await repo.add_word(theme, "Нож")


async def test_deleting_theme_removes_its_words(repo):
    theme = await repo.create("Кухня", owner_id=OWNER)
    word = await repo.add_word(theme, "Нож")
    await repo.add_similar(word, "Вилка")

    await repo.delete_theme(theme)
    assert await repo.get(theme.id) is None
    assert await repo.get_word(word.id) is None


async def test_catalog_shows_custom_themes_only(repo):
    await seed_builtin_themes(repo.session)
    await repo.create("Мемы", owner_id=OWNER)

    catalog = await repo.catalog()
    assert [t.name for t in catalog] == ["Мемы"]
    assert await repo.catalog_size() == 1
    assert len(await repo.builtin()) >= 3


async def test_seed_is_idempotent(repo):
    await seed_builtin_themes(repo.session)
    first = {t.name: t.word_count for t in await repo.builtin()}
    await seed_builtin_themes(repo.session)
    second = {t.name: t.word_count for t in await repo.builtin()}
    assert first == second


async def test_seeded_theme_has_similar_words(repo):
    await seed_builtin_themes(repo.session)
    theme = next(t for t in await repo.builtin() if t.name == "Локации")
    snapshot = await repo.snapshot(theme.id)
    assert all(card.similar for card in snapshot.cards)
