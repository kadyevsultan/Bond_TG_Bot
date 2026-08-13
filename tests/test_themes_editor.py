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


def test_only_owner_can_edit_own_theme():
    mine = Theme(name="Мемы", owner_id=OWNER, is_builtin=False)
    builtin = Theme(name="Еда", owner_id=None, is_builtin=True)

    assert can_edit(mine, OWNER)
    assert not can_edit(mine, STRANGER)
    assert not can_edit(builtin, OWNER)


def test_admin_can_delete_any_custom_theme(monkeypatch):
    from bond_bot import config

    monkeypatch.setattr(config.settings, "admin_ids", [ADMIN])
    someone_else = Theme(name="Мемы", owner_id=OWNER, is_builtin=False)

    assert can_delete(someone_else, OWNER)
    assert can_delete(someone_else, ADMIN)
    assert not can_delete(someone_else, STRANGER)


def test_admin_owns_builtin_themes(monkeypatch):
    from bond_bot import config

    monkeypatch.setattr(config.settings, "admin_ids", [ADMIN])
    builtin = Theme(name="Еда", owner_id=None, is_builtin=True)

    assert can_edit(builtin, ADMIN)
    assert can_delete(builtin, ADMIN)
    assert not can_edit(builtin, OWNER)
    assert not can_delete(builtin, STRANGER)


def test_builtin_stays_locked_without_admins(monkeypatch):
    from bond_bot import config

    monkeypatch.setattr(config.settings, "admin_ids", [])
    builtin = Theme(name="Еда", owner_id=None, is_builtin=True)

    assert not can_edit(builtin, ADMIN)
    assert not can_delete(builtin, ADMIN)


def test_author_label_depends_on_viewer():
    theme = Theme(name="Мемы", owner_id=OWNER, is_builtin=False)
    assert author_of(theme, OWNER) == "вы"
    assert author_of(theme, STRANGER) == "другой игрок"
    assert author_of(Theme(name="Еда", is_builtin=True), OWNER) == "встроенная тема"


async def test_copy_gives_stranger_an_editable_duplicate(repo):
    original = await repo.create("Мемы", owner_id=OWNER)
    word = await repo.add_word(original, "Нож")
    await repo.add_similar(original, word, "Вилка")

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


def test_trash_button_only_for_admin(monkeypatch):
    from bond_bot import config

    monkeypatch.setattr(config.settings, "admin_ids", [ADMIN])

    def labels(is_admin):
        return {b.text for row in kb.hub(is_admin=is_admin).inline_keyboard for b in row}

    assert any("Корзина" in label for label in labels(True))
    assert not any("Корзина" in label for label in labels(False))


def test_deleted_theme_card_offers_restore():
    theme = Theme(id=1, name="Еда", owner_id=None, is_builtin=True, is_deleted=True)
    markup = kb.theme_card(theme, can_edit=True, can_delete=True, page=0)
    labels = [b.text for row in markup.inline_keyboard for b in row]

    assert any("Восстановить" in label for label in labels)
    assert not any("Играть" in label for label in labels)
    assert not any("Удалить" in label for label in labels)


def test_deleted_theme_card_is_read_only_without_rights():
    theme = Theme(id=1, name="Еда", owner_id=None, is_builtin=True, is_deleted=True)
    markup = kb.theme_card(theme, can_edit=False, can_delete=False, page=0)
    labels = [b.text for row in markup.inline_keyboard for b in row]

    assert labels == ["⬅️ Назад"]


def test_deleted_theme_card_text_warns():
    body = texts.theme_card("Еда", 27, "встроенная тема", is_deleted=True)
    assert "корзине" in body
    assert "🗑" in body


def theme_card_labels(theme, **rights):
    markup = kb.theme_card(theme, page=0, **rights)
    return [button.text for row in markup.inline_keyboard for button in row]


def test_admin_keeps_copy_button_on_builtin_theme():
    builtin = Theme(id=1, name="Еда", owner_id=None, is_builtin=True)
    labels = theme_card_labels(builtin, can_edit=True, can_delete=True)

    assert any("Скопировать" in label for label in labels)
    assert any("Добавить слово" in label for label in labels)
    assert any("Удалить тему" in label for label in labels)


def test_own_theme_has_no_copy_button():
    mine = Theme(id=2, name="Мемы", owner_id=OWNER, is_builtin=False)
    labels = theme_card_labels(mine, can_edit=True, can_delete=True)

    assert not any("Скопировать" in label for label in labels)


def test_player_still_copies_builtin_theme():
    builtin = Theme(id=1, name="Еда", owner_id=None, is_builtin=True)
    labels = theme_card_labels(builtin, can_edit=False, can_delete=False)

    assert any("Скопировать" in label for label in labels)
    assert not any("Добавить слово" in label for label in labels)
