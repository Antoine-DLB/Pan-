"""Regression fuzz: random agents play complete games at 4-7 players,
with invariants checked after every action (see tests/simulate.py)."""

import pytest

from tests.simulate import MAX_ACTIONS, play_one_game


@pytest.mark.parametrize("n_players", [4, 5, 6, 7])
def test_random_games_respect_all_invariants(n_players):
    finished = 0
    for seed in range(15):
        result = play_one_game(n_players, seed * 101 + n_players)
        assert result["actions"] < MAX_ACTIONS, "game did not terminate"
        if result["finished"]:
            finished += 1
            assert result["team"] in ("law", "outlaws", "renegade")
    assert finished == 15, "some games never finished"
