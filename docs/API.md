# Contrats API et WebSocket

Toutes les routes sont sous `/api/`, utilisent JSON et, lorsque nécessaire, le cookie de session Django. Les écritures exigent `X-CSRFToken`, obtenu par `GET /api/auth/csrf/`. Aucun jeton durable n'est stocké dans `localStorage`.

## Compte

- `POST /api/auth/register/` — crée un compte non vérifié, ouvre une session et dépose l'email local.
- `POST /api/auth/login/`, `POST /api/auth/logout/`.
- `POST /api/auth/email/verify/` — `{ "token": "…" }`, usage unique.
- `POST /api/auth/email/resend/` — session requise, fréquence limitée.
- `POST /api/auth/password-reset/request/` — `{ "email": "…" }`, réponse non révélatrice.
- `POST /api/auth/password-reset/confirm/` — `{ "token": "…", "new_password": "…" }`, révoque toutes les sessions.
- `GET/PATCH /api/me/` — inclut `email_verified` et `email_verified_at`; seuls le nom affiché et la bio sont modifiables.
- `GET /api/sessions/` — descriptions indicatives et session actuelle.
- `DELETE /api/sessions/{uuid}/` — révoque une autre session.
- `DELETE /api/sessions/others/` — révoque toutes les autres sessions.
- `GET/POST /api/blocks/`, `DELETE /api/blocks/{public_id}/`.
- `GET /api/users/search/?public_id=...` — adresse vérifiée requise, correspondance exacte, sans email.

Les secrets de vérification/récupération ne sont stockés qu'après SHA-256, expirent et deviennent invalides après consommation. Une modification d'adresse invalide les liens de vérification existants.

## Conversations et messages

- `GET/POST /api/conversations/` ;
- `GET /api/conversations/{uuid}/` ;
- `GET /api/conversations/{uuid}/messages/` avec `before` ou `after` ;
- `POST /api/conversations/{uuid}/messages/` avec `client_id` et `content`.

La vérification email est imposée côté serveur. Un blocage dans l'un ou l'autre sens retourne une indisponibilité générique à l'envoi ; l'historique reste accessible. Le contrôle est répété dans la transaction qui crée le message.

## WebSocket

Connexion : `wss://hôte/ws/conversations/{uuid}/` avec cookie de session et origine autorisée. Le serveur revalide la session, la vérification email, l'appartenance et le blocage à l'ouverture, au heartbeat et avant chaque événement.

- révocation de la session : fermeture `4401` ;
- conversation non autorisée ou blocage : fermeture `4403`, sans indiquer l'auteur du blocage ;
- message : `message.created`.

Chaque socket rejoint un groupe dérivé par SHA-256 de la clé de session, jamais exposé au client. L'outbox et le rattrapage `?after=` restent la garantie de livraison après reconnexion.
