# TableChat — V1

TableChat est une application web française de jeux de société entre amis. Elle propose les Échecs et l’Awalé : comptes, amis, invitations privées, parties serveur autoritaires, adversaires IA, chat persistant et leçons interactives.

## Architecture retenue

- `frontend/` : Next.js 15 App Router, React 19, TypeScript strict, `react-chessboard` et `chess.js`.
- `backend/` : Django 5.1, Django REST Framework, Channels/ASGI et Celery.
- PostgreSQL : source de vérité pour comptes, relations, parties, messages et progression.
- Redis : couche Channels et broker Celery, jamais stockage métier unique.
- `games` reste générique (type de jeu, partie, participants, invitation) ; `chess_game` contient les règles et états d’échecs, tandis que `awale` possède son propre moteur Abapa, son état persistant et son IA alpha-bêta.

Les sessions Django avec cookie HttpOnly sont utilisées. Le frontend récupère d’abord un cookie CSRF via `GET /api/auth/csrf/`, envoie `X-CSRFToken` pour toute mutation et inclut les cookies dans les appels HTTP. Les WebSockets réutilisent le cookie de session via `AuthMiddlewareStack` et vérifient l’appartenance à la partie ou à la conversation avant d’accepter la connexion.

## Démarrage Docker (recommandé)

Prérequis : Docker Desktop et Docker Compose.

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item .env.example .env
docker compose up --build
docker compose exec backend python manage.py seed_demo
```

Ouvrir `http://localhost:3000`. Deux comptes de démonstration sont créés :

- `alice@tablechat.local` / `TableChat123!`
- `camille@tablechat.local` / `TableChat123!`

Le seed est idempotent et crée aussi leur amitié, une conversation avec message et cinq leçons.

## Démarrage local sans Docker

Le mode local utilise SQLite si `POSTGRES_HOST` n’est pas défini. PostgreSQL demeure le stockage de production et du Compose.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
$env:USE_INMEMORY_CHANNELS="true"
cd backend
python manage.py migrate
python manage.py seed_demo
daphne -b 127.0.0.1 -p 8000 tablechat.asgi:application
```

Dans un second terminal :

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Les fichiers Stockfish navigateur sont déjà présents dans `frontend/public/stockfish/`. Pour les régénérer depuis le paquet verrouillé :

```powershell
Copy-Item node_modules/stockfish/src/stockfish-nnue-16-single.js public/stockfish/stockfish.js
Copy-Item node_modules/stockfish/src/stockfish-nnue-16-single.wasm public/stockfish/stockfish-nnue-16-single.wasm
```

Le binaire Stockfish serveur est installé automatiquement par le Dockerfile Debian (`apt install stockfish`). Hors Docker, installer Stockfish puis renseigner son chemin dans `STOCKFISH_PATH`. Les niveaux `Découverte` et `Club` utilisent le moteur WebAssembly dans un Web Worker ; en cas d’indisponibilité, le serveur prend le relais. `Confirmé` et `Expert` utilisent le binaire serveur avec temps, profondeur, hash et threads bornés. Ces noms ne représentent pas un Elo officiel.

## Routes HTTP principales

| Domaine | Routes |
|---|---|
| Auth | `GET csrf/`, `POST register/`, `POST login/`, `POST logout/`, `GET/PATCH me/`, `GET users/?q=` |
| Amis | `GET/POST /api/friends/`, `POST /api/friends/<id>/{accept,decline,cancel,remove}/` |
| Parties | `GET/POST /api/games/`, `GET /api/games/<id>/`, `POST /api/games/<id>/{resign,draw}/` |
| Invitations | `GET/POST /api/games/invitations/`, `POST .../<id>/{accept,decline,cancel}/` |
| Échecs | `GET .../games/<id>/state/`, `POST .../moves/`, `POST .../ai-turn/`, `POST .../engine/` |
| Awalé | `GET /api/awale/games/<id>/state/`, `POST .../moves/`, `POST .../ai-turn/` |
| Chat | `GET/POST conversations/`, `GET/POST .../messages/`, `POST .../read/` |
| Leçons | `GET lessons/`, `GET lessons/<id>/`, `POST lessons/<id>/{start,attempt,hint,undo}/` |

Toutes les routes sont préfixées par `/api/`. Les listes et historiques sont paginés (30 éléments par défaut).

## WebSockets

- `/ws/games/<uuid>/` : le client reçoit `game.state`, envoie `game.move` avec `{uci, request_id, revision}` ou `game.sync`. Les erreurs arrivent via `game.error`.
- `/ws/awale/games/<uuid>/` : le client reçoit `awale.state`, envoie `awale.move` avec `{pit, request_id, revision}` ou `awale.sync`.
- `/ws/conversations/<uuid>/` : le client envoie/reçoit `chat.message` avec `{content, client_id}`. `client_id` déduplique les reprises ; la fréquence et la longueur sont bornées.

Pour un coup multijoueur, le serveur verrouille la ligne `ChessState`, revérifie participant, statut, tour, révision et légalité avec `python-chess`, calcule SAN/FEN/PGN et fin de partie, incrémente la révision, persiste le tout puis diffuse l’état confirmé. Un FEN client n’est jamais accepté comme nouvel état.

Pour l’Awalé, le serveur applique le règlement immuable `abapa_tablechat_v1` : semis avec saut du trou d’origine, captures en chaîne, annulation d’une capture affamant l’adversaire, obligation de nourrir, majorité à 25 graines, décompte final et troisième répétition TableChat. La somme plateau + scores est vérifiée à 48 graines à chaque transition.

## Tester deux sessions

1. Ouvrir Chrome sur `http://localhost:3000` et se connecter avec Alice.
2. Ouvrir une fenêtre privée ou un autre navigateur et se connecter avec Camille.
3. Dans **Amis**, inviter Camille depuis Alice ; accepter depuis Camille.
4. Les deux navigateurs sont redirigés vers la même partie. Jouer un coup puis actualiser l’autre fenêtre pour vérifier la reprise complète.
5. Couper brièvement le réseau : l’indicateur passe à « Reconnexion… » et aucun abandon automatique n’est déclenché.

Pour deux appareils du même réseau, le frontend utilise automatiquement le nom d’hôte depuis lequel il est ouvert. Django doit néanmoins écouter sur `0.0.0.0` et autoriser l’adresse ainsi que l’origine LAN.

Sous Windows, le script suivant détecte automatiquement l’adresse du réseau principal, configure Django/CSRF/CORS, écoute sur toutes les interfaces et lance les deux services :

```powershell
.\scripts\start-lan.ps1
```

Une adresse peut aussi être imposée : `.\scripts\start-lan.ps1 -LanAddress 192.168.1.11`. Le téléphone et l’ordinateur doivent être sur le même Wi‑Fi. Si Windows affiche une demande de pare-feu, autoriser Python et Node.js uniquement sur les réseaux privés.

## Tests et vérifications

```powershell
cd backend
$env:USE_INMEMORY_CHANNELS="true"
..\.venv\Scripts\python -m pytest -q
..\.venv\Scripts\python manage.py check

cd ../frontend
npm run build
```

Les tests ciblent la persistance/déduplication d’un coup légal, le refus des coups illégaux, hors-tour et tiers, le roque, la prise en passant, le mat, l’auto-ajout, les demandes d’amitié croisées et une leçon guidée complète. `python-chess` gère aussi promotion, pat, répétitions et nullités automatiques conformément à ses règles.

## Pédagogie guidée

Le parcours reprend les principes d’un coach virtuel pas à pas, sans copier de contenu ou d’identité tiers :

- progression séquentielle avec leçon recommandée, états verrouillé/disponible/terminé ;
- objectif annoncé et message du « maître du club » adapté après chaque coup ;
- mauvais coup expliqué sans avancer la position ;
- réponses adverses prévues jouées automatiquement dans les variantes à plusieurs coups ;
- indices progressifs, du concept jusqu’au coup concret ;
- reprise exacte de la position, retour au coup précédent et redémarrage complet ;
- validation et progression persistées côté serveur.

## Tâches Celery et politique de nettoyage

Celery Beat exécute chaque minute `games.tasks.expire_invitations`, qui marque comme expirées les invitations arrivées à échéance (24 h). Les parties, conversations et messages ne sont pas supprimés automatiquement. Toute future politique de rétention devra être explicite et ne devra jamais effacer l’historique à la suppression d’une amitié. Les analyses Stockfish différées ont une limite dure de 8 secondes et deux workers dans le Compose.

## Maquettes et licences

Les trois maquettes et leurs prompts sont dans [`docs/mockups`](docs/mockups/PROMPTS.md). La position fonctionnelle de la leçon est toujours dérivée de la FEN exacte, pas de l’image générée.

- Django (BSD-3-Clause), DRF (BSD), Channels (BSD), Celery (BSD), `python-chess` (GPL-3.0), paquet Python `stockfish` (MIT).
- Stockfish et Stockfish.js sont sous GPL-3.0. Le code source correspondant et les notices doivent rester distribués selon cette licence.
- Next.js et React (MIT), `chess.js` (BSD-2-Clause), `react-chessboard` (MIT), Lucide (ISC).

## Limites connues de la V1

- Parties sans pendule, matchmaking public, tournoi, classement, spectateur, paiements et vocal/vidéo exclus volontairement.
- La proposition de nulle repose sur une double confirmation via l’action `draw` ; l’interface affiche actuellement le même bouton aux deux joueurs sans notification dédiée.
- La notification audio est un signal court activable après interaction ; aucune notification n’est garantie si l’onglet est suspendu ou fermé.
- Le moteur serveur est appelé dans une requête HTTP bornée pour les coups IA. La tâche Celery est disponible pour les analyses pédagogiques longues.
- Le build et les tests automatisés ont été exécutés. La vérification visuelle assistée par navigateur a été bloquée par le garde-fou de contrôle UI, incapable de confirmer l’URL active ; une passe manuelle aux formats ordinateur/tablette/mobile reste recommandée.
- Le fichier Compose a été relu mais n’a pas pu être exécuté dans cet environnement, où la commande `docker` n’est pas installée.

## Ordre de réalisation suivi

1. Maquettes et tokens visuels.
2. Environnement, modèles, sessions et migrations.
3. Règles locales, état serveur et Stockfish hybride.
4. Amitiés, invitations, multijoueur et resynchronisation.
5. Conversations, messages, lecture et son.
6. Leçons, responsive, seed, tests et documentation.
