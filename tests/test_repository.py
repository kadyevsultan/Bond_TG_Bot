import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bond_bot.infrastructure.database.models import Base, Theme
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
    await repo.add_similar(theme, word, "Вилка")
    await repo.add_similar(theme, word, "Ложка")

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
    await repo.add_similar(theme, word, "Вилка")

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


async def builtin_theme(repo):
    theme = Theme(name="Еда", source_name="Еда", owner_id=None, is_builtin=True)
    repo.session.add(theme)
    await repo.session.flush()
    return theme


async def test_editing_builtin_theme_marks_it_customized(repo):
    theme = await builtin_theme(repo)
    assert not theme.is_customized

    await repo.add_word(theme, "Нож")
    assert theme.is_customized


async def test_editing_own_theme_does_not_mark_it(repo):
    theme = await repo.create("Мемы", owner_id=OWNER)
    await repo.add_word(theme, "Нож")
    assert not theme.is_customized


MUTATIONS = ["add_word", "add_similar", "del_similar", "del_word", "rename"]


@pytest.mark.parametrize("mutation", MUTATIONS)
async def test_every_builtin_mutation_marks_customized(repo, mutation):
    theme = await builtin_theme(repo)
    word = await repo.add_word(theme, "Нож")
    similar = await repo.add_similar(theme, word, "Вилка")
    theme.is_customized = False

    if mutation == "add_word":
        await repo.add_word(theme, "Ложка")
    elif mutation == "add_similar":
        await repo.add_similar(theme, word, "Ножницы")
    elif mutation == "del_similar":
        await repo.delete_similar(theme, similar.id)
    elif mutation == "del_word":
        await repo.delete_word(theme, word.id)
    else:
        await repo.rename(theme, "Другое имя")

    assert theme.is_customized


async def test_deleting_builtin_theme_only_hides_it(repo):
    theme = await builtin_theme(repo)
    await repo.add_word(theme, "Нож")

    await repo.delete_theme(theme)

    assert theme.is_deleted
    assert await repo.builtin() == []
    assert [t.name for t in await repo.deleted()] == ["Еда"]
    assert theme.word_count == 1


async def test_restoring_builtin_theme_brings_words_back(repo):
    theme = await builtin_theme(repo)
    await repo.add_word(theme, "Нож")
    await repo.delete_theme(theme)

    await repo.restore_theme(theme)

    assert not theme.is_deleted
    assert [t.name for t in await repo.builtin()] == ["Еда"]
    assert await repo.deleted() == []
    snapshot = await repo.snapshot(theme.id)
    assert [card.text for card in snapshot.cards] == ["Нож"]


async def test_own_theme_is_deleted_for_real(repo):
    theme = await repo.create("Мемы", owner_id=OWNER)
    await repo.delete_theme(theme)

    assert await repo.get(theme.id) is None
    assert await repo.deleted() == []


async def test_deleted_theme_disappears_from_lists(repo):
    mine = await repo.create("Мемы", owner_id=OWNER)
    await repo.add_word(mine, "Нож")
    builtin = await builtin_theme(repo)
    await repo.delete_theme(builtin)

    assert await repo.catalog_size() == 1
    assert [t.name for t in await repo.owned_by(OWNER)] == ["Мемы"]
    assert await repo.builtin() == []
