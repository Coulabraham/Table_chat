# Contrats API et WebSocket

Toutes les routes sont sous `/api/`, utilisent JSON et le cookie de session Django. Les écritures exigent l’en-tête `X-CSRFToken`, obtenu par `GET /api/auth/csrf/`. Aucun jeton durable n’est stocké dans `localStorage`.

## Authentification et profil

- `GET /api/health/` — état du processus.
- `GET /api/auth/csrf/` — initialise/renouvelle la protection CSRF.
- `POST /api/auth/register/` — `email`, `public_id`, `display_name`, `password`.
- `POST /api/auth/login/` — `email`, `password`.
- `POST /api/auth/logout/` — détruit la session et ferme ses WebSockets.
- `GET /api/me/` — profil complet du compte courant.
- `PATCH /api/me/` — modifie uniquement `display_name` et `bio`.
- `GET /api/users/search/?public_id=...` — correspondance exacte, au plus cinq résultats, sans email.

## Conversations et messages

- `GET /api/conversations/` — conversations du compte courant, dernier message et activité.
- `POST /api/conversations/` — `{ "contact_public_id": "bob" }`; récupère la paire existante ou la crée atomiquement.
- `GET /api/conversations/{uuid}/` — réservé à un participant.
- `GET /api/conversations/{uuid}/messages/` — 50 messages récents en ordre serveur croissant.
- `GET .../messages/?before={sequence}` — page précédente.
- `GET .../messages/?after={sequence}` — jusqu’à 100 messages manqués, ordre croissant.
- `POST .../messages/` — `{ "client_id": "uuid", "content": "texte" }`.

`client_id` est unique par auteur. Répéter le même envoi retourne le message existant sans doublon. `server_sequence` est l’identifiant monotone attribué par PostgreSQL et définit l’ordre stable.

## WebSocket

Connexion : `wss://hôte/ws/conversations/{uuid}/` avec le cookie de session existant et une origine autorisée.

Événements serveur :

```json
{"type":"ready"}
{"type":"message.created","message":{"id":42,"server_sequence":42,"conversation_id":"…","author_id":1,"client_id":"…","content":"Bonjour","created_at":"…"}}
```

Le client envoie périodiquement `{"type":"ping"}` et reçoit `{"type":"pong"}`. À chaque événement et ping, le serveur revalide la session. Un logout diffuse une fermeture `4401`. Un non-participant reçoit `4403` lors de la connexion.

L’envoi d’un message se fait par HTTP, puis l’événement WebSocket est publié après commit. `DeliveryOutbox` conserve les diffusions échouées ; le service `event-worker` les réessaie. Le rattrapage `?after=` reste la garantie finale si un événement n’arrive pas.

