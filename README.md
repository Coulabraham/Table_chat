# TableChat

TableChat est une messagerie privée pour essais sur un réseau local. Deux personnes peuvent créer un compte, vérifier leur adresse, se retrouver par identifiant public et échanger des messages persistants en temps réel. PostgreSQL est la source de vérité ; Redis transporte les événements WebSocket.

> Cette version n'utilise pas de chiffrement de bout en bout. TLS protège le transport, mais le serveur et les administrateurs de l'infrastructure peuvent lire les messages. Ne pas ouvrir ce prototype au public.

## Fonctions disponibles

- inscription, connexion et profil ;
- vérification d'adresse email avec lien temporaire à usage unique et renvoi limité ;
- mot de passe oublié sans divulgation de l'existence d'un compte ;
- inventaire indicatif des sessions, révocation d'une session ou de toutes les autres ;
- blocage dans les deux sens sans suppression de l'historique ;
- conversation privée persistante, WebSocket, reconnexion et rattrapage ;
- sauvegarde PostgreSQL et restauration de contrôle dans une base isolée ;
- interface React adaptée au téléphone et à l'ordinateur.

## Démarrage avec Docker

Prérequis : Docker Desktop avec Compose, ports 80 et 443 libres.

1. Copier `.env.example` vers `.env`.
2. Remplacer `DJANGO_SECRET_KEY` et `POSTGRES_PASSWORD` par des valeurs aléatoires fortes.
3. Conserver `SITE_ADDRESS=https://localhost`, `SITE_HOST=localhost` et `APP_BASE_URL=https://localhost` pour un seul ordinateur.
4. Lancer :

```powershell
docker compose up --build -d
docker compose ps
```

Ouvrir `https://localhost`. La boîte de développement Mailpit est disponible uniquement sur le PC à l'adresse `http://localhost:8025`. Aucun email n'est envoyé sur Internet avec la configuration fournie.

Arrêt sans suppression des données :

```powershell
docker compose down
```

Ne lancer `docker compose down -v` que pour supprimer définitivement PostgreSQL, Redis, Mailpit et leurs données.

## Utilisation sur ordinateur et téléphone

Les appareils doivent être sur le même réseau privé. Pour l'adresse LAN `192.168.1.42`, configurer :

```dotenv
SITE_ADDRESS=https://192.168.1.42
SITE_HOST=192.168.1.42
APP_BASE_URL=https://192.168.1.42
DJANGO_ALLOWED_HOSTS=192.168.1.42,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://192.168.1.42,https://localhost
```

Puis recréer les services :

```powershell
docker compose up --build -d
```

Autoriser les ports TCP 80/443 uniquement sur le profil réseau privé. Exporter l'autorité Caddy si nécessaire :

```powershell
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt .\infra\tablechat-local-ca.crt
```

Installer uniquement ce certificat public sur les appareils de test et ouvrir `https://192.168.1.42`. Ne jamais distribuer la clé privée de Caddy. Le PC hôte doit rester allumé et son adresse IP doit rester stable.

## Vérification email et récupération

À l'inscription, le compte est explicitement non vérifié et un email est déposé dans Mailpit. Avant vérification, l'utilisateur peut se connecter, consulter/modifier son profil, gérer ses sessions et blocages, renvoyer le lien, utiliser la récupération et se déconnecter. La recherche de contacts, les conversations et les WebSockets privés sont refusés côté serveur.

Les comptes créés avant la migration `accounts.0003` restent volontairement non vérifiés. Après connexion, ils doivent utiliser **Réglages > Renvoyer le lien**.

Procédure complète : [docs/EMAILS.md](docs/EMAILS.md). Les variables `EMAIL_*` de `.env.example` permettent plus tard de brancher un SMTP réel, mais aucun service externe n'est configuré ou souscrit ici.

## Sauvegarde et restauration

```powershell
.\scripts\backup-postgres.ps1
.\scripts\verify-restore.ps1 -BackupPath ".\backups\tablechat-AAAAMMJJ-HHMMSS.dump"
```

La destination et la rétention sont configurables avec `BACKUP_DESTINATION`, `BACKUP_RETENTION_DAYS` ou les paramètres des scripts. Une copie sur le même PC ne protège pas contre la perte du PC ; conserver une copie chiffrée ailleurs nécessite une décision et une autorisation explicites. Voir [docs/SAUVEGARDE.md](docs/SAUVEGARDE.md).

## Tests et contrôles

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run

cd ..\frontend
npm ci
npm run build
npm run lint
npm audit
$env:TABLECHAT_URL="https://localhost"
$env:TABLECHAT_MAILPIT_URL="http://127.0.0.1:8025"
npm run test:e2e -- --project=desktop
```

La recette navigateur récupère réellement les liens de vérification avec l'API locale Mailpit. Les résultats constatés sont consignés dans [docs/VERIFICATIONS.md](docs/VERIFICATIONS.md).

## Architecture

- `backend/accounts` : utilisateurs, jetons à usage unique, email, récupération, sessions, blocages, CSRF et limitations de débit ;
- `backend/chat` : paire privée canonique, historique par curseur, idempotence, WebSocket et outbox ;
- `frontend` : React/TypeScript, TanStack Query, React Router et Tailwind ;
- `mailpit` : SMTP et boîte locale de développement, liés uniquement à `127.0.0.1:1025/8025` ;
- `infra/Caddyfile` : HTTPS et origine unique ;
- `compose.yaml` : frontend, backend ASGI, worker, PostgreSQL, Redis, Mailpit et Caddy.

Les contrats sont dans [docs/API.md](docs/API.md), la sécurité dans [docs/SECURITE.md](docs/SECURITE.md) et la recette manuelle dans [docs/RECETTE.md](docs/RECETTE.md).

## Limites avant ouverture publique

- aucune modification d'adresse email ni suppression de compte ;
- aucun chiffrement de bout en bout ;
- aucun groupe, fichier, appel, jeu, paiement ou notification Push ;
- autorité TLS interne adaptée au laboratoire, pas à un domaine public ;
- pas encore de supervision, sauvegarde externe chiffrée automatisée, restauration planifiée, audit externe ni test de charge ;
- les informations de navigateur/appareil sont seulement indicatives ;
- le SMTP réel nécessite gestion des secrets, réputation d'envoi, politique de données et autorisation explicite.
