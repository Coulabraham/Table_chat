# Recette à deux utilisateurs

## Validation manuelle sur ordinateur et téléphone

Préparer l’accès HTTPS LAN selon le README, puis utiliser deux adresses email et deux identifiants publics jamais employés.

1. Sur l’ordinateur, créer **Alice** (`alice_test`).
2. Sur le téléphone, créer **Bob** (`bob_test`).
3. Depuis Alice, rechercher exactement `bob_test`, ouvrir la discussion et envoyer « Bonjour Bob ».
4. Sans actualiser le téléphone, constater l’apparition du message puis répondre « Bonjour Alice ».
5. Constater la réponse en direct sur l’ordinateur. Les bulles de l’auteur passent de *En attente* à *Enregistré*, jamais à *Lu*.
6. Actualiser les deux navigateurs : les deux messages doivent rester présents.
7. Exécuter `docker compose restart backend`, attendre son retour, puis actualiser : l’historique doit toujours être présent.
8. Couper le Wi-Fi du téléphone, envoyer un nouveau message depuis Alice, puis réactiver le Wi-Fi : Bob doit le récupérer automatiquement.
9. Créer **Mallory** dans un troisième contexte. Copier l’UUID visible dans l’URL de la conversation Alice/Bob et tenter `/chats/{uuid}` : l’interface doit afficher *Discussion inaccessible* ; les API retournent 404 et le WebSocket 4403.
10. Déconnecter Bob depuis Réglages. Sa socket doit se fermer et toute écriture API ultérieure doit être refusée.
11. Vérifier à 320 px que la saisie et la navigation basse sont visibles ; sur ordinateur, vérifier la liste à gauche et la conversation à droite.

## Idempotence manuelle

Dans les outils réseau du navigateur, recopier une requête `POST .../messages/` avec le même `client_id`. La seconde réponse doit être `200`, contenir le même `id` que la première réponse `201`, et une seule bulle doit apparaître.

## Automatisation

`backend` couvre inscription/session/Argon2, recherche sans fuite d’email, CSRF, paire canonique, idempotence, pagination/rattrapage, validation, interdiction d’un tiers, logout et autorisation WebSocket.

`frontend/e2e/messaging.spec.ts` couvre deux contextes isolés, création des comptes, recherche, aller-retour temps réel et persistance après actualisation. Il doit être lancé contre la pile Compose active. Un vrai redémarrage de conteneur et deux appareils physiques restent des vérifications manuelles, car l’environnement d’exécution du test ne doit pas administrer Docker pendant le scénario navigateur.

