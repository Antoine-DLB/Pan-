"""Random-agent game simulator / fuzzer.

Plays complete games against the engine with agents that try every legal
action (and some illegal ones), checking invariants after every step.

Run directly:  python tests/simulate.py [n_games] [seed]
"""

from __future__ import annotations

import random
import sys
from collections import Counter

sys.path.insert(0, ".")

from game.engine import GameEngine, GameError
from game.models import GamePhase, PendingType, Role

MAX_ACTIONS = 4000


class InvariantError(AssertionError):
    pass


def check_invariants(game: GameEngine, history: list[str]) -> None:
    # 1. exactly 80 cards, no duplicates, none lost
    uids: list[int] = [c.uid for c in game.deck.draw_pile + game.deck.discard_pile]
    for p in game.players:
        uids += [c.uid for c in p.hand] + [c.uid for c in p.table]
    for pend in game.pending:
        uids += [c.uid for c in pend.data.get("cards", [])]
    if len(uids) != 80 or len(set(uids)) != 80:
        raise InvariantError(f"card conservation broken: {len(uids)} cards, {len(set(uids))} unique")

    dying_ids = {
        pend.data["player_id"]
        for pend in game.pending
        if pend.type == PendingType.DEATH
    }
    for p in game.players:
        # 2. HP bounds (hp <= 0 only while a death pending awaits resolution)
        if p.alive and p.hp > p.max_hp:
            raise InvariantError(f"{p.name} above max hp: {p.hp}/{p.max_hp}")
        if p.alive and p.hp <= 0 and p.id not in dying_ids:
            raise InvariantError(f"{p.name} alive with hp={p.hp} and no death pending")
        if not p.alive and (p.hand or p.table):
            raise InvariantError(f"dead {p.name} still holds cards")
        # 3. table: at most one weapon, no duplicate blue card ids
        weapons = [c for c in p.table if c.is_weapon]
        if len(weapons) > 1:
            raise InvariantError(f"{p.name} has {len(weapons)} weapons in play")
        ids = [c.card_id for c in p.table]
        if len(ids) != len(set(ids)):
            raise InvariantError(f"{p.name} has duplicate equipment: {ids}")

    if game.phase != GamePhase.FINISHED:
        # 4. turn player must be alive
        if not game.turn_player.alive:
            raise InvariantError(f"turn player {game.turn_player.name} is dead")
        # 5. pending responders must be alive
        for pend in game.pending:
            if pend.type in (PendingType.SHOT, PendingType.INDIANS):
                ids = pend.data["target_ids"]
                if ids and not game.player_by_id(ids[0]).alive:
                    pass  # tolerated: queue is lazily cleaned at resolution
            elif pend.type == PendingType.DUEL:
                if not game.player_by_id(pend.data["current_id"]).alive:
                    raise InvariantError("duel waits on a dead player")
            elif pend.type == PendingType.DEATH:
                if not game.player_by_id(pend.data["player_id"]).alive:
                    raise InvariantError("death pending for an already dead player")

    # 6. views never leak hidden info
    for viewer in game.players:
        view = game.view_for(viewer.id)
        for entry in view["players"]:
            other = game.player_by_id(entry["id"])
            if "hand" in entry:
                raise InvariantError("hand leaked in player list")
            if (
                entry["role"] is not None
                and other.id != viewer.id
                and other.role != Role.SHERIFF
                and not other.role_revealed
                and game.phase != GamePhase.FINISHED
            ):
                raise InvariantError(f"secret role of {other.name} leaked")


def legal_reaction(game: GameEngine, rng: random.Random) -> tuple:
    """Pick the pending responder and a random legal reaction for them."""
    top = game.pending[-1]
    data = top.data
    if top.type == PendingType.GENERAL_STORE:
        queue = [q for q in data["queue"] if game.player_by_id(q).alive]
        pid = queue[0]
        card = rng.choice(data["cards"])
        return ("pick_store", pid, card.uid)
    if top.type == PendingType.DEATH:
        player = game.player_by_id(data["player_id"])
        beers = [c for c in player.hand if c.card_id == "beer"]
        if beers and len(game.alive_players()) > 2 and rng.random() < 0.9:
            return ("react", player.id, "beer", beers[0].uid)
        return ("react", player.id, "die", None)
    if top.type == PendingType.DUEL:
        player = game.player_by_id(data["current_id"])
        shots = [c for c in player.hand if c.card_id == "shot"]
        if shots and rng.random() < 0.85:
            return ("react", player.id, "discard_shot", shots[0].uid)
        return ("react", player.id, "take", None)
    # SHOT / INDIANS queues
    target_ids = [t for t in data["target_ids"] if game.player_by_id(t).alive]
    player = game.player_by_id(target_ids[0])
    if top.type == PendingType.SHOT:
        options = [("take", None)]
        dodges = [c for c in player.hand if c.card_id == "dodge"]
        if dodges:
            options += [("dodge", dodges[0].uid)] * 4
        if player.has_in_play("barrel") and player.id not in data["barrel_used"]:
            options += [("barrel", None)] * 3
        action, card = rng.choice(options)
        return ("react", player.id, action, card)
    options = [("take", None)]
    shots = [c for c in player.hand if c.card_id == "shot"]
    if shots:
        options += [("discard_shot", shots[0].uid)] * 4
    action, card = rng.choice(options)
    return ("react", player.id, action, card)


def random_play(game: GameEngine, rng: random.Random) -> tuple | None:
    """Pick a random card play for the turn player, or None to end the turn."""
    player = game.turn_player
    if not player.hand or rng.random() < 0.12:
        return None
    others = [p for p in game.alive_players() if p is not player]
    rng.shuffle(others)
    cards = list(player.hand)
    rng.shuffle(cards)
    for card in cards:
        cid = card.card_id
        if cid == "dodge":
            continue
        if cid == "shot":
            if game.shots_played >= 1 and not player.has_in_play("volcanic"):
                continue
            targets = [t for t in others if game.distance(player, t) <= player.attack_range]
            if not targets:
                continue
            return ("play", card.uid, targets[0].id, None)
        if cid == "beer":
            if len(game.alive_players()) <= 2 or player.hp >= player.max_hp:
                continue
            return ("play", card.uid, None, None)
        if cid == "panic":
            targets = [
                t for t in others
                if game.distance(player, t) <= 1 and (t.hand or t.table)
            ]
            if not targets:
                continue
            target = targets[0]
            if target.table and (not target.hand or rng.random() < 0.5):
                return ("play", card.uid, target.id, rng.choice(target.table).uid)
            return ("play", card.uid, target.id, None)
        if cid == "cat_balou":
            targets = [t for t in others if t.hand or t.table]
            if not targets:
                continue
            target = targets[0]
            if target.table and (not target.hand or rng.random() < 0.5):
                return ("play", card.uid, target.id, rng.choice(target.table).uid)
            return ("play", card.uid, target.id, None)
        if cid == "duel":
            return ("play", card.uid, others[0].id, None)
        if cid == "jail":
            targets = [
                t for t in others
                if t.role != Role.SHERIFF and not t.has_in_play("jail")
            ]
            if not targets:
                continue
            return ("play", card.uid, targets[0].id, None)
        if cid in ("mustang", "scope", "barrel", "dynamite"):
            if player.has_in_play(cid):
                continue
            return ("play", card.uid, None, None)
        # weapons, stagecoach, wells_fargo, gatling, indians, general_store, saloon
        return ("play", card.uid, None, None)
    return None


def try_illegal_action(game: GameEngine, rng: random.Random) -> None:
    """Random invalid calls must raise GameError (anything else is a bug)."""
    pid = rng.choice(game.players).id
    attempts = [
        lambda: game.draw_cards("ghost"),
        lambda: game.play_card(pid, 9999),
        lambda: game.react(pid, "dodge", None),
        lambda: game.pick_store(pid, 0),
        lambda: game.discard_cards(pid, [1, 1]),
        lambda: game.end_turn("ghost"),
    ]
    attempt = rng.choice(attempts)
    try:
        attempt()
    except GameError:
        pass  # expected
    # anything else propagates as a bug


def repr_state(game: GameEngine) -> str:
    return f"{game.phase} {game.turn_index} " + " ".join(
        f"{p.id}:{p.hp}:{len(p.hand)}:{len(p.table)}" for p in game.players
    )


def play_one_game(n_players: int, seed: int) -> dict:
    rng = random.Random(seed)
    game = GameEngine(
        [(f"p{i}", f"J{i}") for i in range(n_players)], rng=random.Random(seed + 1)
    )
    history: list[str] = []
    actions = 0
    while not game.finished and actions < MAX_ACTIONS:
        actions += 1
        if rng.random() < 0.03:
            try_illegal_action(game, rng)
        try:
            if game.pending:
                move = legal_reaction(game, rng)
                history.append(str(move))
                if move[0] == "pick_store":
                    game.pick_store(move[1], move[2])
                else:
                    game.react(move[1], move[2], move[3])
            elif game.phase == GamePhase.DRAW:
                history.append("draw")
                game.draw_cards(game.turn_player.id)
            elif game.phase == GamePhase.PLAY:
                move = random_play(game, rng)
                history.append(str(move))
                if move is None:
                    game.end_turn(game.turn_player.id)
                else:
                    game.play_card(
                        game.turn_player.id, move[1],
                        target_id=move[2], target_card_uid=move[3],
                    )
            elif game.phase == GamePhase.DISCARD:
                player = game.turn_player
                extra = len(player.hand) - player.hp
                uids = [c.uid for c in rng.sample(player.hand, extra)]
                history.append(f"discard {uids}")
                game.discard_cards(player.id, uids)
            game.take_events()
            check_invariants(game, history)
        except GameError:
            # a "legal" pick that the engine refused: tolerated but counted
            history.append("  -> GameError (agent picked something refused)")
            raise
    return {
        "finished": game.finished,
        "actions": actions,
        "team": game.winning_team,
        "history": history,
        "game": game,
    }


def main() -> None:
    n_games = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    base_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    stats: Counter = Counter()
    failures = []
    for i in range(n_games):
        n_players = 4 + i % 4
        seed = base_seed + i
        try:
            result = play_one_game(n_players, seed)
        except Exception as exc:  # noqa: BLE001 — fuzzing: report everything
            failures.append((n_players, seed, exc))
            print(f"FAIL players={n_players} seed={seed}: {type(exc).__name__}: {exc}")
            continue
        stats["finished" if result["finished"] else "TIMEOUT"] += 1
        stats[f"win:{result['team']}"] += 1
        stats["actions"] += result["actions"]
    print()
    print(f"games: {n_games}, failures: {len(failures)}")
    for key, value in sorted(stats.items()):
        print(f"  {key}: {value}")
    if stats["finished"]:
        print(f"  avg actions/game: {stats['actions'] // n_games}")
    if failures:
        n_players, seed, _ = failures[0]
        print(f"\nreplay first failure: players={n_players} seed={seed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
