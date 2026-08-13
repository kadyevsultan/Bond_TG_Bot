from __future__ import annotations

from html import escape

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bond_bot.domain.entities import ThemeSnapshot, WordCard
from bond_bot.infrastructure.database.models import SimilarWord, Theme, Word


class DuplicateError(Exception):
    pass


class ThemeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session


    async def get(self, theme_id: int) -> Theme | None:
        return await self.session.scalar(select(Theme).where(Theme.id == theme_id))

    async def builtin(self) -> list[Theme]:
        result = await self.session.scalars(
            select(Theme)
            .where(Theme.is_builtin.is_(True), Theme.is_deleted.is_(False))
            .order_by(Theme.name)
        )
        return list(result)

    async def deleted(self) -> list[Theme]:
        result = await self.session.scalars(
            select(Theme).where(Theme.is_deleted.is_(True)).order_by(Theme.name)
        )
        return list(result)

    async def owned_by(self, owner_id: int) -> list[Theme]:
        result = await self.session.scalars(
            select(Theme)
            .where(Theme.owner_id == owner_id, Theme.is_deleted.is_(False))
            .order_by(Theme.name)
        )
        return list(result)

    async def catalog(self, limit: int = 50, offset: int = 0) -> list[Theme]:
        result = await self.session.scalars(
            select(Theme)
            .where(Theme.is_builtin.is_(False), Theme.is_deleted.is_(False))
            .order_by(Theme.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)

    async def catalog_size(self) -> int:
        return await self.session.scalar(
            select(func.count())
            .select_from(Theme)
            .where(Theme.is_builtin.is_(False), Theme.is_deleted.is_(False))
        ) or 0

    async def snapshot(self, theme_id: int) -> ThemeSnapshot | None:
        theme = await self.get(theme_id)
        if theme is None:
            return None
        return ThemeSnapshot(
            name=theme.name,
            cards=tuple(
                WordCard(text=word.text, similar=tuple(s.text for s in word.similar))
                for word in theme.words
            ),
        )


    async def create(self, name: str, owner_id: int, is_builtin: bool = False) -> Theme:
        theme = Theme(name=name.strip(), owner_id=owner_id, is_builtin=is_builtin)
        self.session.add(theme)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateError(f"Тема «{escape(name)}» у вас уже есть") from exc
        return theme

    def _mark_customized(self, theme: Theme) -> None:
        if theme.is_builtin:
            theme.is_customized = True

    async def rename(self, theme: Theme, name: str) -> None:
        theme.name = name.strip()
        self._mark_customized(theme)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateError(f"Тема «{escape(name)}» у вас уже есть") from exc

    async def delete_theme(self, theme: Theme) -> None:
        if theme.is_builtin:
            theme.is_deleted = True
        else:
            await self.session.delete(theme)
        await self.session.commit()

    async def restore_theme(self, theme: Theme) -> None:
        theme.is_deleted = False
        await self.session.commit()

    async def copy_to(self, theme: Theme, owner_id: int) -> Theme:
        name = await self._free_name(theme.name, owner_id)
        copy = Theme(name=name, owner_id=owner_id, is_builtin=False)
        self.session.add(copy)
        await self.session.flush()

        source_words = await self.session.scalars(
            select(Word).where(Word.theme_id == theme.id).order_by(Word.id)
        )
        for word in source_words:
            new_word = Word(theme_id=copy.id, text=word.text)
            self.session.add(new_word)
            await self.session.flush()
            similar_texts = await self.session.scalars(
                select(SimilarWord.text).where(SimilarWord.word_id == word.id)
            )
            for text in similar_texts:
                self.session.add(SimilarWord(word_id=new_word.id, text=text))

        await self.session.commit()
        await self.session.refresh(copy)
        return copy

    async def _free_name(self, name: str, owner_id: int) -> str:
        taken = set(
            await self.session.scalars(select(Theme.name).where(Theme.owner_id == owner_id))
        )
        if name not in taken:
            return name
        for suffix in range(2, 100):
            candidate = f"{name} ({suffix})"
            if candidate not in taken:
                return candidate
        raise DuplicateError("Слишком много копий этой темы")


    async def add_word(self, theme: Theme, text: str) -> Word:
        word = Word(theme_id=theme.id, text=text.strip())
        self.session.add(word)
        self._mark_customized(theme)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateError(f"Слово «{escape(text)}» уже есть в теме") from exc
        await self.session.refresh(theme)
        return word

    async def delete_word(self, theme: Theme, word_id: int) -> None:
        self._mark_customized(theme)
        await self.session.execute(delete(Word).where(Word.id == word_id))
        await self.session.commit()

    async def get_word(self, word_id: int) -> Word | None:
        return await self.session.get(Word, word_id)


    async def add_similar(self, theme: Theme, word: Word, text: str) -> SimilarWord:
        similar = SimilarWord(word_id=word.id, text=text.strip())
        self.session.add(similar)
        self._mark_customized(theme)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateError(f"«{escape(text)}» уже в списке похожих") from exc
        await self.session.refresh(word)
        return similar

    async def delete_similar(self, theme: Theme, similar_id: int) -> None:
        self._mark_customized(theme)
        await self.session.execute(delete(SimilarWord).where(SimilarWord.id == similar_id))
        await self.session.commit()
