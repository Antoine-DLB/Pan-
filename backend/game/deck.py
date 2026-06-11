"""Deck: draw pile, discard pile, shuffling, recycling and 'draw!' checks."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from .models import Card, CardType, Suit

CARDS_PATH = Path(__file__).parent / "cards.json"


def load_cards(path: Optional[Path] = None) -> list[Card]:
    """Build the full list of physical cards from the JSON definition."""
    raw = json.loads((path or CARDS_PATH).read_text(encoding="utf-8"))
    cards: list[Card] = []
    uid = 0
    for definition in raw["cards"]:
        for copy in definition["copies"]:
            cards.append(
                Card(
                    uid=uid,
                    card_id=definition["id"],
                    name=definition["name"],
                    type=CardType(definition["type"]),
                    suit=Suit(copy["suit"]),
                    value=copy["value"],
                    range=definition.get("range"),
                )
            )
            uid += 1
    return cards


class Deck:
    def __init__(self, cards: Optional[list[Card]] = None, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.draw_pile: list[Card] = list(cards) if cards is not None else load_cards()
        self.discard_pile: list[Card] = []
        self.rng.shuffle(self.draw_pile)

    def draw(self) -> Card:
        """Draw the top card, recycling the discard pile if needed."""
        if not self.draw_pile:
            self._recycle()
        if not self.draw_pile:
            raise RuntimeError("No cards left in deck or discard pile")
        return self.draw_pile.pop()

    def draw_many(self, n: int) -> list[Card]:
        return [self.draw() for _ in range(n)]

    def discard(self, card: Card) -> None:
        self.discard_pile.append(card)

    def draw_check(self) -> Card:
        """'Draw!' (dégainer): reveal the top card and discard it immediately."""
        card = self.draw()
        self.discard(card)
        return card

    def _recycle(self) -> None:
        self.draw_pile = self.discard_pile
        self.discard_pile = []
        self.rng.shuffle(self.draw_pile)

    @property
    def draw_count(self) -> int:
        return len(self.draw_pile)

    @property
    def discard_top(self) -> Optional[Card]:
        return self.discard_pile[-1] if self.discard_pile else None
