# Vérifications effectuées le 21 septembre 2026

- `pytest` : **11 tests réussis**. Parcours couverts : inscription/session/Argon2, CSRF de connexion et d’écriture, recherche exacte sans email, paire privée canonique, idempotence, persistance d’historique, rattrapage par séquence, validation de contenu, refus d’un tiers, refus après logout, autorisation et événement WebSocket réel, fermeture WebSocket au logout.
- Playwright local : **2 scénarios réussis**, Chromium desktop et viewport mobile iPhone, avec deux contextes de navigateur isolés. Les scénarios ont réellement créé Alice et Bob, recherché le contact, échangé dans les deux sens via HTTP + WebSocket et retrouvé l’historique après actualisation.
- Build frontend : TypeScript et Vite réussis ; bundle principal d’environ 284 Ko (89,5 Ko gzip lors de la mesure).
- `npm audit` : zéro vulnérabilité connue au moment du contrôle.
- ESLint : réussi sans erreur ni avertissement.
- `pip check` : aucune dépendance Python cassée.
- `manage.py makemigrations --check --dry-run` : aucun changement de schéma manquant.
- `manage.py check --deploy` avec une clé de contrôle : aucun avertissement.
- Inspection visuelle : connexion et conversation en 1440×900 et 320×700 ; aucun débordement horizontal, saisie visible et navigation adaptée.
- Docker Desktop/WSL 2 : pile construite et démarrée avec PostgreSQL 17.6, Redis 8.2, backend Daphne, worker d’outbox, frontend Nginx et Caddy 2.10.
- Recette Playwright contre la vraie pile HTTPS Docker : **2 scénarios réussis** (desktop et mobile), 4 comptes, 2 conversations et 4 messages persistés dans PostgreSQL.
- Redémarrage réel du conteneur backend : compteurs identiques avant/après (`users=4`, `conversations=2`, `messages=4`) et API HTTPS revenue saine.
- Après validation, les 4 comptes `@example.test`, leurs 2 conversations et 4 messages de recette ont été supprimés ; la base livrée est vide.

## Non vérifié dans cet environnement

Aucun téléphone physique n’était disponible. L’accès HTTPS LAN depuis un second appareil et l’installation de l’autorité locale sur ce téléphone doivent encore être validés manuellement selon `docs/RECETTE.md`.
