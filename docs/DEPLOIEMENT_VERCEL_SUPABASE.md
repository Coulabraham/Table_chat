# Déploiement Internet avec Vercel et Supabase

> État vérifié en septembre 2026 : Vercel Services, le runtime Python ASGI et
> les WebSockets de Vercel Functions sont disponibles, mais encore en bêta.
> Une connexion WebSocket reste attachée à une Function jusqu'à sa durée
> maximale. Le backend est configuré à 300 secondes et le frontend se
> reconnecte automatiquement.

Documentation officielle : [Vercel Services](https://vercel.com/docs/services),
[runtime Python](https://vercel.com/docs/functions/runtimes/python),
[WebSockets Vercel Functions](https://vercel.com/kb/guide/do-vercel-serverless-functions-support-websocket-connections)
et [connexions PostgreSQL Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Architecture retenue

- **Vercel Services** publie le frontend Vite à `/` et le backend Django ASGI à `/api` et `/ws` sur le même domaine.
- **Supabase** fournit uniquement PostgreSQL. L'authentification reste celle de Django afin de préserver les comptes, sessions, protections et migrations de TableChat.
- **Upstash Redis**, relié au projet depuis le Marketplace Vercel, fournit le canal partagé de Django Channels et le cache distribué des limitations de fréquence.
- Un **SMTP réel** envoie les vérifications et récupérations de mot de passe. Mailpit reste réservé au développement local.

Le même domaine Vercel pour le frontend, l'API et les WebSockets conserve les cookies de session `HttpOnly` et la protection CSRF sans dépendre des cookies tiers.

## 1. Créer la base Supabase

1. Créer un projet sur Supabase dans une région proche de celle choisie pour Vercel.
2. Dans **Connect**, copier l'URI **Session pooler** sur le port `5432`.
3. Remplacer le mot de passe indiqué et ajouter `sslmode=require` à l'URI. Les caractères réservés du mot de passe doivent être encodés dans l'URL.
4. Conserver cette URI uniquement dans les secrets Vercel sous le nom `DATABASE_URL`.

TableChat utilise un backend Fluid et doit employer le Session pooler, pas l'URI Transaction pooler `:6543`.

## 2. Créer Redis dans Vercel

1. Dans le Marketplace Vercel, installer **Upstash Redis** pour le projet.
2. Copier l'URI Redis TCP chiffrée fournie par Upstash, de forme `rediss://default:...@...:6379`.
3. Définir cette même valeur dans `REDIS_URL` et `CACHE_URL`.

Les variables REST `UPSTASH_REDIS_REST_URL` ou `KV_REST_API_URL` ne remplacent pas l'URI TCP attendue par Django Channels.

## 3. Configurer le SMTP réel

Créer des identifiants SMTP dédiés chez le fournisseur choisi et vérifier l'adresse ou le domaine d'expédition. Ne jamais utiliser ni commiter le mot de passe normal d'une boîte personnelle.

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.fournisseur.example
EMAIL_PORT=587
EMAIL_HOST_USER=identifiant-smtp
EMAIL_HOST_PASSWORD=secret-smtp
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=TableChat <noreply@votre-domaine.example>
```

Pour un fournisseur qui impose le port `465`, utiliser `EMAIL_USE_SSL=true` et `EMAIL_USE_TLS=false`.

## 4. Créer le projet Vercel

1. Importer `Coulabraham/Table_chat` depuis GitHub.
2. Garder la racine du dépôt comme **Root Directory**.
3. Sélectionner le framework **Services**. Le fichier `vercel.json` déclare les services `frontend` et `backend`.
4. Activer Fluid Compute si le projet ne l'a pas déjà activé.
5. Relier Upstash Redis au projet.

Le fichier `.env.production.example` sert de liste de contrôle. Il ne faut pas
le renommer en fichier de production ni y écrire de vrais secrets : toutes les
valeurs sensibles doivent être enregistrées dans les variables chiffrées du
projet Vercel.

Ajouter ces variables aux environnements Production et, si nécessaire, Preview :

```text
DJANGO_SETTINGS_MODULE=tablechat.settings.production
DJANGO_SECRET_KEY=<valeur aléatoire longue et unique>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=.vercel.app,votre-domaine.example
CSRF_TRUSTED_ORIGINS=https://*.vercel.app,https://votre-domaine.example
DATABASE_URL=<URI Session pooler Supabase avec sslmode=require>
DATABASE_CONN_MAX_AGE=60
REDIS_URL=<URI rediss Upstash>
CACHE_URL=<même URI rediss Upstash>
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
APP_BASE_URL=https://votre-projet.vercel.app
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<hôte SMTP>
EMAIL_PORT=587
EMAIL_HOST_USER=<identifiant SMTP>
EMAIL_HOST_PASSWORD=<secret SMTP>
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=TableChat <adresse autorisée>
EMAIL_VERIFICATION_TTL_SECONDS=86400
PASSWORD_RESET_TTL_SECONDS=1800
```

Vercel injecte aussi son propre nom d'hôte ; TableChat l'ajoute automatiquement aux hôtes Django et aux origines CSRF autorisées. `APP_BASE_URL` doit néanmoins désigner l'URL de production stable afin que les liens reçus par email soient corrects.

## 5. Appliquer les migrations

Après avoir enregistré les variables, installer/utiliser le CLI sans l'ajouter
aux dépendances du projet, puis lier le dossier :

```powershell
npx --yes vercel@latest link
```

Appliquer ensuite les migrations avec les variables de production :

```powershell
npx --yes vercel@latest env run --environment=production -- .\.venv\Scripts\python.exe backend\manage.py migrate --noinput
npx --yes vercel@latest env run --environment=production -- .\.venv\Scripts\python.exe backend\manage.py check --deploy
```

La base Supabase neuve reçoit uniquement le schéma Django ; les comptes locaux supprimés ne sont pas recréés.

## 6. Déployer

```powershell
npx --yes vercel@latest --prod
```

Après le premier déploiement, reporter l'URL de production exacte dans `APP_BASE_URL`, puis redéployer si elle était encore provisoire.

## 7. Recette obligatoire

1. `GET https://<domaine>/api/health/` retourne `{"status":"ok"}`.
2. Créer un compte avec une vraie adresse et recevoir le lien de vérification.
3. Consommer le lien une seule fois, puis vérifier qu'il est refusé à la seconde tentative.
4. Ouvrir deux navigateurs ou appareils, démarrer une conversation et vérifier les messages dans les deux sens.
5. Recharger les deux pages et vérifier l'historique Supabase.
6. Révoquer une session et vérifier que son WebSocket est fermé.
7. Bloquer puis débloquer un utilisateur et vérifier les deux sens.
8. Tester le parcours de récupération du mot de passe.

Le frontend reconnecte automatiquement les WebSockets lorsque Vercel ferme une fonction arrivée à sa durée maximale. Les événements non diffusés sont rejoués au prochain envoi ou à la prochaine connexion ; le rattrapage HTTP reste la source de vérité.

## Sécurité et exploitation

- Ne jamais mettre les secrets Vercel, Supabase, Redis ou SMTP dans `.env.example`, GitHub ou une capture d'écran.
- Activer l'authentification multifacteur sur les comptes Vercel, Supabase, GitHub et SMTP.
- Configurer les budgets et alertes d'utilisation avant d'ouvrir largement les inscriptions.
- Consulter les journaux d'erreur Vercel et l'utilisation de la base/Redis.
- Tester régulièrement un export PostgreSQL dans une base isolée. Les sauvegardes proposées par Supabase dépendent du plan choisi et ne remplacent pas nécessairement une copie indépendante.
- Les messages ne sont toujours pas chiffrés de bout en bout : le serveur, Supabase et les sauvegardes peuvent les lire.
