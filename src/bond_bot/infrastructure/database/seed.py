from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bond_bot.infrastructure.database.models import SimilarWord, Theme, Word

logger = logging.getLogger(__name__)

THEMES_DIR = Path(__file__).resolve().parents[2] / "resources" / "themes"


async def seed_builtin_themes(session: AsyncSession) -> None:
    for path in sorted(THEMES_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        await _sync_theme(session, payload["name"], payload["words"])
    await session.commit()


async def _sync_theme(session: AsyncSession, name: str, words: list[dict]) -> None:
    theme = await session.scalar(
        select(Theme).where(Theme.name == name, Theme.is_builtin.is_(True))
    )
    if theme is None:
        theme = Theme(name=name, owner_id=None, is_builtin=True)
        session.add(theme)
        await session.flush()
        logger.info("Добавлена встроенная тема «%s»", name)

    existing = {
        word.text: word
        for word in await session.scalars(select(Word).where(Word.theme_id == theme.id))
    }

    for entry in words:
        word = existing.get(entry["text"])
        if word is None:
            word = Word(theme_id=theme.id, text=entry["text"])
            session.add(word)
            await session.flush()
            known: set[str] = set()
        else:
            known = set(
                await session.scalars(
                    select(SimilarWord.text).where(SimilarWord.word_id == word.id)
                )
            )

        for text in entry.get("similar", []):
            if text not in known:
                session.add(SimilarWord(word_id=word.id, text=text))
