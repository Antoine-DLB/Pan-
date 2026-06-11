"""Far West Showdown — FastAPI app: HTTP routes + WebSocket endpoint.

All game logic lives in game/engine.py; this layer only translates
WebSocket intents into engine calls and broadcasts filtered views.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from game.engine import GameError
from game.manager import GameManager, GameRoom, Seat

CLEANUP_INTERVAL_SECONDS = 60

manager = GameManager()
# code -> {player_id -> WebSocket}; kept out of GameRoom (pure data)
connections: dict[str, dict[str, WebSocket]] = {}


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Far West Showdown", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "rooms": len(manager.rooms)}


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        for code in manager.remove_stale():
            connections.pop(code, None)


# ------------------------------------------------------------------ helpers

async def _send(ws: WebSocket, payload: dict) -> None:
    with contextlib.suppress(Exception):
        await ws.send_json(payload)


async def _broadcast_lobby(room: GameRoom) -> None:
    payload = {"type": "lobby", **room.lobby_view()}
    for ws in list(connections.get(room.code, {}).values()):
        await _send(ws, payload)


async def _broadcast_state(room: GameRoom) -> None:
    if room.engine is None:
        return
    for player_id, ws in list(connections.get(room.code, {}).items()):
        view = room.engine.view_for(player_id)
        await _send(ws, {"type": "state", "code": room.code, "state": view})


async def _attach(ws: WebSocket, room: GameRoom, seat: Seat) -> None:
    """Register the socket for this player, replacing any previous one."""
    peers = connections.setdefault(room.code, {})
    old = peers.get(seat.player_id)
    if old is not None and old is not ws:
        with contextlib.suppress(Exception):
            await old.close()
    peers[seat.player_id] = ws
    seat.connected = True


def _apply_game_action(room: GameRoom, player_id: str, msg: dict) -> None:
    engine = room.engine
    if engine is None:
        raise GameError("La partie n'a pas encore commencé.")
    action = msg.get("action")
    if action == "draw":
        engine.draw_cards(player_id)
    elif action == "play_card":
        engine.play_card(
            player_id,
            int(msg["card"]),
            target_id=msg.get("target"),
            target_card_uid=int(msg["target_card"]) if msg.get("target_card") is not None else None,
        )
    elif action == "end_turn":
        engine.end_turn(player_id)
    elif action == "discard":
        engine.discard_cards(player_id, [int(uid) for uid in msg.get("cards", [])])
    elif action == "react":
        card = msg.get("card")
        engine.react(player_id, msg.get("react", ""), int(card) if card is not None else None)
    elif action == "pick_store":
        engine.pick_store(player_id, int(msg["card"]))
    else:
        raise GameError("Action inconnue.")


# ----------------------------------------------------------------- websocket

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    room: GameRoom | None = None
    seat: Seat | None = None
    try:
        while True:
            try:
                msg = await ws.receive_json()
            except ValueError:
                await _send(ws, {"type": "error", "message": "Message invalide."})
                continue
            action = msg.get("action")
            try:
                if action == "create":
                    room, seat = manager.create_room(msg.get("name", ""))
                    await _attach(ws, room, seat)
                    await _send_session(ws, room, seat)
                    await _broadcast_lobby(room)
                elif action == "join":
                    room, seat = manager.join_room(msg.get("code", ""), msg.get("name", ""))
                    await _attach(ws, room, seat)
                    await _send_session(ws, room, seat)
                    await _broadcast_lobby(room)
                elif action == "reconnect":
                    resumed = manager.resume(msg.get("token", ""))
                    if resumed is None:
                        await _send(ws, {"type": "session_expired"})
                        continue
                    room, seat = resumed
                    await _attach(ws, room, seat)
                    await _send_session(ws, room, seat)
                    if room.started:
                        view = room.engine.view_for(seat.player_id)
                        await _send(ws, {"type": "state", "code": room.code, "state": view})
                        await _broadcast_lobby(room)
                    else:
                        await _broadcast_lobby(room)
                elif room is None or seat is None:
                    await _send(ws, {"type": "error", "message": "Rejoins d'abord une partie."})
                elif action == "start":
                    manager.start_game(room.code, seat.player_id)
                    await _broadcast_state(room)
                else:
                    room.touch()
                    _apply_game_action(room, seat.player_id, msg)
                    await _broadcast_state(room)
            except GameError as exc:
                await _send(ws, {"type": "error", "message": str(exc)})
    except WebSocketDisconnect:
        pass
    finally:
        if room is not None and seat is not None:
            peers = connections.get(room.code, {})
            if peers.get(seat.player_id) is ws:
                peers.pop(seat.player_id, None)
                seat.connected = False
                if room.started:
                    await _broadcast_state(room)
                await _broadcast_lobby(room)


async def _send_session(ws: WebSocket, room: GameRoom, seat: Seat) -> None:
    await _send(
        ws,
        {
            "type": "session",
            "token": seat.token,
            "player_id": seat.player_id,
            "code": room.code,
            "is_host": seat.player_id == room.host_id,
        },
    )


# ------------------------------------------------------------ static frontend

static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
