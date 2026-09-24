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
- `POST /api/conversations/{uuid}/read/` avec `message_id` ; curseur monotone appartenant à la conversation.
- `PATCH /api/conversations/{uuid}/preferences/` avec `muted`.

La vérification email est imposée côté serveur. Un blocage dans l'un ou l'autre sens retourne une indisponibilité générique à l'envoi privé ; l'historique et les groupes communs restent accessibles. Le contrôle est répété dans la transaction qui crée le message.

## Groupes et invitations

- `POST /api/groups/` — création ; le créateur devient propriétaire.
- `GET /api/group-invitations/` — invitations reçues encore valides.
- `POST /api/group-invitations/{uuid}/accept/` ou `/decline/`.
- `DELETE /api/group-invitations/{uuid}/` — annulation autorisée.
- `GET/POST /api/conversations/{uuid}/invitations/` — suivi et invitation par identifiant public.
- `GET /api/conversations/{uuid}/members/`.
- `PATCH/DELETE /api/conversations/{uuid}/members/{user_id}/` — rôle ou retrait selon les droits.
- `POST /api/conversations/{uuid}/transfer-owner/` et `POST /api/conversations/{uuid}/leave/`.
- `PATCH /api/conversations/{uuid}/` — nom/description pour propriétaire ou administrateur.

Une invitation en attente n’accorde aucun accès. L’acceptation enregistre l’ID du dernier message comme borne basse stable : seuls les messages suivants sont visibles. Un retrait ferme l’accès HTTP et WebSocket ; une réinvitation crée une nouvelle période sans restaurer l’ancien historique. Valeurs par défaut : 50 membres, invitation valable 7 jours, 10 créations/heure et 60 invitations/heure.

## WebSocket

Connexion : `wss://hôte/ws/conversations/{uuid}/` avec cookie de session et origine autorisée. Le serveur revalide la session, la vérification email, l'appartenance et le blocage à l'ouverture, au heartbeat et avant chaque événement.

- révocation de la session : fermeture `4401` ;
- conversation non autorisée ou blocage : fermeture `4403`, sans indiquer l'auteur du blocage ;
- message : `message.created` ;
- groupe : `member.joined`, `member.left`, `member.removed`, `member.role_changed`, `ownership.transferred`, `group.updated` ;
- lecture : `read.updated`.

Chaque socket rejoint un groupe dérivé par SHA-256 de la clé de session, jamais exposé au client. L'outbox et le rattrapage `?after=` restent la garantie de livraison après reconnexion.
