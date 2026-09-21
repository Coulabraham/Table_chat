# Tester les emails localement

Mailpit reçoit les emails SMTP de développement sans les transmettre à Internet. Son interface n'est publiée que sur la boucle locale du PC (`127.0.0.1:8025`).

1. Démarrer la pile avec `docker compose up -d --build`.
2. Ouvrir `http://localhost:8025` sur le PC hôte.
3. Créer un compte TableChat : un message **Vérifiez votre adresse TableChat** doit apparaître.
4. Ouvrir le message et son lien. Le jeton se trouve après `#token=` : le fragment n'est pas envoyé dans les journaux HTTP.
5. Après consommation, le même lien doit être refusé.
6. Pour un ancien compte, se connecter, ouvrir **Réglages** puis choisir **Renvoyer le lien**.
7. Pour la récupération, choisir **Mot de passe oublié**, saisir l'adresse, puis ouvrir **Réinitialisez votre mot de passe TableChat** dans Mailpit.
8. Après changement du mot de passe, toutes les sessions antérieures doivent être refusées.

Le renvoi et la récupération sont limités à cinq actions par heure et par combinaison réseau/adresse. La demande de récupération retourne toujours la même réponse, que l'adresse existe ou non.

Pour un futur SMTP réel, renseigner `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` ou `EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL` et `APP_BASE_URL`. Ne pas commiter ces identifiants et ne pas exposer Mailpit sur le réseau public.
