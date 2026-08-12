from __future__ import annotations

import json

import pytest

from bond_bot.infrastructure.database.seed import THEMES_DIR

MIN_WORDS = 25
MAX_LEN = 64

FILES = sorted(THEMES_DIR.glob("*.json"))


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_there_are_enough_builtin_themes():
    assert len(FILES) >= 8


def test_theme_names_are_unique():
    names = [load(path)["name"] for path in FILES]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_theme_file_is_valid(path):
    data = load(path)
    words = data["words"]

    assert data["name"]
    assert len(words) >= MIN_WORDS

    texts = [word["text"] for word in words]
    assert len(texts) == len(set(texts))

    for word in words:
        similar = word.get("similar", [])
        assert word["text"]
        assert len(word["text"]) <= MAX_LEN
        assert word["text"] not in similar
        assert len(similar) == len(set(similar))
        assert all(len(item) <= MAX_LEN for item in similar)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_double_agent_always_has_a_word_to_give(path):
    for word in load(path)["words"]:
        assert word.get("similar"), f"{word['text']} без похожих слов"
