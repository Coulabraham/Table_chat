# Sécurité et limites

## Protections actives

- Sessions serveur Django ; cookie `HttpOnly`, `SameSite=Lax` et `Secure` en HTTPS.
- CSRF sur toutes les écritures, y compris inscription, connexion, vérification et récupération.
- Argon2 en premier mécanisme de hachage et validateurs Django actifs.
- Jetons aléatoires à forte entropie ; seul SHA-256 du secret est stocké. Les sélecteurs ne suffisent pas à utiliser un lien.
- Vérification email : expiration configurable, usage unique, invalidation des anciens liens et invalidation après changement d'adresse.
- Récupération : réponse identique pour adresse existante ou absente, expiration, usage unique et révocation de toutes les sessions.
- Limitations : authentification 10/minute, actions email 5/heure par réseau/adresse, messages 60/minute, autres actions 240/minute.
- Registre de sessions relié aux sessions Django ; aucun identifiant de session n'est retourné à l'interface.
- Révocation transmise au groupe WebSocket dérivé par SHA-256 de la clé de session.
- Blocage contrôlé sous verrou transactionnel avant l'écriture, puis revérifié sur les sockets ouvertes.
- Email absent des serializers publics ; recherche exacte par identifiant, maximum cinq résultats.
- PostgreSQL et Redis ne publient aucun port hôte. SMTP Mailpit et son interface sont liés exclusivement à `127.0.0.1`, donc inaccessibles depuis le LAN.
- Secrets fournis par `.env`, absent du dépôt. Les journaux applicatifs ne consignent ni mot de passe, cookie, jeton ni contenu de message.

## Comptes existants

La migration `accounts.0003` ajoute `email_verified_at` avec `NULL`. Aucun compte antérieur n'est considéré silencieusement comme vérifié. Ces comptes peuvent se connecter et renvoyer un lien, mais pas utiliser la recherche, les conversations ou les WebSockets avant validation.

## Sessions et appareils

Le navigateur et la plateforme sont déduits grossièrement du `User-Agent`; l'adresse réseau et la dernière activité complètent l'affichage. Ces données sont indicatives, modifiables par le client et ne constituent jamais une identité matérielle certaine.

## Sauvegardes

Les sauvegardes contiennent des données privées en clair au niveau applicatif. Le script limite l'ACL Windows au compte courant et ne transmet rien, mais `pg_dump` ne chiffre pas le fichier. Utiliser un volume chiffré, limiter les accès, tester les restaurations et distinguer une copie sur le même disque d'une copie hors machine.

## Confidentialité et limites

Il n'y a pas de chiffrement de bout en bout. TLS protège le transport, mais le serveur et toute personne disposant d'un accès suffisant à PostgreSQL ou aux sauvegardes peuvent lire les messages.

Avant un accès public, il faut notamment : domaine et certificat public, changement/suppression de compte, politique de données, rotation des secrets, SMTP réel protégé, sauvegarde externe chiffrée, observabilité sans contenu privé, audit indépendant, tests de charge et décision cryptographique formelle sur l'E2EE.
