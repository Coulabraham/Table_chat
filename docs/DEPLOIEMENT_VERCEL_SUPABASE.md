# Déploiement Internet avec Vercel et Supabase

> État vérifié en septembre 2026 : Vercel Services, le runtime Python ASGI et
> les WebSockets de Vercel Functions sont disponibles, mais encore en bêta.
> Une connexion WebSocket reste attachée à une Function jusqu'à sa durée
> maximale. Le backend est configuré à 300 secondes et le frontend se
> reconnecte automatiquement.

Documentation officielle : [Vercel Services](https://vercel.com/docs/services),
[runtime Python](https://vercel.com/docs/functions/runtimes/python),
[WebSockets Vercel Functions](https://vercel.com/docs/functions/websockets)
et [connexions PostgreSQL Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres).

État réellement contrôlé le 23 septembre 2026 : projet Vercel Services en
`iad1`, alias `https://table-chat-blush.vercel.app`, ASGI Django Channels,
Supabase opérationnel et échange WebSocket bidirectionnel validé avec deux
sessions. Les WebSockets Vercel sont en bêta, nécessitent Fluid Compute et
s'arrêtent à la durée maximale de la Function.

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
`DATABASE_CONN_MAX_AGE=0` est indispensable avec la limite du pool Supabase :
chaque requête Vercel libère sa connexion au lieu d'occuper durablement un des
clients disponibles.

## 2. Créer Redis dans Vercel

1. Dans le Marketplace Vercel, installer **Upstash Redis** pour le projet.
2. Copier l'URI Redis TCP chiffrée fournie par Upstash, de forme `rediss://default:...@...:6379`.
3. Définir cette même valeur dans `REDIS_URL` et `CACHE_URL`.

Les variables REST `UPSTASH_REDIS_REST_URL` ou `KV_REST_API_URL` ne remplacent pas l'URI TCP attendue par Django Channels.

TableChat fige `redis-py==7.4.0` et fournit au canal `socket_timeout=None`.
Cette configuration est intentionnelle : `channels-redis 4.3.0` attend cinq
secondes dans `BZPOPMIN`; un délai client identique coupe à tort les sockets
inactives. Ne pas retirer ce réglage sans refaire une recette WebSocket de plus
de cinq secondes et inspecter les journaux Vercel.

## 3. Préparer Resend et la vérification email

La production utilise actuellement les identifiants SMTP Resend et
`onboarding@resend.dev`. Cette adresse de test ne peut envoyer qu'à l'adresse du
propriétaire autorisée par Resend. Elle permet une recette technique, mais pas
la vérification des futurs inscrits. Conserver
`REQUIRE_EMAIL_VERIFICATION=false` tant qu'un domaine d'envoi n'est pas prêt.

Procédure sans exposer l'API key :

1. disposer d'un domaine ou sous-domaine contrôlé; ne rien acheter
   automatiquement;
2. dans **Resend > Domains > Add domain**, choisir de préférence un sous-domaine
   d'envoi tel que `mail.example.com`;
3. copier exactement chez le fournisseur DNS les enregistrements affichés par
   Resend. Ils comprennent les preuves DKIM et SPF nécessaires à l'envoi
   (TXT et, selon la configuration proposée, MX); ajouter DMARC selon la
   recommandation Resend;
4. attendre que la capacité **Sending** soit `Verified`. Ne pas recopier des
   valeurs d'un autre domaine;
5. créer une API key dédiée à TableChat avec les droits minimums, l'enregistrer
   comme secret Vercel `EMAIL_HOST_PASSWORD`, et ne jamais la mettre dans Git;
6. utiliser une adresse du domaine validé, par exemple
   `TableChat <noreply@mail.example.com>`, dans `DEFAULT_FROM_EMAIL`;
7. laisser d'abord `REQUIRE_EMAIL_VERIFICATION=false`, envoyer un test à une
   adresse possédée et autorisée, vérifier `Sent` puis `Delivered` dans Resend,
   le lien HTTPS et sa consommation unique;
8. tester inscription, renvoi limité et récupération avec au moins deux
   fournisseurs de boîte si possible;
9. seulement ensuite préparer les comptes existants et passer la variable à
   `true`.

Au moment de la réactivation, les comptes dont `email_verified_at` est vide ne
sont pas promus automatiquement. Ils restent connectables, ouvrent
`/verify-email`, demandent un nouveau lien puis récupèrent la messagerie après
validation. Prévenir les testeurs avant le changement et conserver un chemin
de retour à `false` si la délivrabilité échoue.

Paramètres SMTP Resend :

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<API key Resend dédiée>
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=TableChat <noreply@mail.example.com>
```

Resend accepte aussi le port `465`; dans ce cas utiliser
`EMAIL_USE_SSL=true` et `EMAIL_USE_TLS=false`. Documentation :
[SMTP Resend](https://resend.com/docs/send-with-smtp) et
[domaines Resend](https://resend.com/docs/dashboard/domains/introduction).

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
DATABASE_CONN_MAX_AGE=0
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
REQUIRE_EMAIL_VERIFICATION=true
EMAIL_VERIFICATION_TTL_SECONDS=86400
PASSWORD_RESET_TTL_SECONDS=1800
```

Pour des essais privés uniquement, `REQUIRE_EMAIL_VERIFICATION=false` autorise
immédiatement les comptes nouveaux et existants sans les marquer vérifiés et
sans envoyer de lien. La même politique est appliquée par HTTP et WebSocket.
Remettre la valeur à `true` avant toute ouverture publique, mais uniquement
après la procédure Resend ci-dessus.

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
9. Inspecter une trame `message.created`; un message visible après un simple
   rechargement HTTP ne prouve pas le temps réel.

La sonde automatisée réalise cette recette sans incorporer le mot de passe :

```powershell
cd frontend
$env:TABLECHAT_URL="https://table-chat-blush.vercel.app"
$env:TABLECHAT_TEST_PASSWORD="<secret partagé de recette>"
node scripts/production-realtime-check.mjs
```

Le frontend reconnecte automatiquement les WebSockets lorsque Vercel ferme une
Function arrivée à sa durée maximale. Les événements non diffusés sont rejoués
au prochain envoi, à la prochaine connexion ou sur le ping de 20 secondes d'un
socket ouvert; le rattrapage HTTP depuis PostgreSQL reste la source de vérité.

## 8. Outbox sur Vercel

Le service `event-worker` de `compose.yaml` existe seulement en local. Vercel
n'exécute pas `retry_pending_events --watch` en arrière-plan.

En production :

- la transaction crée `Message` et `DeliveryOutbox` ensemble;
- `transaction.on_commit` tente immédiatement la diffusion Redis;
- un échec conserve l'outbox et calcule un délai croissant, plafonné à cinq
  minutes;
- les connexions, pings et nouveaux envois relancent les lignes arrivées à
  échéance;
- `(author, client_id)` est unique et le frontend fusionne les événements par
  `id`/`client_id`.

Il s'agit d'une reprise opportuniste compatible avec les Functions, pas d'un
worker permanent. Pour un trafic important, utiliser une file/queue managée ou
un service persistant et conserver la même idempotence.

## 9. Retour arrière

Chaque déploiement Vercel reste immuable. En cas de régression, utiliser
**Deployments > Promote to Production** sur le dernier déploiement sain ou la
commande de rollback proposée par le CLI Vercel, puis confirmer `/api/health/`
et une connexion. Un retour arrière applicatif ne supprime aucune donnée
Supabase. Ne jamais tenter d'annuler une migration destructive sans sauvegarde
et procédure spécifique.

## Sécurité et exploitation

- Ne jamais mettre les secrets Vercel, Supabase, Redis ou SMTP dans `.env.example`, GitHub ou une capture d'écran.
- Activer l'authentification multifacteur sur les comptes Vercel, Supabase, GitHub et SMTP.
- Configurer les budgets et alertes d'utilisation avant d'ouvrir largement les inscriptions.
- Consulter les journaux d'erreur Vercel et l'utilisation de la base/Redis.
- Les cinq comptes de test partagent un mot de passe : ne pas le publier, ne
  stocker aucune donnée réelle et remplacer/séparer ces accès avant le public.
- Tester régulièrement un export PostgreSQL dans une base isolée. Les sauvegardes proposées par Supabase dépendent du plan choisi et ne remplacent pas nécessairement une copie indépendante.
- Les messages ne sont toujours pas chiffrés de bout en bout : le serveur, Supabase et les sauvegardes peuvent les lire.
