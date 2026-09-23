# TableChat

TableChat est une messagerie privée disponible en local et sur Vercel. Deux personnes peuvent créer un compte, se retrouver par identifiant public et échanger des messages persistants en temps réel. PostgreSQL est la source de vérité; Redis transporte les événements WebSocket entre les instances ASGI.

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

La politique est commandée par `REQUIRE_EMAIL_VERIFICATION` et une même règle est utilisée par les API HTTP et les WebSockets :

- `true` : un compte non vérifié peut gérer son profil, ses sessions et sa sécurité, mais la recherche et la messagerie sont refusées;
- `false` : un compte authentifié non vérifié peut utiliser la messagerie sans être marqué artificiellement comme vérifié en base.

En local, Mailpit reçoit les liens. En production, la valeur reste actuellement à `false`, car le domaine de test Resend ne peut envoyer qu'au propriétaire du compte Resend. Ne pas réactiver la vérification avant d'avoir validé un domaine d'envoi utilisable par tous les utilisateurs concernés.

Les comptes créés avant la migration `accounts.0003` restent volontairement non vérifiés. Après connexion, ils doivent utiliser **Réglages > Renvoyer le lien**.

Procédure locale : [docs/EMAILS.md](docs/EMAILS.md). Préparation Resend : [docs/DEPLOIEMENT_VERCEL_SUPABASE.md](docs/DEPLOIEMENT_VERCEL_SUPABASE.md).

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
npm test
npm run build
npm run lint
npm audit
$env:TABLECHAT_URL="https://localhost"
$env:TABLECHAT_MAILPIT_URL="http://127.0.0.1:8025"
npm run test:e2e -- --project=desktop
```

La recette locale récupère réellement les liens de vérification avec Mailpit. Une sonde séparée vérifie les vraies trames en production avec les comptes de test autorisés :

```powershell
cd frontend
$env:TABLECHAT_URL="https://table-chat-blush.vercel.app"
$env:TABLECHAT_TEST_PASSWORD="<mot de passe de recette>"
node scripts/production-realtime-check.mjs
```

Les résultats constatés sont consignés dans [docs/VERIFICATIONS.md](docs/VERIFICATIONS.md).

## Architecture

- `backend/accounts` : utilisateurs, jetons à usage unique, email, récupération, sessions, blocages, CSRF et limitations de débit ;
- `backend/chat` : paire privée canonique, historique par curseur, idempotence, WebSocket et outbox ;
- `frontend` : React/TypeScript, TanStack Query, React Router et Tailwind ;
- `mailpit` : SMTP et boîte locale de développement, liés uniquement à `127.0.0.1:1025/8025` ;
- `infra/Caddyfile` : HTTPS et origine unique ;
- `compose.yaml` : frontend, backend ASGI, worker, PostgreSQL, Redis, Mailpit et Caddy;
- Vercel : aucun worker Docker permanent; l'outbox est relancée après écriture, à la connexion, au nouvel envoi et sur les pings WebSocket.

Les contrats sont dans [docs/API.md](docs/API.md), la sécurité dans [docs/SECURITE.md](docs/SECURITE.md) et la recette manuelle dans [docs/RECETTE.md](docs/RECETTE.md).

## Déploiement Internet

Le déploiement actif est `https://table-chat-blush.vercel.app`. La configuration Vercel Services conserve le frontend, l'API Django et les WebSockets sur la même origine. Supabase fournit PostgreSQL et Upstash le Redis TCP chiffré `rediss://`. Les WebSockets Vercel Functions sont en bêta et exigent Fluid Compute; le client reconnecte automatiquement une connexion interrompue et rattrape l'historique depuis PostgreSQL. Voir [.env.production.example](.env.production.example) et [docs/DEPLOIEMENT_VERCEL_SUPABASE.md](docs/DEPLOIEMENT_VERCEL_SUPABASE.md).

## Limites avant ouverture publique

- aucune modification d'adresse email ni suppression de compte ;
- aucun chiffrement de bout en bout ;
- aucun groupe, fichier, appel, jeu, paiement ou notification Push ;
- l'autorité TLS de Caddy reste strictement locale ; le déploiement public utilise le certificat géré par Vercel ;
- pas encore de supervision, sauvegarde externe chiffrée automatisée, restauration planifiée, audit externe ni test de charge ;
- les informations de navigateur/appareil sont seulement indicatives ;
- les cinq comptes de recette partagent un mot de passe et doivent être remplacés ou individualisés avant une ouverture publique;
- Resend nécessite encore un domaine d'envoi vérifié avant de remettre `REQUIRE_EMAIL_VERIFICATION=true`.
