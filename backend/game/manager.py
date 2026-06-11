"""GameManager: active rooms, join codes, session tokens, lifecycle.

Pure orchestration — no FastAPI / WebSocket imports, so it stays testable.
"""

from __future__ import annotations

import random
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .engine import GameEngine, GameError

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # unambiguous characters
CODE_LENGTH = 5
MIN_PLAYERS = 4
MAX_PLAYERS = 7
GAME_TTL_SECONDS = 3600  # rooms are dropped after 1h of inactivity
MAX_NAME_LENGTH = 20


@dataclass
class Seat:
    player_id: str
    name: str
    token: str
    connected: bool = False


@dataclass
class GameRoom:
    code: str
    host_id: str
    seats: list[Seat] = field(default_factory=list)
    engine: Optional[GameEngine] = None
    last_activity: float = field(default_factory=time.time)

    @property
    def started(self) -> bool:
        return self.engine is not None

    def touch(self) -> None:
        self.last_activity = time.time()

    def seat_by_id(self, player_id: str) -> Optional[Seat]:
        return next((s for s in self.seats if s.player_id == player_id), None)

    def lobby_view(self) -> dict:
        return {
            "code": self.code,
            "host_id": self.host_id,
            "started": self.started,
            "players": [
                {"id": s.player_id, "name": s.name, "connected": s.connected}
                for s in self.seats
            ],
            "can_start": MIN_PLAYERS <= len(self.seats) <= MAX_PLAYERS,
        }


class GameManager:
    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.rooms: dict[str, GameRoom] = {}
        self.tokens: dict[str, tuple[str, str]] = {}  # token -> (code, player_id)

    # ----------------------------------------------------------------- rooms

    def create_room(self, name: str) -> tuple[GameRoom, Seat]:
        code = self._new_code()
        seat = self._new_seat(name)
        room = GameRoom(code=code, host_id=seat.player_id, seats=[seat])
        self.rooms[code] = room
        self.tokens[seat.token] = (code, seat.player_id)
        return room, seat

    def join_room(self, code: str, name: str) -> tuple[GameRoom, Seat]:
        room = self.rooms.get(code.strip().upper())
        if room is None:
            raise GameError("Partie introuvable : vérifie le code.")
        if room.started:
            raise GameError("Cette partie a déjà commencé.")
        if len(room.seats) >= MAX_PLAYERS:
            raise GameError("Cette partie est complète (7 joueurs max).")
        seat = self._new_seat(name)
        room.seats.append(seat)
        self.tokens[seat.token] = (room.code, seat.player_id)
        room.touch()
        return room, seat

    def resume(self, token: str) -> Optional[tuple[GameRoom, Seat]]:
        entry = self.tokens.get(token)
        if entry is None:
            return None
        code, player_id = entry
        room = self.rooms.get(code)
        if room is None:
            return None
        seat = room.seat_by_id(player_id)
        if seat is None:
            return None
        room.touch()
        return room, seat

    def start_game(self, code: str, player_id: str) -> GameRoom:
        room = self.rooms.get(code)
        if room is None:
            raise GameError("Partie introuvable.")
        if room.started:
            raise GameError("La partie a déjà commencé.")
        if player_id != room.host_id:
            raise GameError("Seul l'hôte peut lancer la partie.")
        if not MIN_PLAYERS <= len(room.seats) <= MAX_PLAYERS:
            raise GameError(f"Il faut entre {MIN_PLAYERS} et {MAX_PLAYERS} joueurs.")
        room.engine = GameEngine(
            [(s.player_id, s.name) for s in room.seats], rng=self.rng
        )
        room.touch()
        return room

    def remove_stale(self, now: Optional[float] = None) -> list[str]:
        now = now if now is not None else time.time()
        stale = [
            code
            for code, room in self.rooms.items()
            if now - room.last_activity > GAME_TTL_SECONDS
        ]
        for code in stale:
            room = self.rooms.pop(code)
            for seat in room.seats:
                self.tokens.pop(seat.token, None)
        return stale

    # --------------------------------------------------------------- helpers

    def _new_code(self) -> str:
        for _ in range(100):
            code = "".join(self.rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self.rooms:
                return code
        raise RuntimeError("Could not allocate a room code")

    @staticmethod
    def _new_seat(name: str) -> Seat:
        name = name.strip()[:MAX_NAME_LENGTH]
        if not name:
            raise GameError("Choisis un pseudo.")
        return Seat(
            player_id=uuid.uuid4().hex[:8],
            name=name,
            token=secrets.token_urlsafe(16),
        )
