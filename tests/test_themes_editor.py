from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bond_bot.infrastructure.database.models import Base, Theme
from bond_bot.infrastructure.database.repository import ThemeRepository
from bond_bot.presentation import texts
from bond_bot.presentation.handlers.themes import author_of, can_delete, can_edit
from bond_bot.presentation.keyboards import themes as kb

OWNER = 111
STRANGER = 222
ADMIN = 333


@pytest_asyncio.fixture
async def repo():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield ThemeRepository(session)
    await engine.dispose()


def test_only_owner_can_edit():
    mine = Theme(name="Мемы", owner_id=OWNER, is_builtin=False)
    builtin = Theme(name="Еда", owner_id=None, is_builtin=True)

    assert can_edit(mine, OWNER)
    assert not can_edit(mine, STRANGER)
    assert not can_edit(builtin, OWNER)


def test_admin_can_delete_any_custom_theme(monkeypatch):
    from bond_bot import config

    monkeypatch.setattr(config.settings, "admin_id", ADMIN)
    someone_else = Theme(name="Мемы", owner_id=OWNER, is_builtin=False)
    builtin = Theme(name="Еда", owner_id=None, is_builtin=True)

    assert can_delete(someone_else, OWNER)
    assert can_delete(someone_else, ADMIN)
    assert not can_delete(someone_else, STRANGER)
    assert not can_delete(builtin, ADMIN)


def test_author_label_depends_on_viewer():
    theme = Theme(name="Мемы", owner_id=OWNER, is_builtin=False)
    assert author_of(theme, OWNER) == "вы"
    assert author_of(theme, STRANGER) == "другой игрок"
    assert author_of(Theme(name="Еда", is_builtin=True), OWNER) == "встроенная тема"


async def test_copy_gives_stranger_an_editable_duplicate(repo):
    original = await repo.create("Мемы", owner_id=OWNER)
    word = await repo.add_word(original, "Нож")
    await repo.add_similar(word, "Вилка")

    copy = await repo.copy_to(original, STRANGER)

    assert copy.owner_id == STRANGER
    assert copy.id != original.id
    snapshot = await repo.snapshot(copy.id)
    assert snapshot.cards[0].text == "Нож"
    assert snapshot.cards[0].similar == ("Вилка",)
    assert can_edit(copy, STRANGER)


async def test_copying_twice_does_not_collide(repo):
    original = await repo.create("Мемы", owner_id=OWNER)
    await repo.add_word(original, "Нож")

    first = await repo.copy_to(original, STRANGER)
    second = await repo.copy_to(original, STRANGER)

    assert first.name == "Мемы"
    assert second.name == "Мемы (2)"


async def test_deleting_theme_does_not_touch_the_original(repo):
    original = await repo.create("Мемы", owner_id=OWNER)
    await repo.add_word(original, "Нож")
    copy = await repo.copy_to(original, STRANGER)

    await repo.delete_theme(copy)

    assert await repo.get(original.id) is not None
    assert (await repo.snapshot(original.id)).cards[0].text == "Нож"


@pytest.mark.parametrize("count", [0, 1, 8, 9, 20])
def test_theme_list_paginates(count):
    themes = [Theme(id=i, name=f"Тема {i}", owner_id=OWNER) for i in range(1, count + 1)]
    for theme in themes:
        theme.words = []
    chunk = themes[: kb.PAGE_SIZE]
    markup = kb.theme_list(chunk, "mine", 0, count)
    buttons = [b.text for row in markup.inline_keyboard for b in row]

    assert len([b for b in buttons if b.startswith("Тема")]) == min(count, kb.PAGE_SIZE)
    if count > kb.PAGE_SIZE:
        assert any("▶️" in b for b in buttons)


def test_word_card_text_explains_empty_similar_list():
    assert texts.NO_SIMILAR_HINT in texts.editor_word_card("Нож", [])
    assert "Вилка" in texts.editor_word_card("Нож", ["Вилка"])
