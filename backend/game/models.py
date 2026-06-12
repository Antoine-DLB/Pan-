"""Core data models for the game engine. No FastAPI / network code here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Role(str, Enum):
    SHERIFF = "sheriff"
    DEPUTY = "deputy"
    OUTLAW = "outlaw"
    RENEGADE = "renegade"


# Role distribution by player count (sheriff, deputies, outlaws, renegade).
ROLE_SETUP: dict[int, list[Role]] = {
    4: [Role.SHERIFF, Role.OUTLAW, Role.OUTLAW, Role.RENEGADE],
    5: [Role.SHERIFF, Role.DEPUTY, Role.OUTLAW, Role.OUTLAW, Role.RENEGADE],
    6: [Role.SHERIFF, Role.DEPUTY, Role.OUTLAW, Role.OUTLAW, Role.OUTLAW, Role.RENEGADE],
    7: [Role.SHERIFF, Role.DEPUTY, Role.DEPUTY, Role.OUTLAW, Role.OUTLAW, Role.OUTLAW, Role.RENEGADE],
}


class Suit(str, Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"


CARD_VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


class CardType(str, Enum):
    BROWN = "brown"  # action card, discarded after use
    BLUE = "blue"    # equipment, stays in play


class GamePhase(str, Enum):
    DRAW = "draw"
    PLAY = "play"
    DISCARD = "discard"
    FINISHED = "finished"


class PendingType(str, Enum):
    """Reaction sub-states. While a pending exists, normal play is blocked."""

    SHOT = "shot"                    # target(s) must dodge / use barrel / take the hit
    INDIANS = "indians"              # target(s) must discard a shot or lose 1 HP
    DUEL = "duel"                    # alternating shot discards
    GENERAL_STORE = "general_store"  # players pick revealed cards in order
    DEATH = "death"                  # player at 0 HP may play beer(s) to survive


@dataclass
class Card:
    uid: int            # unique per physical card in the deck
    card_id: str        # internal id, e.g. "shot"
    name: str           # display name (French), from cards.json
    type: CardType
    suit: Suit
    value: str          # "2".."10", "J", "Q", "K", "A"
    range: Optional[int] = None  # weapon range, only for weapon cards
    effect: str = ""    # rules text shown to players, from cards.json

    @property
    def is_weapon(self) -> bool:
        return self.range is not None

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "id": self.card_id,
            "name": self.name,
            "type": self.type.value,
            "suit": self.suit.value,
            "value": self.value,
            "range": self.range,
            "effect": self.effect,
        }


@dataclass
class Player:
    id: str
    name: str
    role: Optional[Role] = None
    hp: int = 0
    max_hp: int = 0
    hand: list[Card] = field(default_factory=list)
    table: list[Card] = field(default_factory=list)  # blue cards in play
    alive: bool = True
    role_revealed: bool = False

    def has_in_play(self, card_id: str) -> bool:
        return any(c.card_id == card_id for c in self.table)

    def get_in_play(self, card_id: str) -> Optional[Card]:
        return next((c for c in self.table if c.card_id == card_id), None)

    @property
    def weapon(self) -> Optional[Card]:
        return next((c for c in self.table if c.is_weapon), None)

    @property
    def attack_range(self) -> int:
        weapon = self.weapon
        return weapon.range if weapon else 1

    def hand_card(self, uid: int) -> Optional[Card]:
        return next((c for c in self.hand if c.uid == uid), None)

    def table_card(self, uid: int) -> Optional[Card]:
        return next((c for c in self.table if c.uid == uid), None)


@dataclass
class Pending:
    """One entry of the reaction stack."""

    type: PendingType
    data: dict = field(default_factory=dict)
