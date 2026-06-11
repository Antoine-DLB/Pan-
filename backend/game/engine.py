"""GameEngine: authoritative rules state machine.

This module knows nothing about FastAPI or WebSockets. Clients send intents
(draw, play_card, react, ...), the engine validates them, mutates state and
exposes per-player filtered views via `view_for`.
"""

from __future__ import annotations

import random
from typing import Optional

from .deck import Deck
from .models import (
    ROLE_SETUP,
    Card,
    CardType,
    GamePhase,
    Pending,
    PendingType,
    Player,
    Role,
    Suit,
)

DYNAMITE_VALUES = {"2", "3", "4", "5", "6", "7", "8", "9"}
SHERIFF_BONUS_HP = 1
BASE_HP = 4
OUTLAW_KILL_REWARD = 3
TURN_DRAW_COUNT = 2

ROLE_LABELS = {
    Role.SHERIFF: "Shérif",
    Role.DEPUTY: "Adjoint",
    Role.OUTLAW: "Hors-la-loi",
    Role.RENEGADE: "Renégat",
}


class GameError(Exception):
    """Invalid move; the message is safe to show to the player (French UI)."""


class GameEngine:
    def __init__(self, players: list[tuple[str, str]], rng: Optional[random.Random] = None):
        if not 4 <= len(players) <= 7:
            raise GameError("Il faut entre 4 et 7 joueurs.")
        self.rng = rng or random.Random()
        self.players: list[Player] = [Player(id=pid, name=name) for pid, name in players]
        self.deck = Deck(rng=self.rng)
        self.phase = GamePhase.DRAW
        self.turn_index = 0
        self.pending: list[Pending] = []
        self.shots_played = 0
        self.winning_team: Optional[str] = None
        self.winners: list[str] = []
        self.log: list[str] = []
        self._setup()

    # ------------------------------------------------------------------ setup

    def _setup(self) -> None:
        roles = list(ROLE_SETUP[len(self.players)])
        self.rng.shuffle(roles)
        for player, role in zip(self.players, roles):
            player.role = role
            player.max_hp = BASE_HP + (SHERIFF_BONUS_HP if role == Role.SHERIFF else 0)
            player.hp = player.max_hp
            player.hand = self.deck.draw_many(player.hp)
        self.turn_index = next(i for i, p in enumerate(self.players) if p.role == Role.SHERIFF)
        self._log(f"La partie commence. {self.turn_player.name} est le Shérif.")

    # ------------------------------------------------------------ basic state

    @property
    def turn_player(self) -> Player:
        return self.players[self.turn_index]

    @property
    def finished(self) -> bool:
        return self.phase == GamePhase.FINISHED

    def player_by_id(self, pid: str) -> Player:
        player = next((p for p in self.players if p.id == pid), None)
        if player is None:
            raise GameError("Joueur inconnu.")
        return player

    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def _log(self, message: str) -> None:
        self.log.append(message)
        del self.log[:-50]

    def distance(self, attacker: Player, target: Player) -> int:
        alive = self.alive_players()
        ia, ib = alive.index(attacker), alive.index(target)
        n = len(alive)
        d = min((ia - ib) % n, (ib - ia) % n)
        if target.has_in_play("mustang"):
            d += 1
        if attacker.has_in_play("scope"):
            d -= 1
        return d

    def _discard_from_hand(self, player: Player, card: Card) -> None:
        player.hand.remove(card)
        self.deck.discard(card)

    def _discard_from_table(self, player: Player, card: Card) -> None:
        player.table.remove(card)
        self.deck.discard(card)

    # ------------------------------------------------------------- turn flow

    def draw_cards(self, pid: str) -> None:
        self._ensure_turn(pid, GamePhase.DRAW)
        player = self.turn_player
        player.hand.extend(self.deck.draw_many(TURN_DRAW_COUNT))
        self.phase = GamePhase.PLAY
        self._log(f"{player.name} pioche {TURN_DRAW_COUNT} cartes.")

    def end_turn(self, pid: str) -> None:
        self._ensure_turn(pid, GamePhase.PLAY)
        player = self.turn_player
        if len(player.hand) > player.hp:
            self.phase = GamePhase.DISCARD
        else:
            self._advance_turn()
            self._autoresolve()

    def discard_cards(self, pid: str, card_uids: list[int]) -> None:
        self._ensure_turn(pid, GamePhase.DISCARD)
        player = self.turn_player
        if not card_uids:
            raise GameError("Choisis au moins une carte à défausser.")
        cards = []
        for uid in card_uids:
            card = player.hand_card(uid)
            if card is None or card in cards:
                raise GameError("Carte invalide.")
            cards.append(card)
        for card in cards:
            self._discard_from_hand(player, card)
        self._log(f"{player.name} défausse {len(cards)} carte(s).")
        if len(player.hand) <= player.hp:
            self._advance_turn()
            self._autoresolve()

    def _ensure_turn(self, pid: str, phase: GamePhase) -> None:
        if self.finished:
            raise GameError("La partie est terminée.")
        if self.pending:
            raise GameError("Une réaction est en attente.")
        if self.turn_player.id != pid:
            raise GameError("Ce n'est pas ton tour.")
        if self.phase != phase:
            raise GameError("Action impossible dans cette phase.")

    def _advance_turn(self) -> None:
        if self.finished:
            return
        self.shots_played = 0
        idx = self.turn_index
        for _ in range(len(self.players)):
            idx = (idx + 1) % len(self.players)
            if self.players[idx].alive:
                break
        self.turn_index = idx
        self._start_turn_checks()

    def _next_alive_after(self, player: Player) -> Player:
        idx = self.players.index(player)
        for _ in range(len(self.players)):
            idx = (idx + 1) % len(self.players)
            if self.players[idx].alive:
                return self.players[idx]
        return player

    def _start_turn_checks(self) -> None:
        """Beginning of turn: dynamite first, then jail, then the draw phase."""
        self.phase = GamePhase.DRAW
        player = self.turn_player
        dynamite = player.get_in_play("dynamite")
        if dynamite:
            check = self.deck.draw_check()
            if check.suit == Suit.SPADES and check.value in DYNAMITE_VALUES:
                self._discard_from_table(player, dynamite)
                self._log(f"La Dynamite explose sur {player.name} : 3 dégâts !")
                self._apply_damage(player, 3, source=None, ctx="turn_start")
                if player.hp >= 1:
                    self._after_dynamite()
                # otherwise a DEATH pending resumes the turn via its ctx
                return
            next_player = self._next_alive_after(player)
            player.table.remove(dynamite)
            next_player.table.append(dynamite)
            self._log(f"La Dynamite ne saute pas et passe à {next_player.name}.")
        self._after_dynamite()

    def _after_dynamite(self) -> None:
        player = self.turn_player
        jail = player.get_in_play("jail")
        if jail:
            self._discard_from_table(player, jail)
            check = self.deck.draw_check()
            if check.suit != Suit.HEARTS:
                self._log(f"{player.name} reste en Prison et passe son tour.")
                self._advance_turn()
                return
            self._log(f"{player.name} s'évade de Prison et joue normalement.")
        self._log(f"C'est au tour de {player.name}.")

    # ------------------------------------------------------------- play cards

    def play_card(
        self,
        pid: str,
        card_uid: int,
        target_id: Optional[str] = None,
        target_card_uid: Optional[int] = None,
    ) -> None:
        self._ensure_turn(pid, GamePhase.PLAY)
        player = self.turn_player
        card = player.hand_card(card_uid)
        if card is None:
            raise GameError("Cette carte n'est pas dans ta main.")

        if card.type == CardType.BLUE:
            self._play_blue(player, card, target_id)
        else:
            self._play_brown(player, card, target_id, target_card_uid)
        self._autoresolve()

    def _require_target(self, target_id: Optional[str], allow_self: bool = False) -> Player:
        if target_id is None:
            raise GameError("Cette carte nécessite une cible.")
        target = self.player_by_id(target_id)
        if not target.alive:
            raise GameError("Cette cible est déjà éliminée.")
        if not allow_self and target is self.turn_player:
            raise GameError("Tu ne peux pas te cibler toi-même.")
        return target

    def _play_brown(
        self,
        player: Player,
        card: Card,
        target_id: Optional[str],
        target_card_uid: Optional[int],
    ) -> None:
        cid = card.card_id
        if cid == "shot":
            target = self._require_target(target_id)
            if self.shots_played >= 1 and not player.has_in_play("volcanic"):
                raise GameError("Tu as déjà joué un Tir ce tour-ci.")
            if self.distance(player, target) > player.attack_range:
                raise GameError("Cette cible est hors de portée.")
            self._discard_from_hand(player, card)
            self.shots_played += 1
            self._log(f"{player.name} tire sur {target.name} !")
            self._push_shot(player, [target], gatling=False)
        elif cid == "dodge":
            raise GameError("L'Esquive ne se joue qu'en réaction à un Tir.")
        elif cid == "beer":
            if len(self.alive_players()) <= 2:
                raise GameError("La Gnôle est sans effet à 2 joueurs restants.")
            if player.hp >= player.max_hp:
                raise GameError("Tes PV sont déjà au maximum.")
            self._discard_from_hand(player, card)
            player.hp += 1
            self._log(f"{player.name} boit une Gnôle et récupère 1 PV.")
        elif cid == "saloon":
            self._discard_from_hand(player, card)
            for p in self.alive_players():
                p.hp = min(p.hp + 1, p.max_hp)
            self._log(f"{player.name} offre une Tournée générale : tout le monde récupère 1 PV.")
        elif cid == "stagecoach":
            self._discard_from_hand(player, card)
            player.hand.extend(self.deck.draw_many(2))
            self._log(f"{player.name} joue Diligence et pioche 2 cartes.")
        elif cid == "wells_fargo":
            self._discard_from_hand(player, card)
            player.hand.extend(self.deck.draw_many(3))
            self._log(f"{player.name} joue Convoi d'or et pioche 3 cartes.")
        elif cid == "panic":
            target = self._require_target(target_id)
            if self.distance(player, target) > 1:
                raise GameError("Vol à la tire ne fonctionne qu'à distance 1.")
            stolen = self._take_card_from(target, target_card_uid)
            self._discard_from_hand(player, card)
            player.hand.append(stolen)
            self._log(f"{player.name} vole une carte à {target.name}.")
        elif cid == "cat_balou":
            target = self._require_target(target_id)
            stolen = self._take_card_from(target, target_card_uid)
            self._discard_from_hand(player, card)
            self.deck.discard(stolen)
            self._log(f"{player.name} sabote {target.name} : une carte défaussée.")
        elif cid == "gatling":
            self._discard_from_hand(player, card)
            targets = self._others_in_order(player)
            self._log(f"{player.name} arrose tout le monde à la Mitraille !")
            self._push_shot(player, targets, gatling=True)
        elif cid == "indians":
            self._discard_from_hand(player, card)
            targets = self._others_in_order(player)
            self._log(f"{player.name} déclenche une Embuscade !")
            self.pending.append(
                Pending(
                    PendingType.INDIANS,
                    {"source_id": player.id, "target_ids": [t.id for t in targets]},
                )
            )
        elif cid == "duel":
            target = self._require_target(target_id)
            self._discard_from_hand(player, card)
            self._log(f"{player.name} provoque {target.name} en Duel !")
            self.pending.append(
                Pending(
                    PendingType.DUEL,
                    {"source_id": player.id, "other_id": target.id, "current_id": target.id},
                )
            )
        elif cid == "general_store":
            self._discard_from_hand(player, card)
            alive = self.alive_players()
            revealed = self.deck.draw_many(len(alive))
            start = alive.index(player)
            queue = [alive[(start + i) % len(alive)].id for i in range(len(alive))]
            self._log(f"{player.name} ouvre le Bazar : {len(revealed)} cartes révélées.")
            self.pending.append(
                Pending(PendingType.GENERAL_STORE, {"cards": revealed, "queue": queue})
            )
        else:
            raise GameError("Carte inconnue.")

    def _play_blue(self, player: Player, card: Card, target_id: Optional[str]) -> None:
        cid = card.card_id
        if cid == "jail":
            target = self._require_target(target_id)
            if target.role == Role.SHERIFF:
                raise GameError("Impossible d'emprisonner le Shérif.")
            if target.has_in_play("jail"):
                raise GameError("Ce joueur est déjà en Prison.")
            player.hand.remove(card)
            target.table.append(card)
            self._log(f"{player.name} jette {target.name} en Prison.")
            return
        if card.is_weapon:
            old = player.weapon
            if old:
                self._discard_from_table(player, old)
            player.hand.remove(card)
            player.table.append(card)
            self._log(f"{player.name} s'équipe : {card.name} (portée {card.range}).")
            return
        if player.has_in_play(cid):
            raise GameError("Tu as déjà cette carte en jeu.")
        player.hand.remove(card)
        player.table.append(card)
        self._log(f"{player.name} pose {card.name} devant lui.")

    def _take_card_from(self, target: Player, target_card_uid: Optional[int]) -> Card:
        """Remove a card from target: a chosen in-play card, or a random hand card."""
        if target_card_uid is not None:
            card = target.table_card(target_card_uid)
            if card is None:
                raise GameError("Cette carte n'est pas en jeu devant la cible.")
            target.table.remove(card)
            return card
        if not target.hand:
            if target.table:
                raise GameError("Sa main est vide : choisis une carte en jeu.")
            raise GameError("Cette cible n'a aucune carte.")
        card = self.rng.choice(target.hand)
        target.hand.remove(card)
        return card

    def _others_in_order(self, player: Player) -> list[Player]:
        alive = self.alive_players()
        start = alive.index(player)
        return [alive[(start + i) % len(alive)] for i in range(1, len(alive))]

    def _push_shot(self, source: Player, targets: list[Player], gatling: bool) -> None:
        self.pending.append(
            Pending(
                PendingType.SHOT,
                {
                    "source_id": source.id,
                    "target_ids": [t.id for t in targets],
                    "gatling": gatling,
                    "barrel_used": [],
                },
            )
        )

    # -------------------------------------------------------------- reactions

    def react(self, pid: str, action: str, card_uid: Optional[int] = None) -> None:
        if self.finished:
            raise GameError("La partie est terminée.")
        if not self.pending:
            raise GameError("Aucune réaction n'est attendue.")
        top = self.pending[-1]
        if top.type == PendingType.SHOT:
            self._react_shot(top, pid, action, card_uid)
        elif top.type == PendingType.INDIANS:
            self._react_indians(top, pid, action, card_uid)
        elif top.type == PendingType.DUEL:
            self._react_duel(top, pid, action, card_uid)
        elif top.type == PendingType.DEATH:
            self._react_death(top, pid, action, card_uid)
        else:
            raise GameError("Utilise le choix de carte du Bazar.")
        self._autoresolve()

    def _current_target(self, pending: Pending) -> Player:
        target_ids = pending.data["target_ids"]
        while target_ids and not self.player_by_id(target_ids[0]).alive:
            target_ids.pop(0)
        if not target_ids:
            raise GameError("Aucune cible en attente.")
        return self.player_by_id(target_ids[0])

    def _react_shot(self, pending: Pending, pid: str, action: str, card_uid: Optional[int]) -> None:
        target = self._current_target(pending)
        if target.id != pid:
            raise GameError("Ce n'est pas à toi de réagir.")
        if action == "barrel":
            if not target.has_in_play("barrel"):
                raise GameError("Tu n'as pas de Tonneau en jeu.")
            if target.id in pending.data["barrel_used"]:
                raise GameError("Tonneau déjà utilisé contre ce Tir.")
            pending.data["barrel_used"].append(target.id)
            check = self.deck.draw_check()
            if check.suit == Suit.HEARTS:
                pending.data["target_ids"].pop(0)
                self._log(f"{target.name} dégaine un Cœur : le Tir ricoche sur le Tonneau !")
            else:
                self._log(f"{target.name} dégaine… raté, le Tonneau ne suffit pas.")
        elif action == "dodge":
            card = target.hand_card(card_uid) if card_uid is not None else None
            if card is None or card.card_id != "dodge":
                raise GameError("Choisis une Esquive de ta main.")
            self._discard_from_hand(target, card)
            pending.data["target_ids"].pop(0)
            self._log(f"{target.name} esquive le Tir !")
        elif action == "take":
            pending.data["target_ids"].pop(0)
            source = self.player_by_id(pending.data["source_id"])
            self._log(f"{target.name} encaisse le Tir : -1 PV.")
            self._apply_damage(target, 1, source)
        else:
            raise GameError("Réaction invalide.")

    def _react_indians(self, pending: Pending, pid: str, action: str, card_uid: Optional[int]) -> None:
        target = self._current_target(pending)
        if target.id != pid:
            raise GameError("Ce n'est pas à toi de réagir.")
        if action == "discard_shot":
            card = target.hand_card(card_uid) if card_uid is not None else None
            if card is None or card.card_id != "shot":
                raise GameError("Choisis un Tir de ta main.")
            self._discard_from_hand(target, card)
            pending.data["target_ids"].pop(0)
            self._log(f"{target.name} repousse l'Embuscade en défaussant un Tir.")
        elif action == "take":
            pending.data["target_ids"].pop(0)
            source = self.player_by_id(pending.data["source_id"])
            self._log(f"{target.name} subit l'Embuscade : -1 PV.")
            self._apply_damage(target, 1, source)
        else:
            raise GameError("Réaction invalide.")

    def _react_duel(self, pending: Pending, pid: str, action: str, card_uid: Optional[int]) -> None:
        current = self.player_by_id(pending.data["current_id"])
        if current.id != pid:
            raise GameError("Ce n'est pas à toi de réagir.")
        source = self.player_by_id(pending.data["source_id"])
        other = self.player_by_id(pending.data["other_id"])
        opponent = other if current is source else source
        if action == "discard_shot":
            card = current.hand_card(card_uid) if card_uid is not None else None
            if card is None or card.card_id != "shot":
                raise GameError("Choisis un Tir de ta main.")
            self._discard_from_hand(current, card)
            pending.data["current_id"] = opponent.id
            self._log(f"{current.name} riposte au Duel : à {opponent.name} de jouer.")
        elif action == "take":
            self.pending.pop()
            self._log(f"{current.name} perd le Duel : -1 PV.")
            self._apply_damage(current, 1, opponent)
        else:
            raise GameError("Réaction invalide.")

    def _react_death(self, pending: Pending, pid: str, action: str, card_uid: Optional[int]) -> None:
        player = self.player_by_id(pending.data["player_id"])
        if player.id != pid:
            raise GameError("Ce n'est pas à toi de réagir.")
        if action == "beer":
            if len(self.alive_players()) <= 2:
                raise GameError("La Gnôle ne peut plus te sauver à 2 joueurs.")
            card = player.hand_card(card_uid) if card_uid is not None else None
            if card is None or card.card_id != "beer":
                raise GameError("Choisis une Gnôle de ta main.")
            self._discard_from_hand(player, card)
            player.hp += 1
            self._log(f"{player.name} avale une Gnôle in extremis.")
            if player.hp >= 1:
                self.pending.pop()
                self._log(f"{player.name} survit avec 1 PV !")
                if pending.data.get("ctx") == "turn_start":
                    self._after_dynamite()
        elif action == "die":
            self._die(pending)
        else:
            raise GameError("Réaction invalide.")

    def pick_store(self, pid: str, card_uid: int) -> None:
        if self.finished:
            raise GameError("La partie est terminée.")
        if not self.pending or self.pending[-1].type != PendingType.GENERAL_STORE:
            raise GameError("Aucun Bazar en cours.")
        data = self.pending[-1].data
        queue: list[str] = data["queue"]
        while queue and not self.player_by_id(queue[0]).alive:
            queue.pop(0)
        if not queue or queue[0] != pid:
            raise GameError("Ce n'est pas à toi de choisir.")
        card = next((c for c in data["cards"] if c.uid == card_uid), None)
        if card is None:
            raise GameError("Cette carte n'est pas dans le Bazar.")
        data["cards"].remove(card)
        player = self.player_by_id(queue.pop(0))
        player.hand.append(card)
        self._log(f"{player.name} prend « {card.name} » au Bazar.")
        self._autoresolve()

    # ------------------------------------------------------- damage and death

    def _apply_damage(self, target: Player, amount: int, source: Optional[Player], ctx: Optional[str] = None) -> None:
        target.hp -= amount
        if target.hp <= 0:
            self.pending.append(
                Pending(
                    PendingType.DEATH,
                    {
                        "player_id": target.id,
                        "source_id": source.id if source else None,
                        "ctx": ctx,
                    },
                )
            )

    def _can_be_saved(self, player: Player) -> bool:
        if len(self.alive_players()) <= 2:
            return False
        return any(c.card_id == "beer" for c in player.hand)

    def _die(self, pending: Pending) -> None:
        assert self.pending[-1] is pending
        self.pending.pop()
        player = self.player_by_id(pending.data["player_id"])
        source_id = pending.data.get("source_id")
        source = self.player_by_id(source_id) if source_id else None
        self._kill(player, source)
        if not self.finished:
            self._cleanup_pending_after_death(player)

    def _kill(self, player: Player, source: Optional[Player]) -> None:
        player.alive = False
        player.role_revealed = True
        player.hp = 0
        for card in list(player.hand):
            self._discard_from_hand(player, card)
        for card in list(player.table):
            self._discard_from_table(player, card)
        self._log(f"{player.name} est éliminé ! C'était : {ROLE_LABELS[player.role]}.")
        if source and source is not player and source.alive:
            if player.role == Role.OUTLAW:
                source.hand.extend(self.deck.draw_many(OUTLAW_KILL_REWARD))
                self._log(f"{source.name} touche la prime : {OUTLAW_KILL_REWARD} cartes.")
            if player.role == Role.DEPUTY and source.role == Role.SHERIFF:
                for card in list(source.hand):
                    self._discard_from_hand(source, card)
                for card in list(source.table):
                    self._discard_from_table(source, card)
                self._log(f"{source.name} a abattu son propre Adjoint : il défausse tout !")
        self._check_win()

    def _cleanup_pending_after_death(self, dead: Player) -> None:
        kept: list[Pending] = []
        for p in self.pending:
            if p.type in (PendingType.SHOT, PendingType.INDIANS):
                p.data["target_ids"] = [t for t in p.data["target_ids"] if t != dead.id]
            elif p.type == PendingType.DUEL:
                if dead.id in (p.data["source_id"], p.data["other_id"]):
                    continue
            elif p.type == PendingType.GENERAL_STORE:
                p.data["queue"] = [q for q in p.data["queue"] if q != dead.id]
            elif p.type == PendingType.DEATH:
                if p.data["player_id"] == dead.id:
                    continue
            kept.append(p)
        self.pending = kept

    def _check_win(self) -> None:
        sheriff = next(p for p in self.players if p.role == Role.SHERIFF)
        alive = self.alive_players()
        team: Optional[str] = None
        if not sheriff.alive:
            if len(alive) == 1 and alive[0].role == Role.RENEGADE:
                team = "renegade"
            else:
                team = "outlaws"
        elif not any(p.role in (Role.OUTLAW, Role.RENEGADE) for p in alive):
            team = "law"
        if team is None:
            return
        self.phase = GamePhase.FINISHED
        self.winning_team = team
        if team == "renegade":
            self.winners = [p.id for p in self.players if p.role == Role.RENEGADE]
            self._log("Le Renégat l'emporte, seul maître de la ville !")
        elif team == "outlaws":
            self.winners = [p.id for p in self.players if p.role == Role.OUTLAW]
            self._log("Le Shérif est mort : les Hors-la-loi l'emportent !")
        else:
            self.winners = [p.id for p in self.players if p.role in (Role.SHERIFF, Role.DEPUTY)]
            self._log("La loi triomphe : le camp du Shérif l'emporte !")
        for p in self.players:
            p.role_revealed = True
        self.pending.clear()

    # ------------------------------------------------------------ resolution

    def _autoresolve(self) -> None:
        """Resolve everything that needs no player input (forced reactions,
        empty queues, dead turn players...). Stops when waiting on a player."""
        for _ in range(1000):  # hard bound, every iteration makes progress
            if self.finished:
                return
            if not self.pending:
                if not self.turn_player.alive:
                    self._advance_turn()
                    continue
                return
            top = self.pending[-1]
            if top.type == PendingType.DEATH:
                player = self.player_by_id(top.data["player_id"])
                if player.hp >= 1:
                    self.pending.pop()
                    continue
                if self._can_be_saved(player):
                    return
                self._die(top)
                continue
            if top.type == PendingType.SHOT:
                if self._auto_shot(top):
                    continue
                return
            if top.type == PendingType.INDIANS:
                if self._auto_indians(top):
                    continue
                return
            if top.type == PendingType.DUEL:
                if self._auto_duel(top):
                    continue
                return
            if top.type == PendingType.GENERAL_STORE:
                if self._auto_store(top):
                    continue
                return
        raise RuntimeError("Auto-resolution did not converge")

    def _auto_shot(self, pending: Pending) -> bool:
        target_ids = pending.data["target_ids"]
        while target_ids and not self.player_by_id(target_ids[0]).alive:
            target_ids.pop(0)
        if not target_ids:
            self.pending.pop()
            return True
        target = self.player_by_id(target_ids[0])
        can_dodge = any(c.card_id == "dodge" for c in target.hand)
        can_barrel = target.has_in_play("barrel") and target.id not in pending.data["barrel_used"]
        if can_dodge or can_barrel:
            return False
        target_ids.pop(0)
        source = self.player_by_id(pending.data["source_id"])
        self._log(f"{target.name} ne peut pas esquiver : -1 PV.")
        self._apply_damage(target, 1, source)
        return True

    def _auto_indians(self, pending: Pending) -> bool:
        target_ids = pending.data["target_ids"]
        while target_ids and not self.player_by_id(target_ids[0]).alive:
            target_ids.pop(0)
        if not target_ids:
            self.pending.pop()
            return True
        target = self.player_by_id(target_ids[0])
        if any(c.card_id == "shot" for c in target.hand):
            return False
        target_ids.pop(0)
        source = self.player_by_id(pending.data["source_id"])
        self._log(f"{target.name} n'a pas de Tir : l'Embuscade le touche, -1 PV.")
        self._apply_damage(target, 1, source)
        return True

    def _auto_duel(self, pending: Pending) -> bool:
        current = self.player_by_id(pending.data["current_id"])
        if any(c.card_id == "shot" for c in current.hand):
            return False
        source = self.player_by_id(pending.data["source_id"])
        other = self.player_by_id(pending.data["other_id"])
        opponent = other if current is source else source
        self.pending.pop()
        self._log(f"{current.name} est à court de Tirs et perd le Duel : -1 PV.")
        self._apply_damage(current, 1, opponent)
        return True

    def _auto_store(self, pending: Pending) -> bool:
        data = pending.data
        queue: list[str] = data["queue"]
        while queue and not self.player_by_id(queue[0]).alive:
            queue.pop(0)
        cards: list[Card] = data["cards"]
        if not queue or not cards:
            for card in cards:
                self.deck.discard(card)
            self.pending.pop()
            return True
        if len(cards) == 1:
            player = self.player_by_id(queue.pop(0))
            card = cards.pop()
            player.hand.append(card)
            self._log(f"{player.name} prend la dernière carte du Bazar : « {card.name} ».")
            return True
        return False

    # ------------------------------------------------------------------ views

    def view_for(self, pid: str) -> dict:
        me = self.player_by_id(pid)
        players = []
        for p in self.players:
            role_visible = (
                p.role == Role.SHERIFF or p.role_revealed or p.id == pid or self.finished
            )
            entry = {
                "id": p.id,
                "name": p.name,
                "hp": p.hp,
                "max_hp": p.max_hp,
                "alive": p.alive,
                "hand_count": len(p.hand),
                "table": [c.to_dict() for c in p.table],
                "role": p.role.value if role_visible else None,
                "is_turn": p is self.turn_player and not self.finished,
            }
            if p.alive and me.alive and p is not me:
                d = self.distance(me, p)
                entry["distance"] = d
                entry["in_range"] = d <= me.attack_range
            players.append(entry)
        view = {
            "phase": self.phase.value,
            "turn_player_id": self.turn_player.id,
            "players": players,
            "you": {
                "id": me.id,
                "role": me.role.value,
                "hp": me.hp,
                "max_hp": me.max_hp,
                "alive": me.alive,
                "hand": [c.to_dict() for c in me.hand],
                "table": [c.to_dict() for c in me.table],
                "attack_range": me.attack_range,
                "can_play_shot": self.shots_played < 1 or me.has_in_play("volcanic"),
            },
            "deck_count": self.deck.draw_count,
            "discard_top": self.deck.discard_top.to_dict() if self.deck.discard_top else None,
            "pending": self._pending_view(pid),
            "log": self.log[-30:],
            "winning_team": self.winning_team,
            "winners": self.winners,
        }
        return view

    def _pending_view(self, pid: str) -> Optional[dict]:
        if not self.pending:
            return None
        top = self.pending[-1]
        data = top.data
        view: dict = {"type": top.type.value}
        if top.type in (PendingType.SHOT, PendingType.INDIANS):
            target_ids = [t for t in data["target_ids"] if self.player_by_id(t).alive]
            responder = target_ids[0] if target_ids else None
            view.update(
                {
                    "source_id": data["source_id"],
                    "responder_id": responder,
                    "gatling": data.get("gatling", False),
                    "remaining": len(target_ids),
                }
            )
            if top.type == PendingType.SHOT and responder == pid:
                target = self.player_by_id(pid)
                view["can_barrel"] = (
                    target.has_in_play("barrel") and pid not in data["barrel_used"]
                )
        elif top.type == PendingType.DUEL:
            view.update(
                {
                    "source_id": data["source_id"],
                    "other_id": data["other_id"],
                    "responder_id": data["current_id"],
                }
            )
        elif top.type == PendingType.DEATH:
            view.update(
                {
                    "responder_id": data["player_id"],
                    "source_id": data.get("source_id"),
                }
            )
        elif top.type == PendingType.GENERAL_STORE:
            queue = [q for q in data["queue"] if self.player_by_id(q).alive]
            view.update(
                {
                    "responder_id": queue[0] if queue else None,
                    "cards": [c.to_dict() for c in data["cards"]],
                    "queue": queue,
                }
            )
        return view
