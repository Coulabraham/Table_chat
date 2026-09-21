# Sécurité et limites

- Sessions serveur Django ; cookie `HttpOnly`, `SameSite=Lax`, `Secure` en environnement HTTPS.
- CSRF explicite, y compris sur inscription et connexion ; origines CORS/CSRF restrictives.
- Mots de passe hachés en Argon2 et validateurs Django actifs.
- Limites : authentification 10/minute par adresse, messages 60/minute par utilisateur, autres actions authentifiées 240/minute ; contenu limité à 4 000 caractères et corps HTTP à 64 Kio.
- Email jamais inclus dans les serializers publics. Recherche exacte par identifiant, maximum cinq résultats.
- Autorisations recalculées côté serveur pour chaque conversation, historique, envoi et abonnement WebSocket.
- Origine WebSocket validée contre `ALLOWED_HOSTS`; session contrôlée à l’ouverture, sur chaque événement et au heartbeat.
- Les messages React restent du texte ; aucun HTML utilisateur n’est injecté.
- PostgreSQL et Redis ne publient aucun port hôte dans Compose. Les secrets viennent de `.env`, absent du dépôt.
- Les journaux applicatifs ne consignent ni mot de passe, ni cookie, ni contenu de message.
- Réglages distincts `development`, `test` et `production`; la production refuse la clé secrète par défaut et active redirection/HSTS.

## Confidentialité

Il n’y a pas de chiffrement de bout en bout. TLS protège le transport, mais le serveur et toute personne disposant d’un accès suffisant à la base peuvent lire les messages. Aucun cadenas ni statut trompeur n’est affiché.

Avant un accès public, il faut au minimum ajouter : vérification d’email, récupération/suppression de compte, politique de données, rotation des secrets, sauvegardes chiffrées et restauration testée, observabilité sans contenu privé, audit externe, tests de charge, protection de bordure et une décision cryptographique formelle sur l’E2EE.
