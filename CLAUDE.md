# CLAUDE.md — Far West Showdown (jeu de cartes western multijoueur)

## Contexte du projet

Web app multijoueur temps réel inspirée des mécaniques classiques des jeux de rôles cachés western (type shérif / hors-la-loi). Chaque joueur utilise son propre téléphone via navigateur. Un joueur crée une partie, obtient un code court, les autres rejoignent avec ce code (modèle Kahoot/Jackbox).

**Important — Propriété intellectuelle** : ce projet réplique des mécaniques de jeu (non protégeables) mais NE DOIT PAS utiliser le nom, les illustrations, ni les textes exacts d'un jeu commercial existant. Tous les noms de cartes affichés et visuels sont des créations originales. Les noms de cartes sont externalisés dans un fichier de configuration pour pouvoir être modifiés facilement.

## Stack technique

- **Backend** : Python 3.12, FastAPI, WebSockets natifs (pas de Socket.IO), uvicorn
- **Frontend** : React + Vite, mobile-first, pas de librairie UI lourde (CSS modules ou Tailwind)
- **État du jeu** : en mémoire serveur (pas de base de données en V1, parties éphémères)
- **Déploiement** : Docker multi-stage (build React → servi par FastAPI en statique), Docker Compose, Traefik (VPS Hostinger existant)
- **Pas de dépendances inutiles** : pas de Redis, pas de Celery, pas d'ORM en V1

## Architecture

```
project/
├── backend/
│   ├── main.py              # FastAPI app, routes HTTP + endpoint WebSocket
│   ├── game/
│   │   ├── manager.py       # GameManager : parties actives, codes, joueurs connectés
│   │   ├── engine.py        # GameEngine : machine à états, validation des coups
│   │   ├── deck.py          # Deck : pioche, défausse, mélange, recyclage
│   │   ├── models.py        # Player, Card, GameState (dataclasses ou Pydantic)
│   │   └── cards.json       # Définition des cartes : id, nom affiché, type, effet, quantité
│   ├── tests/               # pytest : moteur de règles testé sans réseau
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── screens/         # Home, Lobby, Game
│   │   ├── components/      # Hand, PlayerArc, ReactionModal, HealthBar...
│   │   └── hooks/useGameSocket.js   # connexion WS, reconnexion, état du jeu
│   └── package.json
├── docker-compose.yml
├── Dockerfile
└── CLAUDE.md
```

## Principes de conception (non négociables)

1. **Serveur autoritaire** : toute la logique de jeu vit côté serveur. Le client n'envoie que des intentions (`play_card`, `pass`, `react`), le serveur valide et renvoie l'état.
2. **État filtré par joueur** : le serveur n'envoie JAMAIS à un client la main ou le rôle secret d'un autre joueur. Chaque client reçoit une vue personnalisée de l'état.
3. **Machine à états explicite** : les phases et sous-états sont des enums, chaque transition est validée. Aucune logique de règle dans les handlers WebSocket.
4. **Moteur testable sans réseau** : `engine.py` ne connaît ni FastAPI ni les WebSockets. Les tests pytest jouent des parties complètes en appelant directement le moteur.
5. **Reconnexion** : chaque joueur reçoit un token de session à la connexion. Recharger la page → reconnexion à sa place dans la partie en cours.
6. **Séparation des concerns** : pattern services/models déjà utilisé dans mes autres projets.

## Règles du jeu — V1

### Mise en place
- 4 à 7 joueurs
- Rôles distribués aléatoirement selon le nombre de joueurs :
  - 4 joueurs : 1 Shérif, 2 Hors-la-loi, 1 Renégat
  - 5 joueurs : 1 Shérif, 1 Adjoint, 2 Hors-la-loi, 1 Renégat
  - 6 joueurs : 1 Shérif, 1 Adjoint, 3 Hors-la-loi, 1 Renégat
  - 7 joueurs : 1 Shérif, 2 Adjoints, 3 Hors-la-loi, 1 Renégat
- Seul le rôle du Shérif est public. Les autres rôles sont secrets.
- V1 sans personnages : tous les joueurs ont 4 points de vie (PV), le Shérif en a 5.
- Chaque joueur pioche autant de cartes que ses PV de départ.
- Le Shérif commence.

### Objectifs de victoire
- **Shérif + Adjoints** : éliminer tous les Hors-la-loi ET le Renégat
- **Hors-la-loi** : éliminer le Shérif
- **Renégat** : être le dernier survivant (éliminer tout le monde, le Shérif en dernier)
- Si le Shérif meurt et que le Renégat est le seul autre survivant → le Renégat gagne. Sinon → les Hors-la-loi gagnent (même morts).
- Si tous les Hors-la-loi et le Renégat sont morts → le camp du Shérif gagne.
- Cas particulier : si le Shérif élimine lui-même un de ses Adjoints, il défausse toute sa main et ses cartes en jeu.
- Éliminer un Hors-la-loi (par n'importe qui) → le tueur pioche 3 cartes.

### Tour de jeu (3 phases)
1. **Pioche** : piocher 2 cartes
2. **Jeu** : jouer autant de cartes que souhaité, avec 2 limites :
   - 1 seule carte "Tir" (Bang) par tour
   - 1 seule arme en jeu à la fois (poser une nouvelle arme défausse l'ancienne)
3. **Défausse** : se défausser pour ne pas dépasser un nombre de cartes en main égal à ses PV actuels

### Distance
- Les joueurs sont assis en cercle virtuel (ordre de connexion au lobby). Les joueurs éliminés ne comptent plus dans le calcul.
- Distance de base = nombre minimal de sièges entre deux joueurs (dans les deux sens).
- Modificateurs :
  - Cible équipée d'un "Cheval" (Mustang) : +1 pour la voir
  - Attaquant équipé d'une "Longue-vue" (Lunette) : -1 pour viser les autres
- Une cible est atteignable si distance ≤ portée de l'arme de l'attaquant (portée 1 sans arme).

### Cartes V1 (deck de 80 cartes)
⚠️ Vérifier les quantités exactes contre les règles officielles avant implémentation : https://www.dvgiochi.com/giochi/bang/download/Bang_rules_FRA.pdf

Les noms affichés ci-dessous sont des noms originaux. Les IDs internes sont en anglais générique.

**Cartes marron (action, défaussées après usage) :**
| ID interne | Nom affiché | Qté | Effet |
|---|---|---|---|
| shot | Tir ! | 25 | Inflige 1 dégât à une cible à portée. La cible peut jouer "Esquive" pour annuler. |
| dodge | Esquive | 12 | Annule un Tir. Jouable uniquement en réaction. |
| beer | Gnôle | 6 | Récupère 1 PV (max PV de départ). Sans effet à 2 joueurs restants. Peut être jouée hors tour pour annuler le dégât fatal. |
| panic | Vol à la tire | 4 | Prend une carte (main ou en jeu) à un joueur à distance 1. |
| cat_balou | Sabotage | 4 | Force un joueur (n'importe quelle distance) à défausser une carte. |
| stagecoach | Diligence | 2 | Pioche 2 cartes. |
| wells_fargo | Convoi d'or | 1 | Pioche 3 cartes. |
| gatling | Mitraille | 1 | Équivaut à un Tir contre TOUS les autres joueurs (ne compte pas dans la limite de 1 Tir/tour). |
| indians | Embuscade | 2 | Tous les autres joueurs défaussent un Tir ou perdent 1 PV. |
| duel | Duel | 3 | La cible et l'attaquant défaussent alternativement des Tirs (la cible commence). Le premier qui ne peut pas perd 1 PV. |
| general_store | Bazar | 2 | Révéler autant de cartes que de joueurs en vie ; chacun en choisit une, en commençant par le joueur actif. |
| saloon | Tournée générale | 1 | Tous les joueurs en vie récupèrent 1 PV. |

**Cartes bleues (équipement, posées devant soi) :**
| ID interne | Nom affiché | Qté | Effet |
|---|---|---|---|
| volcanic | Pétoire rapide | 2 | Arme portée 1, mais Tirs illimités par tour. |
| schofield | Revolver | 3 | Arme portée 2. |
| remington | Carabine courte | 1 | Arme portée 3. |
| rev_carabine | Carabine longue | 1 | Arme portée 4. |
| winchester | Fusil | 1 | Arme portée 5. |
| mustang | Cheval | 2 | Les autres vous voient à distance +1. |
| scope | Longue-vue | 1 | Vous voyez les autres à distance -1. |
| barrel | Tonneau | 2 | Quand visé par un Tir : "dégainer" (révéler la 1re carte de la pioche). Si Cœur → le Tir est annulé. |
| jail | Prison | 3 | Se pose devant un autre joueur (pas le Shérif). À son tour : il dégaine, Cœur → il défausse la Prison et joue normalement, sinon il défausse la Prison et passe son tour. |
| dynamite | Dynamite | 1 | Reste devant le joueur. À son tour, avant tout : dégainer. Si 2-9 de Pique → explose, 3 dégâts, défaussée. Sinon → passe au joueur suivant. |

- Chaque carte porte aussi une valeur et une couleur (♥♦♣♠) utilisées pour "dégainer" (révéler la carte du dessus de la pioche puis la défausser).
- Pioche vide → mélanger la défausse pour reformer la pioche.

### Gestion de la mort
- Un joueur à 0 PV peut jouer immédiatement une "Gnôle" pour revenir à 1 PV (autant de fois qu'il en a).
- Joueur éliminé : défausse toutes ses cartes, son rôle est révélé à tous.

## V2 — À FAIRE PLUS TARD (NE PAS IMPLÉMENTER MAINTENANT)

⚠️ La V2 ne démarre que lorsque la V1 est stable, testée et déployée en production sur le VPS. Ne pas anticiper de code V2 dans la V1, MAIS concevoir le moteur pour que l'ajout de pouvoirs soit propre (ex: système de hooks/événements dans le moteur : `on_draw`, `on_hit`, `on_empty_hand`, etc.).

Contenu V2 :
- **16 personnages avec pouvoirs uniques** (PV variables 3 ou 4, capacités passives ou déclenchées) — équivalents fonctionnels des personnages classiques, avec noms originaux
- Chaque joueur reçoit un personnage aléatoire en début de partie (ou choix entre 2)
- Exemples de types de pouvoirs à supporter : pioche modifiée, seconde chance sur "dégainer", Tirs comptant comme Esquives et inversement, pioche quand touché, voler des cartes au lieu de Tirer, etc.
- Améliorations UX : animations, sons, historique des actions, spectateur après élimination

## Étapes de développement V1

### Étape 1 — Squelette projet + environnement
- Initialiser backend FastAPI (route `/health`) et frontend Vite React (page d'accueil placeholder)
- `docker-compose.yml` de dev (hot reload backend et frontend)
- **Critères d'acceptation** : `docker compose up` → frontend accessible, `/health` répond 200, README avec commandes de dev

### Étape 2 — Modèles et deck
- `models.py` : Card, Player, Role (enum), GamePhase (enum), GameState
- `cards.json` complet (80 cartes avec valeurs/couleurs réparties)
- `deck.py` : mélange, pioche, défausse, recyclage automatique, "dégainer"
- **Critères d'acceptation** : tests pytest → le deck contient 80 cartes, pioche/recyclage fonctionnent, aucune carte dupliquée ou perdue après 200 pioches

### Étape 3 — Moteur de règles (cœur du projet)
- `engine.py` : machine à états complète
  - Distribution rôles + cartes selon nombre de joueurs
  - Phases du tour, validation de chaque coup
  - Sous-états de réaction : Tir en attente d'Esquive/Tonneau, Duel, Embuscade, Mitraille, Bazar, mort en attente de Gnôle
  - Distance et portée
  - Prison et Dynamite en début de tour
  - Conditions de victoire et fins de partie
- **Critères d'acceptation** : suite pytest jouant des scénarios complets (partie à 4, à 7, victoire de chaque camp, Duel, Dynamite qui tourne, mort du Shérif par le Renégat seul, Shérif tuant son Adjoint). Couverture du moteur ≥ 80%.

### Étape 4 — Couche réseau (GameManager + WebSockets)
- `manager.py` : créer partie (code 5 caractères), rejoindre, démarrer (hôte uniquement, 4-7 joueurs)
- Endpoint WS : réception des intentions, appel moteur, broadcast des états filtrés par joueur
- Tokens de session + reconnexion (rechargement de page → retour dans la partie)
- Timeout : partie supprimée après 1h d'inactivité
- **Critères d'acceptation** : test d'intégration avec plusieurs clients WS simulés jouant un tour complet ; un client déconnecté/reconnecté retrouve son état exact ; un joueur ne reçoit jamais la main/rôle d'un autre (test explicite)

### Étape 5 — Frontend : accueil et lobby
- Écran d'accueil : pseudo + créer/rejoindre
- Lobby : liste des joueurs en temps réel, bouton "Lancer" pour l'hôte (actif à 4+ joueurs)
- `useGameSocket.js` : connexion, reconnexion automatique, état global
- **Critères d'acceptation** : 4 onglets navigateur peuvent créer/rejoindre/lancer une partie ; mobile-first vérifié (375px de large)

### Étape 6 — Frontend : écran de jeu
- Layout mobile : adversaires en haut (PV, équipements, nb de cartes en main, rôle si Shérif ou révélé), zone centrale (défausse, pioche, indicateur de tour), sa main en bas (cartes scrollables horizontalement)
- Interactions : taper une carte → la jouer (avec sélection de cible si nécessaire, cibles hors de portée grisées)
- Modale de réaction avec compte à rebours visuel (ex: "X te tire dessus !")
- Écrans de fin : rôles révélés, camp vainqueur
- **Critères d'acceptation** : partie complète jouable à 4 sur téléphones ; toutes les cartes V1 jouables via l'UI ; aucune action invalide possible côté UI (et de toute façon rejetée côté serveur)

### Étape 7 — Déploiement production
- Dockerfile multi-stage : build React → fichiers statiques servis par FastAPI
- `docker-compose.prod.yml` avec labels Traefik (même pattern que le Wine Cellar Agent), sous-domaine dédié, HTTPS
- Variables d'environnement via `.env` (jamais commitées)
- **Critères d'acceptation** : partie jouable depuis 4 téléphones en 4G sur l'URL publique ; WebSockets fonctionnels derrière Traefik (wss://)

## Conventions

- Code et commentaires en anglais, UI en français
- Commits atomiques par étape : `feat(stage-N): description`
- Ne jamais passer à l'étape suivante sans validation des critères d'acceptation
- Lancer `pytest` avant chaque commit touchant au backend
- En cas de doute sur une règle du jeu : me demander plutôt qu'inventer
