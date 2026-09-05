# TableChat — Développement de la V1 : plateforme sociale et module Échecs

## 1. Mission et objectif

Développe **TableChat**, une application web de jeux de société en ligne, dont la première version propose un module d’échecs complet.

L’utilisateur doit pouvoir :

- Créer un compte et gérer son profil.
- Ajouter des amis déjà inscrits.
- Jouer aux échecs contre une IA de difficulté réglable.
- Inviter un ami et jouer depuis deux appareils distincts.
- Discuter avec ses amis pendant et en dehors des parties.
- Progresser grâce à des leçons interactives.

Construis une application fonctionnelle de bout en bout, avec une interface soignée et des données persistantes. Les comptes, les amis, les conversations et la gestion générale des parties doivent être réutilisables pour d’autres jeux.

**Principe d’architecture :** isoler les règles des échecs sans construire prématurément un moteur universel de jeux.

## 2. Périmètre de la V1

### À livrer

- Authentification et profil.
- Relations d’amitié et invitations à jouer.
- Parties contre Stockfish.
- Parties privées entre deux amis.
- Chat persistant et notifications sonores.
- Leçons interactives avec indices.
- Installation locale reproductible et données de démonstration.

### Hors périmètre

Sauf demande ultérieure, ne pas implémenter :

- Matchmaking public.
- Tournois et classements compétitifs.
- Paiements et abonnements.
- Chat vocal ou vidéo.
- Mode spectateur.
- Applications mobiles natives.
- Création automatique de nouveaux contenus pédagogiques.

Prévoir les extensions utiles dans l’organisation du code, sans développer ces fonctionnalités.

## 3. Stack technique

### Frontend

- Next.js avec App Router.
- TypeScript en mode strict.
- Tailwind CSS.
- `react-chessboard` pour l’affichage de l’échiquier.
- `chess.js` pour les interactions locales, les coups possibles et la validation immédiate.

### Backend

- Django et Django REST Framework pour les API HTTP.
- Django Channels avec ASGI pour les WebSockets.
- PostgreSQL pour les données persistantes.
- Redis comme couche de communication Channels et broker Celery.
- Celery pour les traitements différés : expiration des invitations, nettoyage selon une politique documentée et analyses pédagogiques.

### Règles des échecs côté serveur

Utiliser une bibliothèque Python dédiée, telle que `python-chess`, pour valider les coups et déterminer les états de partie.

**Le serveur fait autorité pour les parties multijoueurs.** La validation par `chess.js` améliore l’expérience utilisateur, mais ne remplace jamais la validation serveur.

### Intelligence artificielle

Utiliser Stockfish en mode hybride :

- **Débutant à intermédiaire :** version WebAssembly exécutée dans un Web Worker côté navigateur.
- **Niveaux avancés et indices pédagogiques :** exécutable Stockfish côté serveur, piloté par le package Python `stockfish`.

Le package Python sert d’interface au moteur : prévoir également l’installation du binaire et la configuration de son chemin.

Choisir des versions stables compatibles, les verrouiller et documenter les dépendances ainsi que les licences applicables.

## 4. Organisation du projet

Utiliser une structure lisible avec deux dossiers principaux : `frontend/` et `backend/`.

Organiser Django en applications :

- `accounts` : comptes, authentification et profils.
- `friends` : demandes et relations d’amitié.
- `games` : parties, participants et invitations à jouer.
- `chat` : conversations, messages et état de lecture.
- `chess` : règles, état des parties, Stockfish et leçons.

Éviter tout conflit de nom d’import entre l’application Django dédiée aux échecs et la bibliothèque Python utilisée. Si nécessaire, nommer cette application `chess_game`.

Créer des composants frontend réutilisables, notamment :

- `FriendsList`
- `ChatPanel`
- `ConversationList`
- `GameLobby`
- `UserAvatar`
- `ConnectionStatus`

Les composants d’échiquier, de promotion et d’historique des coups restent propres aux échecs.

## 5. Modèle de données

Définir les modèles, leurs relations, leurs contraintes d’unicité et les index nécessaires.

### Utilisateur et profil

- Compte identifié par une adresse email unique.
- Pseudo public.
- Date de création.
- Niveau estimé aux échecs dans un profil ou des statistiques propres à ce jeu.

Le niveau initial peut être déclaré par l’utilisateur. Ne pas afficher un classement calculé artificiellement sans méthode définie.

### Amitié

Relation entre un demandeur et un destinataire, avec statuts explicites.

Règles :

- Le destinataire doit déjà être inscrit.
- Un utilisateur ne peut pas s’ajouter lui-même.
- Éviter les doublons, y compris les demandes croisées.
- Permettre l’acceptation, le refus, l’annulation d’une demande et la suppression d’un ami.

### Partie générique

Prévoir notamment :

- Un identifiant.
- Un `game_type`, initialement `chess`.
- Un mode : humain contre humain ou humain contre IA.
- Un statut : `waiting`, `in_progress`, `finished`, `cancelled`.
- Les participants et leurs rôles.
- La configuration, dont le niveau d’IA.
- Le résultat et le motif de fin.
- Les dates de création, de début et de fin.

Modéliser séparément l’invitation à jouer : émetteur, destinataire, configuration, statut et expiration.

### État d’une partie d’échecs

Conserver :

- La position FEN actuelle et la position initiale si nécessaire.
- Un historique ordonné des coups en UCI/SAN.
- Un historique PGN ou la possibilité de l’exporter.
- Un numéro de révision pour synchroniser les clients.
- Les informations de pendule si une cadence est activée.

Utiliser `JSONField`, stocké en JSONB dans PostgreSQL, pour les données structurées adaptées. Le PGN est du texte : ne pas le traiter artificiellement comme un document JSON.

### Conversations et messages

- Conversation privée entre deux amis.
- Conversation contextuelle liée à une partie.
- Participants autorisés.
- Auteur, contenu et horodatage de chaque message.
- État de lecture permettant de calculer les messages non lus.

**Les conversations et leurs messages restent consultables après la fin d’une partie.** Une suppression de relation d’amitié ne doit pas effacer automatiquement l’historique.

### Leçons

- Titre.
- Instruction courte en français.
- Position FEN initiale.
- Camp à jouer.
- Objectif.
- Difficulté.
- Solution ou variantes acceptées.
- Indice et explication pédagogique.
- Progression de l’utilisateur.

## 6. Fonctionnalités et comportement attendu

### 6.1 Authentification

Implémenter inscription, connexion, déconnexion et consultation du profil.

Privilégier les sessions Django avec cookies HttpOnly, avec une stratégie documentée pour CSRF, CORS et l’authentification WebSocket. Si une autre solution est nécessaire, justifier ce choix.

Ne jamais exposer les mots de passe ou secrets. La recherche d’amis se fait par pseudo sans publier les adresses email.

### 6.2 Jeu contre l’IA

L’utilisateur choisit son camp et un niveau parmi plusieurs difficultés clairement nommées.

- Centraliser le réglage des niveaux : temps de réflexion, profondeur et paramètres Stockfish compatibles.
- Ne pas présenter ces niveaux comme des Elo officiels.
- Exécuter le moteur navigateur sans bloquer l’interface.
- Prévoir un état « L’IA réfléchit », un délai maximal et une gestion des erreurs.
- Annuler les recherches devenues inutiles après un changement de partie ou une sortie de page.
- Sauvegarder la progression pour reprendre après actualisation.

Les parties utilisant un moteur côté client sont des parties d’entraînement et ne doivent pas servir de base à un classement compétitif.

### 6.3 Échiquier

Prévoir :

- Déplacement par glisser-déposer et par sélection de cases.
- Cases légales visibles à la sélection, avec survol en complément sur ordinateur.
- Mise en évidence du dernier coup et du roi en échec.
- Orientation selon le camp du joueur.
- Choix de promotion.
- Historique des coups.
- Affichage du trait, du résultat et du motif de fin.
- Abandon et proposition de nulle.

Gérer les règles spéciales et les conditions de fin : roque, prise en passant, promotion, échec et mat, pat et règles de nullité applicables. Distinguer les nullités automatiques de celles nécessitant une réclamation.

Livrer d’abord des parties sans pendule. Si une cadence est ajoutée, le serveur doit faire autorité sur le temps restant.

### 6.4 Multijoueur entre amis

Parcours attendu :

1. Rechercher un utilisateur inscrit.
2. Envoyer une demande d’ami.
3. Accepter la demande depuis l’autre compte.
4. Envoyer une invitation à jouer.
5. Accepter ou refuser l’invitation.
6. Ouvrir la même partie sur deux appareils et jouer.

Pour chaque coup, le serveur doit :

- Authentifier l’utilisateur et vérifier sa participation.
- Vérifier que la partie est active et que c’est son tour.
- Vérifier la légalité du coup.
- Enregistrer atomiquement le nouvel état.
- Diffuser l’état confirmé aux deux joueurs.

Utiliser un identifiant de requête et une révision de partie pour gérer les doublons, les messages retardés et les actions concurrentes. Ne jamais accepter un FEN fourni par le client comme nouvel état de référence.

À la reconnexion, récupérer l’état serveur complet et les éléments manquants. Afficher clairement la perte de connexion et la resynchronisation. Une coupure réseau temporaire ne vaut pas abandon.

### 6.5 Chat

Proposer une messagerie indépendante et un chat de partie.

- Messages en temps réel.
- Support des emojis Unicode.
- Historique paginé.
- Indicateur de messages non lus.
- Conservation après actualisation et après la partie.
- Prévention des doublons lors des reconnexions.
- Limites de longueur et de fréquence d’envoi.
- Affichage du contenu comme texte, sans HTML exécutable.

Prévoir une notification sonore désactivable après une interaction utilisateur autorisant l’audio. Tenir compte des restrictions du navigateur : ne pas garantir une notification lorsque l’application est fermée ou suspendue.

### 6.6 Leçons

Afficher une instruction courte à côté de l’échiquier.

- L’utilisateur joue une solution.
- L’application fournit immédiatement un retour.
- Il peut recommencer, demander un indice ou afficher l’explication.
- Sa réussite est enregistrée.

Pour la V1, privilégier des défis courts avec des solutions explicites. Si plusieurs coups satisfont l’objectif, les accepter ou annoncer clairement la contrainte.

Stockfish fournit des coups et des évaluations. Produire les indices lisibles avec des formulations pédagogiques maîtrisées ; ne pas supposer que le moteur génère lui-même une leçon en langage naturel.

## 7. Interface et direction artistique

Créer une ambiance **classique, chaleureuse et sobre**, inspirée d’un club d’échecs traditionnel.

Palette indicative :

- Fond crème : `#F6F1E7`
- Surfaces : `#FFFDF8`
- Texte brun foncé : `#2D241E`
- Accent bois : `#865B3B`
- Accent vert profond : `#315C49`
- Cases claires : `#E8D5B5`
- Cases foncées : `#9C7654`

Définir des tokens cohérents et ajuster les couleurs pour garantir la lisibilité.

Utiliser une police serif pour les titres et une police lisible pour les interfaces. Prévoir :

- Une navigation simple : Jouer, Amis, Messages, Leçons, Profil.
- Un affichage adapté aux ordinateurs, tablettes et téléphones.
- Des états de chargement, d’erreur, de liste vide et de déconnexion.
- Des contrôles utilisables au clavier avec focus visible.
- Des informations qui ne reposent pas uniquement sur la couleur.
- Une mise en page mobile permettant d’accéder facilement à l’échiquier et au chat.

Tous les textes destinés aux utilisateurs doivent être en français.

### 7.1 Maquettes visuelles à produire

Avant l’implémentation visuelle du frontend, générer trois images distinctes de maquettes haute fidélité : l’accueil connecté, une partie entre amis avec chat et une leçon interactive. Utiliser le prompt commun ci-dessous, complété par le prompt de chaque écran. Ces prompts constituent aussi la référence visuelle pour développer l’interface.

Si des maquettes TableChat sont jointes, les utiliser comme références prioritaires de composition et de style, en conservant les exigences fonctionnelles de ce document. Ne pas reproduire leurs éventuelles erreurs de texte, de placement des pièces ou de géométrie de l’échiquier.

Ne pas attendre une validation supplémentaire pour poursuivre le développement, sauf demande explicite. Si aucun outil de génération d’images n’est disponible, le signaler et appliquer cette direction artistique directement au frontend, sans prétendre avoir produit des images.

### 7.2 Prompt commun — Identité visuelle

> Crée une maquette haute fidélité de l’application web TableChat, une plateforme française de jeux de société entre amis, dont le premier jeu est les échecs. Représente une véritable interface d’application connectée, vue de face, occupant toute l’image, au format paysage d’environ 1536 × 1024 pixels. N’ajoute ni ordinateur, ni téléphone, ni décor extérieur, ni perspective, ni barre de navigateur.
>
> L’ambiance évoque un club d’échecs traditionnel : élégante, chaleureuse, calme et accueillante. Utilise un fond crème #F6F1E7, des surfaces ivoire #FFFDF8, un texte brun foncé #2D241E, des accents bois #865B3B et des actions principales vert profond #315C49. Les cases de l’échiquier alternent entre beige #E8D5B5 et bois #9C7654. Réserve les textures bois discrètes à l’échiquier et aux illustrations.
>
> Associe des titres serif élégants à une police sans serif très lisible pour les textes, formulaires et commandes. Prévois des bordures fines, des angles légèrement arrondis, des ombres discrètes et des espacements généreux. Évite les couleurs néon, les dégradés voyants et l’accumulation de cartes ou de statistiques décoratives.
>
> Conserve sur les trois écrans le même en-tête : symbole de cavalier et nom « TableChat » à gauche, navigation « Jouer », « Amis », « Messages », « Leçons », puis avatar et accès au profil à droite. Souligne en vert la rubrique active. Les tailles, les composants, les icônes et les avatars doivent rester cohérents entre les images.
>
> Tous les textes visibles sont en français correct, courts et lisibles. Utilise des pièces d’échecs conventionnelles facilement reconnaissables. Tout échiquier doit être carré, composé exactement de 8 × 8 cases carrées, avec des coordonnées correctement placées. Vue depuis les blancs : a1 en bas à gauche, h1 claire en bas à droite. Aucun texte technique, filigrane ou élément hors périmètre.

### 7.3 Prompt écran 1 — Accueil connecté

> Applique le prompt commun. La rubrique « Jouer » est active. Affiche le titre « Une partie, entre amis. » et le sous-titre « Installez-vous, la table est prête. »
>
> Organise le contenu en deux colonnes : environ deux tiers pour les actions et un tiers pour les amis. Dans la colonne principale, crée un bandeau chaleureux avec le titre « À vous de jouer », un bouton vert « Jouer contre l’IA », un bouton secondaire « Inviter un ami » et une illustration de pièces en bois sur la droite. Cette illustration ne doit pas gêner les textes.
>
> Sous ce bandeau, affiche « Continuer à apprendre » avec deux cartes de leçon : « Le mat en un coup » et « Protéger son roi ». Chaque carte comporte un petit échiquier, un niveau et l’action « Commencer ». Ajoute en dessous une ligne « Votre dernière partie » indiquant « Vous · Thomas », « Victoire » et « Revoir la partie ».
>
> Dans la colonne droite, affiche « Vos amis », avec Camille « En ligne », Thomas « En partie » et Léa « En ligne ». Propose « Inviter » pour les amis disponibles. Ajoute un aperçu de message de Camille : « On fait une partie ? », accompagné d’un indicateur de message non lu.
>
> L’ensemble doit donner immédiatement accès au jeu, aux amis et à l’apprentissage, avec une hiérarchie claire et sans surcharge.

### 7.4 Prompt écran 2 — Partie entre amis et chat

> Applique le prompt commun. La rubrique « Jouer » est active. Affiche le fil d’Ariane « Jouer / Partie entre amis », le titre « Votre partie avec Camille » et un indicateur discret « En direct ».
>
> Réserve environ 60 % de la largeur disponible à la zone de jeu et le reste au panneau latéral. L’échiquier doit rester parfaitement carré, entièrement visible et être l’élément principal. Affiche Camille, camp « Noirs », au-dessus ; puis « Vous », camp « Blancs », et « À vous de jouer » en dessous. Mets en évidence le dernier coup avec une teinte douce. Représente une position de partie cohérente, sans pièces inventées ni cases supplémentaires.
>
> Sous la zone de jeu, prévois les actions discrètes « Proposer la nulle » et « Abandonner ». N’affiche pas de pendule pour cette partie sans limite de temps.
>
> Le panneau latéral comporte les onglets « Discussion » et « Coups ». « Discussion » est actif. Affiche l’avatar de Camille, son statut « En ligne », une commande de son et quelques messages espacés : « Salut ! Prête pour la revanche ? », « Toujours 😄 », « Bien joué ! ». Place en bas le champ « Écrire un message… », un bouton emoji et un bouton d’envoi vert.
>
> Le chat reste confortable à lire sans réduire excessivement le plateau. L’onglet « Coups » permet d’accéder à l’historique sans ajouter un troisième panneau.

### 7.5 Prompt écran 3 — Leçon interactive

> Applique le prompt commun. La rubrique « Leçons » est active. Affiche « Leçons / Premiers mats », le titre « Le mat en un coup », le niveau « Débutant » et la progression « Leçon 2 sur 5 ».
>
> Place à gauche un grand échiquier carré, orienté depuis les blancs. Position exacte : roi blanc en f6, dame blanche en g6, roi noir en h8 ; toutes les autres cases sont vides. Les blancs jouent. Ne montre pas la solution sur l’échiquier initial. Pour l’intégration fonctionnelle, la solution attendue est Dg7#.
>
> À droite, présente un panneau pédagogique aéré : « À VOUS DE JOUER », puis « Trouvez le coup décisif. » et « Le roi noir est à l’étroit. Faites échec et mat en un seul coup. » Ajoute « Objectif : mat en 1 », le bouton « Afficher un indice » avec une icône d’ampoule et l’action « Recommencer ».
>
> Plus bas, affiche un encadré discret « Le conseil du club » contenant « Un roi ne peut pas se déplacer sur une case attaquée. » Termine par un indicateur de progression en cinq étapes et le lien « Toutes les leçons ». Sous le plateau, affiche « Les blancs jouent ».
>
> Préserve une atmosphère calme qui facilite la concentration. N’ajoute ni classement, ni graphique, ni statistique sans rapport avec l’exercice.

### 7.6 Passage des maquettes à l’application

- Fournir les trois images séparément, avec des noms explicites, et conserver les prompts utilisés.
- Utiliser les maquettes comme référence pour les couleurs, la typographie, la hiérarchie et la disposition. Implémenter chaque écran avec de véritables composants interactifs ; ne pas utiliser une capture complète comme interface.
- Les noms, messages et résultats illustrés sont des données de démonstration. Dans l’application, les remplacer par les données de l’utilisateur connecté ou par des états vides appropriés.
- Adapter la composition aux petits écrans sans déformer le plateau. Sur mobile, afficher le chat et les coups dans des onglets sous l’échiquier ; placer les instructions de leçon sous le plateau et empiler les sections de l’accueil.
- Compléter les états absents des images : chargement, erreur, déconnexion, invitation en attente, promotion, fin de partie, leçon réussie et tentative incorrecte.
- Vérifier dans le navigateur la lisibilité, l’absence de débordement, le format carré de l’échiquier et la cohérence visuelle des trois écrans.

## 8. Sécurité, robustesse et exploitation

- Vérifier les autorisations sur chaque API et chaque connexion WebSocket.
- Restreindre l’accès aux parties et conversations à leurs participants.
- Protéger l’authentification, le chat et les requêtes Stockfish contre les abus.
- Borner le temps d’analyse, les ressources et la concurrence des moteurs.
- Ne pas exécuter une analyse Stockfish bloquante dans la boucle WebSocket.
- Utiliser des transactions pour les opérations sensibles.
- Journaliser les erreurs utiles sans exposer de secrets.
- Conserver les secrets dans les variables d’environnement.
- Garder PostgreSQL comme source persistante de référence ; Redis ne doit pas être l’unique stockage des parties ou messages.

Les commentaires utiles du code doivent être en français. Les noms techniques doivent rester cohérents et explicites.

## 9. Méthode de réalisation

Commencer par présenter brièvement :

- L’architecture retenue.
- Les hypothèses et décisions structurantes.
- Les principales routes HTTP et les événements WebSocket.
- L’ordre des étapes de réalisation.

Produire les trois maquettes décrites en section 7, puis développer par parcours fonctionnels :

1. Environnement, modèles et authentification.
2. Partie locale puis partie contre IA.
3. Relations d’amitié et invitations.
4. Multijoueur et reconnexion.
5. Messagerie persistante.
6. Leçons, finition visuelle et vérifications.

Pour les choix courants, adopter une solution raisonnable et la documenter. Poser une question uniquement si une ambiguïté bloque réellement le développement.

Ne pas s’arrêter à un plan, à une maquette ou à des réponses simulées. Si une contrainte empêche une fonctionnalité, indiquer précisément ce qui fonctionne, ce qui manque et pourquoi.

## 10. Livrables

Fournir :

1. Le backend complet : modèles, migrations, API, WebSockets, tâches et intégration Stockfish.
2. Le frontend complet : pages, composants et parcours fonctionnels.
3. Une configuration Docker Compose pour le lancement local.
4. Des fichiers `.env.example` sans secrets.
5. Une commande de seed reproductible avec deux comptes de démonstration et au moins cinq leçons.
6. Des tests ciblés sur les règles et parcours critiques.
7. Un README comprenant :
   - Installation et démarrage.
   - Services et variables d’environnement.
   - Installation du binaire Stockfish et des fichiers WebAssembly.
   - Exécution des migrations, du seed et des tests.
   - Procédure de test sur deux sessions ou appareils.
   - Choix d’architecture et limites connues.

8. Les trois maquettes haute fidélité et leurs prompts de génération.

## 11. Critères d’acceptation

La V1 est terminée lorsque :

- Deux utilisateurs peuvent s’inscrire, devenir amis et lancer une partie.
- Un coup légal est enregistré et visible sur les deux appareils.
- Un coup illégal, hors tour ou envoyé par un tiers est refusé côté serveur.
- Une actualisation ou reconnexion restaure la partie sans divergence.
- Les règles spéciales et les fins de partie sont correctement traitées.
- Une partie contre l’IA fonctionne à chaque niveau proposé.
- Les messages arrivent en temps réel et restent accessibles après la partie.
- Les leçons proposent validation, indice et sauvegarde de progression.
- Les trois écrans respectent la direction visuelle des maquettes et utilisent de vrais composants interactifs.
- L’interface reste utilisable sur mobile.
- Le projet peut être lancé depuis un environnement vierge en suivant le README.

À la livraison, récapituler les fonctionnalités réalisées, les vérifications effectivement exécutées et les éventuelles limites restantes.
