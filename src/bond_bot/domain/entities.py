from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class SpyMode(str, Enum):

    CLASSIC = "classic"

    DOUBLE_AGENT = "double_agent"


class Phase(str, Enum):

    DEALING = "dealing"

    DISCUSSION = "discussion"

    VOTING = "voting"

    TIE = "tie"

    SPY_GUESS = "spy_guess"

    FINISHED = "finished"


class Outcome(str, Enum):

    CIVILIANS_BY_VOTE = "civilians_by_vote"

    CIVILIANS_BY_WRONG_GUESS = "civilians_by_wrong_guess"

    SPIES_BY_SURVIVAL = "spies_by_survival"

    SPIES_BY_GUESS = "spies_by_guess"

    @property
    def civilians_won(self) -> bool:
        return self in (self.CIVILIANS_BY_VOTE, self.CIVILIANS_BY_WRONG_GUESS)


class TieResolution(Enum):

    REVOTE = auto()

    KICK_ALL = auto()

    EXTRA_ROUND = auto()


@dataclass(frozen=True)
class WordCard:

    text: str
    similar: tuple[str, ...] = ()


@dataclass(frozen=True)
class ThemeSnapshot:

    name: str
    cards: tuple[WordCard, ...]

    @property
    def words(self) -> list[str]:
        return [card.text for card in self.cards]


@dataclass
class Player:

    number: int
    is_spy: bool
    word: str | None

    eliminated: bool = False

    @property
    def label(self) -> str:
        return f"Игрок {self.number}"


@dataclass
class Game:

    theme_name: str
    civilian_word: str
    spy_mode: SpyMode
    players: list[Player]
    theme_words: list[str]

    phase: Phase = Phase.DEALING
    dealt_count: int = 0

    votes: dict[int, int] = field(default_factory=dict)

    round_number: int = 1
    outcome: Outcome | None = None
    last_eliminated: list[Player] = field(default_factory=list)

    @property
    def alive(self) -> list[Player]:
        return [p for p in self.players if not p.eliminated]

    @property
    def spies(self) -> list[Player]:
        return [p for p in self.players if p.is_spy]

    @property
    def alive_spies(self) -> list[Player]:
        return [p for p in self.alive if p.is_spy]

    @property
    def is_finished(self) -> bool:
        return self.phase is Phase.FINISHED

    def player(self, number: int) -> Player:
        return self.players[number - 1]
