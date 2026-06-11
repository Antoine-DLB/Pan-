# Far West Showdown

Jeu de cartes western multijoueur en temps réel. Chaque joueur utilise son
téléphone via navigateur : un joueur crée une partie, obtient un code court,
les autres rejoignent avec ce code.

- **Backend** : Python 3.12, FastAPI, WebSockets natifs
- **Frontend** : React + Vite, mobile-first
- **État** : en mémoire serveur (parties éphémères, pas de base de données)

## Développement

### Avec Docker (recommandé)

```bash
docker compose up
```

- Frontend : http://localhost:5173
- Backend : http://localhost:8000 (health check : http://localhost:8000/health)

Le hot reload est actif sur les deux services.

### Sans Docker

Backend :

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend :

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

## Production

Build multi-stage (React compilé puis servi en statique par FastAPI) :

```bash
cp .env.example .env   # puis éditer DOMAIN
docker compose -f docker-compose.prod.yml up -d --build
```

Le service expose des labels Traefik (HTTPS + WebSockets `wss://`).

## Règles (V1)

4 à 7 joueurs, rôles cachés (Shérif public, Adjoints, Hors-la-loi, Renégat).
Voir `CLAUDE.md` pour les règles complètes et la liste des cartes. Les noms
des cartes sont définis dans `backend/game/cards.json` et modifiables sans
toucher au code.
