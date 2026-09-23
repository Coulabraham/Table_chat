# Vérifications TableChat — 23 septembre 2026

Ce document distingue les contrôles automatisés locaux des validations effectuées sur `https://table-chat-blush.vercel.app`.

## Résultat local

- Backend : **35 tests réussis** avec `pytest`.
- Matrice HTTP et WebSocket : compte vérifié/non vérifié × vérification obligatoire activée/désactivée.
- Refus testés : anonyme, session expirée, session révoquée, personne extérieure et blocage.
- WebSocket ouvert : révocation → `4401`, blocage → `4403`, email requis → `4404`.
- Frontend : **5 tests Vitest réussis**. Les codes d'autorisation ne sont pas reconnectés en boucle; les fermetures transitoires utilisent un recul exponentiel borné.
- Déduplication frontend testée par `id` et `client_id`.
- Panne Redis simulée : le message reste dans PostgreSQL et l'outbox, une reprise ultérieure le diffuse, et une répétition du même `client_id` ne crée qu'une ligne.
- Relance sans worker permanent testée sur connexion et ping WebSocket.
- `makemigrations --check --dry-run` : aucun changement manquant.
- `manage.py check` : aucune erreur.
- Build TypeScript/Vite et ESLint : réussis.
- `npm audit` : zéro vulnérabilité connue au niveau contrôlé.

## Cause des coupures observées en production

Deux défauts distincts ont été reproduits :

1. le consommateur WebSocket vérifiait directement `email_verified_at`, contrairement aux permissions HTTP qui respectaient `REQUIRE_EMAIL_VERIFICATION=false`;
2. `channels-redis 4.3.0` appelle `BZPOPMIN` avec un blocage de 5 secondes, tandis que `redis-py 8.1` avait aussi un délai de lecture par défaut de 5 secondes. Le lecteur expirait normalement après environ 5 secondes et l'exception fermait le consommateur ASGI.

La politique d'accès est désormais commune. `redis-py` est figé à `7.4.0` et le canal définit explicitement `socket_timeout=None`, un délai de connexion de 5 secondes et le keepalive. Le transport de production reste l'URI Redis TCP chiffrée `rediss://` sur le port natif Upstash, pas l'API REST.

## Recette réellement passée en ligne

La sonde `frontend/scripts/production-realtime-check.mjs` utilise uniquement les comptes de test autorisés. Le passage réussi, identifié par le marqueur `prod-1790202450757`, a vérifié :

- deux contextes Chromium indépendants connectés avec leurs cookies de session;
- réception de la trame WebSocket `ready` des deux côtés;
- message Alice → Bob puis Bob → Alice, avec observation directe de vraies trames `message.created`;
- même `client_id` envoyé deux fois : réponses `201` puis `200`, même identifiant serveur et une seule ligne dans l'historique;
- fermeture contrôlée de la vue de Bob, message envoyé pendant son absence, réouverture d'un nouveau WebSocket authentifié et rattrapage du message;
- historique présent après rechargement des deux pages;
- blocage sur connexions déjà ouvertes : fermeture et interface indisponible des deux côtés, puis déblocage de nettoyage;
- révocation de toutes les autres sessions d'un compte de test : socket ouverte fermée et navigateur renvoyé vers `/login`.

Cette fermeture contrôlée simule l'effet d'une fin de Function Vercel. Vercel ferme aussi réellement les WebSockets à la durée maximale de la Function; le client recrée alors le socket et recharge les messages manquants depuis PostgreSQL.

## Outbox et worker

- Docker local exécute `python manage.py retry_pending_events --watch` dans le service `event-worker`.
- Vercel n'exécute **aucun** processus Docker permanent pour ce dépôt.
- En ligne, la première tentative part dans `transaction.on_commit` après l'écriture PostgreSQL.
- En cas d'échec Redis, l'outbox conserve l'événement avec compteur, erreur non sensible et prochaine date de tentative.
- Une connexion, un nouvel envoi ou le ping de 20 secondes d'un socket déjà ouvert relance les événements arrivés à échéance.
- La contrainte unique `(author, client_id)` empêche le doublon en base; le frontend fusionne aussi les répétitions éventuelles d'une livraison au moins une fois.

Ce mécanisme est adapté au prototype sur Vercel, mais ce n'est pas une file à garantie forte avec worker dédié : sans socket ouverte, nouvelle connexion ou nouvel envoi, une ligne d'outbox attend. Un service de tâches permanent ou une file managée sera préférable avant une forte charge.

## Email

Resend SMTP est configuré avec son domaine de test. Un envoi vers l'adresse propriétaire autorisée a déjà été reçu, mais `onboarding@resend.dev` ne permet pas d'envoyer les vérifications à tous les futurs utilisateurs. `REQUIRE_EMAIL_VERIFICATION` reste donc volontairement à `false`.

La réactivation exige un domaine contrôlé, ses enregistrements SPF/DKIM validés par Resend, une adresse `From` de ce domaine, puis des essais de livraison vers des destinataires autorisés. Aucun domaine n'a été acheté et aucun compte existant n'a été marqué artificiellement comme vérifié.

## Comptes de test et confidentialité

Les cinq comptes `test1@example.test` à `test5@example.test` partagent volontairement un mot de passe de recette. Ils ne doivent jamais devenir des comptes publics ou privilégiés. Ne pas publier leur mot de passe, ne pas y stocker de conversation réelle et les remplacer ou leur attribuer des mots de passe distincts avant une ouverture publique. Ils n'ont pas été supprimés et leurs accès n'ont pas été modifiés.

Les messages ne sont **pas chiffrés de bout en bout**. TLS chiffre le transport, mais le serveur, PostgreSQL/Supabase et les sauvegardes peuvent lire le contenu.

## Verdict

La messagerie privée est stable pour poursuivre le développement fonctionnel en environnement de test. Le démarrage des groupes peut commencer sur une branche séparée, à condition de conserver ces tests. L'ouverture publique reste bloquée par le domaine d'envoi email, le traitement des comptes de test, l'observabilité et une stratégie d'outbox/worker plus robuste à grande échelle.
