"""Stage 4 acceptance: WS clients play a turn, reconnection restores state,
and no client ever receives another player's hand or secret role."""

import time

import pytest
from fastapi.testclient import TestClient

import main
from game.engine import GameError
from game.manager import GameManager
from main import app, manager


@pytest.fixture(autouse=True)
def reset_state():
    manager.rooms.clear()
    manager.tokens.clear()
    main.connections.clear()
    yield


def recv_until(ws, msg_type, attempts=80):
    for _ in range(attempts):
        msg = ws.receive_json()
        if msg["type"] == msg_type:
            return msg
    raise AssertionError(f"never received {msg_type}")


def assert_state_is_private(state, viewer_id):
    assert state["you"]["id"] == viewer_id
    for entry in state["players"]:
        assert "hand" not in entry, "another player's hand was leaked"
        if entry["id"] != viewer_id and entry["role"] not in (None, "sheriff"):
            assert entry.get("alive") is False or state["phase"] == "finished"


# ----------------------------------------------------------------- manager

def test_manager_create_and_join():
    m = GameManager()
    room, host = m.create_room("Alice")
    assert len(room.code) == 5
    _, seat = m.join_room(room.code.lower(), "Bob")
    assert len(room.seats) == 2
    assert m.resume(seat.token)[1].player_id == seat.player_id
    assert m.resume("bad-token") is None


def test_manager_start_requires_host_and_player_count():
    m = GameManager()
    room, host = m.create_room("Alice")
    with pytest.raises(GameError):
        m.start_game(room.code, host.player_id)  # only 1 player
    seats = [m.join_room(room.code, f"J{i}")[1] for i in range(3)]
    with pytest.raises(GameError):
        m.start_game(room.code, seats[0].player_id)  # not the host
    m.start_game(room.code, host.player_id)
    assert room.started
    with pytest.raises(GameError):
        m.join_room(room.code, "Late")  # already started


def test_manager_room_full_and_bad_code():
    m = GameManager()
    room, _ = m.create_room("Alice")
    for i in range(6):
        m.join_room(room.code, f"J{i}")
    with pytest.raises(GameError):
        m.join_room(room.code, "TooMany")
    with pytest.raises(GameError):
        m.join_room("XXXXX", "Bob")
    with pytest.raises(GameError):
        m.create_room("   ")


def test_manager_removes_stale_rooms():
    m = GameManager()
    room, seat = m.create_room("Alice")
    assert m.remove_stale(now=time.time() + 3599) == []
    assert m.remove_stale(now=time.time() + 3601) == [room.code]
    assert m.resume(seat.token) is None


# --------------------------------------------------------------- websocket

def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_full_lobby_game_turn_and_reconnect():
    client = TestClient(app)
    with client.websocket_connect("/ws") as w0:
        w0.send_json({"action": "create", "name": "Alice"})
        s0 = recv_until(w0, "session")
        code = s0["code"]
        assert s0["is_host"]

        with client.websocket_connect("/ws") as w1, \
             client.websocket_connect("/ws") as w2, \
             client.websocket_connect("/ws") as w3:
            sockets = [w0, w1, w2, w3]
            sessions = [s0]
            for i, ws in enumerate(sockets[1:], start=1):
                ws.send_json({"action": "join", "code": code, "name": f"J{i}"})
                sessions.append(recv_until(ws, "session"))

            lobby = recv_until(w0, "lobby")
            while len(lobby["players"]) < 4:
                lobby = recv_until(w0, "lobby")
            assert lobby["can_start"]

            # a non-host cannot start
            w1.send_json({"action": "start"})
            assert "hôte" in recv_until(w1, "error")["message"]

            w0.send_json({"action": "start"})
            states = {}
            for ws, session in zip(sockets, sessions):
                msg = recv_until(ws, "state")
                states[session["player_id"]] = msg["state"]
                assert_state_is_private(msg["state"], session["player_id"])

            by_id = {s["player_id"]: ws for s, ws in zip(sessions, sockets)}
            turn_id = next(iter(states.values()))["turn_player_id"]
            turn_ws = by_id[turn_id]

            # play a full first turn: draw, then end turn (discarding down to HP)
            turn_ws.send_json({"action": "draw"})
            state = recv_until(turn_ws, "state")["state"]
            assert state["phase"] == "play"
            assert len(state["you"]["hand"]) == 7  # sheriff: 5 + 2

            turn_ws.send_json({"action": "end_turn"})
            state = recv_until(turn_ws, "state")["state"]
            assert state["phase"] == "discard"
            extra = [c["uid"] for c in state["you"]["hand"][:2]]
            turn_ws.send_json({"action": "discard", "cards": extra})
            state = recv_until(turn_ws, "state")["state"]
            assert state["phase"] == "draw"
            assert state["turn_player_id"] != turn_id

            # invalid action out of turn is rejected without crashing
            not_turn = next(pid for pid in by_id if pid != state["turn_player_id"])
            by_id[not_turn].send_json({"action": "draw"})
            assert recv_until(by_id[not_turn], "error")

            # --- reconnection: drop a player (not the one who just played,
            # whose hand changed) and resume with the token
            victim = next(
                s for s in sessions[1:] if s["player_id"] != turn_id
            )
            by_id[victim["player_id"]].close()
            before = states[victim["player_id"]]["you"]
            with client.websocket_connect("/ws") as w2bis:
                w2bis.send_json({"action": "reconnect", "token": victim["token"]})
                session = recv_until(w2bis, "session")
                assert session["player_id"] == victim["player_id"]
                state = recv_until(w2bis, "state")["state"]
                assert_state_is_private(state, victim["player_id"])
                # same hand as before the disconnection
                assert [c["uid"] for c in state["you"]["hand"]] == [
                    c["uid"] for c in before["hand"]
                ]


def test_reconnect_with_bad_token():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "reconnect", "token": "nope"})
        assert recv_until(ws, "session_expired")


def test_actions_require_joining_first():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"action": "draw"})
        assert recv_until(ws, "error")


def test_malformed_payloads_do_not_kill_the_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws") as w0:
        w0.send_json({"action": "create", "name": "Host"})
        s0 = recv_until(w0, "session")
        import contextlib

        with contextlib.ExitStack() as stack:
            for i in range(3):
                w = stack.enter_context(client.websocket_connect("/ws"))
                w.send_json({"action": "join", "code": s0["code"], "name": f"J{i}"})
                recv_until(w, "session")
            w0.send_json({"action": "start"})
            recv_until(w0, "state")

            bad_payloads = [
                {"action": "play_card"},                     # missing card
                {"action": "play_card", "card": "abc"},      # non-int card
                {"action": "play_card", "card": None},
                {"action": "discard", "cards": ["x", None]},
                {"action": "discard", "cards": "notalist"},
                {"action": "react", "react": "dodge", "card": "zz"},
                {"action": "pick_store"},
                "just a string",                             # not a dict
                ["a", "list"],
                42,
                {"action": None},
                {},
            ]
            for payload in bad_payloads:
                w0.send_json(payload)
                assert recv_until(w0, "error"), f"no error for {payload!r}"

            # the connection must still be usable afterwards
            w0.send_json({"action": "reconnect", "token": s0["token"]})
            assert recv_until(w0, "session")
