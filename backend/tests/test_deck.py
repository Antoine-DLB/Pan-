"""Stage 2 acceptance: deck has 80 cards, draw/recycle works, no card lost or duplicated."""

import random
from collections import Counter

import pytest

from game.deck import Deck, load_cards
from game.models import CardType, Suit


def test_deck_has_80_cards():
    cards = load_cards()
    assert len(cards) == 80


def test_card_quantities_match_rules():
    counts = Counter(c.card_id for c in load_cards())
    expected = {
        "shot": 25, "dodge": 12, "beer": 6, "panic": 4, "cat_balou": 4,
        "stagecoach": 2, "wells_fargo": 1, "gatling": 1, "indians": 2,
        "duel": 3, "general_store": 2, "saloon": 1,
        "volcanic": 2, "schofield": 3, "remington": 1, "rev_carabine": 1,
        "winchester": 1, "mustang": 2, "scope": 1, "barrel": 2,
        "jail": 3, "dynamite": 1,
    }
    assert counts == expected


def test_uids_are_unique():
    cards = load_cards()
    assert len({c.uid for c in cards}) == 80


def test_every_card_has_suit_and_value():
    for card in load_cards():
        assert isinstance(card.suit, Suit)
        assert card.value in {"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}


def test_weapons_have_range():
    ranges = {c.card_id: c.range for c in load_cards() if c.range is not None}
    assert ranges == {
        "volcanic": 1, "schofield": 2, "remington": 3,
        "rev_carabine": 4, "winchester": 5,
    }
    for card in load_cards():
        if card.card_id not in ranges:
            assert card.range is None


def test_draw_and_discard():
    deck = Deck(rng=random.Random(42))
    card = deck.draw()
    assert deck.draw_count == 79
    deck.discard(card)
    assert deck.discard_top is card


def test_draw_check_reveals_and_discards():
    deck = Deck(rng=random.Random(42))
    card = deck.draw_check()
    assert deck.discard_top is card
    assert deck.draw_count == 79


def test_no_card_lost_or_duplicated_after_200_draws():
    deck = Deck(rng=random.Random(7))
    seen = []
    for _ in range(200):
        card = deck.draw()
        seen.append(card.uid)
        deck.discard(card)  # discard immediately so the deck can recycle
    # Whole deck cycles: all 80 uids appear, none duplicated within one cycle
    total = deck.draw_count + len(deck.discard_pile)
    assert total == 80
    all_uids = sorted(c.uid for c in deck.draw_pile + deck.discard_pile)
    assert all_uids == list(range(80))


def test_recycle_when_empty():
    deck = Deck(rng=random.Random(1))
    drawn = [deck.draw() for _ in range(80)]
    for c in drawn:
        deck.discard(c)
    assert deck.draw_count == 0
    card = deck.draw()  # forces recycle
    assert card is not None
    assert deck.draw_count == 79
    assert len(deck.discard_pile) == 0


def test_draw_raises_when_truly_empty():
    deck = Deck(rng=random.Random(1))
    for _ in range(80):
        deck.draw()  # never discarded -> nothing to recycle
    with pytest.raises(RuntimeError):
        deck.draw()
