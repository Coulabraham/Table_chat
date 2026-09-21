# Vérifications effectuées le 21 septembre 2026

## Lot 1 — messagerie

- Messagerie privée persistante, idempotence, pagination, rattrapage et WebSocket validés.
- Redémarrage du backend sans perte de données validé.
- Interface contrôlée en desktop et viewport mobile.

## Lot 2 — comptes et protections

- `pytest` : **19 tests réussis**.
- Vérification email : inscription non vérifiée, dépôt d'email, consommation unique, expiration et invalidation après changement d'adresse.
- Renvoi : cinq réponses acceptées puis limitation HTTP 429.
- Récupération : réponse identique pour adresse existante/absente, nouveau mot de passe Argon2, lien non réutilisable et révocation des sessions.
- Sessions : session actuelle distinguée, autre session révoquée, socket correspondante fermée en `4401`.
- Blocage : envoi refusé dans les deux sens, historique conservé, déblocage fonctionnel et socket ouverte fermée en `4403`.
- Absence de régression de la messagerie couverte par les anciens tests complétés.
- `makemigrations --check --dry-run` : aucun changement manquant ; `manage.py check` : aucune erreur.
- Frontend : compilation TypeScript/Vite réussie, ESLint réussi, `npm audit` à zéro vulnérabilité connue.
- Playwright contre la pile Docker HTTPS : scénario complet **desktop réussi** et **mobile réussi**. Il crée deux comptes, récupère leurs vrais emails via Mailpit, consomme les liens, échange dans les deux sens et recharge l'historique.
- Playwright en mode développement local : scénario desktop réussi avec le même parcours de vérification email réel.
- Contrôle visuel automatisé à `1440x900` et `320x700` : aucun débordement horizontal sur la connexion, la récupération, les discussions et les réglages ; zone de saisie visible dans les deux formats.
- Docker : backend, PostgreSQL, Redis, worker, frontend, Caddy et Mailpit démarrés ; API `/api/health/` saine.
- Migration réelle `accounts.0003` appliquée sans perte : compteurs historiques avant/après `4 utilisateurs`, `3 conversations`, `9 messages`. Les quatre comptes existants sont explicitement non vérifiés.
- Sauvegarde pré-migration puis post-migration créées localement. Chaque fichier a été restauré dans une base isolée ; contrôle post-migration : `4|3|9`. La base temporaire a été supprimée après le test.
- Les quatre comptes, deux conversations et quatre messages créés uniquement par Playwright ont été supprimés après assertions ; aucune donnée historique n'a été supprimée.

## Limites de la vérification

- L'envoi SMTP externe n'a volontairement pas été essayé ; seul Mailpit local est configuré.
- Aucun service de sauvegarde externe n'a été appelé.
- Le rendu a été automatisé avec Chromium desktop/mobile ; les menus natifs d'installation de certificat restent dépendants de chaque appareil physique.
- Les messages restent lisibles par le serveur et dans les sauvegardes.
