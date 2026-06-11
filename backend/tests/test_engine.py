"""Stage 3 acceptance: full game scenarios played directly against the engine."""

import random
from collections import Counter

import pytest

from game.engine import DYNAMITE_VALUES, GameEngine, GameError
from game.models import GamePhase, PendingType, Role, Suit


# ----------------------------------------------------------------- helpers

def make_game(n=4, seed=1):
    return GameEngine([(f"p{i}", f"Joueur{i}") for i in range(n)], rng=random.Random(seed))


def by_role(game, role):
    return next(p for p in game.players if p.role == role)


def neighbor(game, player, offset=1):
    alive = game.alive_players()
    i = alive.index(player)
    return alive[(i + offset) % len(alive)]


def give(game, player, card_id, n=1):
    """Move n copies of card_id into player's hand, wherever they are."""
    already = [c for c in player.hand if c.card_id == card_id]
    moved = already[:n]
    pools = [game.deck.draw_pile, game.deck.discard_pile] + [
        p.hand for p in game.players if p is not player
    ]
    for pool in pools:
        for card in list(pool):
            if card.card_id == card_id and len(moved) < n:
                pool.remove(card)
                player.hand.append(card)
                moved.append(card)
    assert len(moved) == n, f"could not find {n}x {card_id}"
    return moved


def equip(game, player, card_id):
    """Put a card of card_id directly into player's in-play zone."""
    card = give(game, player, card_id)[0]
    player.hand.remove(card)
    player.table.append(card)
    return card


def clear_hand(game, player):
    for card in list(player.hand):
        player.hand.remove(card)
        game.deck.discard(card)


def hand_uid(player, card_id):
    return next(c.uid for c in player.hand if c.card_id == card_id)


def start_play(game):
    game.draw_cards(game.turn_player.id)


def plant_check(game, predicate):
    """Put a matching card on top of the draw pile (next 'draw!' result)."""
    card = next(c for c in game.deck.draw_pile if predicate(c))
    game.deck.draw_pile.remove(card)
    game.deck.draw_pile.append(card)
    return card


def total_cards(game):
    n = game.deck.draw_count + len(game.deck.discard_pile)
    for p in game.players:
        n += len(p.hand) + len(p.table)
    for pending in game.pending:
        n += len(pending.data.get("cards", []))
    return n


def damage(game, target, amount, source):
    """Test shortcut: apply raw damage then resolve."""
    game._apply_damage(target, amount, source)
    game._autoresolve()


# ------------------------------------------------------------------- setup

@pytest.mark.parametrize(
    "n,expected",
    [
        (4, {Role.SHERIFF: 1, Role.OUTLAW: 2, Role.RENEGADE: 1}),
        (5, {Role.SHERIFF: 1, Role.DEPUTY: 1, Role.OUTLAW: 2, Role.RENEGADE: 1}),
        (6, {Role.SHERIFF: 1, Role.DEPUTY: 1, Role.OUTLAW: 3, Role.RENEGADE: 1}),
        (7, {Role.SHERIFF: 1, Role.DEPUTY: 2, Role.OUTLAW: 3, Role.RENEGADE: 1}),
    ],
)
def test_role_distribution(n, expected):
    game = make_game(n)
    assert Counter(p.role for p in game.players) == expected


def test_invalid_player_count():
    with pytest.raises(GameError):
        make_game(3)
    with pytest.raises(GameError):
        make_game(8)


def test_initial_hp_and_hands():
    game = make_game(4)
    for p in game.players:
        expected_hp = 5 if p.role == Role.SHERIFF else 4
        assert p.hp == p.max_hp == expected_hp
        assert len(p.hand) == expected_hp
    assert game.turn_player.role == Role.SHERIFF
    assert game.phase == GamePhase.DRAW
    assert total_cards(game) == 80


def test_only_sheriff_role_is_public():
    game = make_game(4)
    sheriff = by_role(game, Role.SHERIFF)
    other = neighbor(game, sheriff)
    view = game.view_for(other.id)
    for entry in view["players"]:
        player = game.player_by_id(entry["id"])
        if player is other or player.role == Role.SHERIFF:
            assert entry["role"] is not None
        else:
            assert entry["role"] is None
        assert "hand" not in entry  # never leak other hands


# --------------------------------------------------------------- turn flow

def test_draw_phase_then_play():
    game = make_game(4)
    sheriff = game.turn_player
    before = len(sheriff.hand)
    game.draw_cards(sheriff.id)
    assert len(sheriff.hand) == before + 2
    assert game.phase == GamePhase.PLAY
    with pytest.raises(GameError):
        game.draw_cards(sheriff.id)


def test_cannot_act_out_of_turn():
    game = make_game(4)
    other = neighbor(game, game.turn_player)
    with pytest.raises(GameError):
        game.draw_cards(other.id)


def test_end_turn_requires_discard_when_over_limit():
    game = make_game(4)
    sheriff = game.turn_player
    start_play(game)  # 7 cards in hand, 5 HP
    game.end_turn(sheriff.id)
    assert game.phase == GamePhase.DISCARD
    uids = [c.uid for c in sheriff.hand[:2]]
    game.discard_cards(sheriff.id, uids)
    assert len(sheriff.hand) == 5
    assert game.turn_player is not sheriff
    assert game.phase == GamePhase.DRAW


def test_end_turn_without_discard():
    game = make_game(4)
    sheriff = game.turn_player
    start_play(game)
    clear_hand(game, sheriff)
    game.end_turn(sheriff.id)
    assert game.turn_player is neighbor(game, sheriff)


# -------------------------------------------------------------------- shot

def test_shot_dodged():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    give(game, shooter, "shot")
    give(game, target, "dodge")
    hp = target.hp
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    assert game.pending[-1].type == PendingType.SHOT
    game.react(target.id, "dodge", hand_uid(target, "dodge"))
    assert target.hp == hp
    assert not game.pending


def test_shot_auto_hits_without_defense():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    give(game, shooter, "shot")
    clear_hand(game, target)
    hp = target.hp
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    assert target.hp == hp - 1
    assert not game.pending


def test_one_shot_per_turn_unless_volcanic():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    clear_hand(game, target)
    give(game, shooter, "shot", 2)
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    with pytest.raises(GameError):
        game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    give(game, shooter, "volcanic")
    game.play_card(shooter.id, hand_uid(shooter, "volcanic"))
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    assert target.hp == target.max_hp - 2


def test_range_and_weapons():
    game = make_game(5)
    shooter = game.turn_player
    far = neighbor(game, shooter, 2)  # distance 2 in a 5-player circle
    start_play(game)
    give(game, shooter, "shot")
    clear_hand(game, far)
    with pytest.raises(GameError):
        game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=far.id)
    give(game, shooter, "schofield")
    game.play_card(shooter.id, hand_uid(shooter, "schofield"))
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=far.id)
    assert far.hp == far.max_hp - 1


def test_new_weapon_replaces_old():
    game = make_game(4)
    player = game.turn_player
    start_play(game)
    give(game, player, "schofield")
    give(game, player, "winchester")
    game.play_card(player.id, hand_uid(player, "schofield"))
    game.play_card(player.id, hand_uid(player, "winchester"))
    weapons = [c for c in player.table if c.is_weapon]
    assert len(weapons) == 1 and weapons[0].card_id == "winchester"
    assert player.attack_range == 5


def test_mustang_and_scope_modify_distance():
    game = make_game(4)
    a = game.turn_player
    b = neighbor(game, a)
    assert game.distance(a, b) == 1
    equip(game, b, "mustang")
    assert game.distance(a, b) == 2
    equip(game, a, "scope")
    assert game.distance(a, b) == 1


def test_barrel_saves_on_heart():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    give(game, shooter, "shot")
    clear_hand(game, target)
    equip(game, target, "barrel")
    plant_check(game, lambda c: c.suit == Suit.HEARTS)
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    game.react(target.id, "barrel")
    assert target.hp == target.max_hp
    assert not game.pending


def test_barrel_fails_then_takes_hit():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    give(game, shooter, "shot")
    clear_hand(game, target)
    equip(game, target, "barrel")
    plant_check(game, lambda c: c.suit == Suit.SPADES)
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    game.react(target.id, "barrel")  # fails, no dodge in hand -> auto hit
    assert target.hp == target.max_hp - 1
    assert not game.pending


# ----------------------------------------------------- beer / saloon / draw

def test_beer_heals_up_to_max():
    game = make_game(4)
    player = game.turn_player
    start_play(game)
    give(game, player, "beer", 2)
    with pytest.raises(GameError):  # already at max HP
        game.play_card(player.id, hand_uid(player, "beer"))
    player.hp -= 1
    game.play_card(player.id, hand_uid(player, "beer"))
    assert player.hp == player.max_hp


def test_saloon_heals_everyone():
    game = make_game(4)
    player = game.turn_player
    start_play(game)
    give(game, player, "saloon")
    for p in game.players:
        p.hp = max(1, p.hp - 1)
    game.play_card(player.id, hand_uid(player, "saloon"))
    for p in game.alive_players():
        assert p.hp in (p.max_hp, 2)  # +1, capped


def test_stagecoach_and_wells_fargo():
    game = make_game(4)
    player = game.turn_player
    start_play(game)
    give(game, player, "stagecoach")
    give(game, player, "wells_fargo")
    n = len(player.hand)
    game.play_card(player.id, hand_uid(player, "stagecoach"))
    assert len(player.hand) == n + 1  # -1 played, +2 drawn
    n = len(player.hand)
    game.play_card(player.id, hand_uid(player, "wells_fargo"))
    assert len(player.hand) == n + 2  # -1 played, +3 drawn


def test_dodge_cannot_be_played_proactively():
    game = make_game(4)
    player = game.turn_player
    start_play(game)
    give(game, player, "dodge")
    with pytest.raises(GameError):
        game.play_card(player.id, hand_uid(player, "dodge"))


# ------------------------------------------------------- panic / cat balou

def test_panic_steals_at_distance_1():
    game = make_game(4)
    player = game.turn_player
    target = neighbor(game, player)
    far = neighbor(game, player, 2)
    start_play(game)
    give(game, player, "panic", 2)
    n = len(player.hand)
    game.play_card(player.id, hand_uid(player, "panic"), target_id=target.id)
    assert len(player.hand) == n  # -1 panic, +1 stolen
    with pytest.raises(GameError):  # distance 2
        game.play_card(player.id, hand_uid(player, "panic"), target_id=far.id)


def test_cat_balou_discards_table_card():
    game = make_game(4)
    player = game.turn_player
    target = neighbor(game, player, 2)
    start_play(game)
    give(game, player, "cat_balou")
    mustang = equip(game, target, "mustang")
    game.play_card(
        player.id, hand_uid(player, "cat_balou"),
        target_id=target.id, target_card_uid=mustang.uid,
    )
    assert not target.table
    assert game.deck.discard_top is not None


# -------------------------------------------------- gatling / indians / duel

def test_gatling_hits_everyone_except_dodger():
    game = make_game(4)
    shooter = game.turn_player
    others = game._others_in_order(shooter)
    start_play(game)
    give(game, shooter, "gatling")
    give(game, others[0], "dodge")
    for p in others[1:]:
        clear_hand(game, p)
    game.play_card(shooter.id, hand_uid(shooter, "gatling"))
    assert game.pending[-1].type == PendingType.SHOT
    game.react(others[0].id, "dodge", hand_uid(others[0], "dodge"))
    assert others[0].hp == others[0].max_hp
    for p in others[1:]:
        assert p.hp == p.max_hp - 1
    assert not game.pending


def test_gatling_does_not_count_as_shot_limit():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    for p in game._others_in_order(shooter):
        clear_hand(game, p)
    give(game, shooter, "shot")
    give(game, shooter, "gatling")
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    game.play_card(shooter.id, hand_uid(shooter, "gatling"))  # no GameError
    assert target.hp == target.max_hp - 2


def test_indians_discard_shot_or_lose_hp():
    game = make_game(4)
    player = game.turn_player
    others = game._others_in_order(player)
    start_play(game)
    give(game, player, "indians")
    give(game, others[0], "shot")
    for p in others[1:]:
        clear_hand(game, p)
    game.play_card(player.id, hand_uid(player, "indians"))
    game.react(others[0].id, "discard_shot", hand_uid(others[0], "shot"))
    assert others[0].hp == others[0].max_hp
    for p in others[1:]:
        assert p.hp == p.max_hp - 1
    assert not game.pending


def test_duel_alternates_until_loser():
    game = make_game(4)
    player = game.turn_player
    target = neighbor(game, player, 2)  # any distance is fine for a duel
    start_play(game)
    give(game, player, "duel")
    clear_hand(game, target)
    give(game, target, "shot", 2)
    # keep exactly one shot for the duel starter
    shots = [c for c in player.hand if c.card_id == "shot"]
    give(game, player, "shot", 0) if shots else None
    for c in shots[1:]:
        player.hand.remove(c)
        game.deck.discard(c)
    if not shots:
        give(game, player, "shot")
    game.play_card(player.id, hand_uid(player, "duel"), target_id=target.id)
    # target begins, has 2 shots; attacker has 1
    game.react(target.id, "discard_shot", hand_uid(target, "shot"))
    game.react(player.id, "discard_shot", hand_uid(player, "shot"))
    # back to target with 1 shot left, attacker now has none
    game.react(target.id, "discard_shot", hand_uid(target, "shot"))
    # attacker has no shot -> auto-loses
    assert player.hp == player.max_hp - 1
    assert not game.pending


def test_duel_take_voluntarily():
    game = make_game(4)
    player = game.turn_player
    target = neighbor(game, player)
    start_play(game)
    give(game, player, "duel")
    give(game, target, "shot")
    game.play_card(player.id, hand_uid(player, "duel"), target_id=target.id)
    game.react(target.id, "take")
    assert target.hp == target.max_hp - 1
    assert not game.pending


# ------------------------------------------------------------ general store

def test_general_store_everyone_picks():
    game = make_game(4)
    player = game.turn_player
    start_play(game)
    give(game, player, "general_store")
    sizes = {p.id: len(p.hand) for p in game.players}
    game.play_card(player.id, hand_uid(player, "general_store"))
    pending = game.pending[-1]
    assert pending.type == PendingType.GENERAL_STORE
    assert len(pending.data["cards"]) == 4
    order = list(pending.data["queue"])
    assert order[0] == player.id
    for pid in order[:-1]:
        card = pending.data["cards"][0]
        game.pick_store(pid, card.uid)
    # last card is auto-assigned
    assert not game.pending
    for p in game.players:
        expected = sizes[p.id] + (0 if p is player else 1)  # player spent the store card
        assert len(p.hand) == expected
    assert total_cards(game) == 80


# ------------------------------------------------------------- jail / dynamite

def test_jail_cannot_target_sheriff():
    game = make_game(4)
    sheriff = game.turn_player
    outlaw = by_role(game, Role.OUTLAW)
    start_play(game)
    give(game, outlaw, "jail")
    # move the jail into the sheriff's hand to try jailing someone
    card = outlaw.hand.pop()
    sheriff.hand.append(card)
    with pytest.raises(GameError):
        # sheriff jails himself? no: jailing the sheriff is what is forbidden
        game.play_card(sheriff.id, card.uid, target_id=sheriff.id)


def test_jail_skips_turn_on_non_heart():
    game = make_game(4)
    sheriff = game.turn_player
    target = neighbor(game, sheriff)
    after = neighbor(game, sheriff, 2)
    start_play(game)
    give(game, sheriff, "jail")
    game.play_card(sheriff.id, hand_uid(sheriff, "jail"), target_id=target.id)
    assert target.has_in_play("jail")
    clear_hand(game, sheriff)
    plant_check(game, lambda c: c.suit == Suit.SPADES)
    game.end_turn(sheriff.id)
    assert game.turn_player is after  # target was skipped
    assert not target.has_in_play("jail")


def test_jail_escape_on_heart():
    game = make_game(4)
    sheriff = game.turn_player
    target = neighbor(game, sheriff)
    start_play(game)
    give(game, sheriff, "jail")
    game.play_card(sheriff.id, hand_uid(sheriff, "jail"), target_id=target.id)
    clear_hand(game, sheriff)
    plant_check(game, lambda c: c.suit == Suit.HEARTS)
    game.end_turn(sheriff.id)
    assert game.turn_player is target
    assert not target.has_in_play("jail")


def test_dynamite_passes_when_safe():
    game = make_game(4)
    sheriff = game.turn_player
    target = neighbor(game, sheriff)
    after = neighbor(game, sheriff, 2)
    equip(game, target, "dynamite")
    start_play(game)
    clear_hand(game, sheriff)
    plant_check(game, lambda c: c.suit == Suit.HEARTS)
    game.end_turn(sheriff.id)
    assert game.turn_player is target
    assert not target.has_in_play("dynamite")
    assert after.has_in_play("dynamite")


def test_dynamite_explodes():
    game = make_game(4)
    sheriff = game.turn_player
    target = neighbor(game, sheriff)
    equip(game, target, "dynamite")
    start_play(game)
    clear_hand(game, sheriff)
    plant_check(
        game, lambda c: c.suit == Suit.SPADES and c.value in DYNAMITE_VALUES
    )
    game.end_turn(sheriff.id)
    assert target.hp == target.max_hp - 3
    assert not target.has_in_play("dynamite")
    assert game.turn_player is target  # survived, plays normally
    assert total_cards(game) == 80


def test_dynamite_kills_and_turn_passes():
    game = make_game(4)
    sheriff = game.turn_player
    target = neighbor(game, sheriff)
    after = neighbor(game, sheriff, 2)
    equip(game, target, "dynamite")
    target.hp = 2
    clear_hand(game, target)
    start_play(game)
    clear_hand(game, sheriff)
    plant_check(
        game, lambda c: c.suit == Suit.SPADES and c.value in DYNAMITE_VALUES
    )
    game.end_turn(sheriff.id)
    assert not target.alive
    assert game.turn_player is after
    assert total_cards(game) == 80


# ---------------------------------------------------------------- death/beer

def test_beer_saves_from_fatal_damage():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    give(game, shooter, "shot")
    clear_hand(game, target)
    give(game, target, "beer")
    target.hp = 1
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    assert game.pending[-1].type == PendingType.DEATH
    game.react(target.id, "beer", hand_uid(target, "beer"))
    assert target.alive and target.hp == 1
    assert not game.pending


def test_player_dies_without_beer():
    game = make_game(4)
    shooter = game.turn_player
    target = neighbor(game, shooter)
    start_play(game)
    give(game, shooter, "shot")
    clear_hand(game, target)
    target.hp = 1
    game.play_card(shooter.id, hand_uid(shooter, "shot"), target_id=target.id)
    assert not target.alive
    assert target.role_revealed
    assert not target.hand and not target.table


def test_outlaw_killer_draws_three():
    game = make_game(4, seed=3)
    sheriff = by_role(game, Role.SHERIFF)
    outlaw = by_role(game, Role.OUTLAW)
    clear_hand(game, outlaw)
    outlaw.hp = 1
    n = len(sheriff.hand)
    damage(game, outlaw, 1, sheriff)
    assert not outlaw.alive
    assert len(sheriff.hand) == n + 3


def test_sheriff_killing_deputy_discards_everything():
    game = make_game(5)
    sheriff = by_role(game, Role.SHERIFF)
    deputy = by_role(game, Role.DEPUTY)
    equip(game, sheriff, "mustang")
    clear_hand(game, deputy)
    deputy.hp = 1
    damage(game, deputy, 1, sheriff)
    assert not deputy.alive
    assert not sheriff.hand and not sheriff.table
    assert not game.finished


# ------------------------------------------------------------ win conditions

def kill(game, player, source=None):
    clear_hand(game, player)
    player.hp = 1
    damage(game, player, 1, source)


def test_outlaws_win_when_sheriff_dies():
    game = make_game(4)
    sheriff = by_role(game, Role.SHERIFF)
    outlaw = by_role(game, Role.OUTLAW)
    kill(game, sheriff, outlaw)
    assert game.finished
    assert game.winning_team == "outlaws"
    outlaw_ids = {p.id for p in game.players if p.role == Role.OUTLAW}
    assert set(game.winners) == outlaw_ids


def test_outlaws_win_even_dead_if_sheriff_dies_with_others_alive():
    game = make_game(4)
    sheriff = by_role(game, Role.SHERIFF)
    outlaws = [p for p in game.players if p.role == Role.OUTLAW]
    kill(game, outlaws[0], sheriff)
    kill(game, outlaws[1], sheriff)
    assert not game.finished  # renegade still alive
    # renegade kills the sheriff... but a dead outlaw camp still wins? No:
    # alive = sheriff + renegade -> sheriff dies -> renegade is sole survivor
    renegade = by_role(game, Role.RENEGADE)
    kill(game, sheriff, renegade)
    assert game.winning_team == "renegade"
    assert game.winners == [renegade.id]


def test_renegade_wins_only_as_sole_survivor():
    game = make_game(5)
    sheriff = by_role(game, Role.SHERIFF)
    deputy = by_role(game, Role.DEPUTY)
    renegade = by_role(game, Role.RENEGADE)
    # sheriff dies while deputy and outlaws are alive -> outlaws win
    kill(game, sheriff, renegade)
    assert game.winning_team == "outlaws"


def test_law_wins_when_outlaws_and_renegade_dead():
    game = make_game(4)
    sheriff = by_role(game, Role.SHERIFF)
    for p in game.players:
        if p.role in (Role.OUTLAW, Role.RENEGADE):
            kill(game, p, sheriff)
    assert game.finished
    assert game.winning_team == "law"
    assert sheriff.id in game.winners
    for p in game.players:
        assert p.role_revealed


def test_no_actions_after_game_over():
    game = make_game(4)
    sheriff = by_role(game, Role.SHERIFF)
    kill(game, sheriff, by_role(game, Role.OUTLAW))
    with pytest.raises(GameError):
        game.draw_cards(game.turn_player.id)
    with pytest.raises(GameError):
        game.react(game.players[0].id, "take")


# ------------------------------------------------------------ full 7p game

def test_seven_player_game_full_cycle():
    """Play several full turns at 7 players; card count stays at 80."""
    game = make_game(7, seed=11)
    for _ in range(30):
        if game.finished:
            break
        player = game.turn_player
        if game.pending:
            # resolve any pending with the most conservative action
            view = game._pending_view(player.id)
            top = game.pending[-1]
            responder = top.data.get("current_id") or (
                top.data.get("target_ids") or [None]
            )[0] or top.data.get("player_id")
            if top.type == PendingType.GENERAL_STORE:
                queue = [q for q in top.data["queue"] if game.player_by_id(q).alive]
                game.pick_store(queue[0], top.data["cards"][0].uid)
            elif top.type == PendingType.DEATH:
                game.react(top.data["player_id"], "die")
            else:
                game.react(responder, "take")
            continue
        if game.phase == GamePhase.DRAW:
            game.draw_cards(player.id)
        elif game.phase == GamePhase.PLAY:
            game.end_turn(player.id)
        elif game.phase == GamePhase.DISCARD:
            extra = len(player.hand) - player.hp
            game.discard_cards(player.id, [c.uid for c in player.hand[:extra]])
        assert total_cards(game) == 80
    assert total_cards(game) == 80


def test_views_never_leak_hidden_info():
    game = make_game(7, seed=5)
    sheriff = by_role(game, Role.SHERIFF)
    for viewer in game.players:
        view = game.view_for(viewer.id)
        assert view["you"]["id"] == viewer.id
        for entry in view["players"]:
            other = game.player_by_id(entry["id"])
            assert "hand" not in entry
            if other is not viewer and other.role != Role.SHERIFF:
                assert entry["role"] is None
