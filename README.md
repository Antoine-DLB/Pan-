# Far West Showdown

Real-time multiplayer western card game. Each player uses their own phone
through the browser: one player creates a game and gets a short code, the
others join with that code (Kahoot/Jackbox model).

- **Backend**: Python 3.12, FastAPI, native WebSockets
- **Frontend**: React + Vite, mobile-first
- **State**: in-memory on the server (ephemeral games, no database)

## Development

### With Docker (recommended)

```bash
docker compose up
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (health check: http://localhost:8000/health)

Hot reload is enabled on both services.

### Without Docker

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
pytest
```

To run a large randomized simulation campaign (random agents play complete
games while invariants are checked after every action):

```bash
cd backend
python tests/simulate.py 5000
```

## Production

Multi-stage build (React compiled, then served statically by FastAPI):

```bash
cp .env.example .env   # then edit DOMAIN
docker compose -f docker-compose.prod.yml up -d --build
```

The service exposes Traefik labels (HTTPS + `wss://` WebSockets).

## Rules (V1)

4 to 7 players with hidden roles (the Sheriff is public; Deputies, Outlaws
and the Renegade are secret). See `CLAUDE.md` for the complete rules and the
full card list. Card display names live in `backend/game/cards.json` and can
be changed without touching the code.

## Architecture notes

- **Authoritative server**: all game logic runs server-side. Clients only
  send intents (`play_card`, `react`, ...); the server validates and
  broadcasts a per-player filtered view, so a client never receives another
  player's hand or secret role.
- **Engine is network-free**: `backend/game/engine.py` knows nothing about
  FastAPI or WebSockets and is driven directly by the pytest suite.
- **Reconnection**: each player gets a session token; reloading the page
  rejoins the game in progress at the same seat.
