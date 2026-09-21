# Table Chat

Prototype fonctionnel de messagerie privée pour essais privés. Deux utilisateurs peuvent créer un compte, se retrouver par identifiant public et échanger des messages persistants en temps réel. PostgreSQL est la source de vérité ; Redis transporte les événements WebSocket.

> Important : cette version n’utilise pas de chiffrement de bout en bout. Le serveur peut lire les messages. La vérification d’email et la récupération de mot de passe ne sont pas implémentées ; ne pas ouvrir ce prototype au public.

## Démarrage recommandé avec Docker

Prérequis : Docker Desktop avec Compose, ports 80 et 443 libres.

1. Copier `.env.example` vers `.env`.
2. Remplacer `DJANGO_SECRET_KEY` et `POSTGRES_PASSWORD` par des valeurs aléatoires fortes.
3. Pour un seul ordinateur, conserver `SITE_ADDRESS=https://localhost`.
4. Lancer :

```powershell
docker compose up --build -d
docker compose ps
```

Ouvrir `https://localhost`. Caddy produit un certificat local ; le navigateur demandera de faire confiance à son autorité locale. L’API (`/api`) et les WebSockets (`/ws`) partagent exactement la même origine que le frontend.

Arrêt sans supprimer les données :

```powershell
docker compose down
```

Redémarrage, les comptes et messages étant conservés dans le volume PostgreSQL :

```powershell
docker compose up -d
```

Ne lancer `docker compose down -v` que si la suppression définitive de la base de développement est souhaitée.

## Utilisation sur ordinateur et téléphone

Les deux appareils doivent être sur le même réseau privé. Aucun port PostgreSQL ou Redis n’est publié.

1. Trouver l’adresse IPv4 LAN de l’ordinateur avec `ipconfig`, par exemple `192.168.1.42`.
2. Dans `.env`, régler exactement :

```dotenv
SITE_ADDRESS=https://192.168.1.42
DJANGO_ALLOWED_HOSTS=192.168.1.42,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://192.168.1.42
```

3. Relancer `docker compose up --build -d`.
4. Autoriser les ports TCP 80/443 dans le pare-feu uniquement pour le profil réseau privé.
5. Exporter l’autorité locale de Caddy :

```powershell
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt .\infra\tablechat-local-ca.crt
```

6. Installer ce certificat comme autorité de confiance sur les deux appareils de test. Ne jamais distribuer sa clé privée. Sur iPhone, activer ensuite la confiance complète dans *Réglages > Général > Informations > Réglages des certificats* ; sur Android, installer le certificat CA utilisateur selon la version du système.
7. Ouvrir `https://192.168.1.42` sur les deux appareils. Ne pas utiliser `localhost` sur le téléphone.

Si l’installation d’une CA locale est interdite par la politique de l’appareil, utiliser deux contextes de navigateur isolés sur l’ordinateur pour la recette automatisée. Ne pas contourner TLS ni désactiver CSRF/origines autorisées.

## Développement sans Docker

Cette voie sert au développement local sur un seul ordinateur. SQLite et le canal mémoire du réglage de test ne remplacent pas PostgreSQL/Redis pour une recette de déploiement.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c .\backend\constraints.txt -r .\backend\requirements-dev.txt
$env:DJANGO_SETTINGS_MODULE="tablechat.settings.test"
.\.venv\Scripts\python.exe .\backend\manage.py migrate
cd backend
..\.venv\Scripts\python.exe -m daphne -b 127.0.0.1 -p 8000 tablechat.asgi:application
```

Dans un second terminal :

```powershell
cd frontend
npm ci
npm run dev
```

Ouvrir `http://127.0.0.1:5173`.

## Tests et contrôles

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run

cd ..\frontend
npm ci
npm run build
npm audit
npx playwright install chromium
$env:TABLECHAT_URL="https://localhost"
npm run test:e2e -- --project=desktop
```

Pour une recette locale autonome (SQLite + canal mémoire, ports 8001/5174), après les migrations : `npm run test:e2e:local`.

Le test Playwright utilise deux contextes de navigateur indépendants. Il exige la pile Docker active. La procédure manuelle complète est dans [docs/RECETTE.md](docs/RECETTE.md).
Le compte rendu factuel de cette livraison est dans [docs/VERIFICATIONS.md](docs/VERIFICATIONS.md).

## Architecture

- `backend/accounts` : utilisateur, sessions, CSRF, authentification, profil, recherche exacte et limitation de débit.
- `backend/chat` : conversations à deux participants, historique par curseur, messages idempotents, WebSocket et outbox de rattrapage.
- `frontend` : React/TypeScript, TanStack Query, React Router et Tailwind ; navigation mobile/desktop, états d’envoi et reconnexion progressive.
- `infra/Caddyfile` : terminaison HTTPS et origine unique.
- `compose.yaml` : frontend, backend ASGI, worker d’événements, PostgreSQL, Redis et Caddy.

Les contrats HTTP et temps réel sont résumés dans [docs/API.md](docs/API.md). Les décisions de sécurité et limites sont dans [docs/SECURITE.md](docs/SECURITE.md).

## Limites avant ouverture publique

- Pas de vérification d’email, récupération de mot de passe, suppression de compte ni gestion multi-session.
- Pas d’E2EE : messages lisibles par le serveur et les administrateurs de l’infrastructure.
- Pas de pièces jointes, groupes, appels, notifications Push, jeux ni paiements.
- Le mécanisme d’outbox rediffuse les événements, mais une exploitation publique demanderait supervision, métriques, alertes, sauvegardes chiffrées/restaurations testées et tests de charge.
- La limitation DRF utilise le cache configuré ; pour plusieurs réplicas publics, configurer un cache Redis dédié et une protection en bordure.
- L’autorité TLS interne Caddy convient à un laboratoire privé, pas à un domaine public.
