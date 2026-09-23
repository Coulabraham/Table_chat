# Sécurité et limites

## Protections actives

- Sessions serveur Django ; cookie `HttpOnly`, `SameSite=Lax` et `Secure` en HTTPS.
- CSRF sur toutes les écritures, y compris inscription, connexion, vérification et récupération.
- Argon2 en premier mécanisme de hachage et validateurs Django actifs.
- Jetons aléatoires à forte entropie ; seul SHA-256 du secret est stocké. Les sélecteurs ne suffisent pas à utiliser un lien.
- Vérification email : expiration configurable, usage unique, invalidation des anciens liens et invalidation après changement d'adresse. La politique d'accès est centralisée pour HTTP et WebSocket.
- Récupération : réponse identique pour adresse existante ou absente, expiration, usage unique et révocation de toutes les sessions.
- Limitations : authentification 10/minute, actions email 5/heure par réseau/adresse, messages 60/minute, autres actions 240/minute.
- Registre de sessions relié aux sessions Django ; aucun identifiant de session n'est retourné à l'interface.
- Révocation transmise au groupe WebSocket dérivé par SHA-256 de la clé de session.
- Blocage contrôlé sous verrou transactionnel avant l'écriture, puis revérifié sur les sockets ouvertes.
- Fermetures WebSocket explicites : authentification/session `4401`, accès conversation/blocage `4403`, email requis `4404`. Le frontend ne reconnecte pas automatiquement ces refus.
- Email absent des serializers publics ; recherche exacte par identifiant, maximum cinq résultats.
- PostgreSQL et Redis ne publient aucun port hôte. SMTP Mailpit et son interface sont liés exclusivement à `127.0.0.1`, donc inaccessibles depuis le LAN.
- Secrets fournis par `.env`, absent du dépôt. Les journaux applicatifs ne consignent ni mot de passe, cookie, jeton ni contenu de message.

## Politique email actuelle

`REQUIRE_EMAIL_VERIFICATION=false` est un contournement temporaire de politique, pas une validation des adresses. Les lignes `email_verified_at` restent inchangées. Dans ce mode, les comptes authentifiés actifs accèdent à la messagerie; dans le mode `true`, les comptes sans date de vérification sont refusés par HTTP et WebSocket.

Le domaine de test Resend ne permet pas d'envoyer à tous les utilisateurs. La vérification obligatoire ne doit être réactivée qu'après validation d'un domaine contrôlé et test de l'expéditeur réel.

## Comptes existants

La migration `accounts.0003` ajoute `email_verified_at` avec `NULL`. Aucun compte antérieur n'est considéré silencieusement comme vérifié. Lors de la future réactivation, ils pourront se connecter et demander un lien, mais ne pourront plus utiliser la recherche, les conversations ou les WebSockets avant validation.

Les cinq comptes de test `test1@example.test` à `test5@example.test` partagent un mot de passe de recette. Ils sont réservés aux essais, sans donnée réelle et sans rôle privilégié. Avant toute ouverture publique, supprimer ces comptes avec autorisation explicite ou leur attribuer des mots de passe uniques non partagés. Aucun de ces accès ne doit être publié.

## Redis, WebSockets et disponibilité

Le canal de production utilise le protocole Redis TCP natif avec TLS (`rediss://`), un délai de connexion borné et aucun délai de lecture sur la commande bloquante de `channels-redis`. `redis-py` est figé à une version testée. Les groupes expirent après dix minutes pour limiter les entrées orphelines si Redis est indisponible lors d'une déconnexion.

Une indisponibilité Redis n'annule pas l'écriture du message PostgreSQL. L'outbox retente après un délai croissant lors d'un nouvel envoi, d'une connexion ou d'un ping. La livraison est donc au moins une fois : l'unicité en base et la fusion frontend empêchent l'affichage en double. Pour une charge publique importante, une file managée et un worker permanent restent recommandés.

## Sessions et appareils

Le navigateur et la plateforme sont déduits grossièrement du `User-Agent`; l'adresse réseau et la dernière activité complètent l'affichage. Ces données sont indicatives, modifiables par le client et ne constituent jamais une identité matérielle certaine.

## Sauvegardes

Les sauvegardes contiennent des données privées en clair au niveau applicatif. Le script limite l'ACL Windows au compte courant et ne transmet rien, mais `pg_dump` ne chiffre pas le fichier. Utiliser un volume chiffré, limiter les accès, tester les restaurations et distinguer une copie sur le même disque d'une copie hors machine.

## Confidentialité et limites

Il n'y a pas de chiffrement de bout en bout. TLS protège le transport, mais le serveur et toute personne disposant d'un accès suffisant à PostgreSQL ou aux sauvegardes peuvent lire les messages.

Avant un accès public, il faut notamment : domaine et certificat public, changement/suppression de compte, politique de données, rotation des secrets, SMTP réel protégé, sauvegarde externe chiffrée, observabilité sans contenu privé, audit indépendant, tests de charge et décision cryptographique formelle sur l'E2EE.
