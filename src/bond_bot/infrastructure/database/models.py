from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Theme(Base):

    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))

    owner_id: Mapped[int | None] = mapped_column(BigInteger, index=True, default=None)

    is_builtin: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    words: Mapped[list[Word]] = relationship(
        back_populates="theme",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Word.id",
    )

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_theme_owner_name"),)

    @property
    def word_count(self) -> int:
        return len(self.words)


class Word(Base):

    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(64))

    theme: Mapped[Theme] = relationship(back_populates="words")
    similar: Mapped[list[SimilarWord]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SimilarWord.id",
    )

    __table_args__ = (UniqueConstraint("theme_id", "text", name="uq_word_theme_text"),)


class SimilarWord(Base):

    __tablename__ = "similar_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(64))

    word: Mapped[Word] = relationship(back_populates="similar")

    __table_args__ = (UniqueConstraint("word_id", "text", name="uq_similar_word_text"),)


def utcnow() -> datetime:
    return datetime.now(UTC)
