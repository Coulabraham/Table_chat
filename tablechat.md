# Cahier des charges — Table Chat
**Version 1.0 — Document de référence initial**

**1. Présentation du projet**

Table Chat est une application de messagerie accessible sur téléphone, tablette et ordinateur sous forme de Progressive Web App — PWA.

Elle permet aux utilisateurs de discuter en privé ou en groupe, de partager des fichiers et, à terme, de passer des appels audio et vidéo.

L’application comprend une boutique interne de jeux de société multijoueurs. **Seule l’équipe éditrice de Table Chat peut publier des jeux dans cette boutique.** Les utilisateurs téléchargent les jeux de leur choix et invitent leurs contacts à jouer.

La messagerie constitue la fonction principale du produit. L’espace de jeux la complète sans être nécessaire pour utiliser les discussions.

**2. Objectifs**

- Proposer une messagerie simple, fluide et respectueuse de la vie privée.
- Offrir une interface adaptée aux usages mobiles et aux ordinateurs.
- Permettre de jouer avec ses contacts depuis la même application.
- Télécharger les jeux à la demande pour limiter le poids initial.
- Assurer la reprise des messages et des parties après une interruption réseau.
- Permettre l’ajout de nouveaux jeux sans reconstruire toute l’application.

**3. Public et supports**

L’application s’adresse aux personnes souhaitant communiquer et jouer avec leurs proches ou leurs communautés.

Supports visés :

- Téléphones Android.
- iPhone.
- Tablettes.
- Ordinateurs Windows, macOS et Linux disposant d’un navigateur compatible.

L’application doit fonctionner dans le navigateur et proposer son installation lorsque celle-ci est disponible. Les parcours essentiels seront testés sur Safari iPhone, Chrome Android et les principaux navigateurs de bureau.

Les notifications, le stockage local et les activités en arrière-plan dépendent des capacités du navigateur et du système. L’interface doit expliquer les éventuelles limitations au moment concerné.

**4. Identité visuelle et navigation**

Le design s’inspire de la sobriété et des couleurs de Telegram, avec une identité propre à Table Chat.

Principes :

- Bleu comme couleur principale.
- Fonds clairs et mode sombre.
- Bulles de messages arrondies.
- Typographie lisible et contrastes suffisants.
- Icônes accompagnées de libellés pour la navigation principale.
- Zones tactiles confortables.
- Animations discrètes, compatibles avec les préférences de réduction des mouvements.

La navigation mobile comporte quatre onglets en bas :

| Onglet | Fonction |
|---|---|
| Discussions | Conversations privées et groupes |
| Appels | Appels audio et vidéo, historique |
| Jeux | Bibliothèque, boutique et parties |
| Réglages | Profil et préférences |

L’onglet Appels devient accessible lorsque la fonctionnalité est opérationnelle.

Sur ordinateur, l’interface utilise plusieurs colonnes lorsque cela améliore la lecture. Sur téléphone, le clavier virtuel et les zones réservées par le système ne doivent pas masquer la saisie ou les commandes.

**5. Comptes et identité**

La première version utilise une inscription par adresse email et mot de passe.

Fonctions attendues :

- Inscription et vérification de l’adresse email.
- Connexion et déconnexion.
- Récupération du compte.
- Identifiant public unique pour être trouvé par ses contacts.
- Nom affiché, avatar et description facultative.
- Modification du profil.
- Consultation et révocation des sessions connectées.
- Suppression du compte.

L’adresse email n’est pas affichée publiquement.

La recherche de contacts repose initialement sur l’identifiant public et les liens d’invitation. L’import automatique du carnet d’adresses ne fait pas partie de la première version.

Les administrateurs disposent d’une authentification multifacteur.

**6. Messagerie**

Les utilisateurs peuvent :

- Créer une conversation privée.
- Envoyer et recevoir des messages texte en temps réel.
- Consulter un historique paginé.
- Répondre à un message.
- Consulter les messages non lus.
- Recevoir des notifications selon leurs préférences.
- Conserver des brouillons.
- Réessayer un envoi ayant échoué.
- Bloquer et signaler un utilisateur.

Les états d’un message distinguent :

- En attente sur l’appareil.
- Enregistré par le serveur.
- Reçu par un appareil destinataire.
- Lu, lorsque les accusés de lecture sont activés.
- Échec nécessitant une nouvelle tentative.

Une confirmation du serveur ne doit pas être présentée comme une lecture par le destinataire.

Les fonctions d’édition, de suppression pour les participants, de réactions, de transfert et de messages épinglés sont prévues après le parcours de messagerie initial. Leurs délais et effets devront être définis avant leur développement.

Une suppression ne peut pas garantir l’effacement d’une copie déjà exportée ou enregistrée par un destinataire.

**7. Groupes**

Les groupes comprennent les rôles suivants :

| Rôle | Droits |
|---|---|
| Propriétaire | Gestion du groupe, des administrateurs et transfert de propriété |
| Administrateur | Gestion des membres et paramètres autorisés |
| Membre | Participation aux conversations et parties autorisées |

Fonctions :

- Création d’un groupe avec nom et image.
- Invitations, acceptation et départ.
- Ajout et retrait de membres.
- Gestion des rôles.
- Désactivation des notifications.
- Contrôle des personnes autorisées à inviter.

Règle initiale : un nouveau membre accède aux messages envoyés après son arrivée. Un membre retiré ne peut plus recevoir de nouveaux messages du groupe.

Le transfert de propriété doit être traité avant le départ ou la suppression du compte du propriétaire.

**8. Pièces jointes**

Formats prévus :

- Images.
- Documents autorisés.
- Messages vocaux.
- Vidéos courtes dans une évolution ultérieure.

Chaque catégorie dispose de limites configurables de taille, de fréquence et de stockage. Les valeurs seront arrêtées avant la bêta selon les coûts d’hébergement et les essais sur mobile.

Le téléchargement affiche sa progression et ses erreurs.

Les pièces jointes privées nécessitent une autorisation d’accès. Leur suppression et leur durée de conservation suivent une politique documentée.

Lorsque les fichiers sont chiffrés de bout en bout, le serveur ne peut pas les analyser en clair. Les protections doivent alors inclure des restrictions de format, des précautions d’ouverture et des mécanismes de signalement.

**9. Boutique officielle de jeux**

L’espace Jeux contient :

| Section | Contenu |
|---|---|
| Mes jeux | Jeux présents sur cet appareil |
| Boutique | Catalogue publié par l’équipe |
| Mes parties | Invitations, parties en cours et résultats |

Chaque fiche de jeu comprend :

- Nom et description.
- Illustrations ou captures.
- Règles et variante proposée.
- Nombre minimal et maximal de joueurs.
- Taille du téléchargement.
- Version et changements récents.
- Modes disponibles : en ligne, local ou solo selon le jeu.
- Actions de téléchargement, mise à jour, lancement et suppression.

La version initiale prévoit un catalogue gratuit. Les paiements et abonnements ne sont pas inclus dans ce périmètre.

Aucun utilisateur ne peut téléverser ou publier son propre jeu.

**10. Téléchargement et mises à jour**

Le téléchargement correspond au stockage local des fichiers web nécessaires au jeu.

Le gestionnaire doit :

- Vérifier la compatibilité et l’espace disponible.
- Afficher une progression.
- Permettre l’annulation.
- Gérer les interruptions et nouvelles tentatives.
- Vérifier les fichiers avant activation.
- Marquer un jeu comme installé uniquement lorsque la version est complète.
- Détecter les fichiers absents ou effacés.
- Permettre la suppression d’un jeu.
- Préserver une version utilisée par une partie en cours.

La désinstallation retire les fichiers locaux du jeu. Elle ne supprime pas automatiquement les résultats ou les parties conservés sur le serveur.

Les installations sont propres à chaque appareil. Un jeu téléchargé sur ordinateur doit être téléchargé séparément sur téléphone.

Le stockage du navigateur peut être effacé ou libéré. L’application doit pouvoir proposer un nouveau téléchargement sans perdre les données de partie persistantes.

**11. Jeux multijoueurs**

Jeux envisagés :

- Dames.
- Ludo.
- Échecs.
- Jeu de lettres de type Scrabble, avec nom, dictionnaire et ressources à valider.

Les variantes des règles sont fixées avant le développement de chaque jeu.

Le premier jeu proposé sera les dames. Il servira à valider l’ensemble du parcours multijoueur.

Parcours principal :

1. Choisir un jeu installé.
2. Créer une partie.
3. Sélectionner ses paramètres.
4. Inviter des contacts ou les membres d’une conversation.
5. Attendre que les participants soient prêts.
6. Jouer.
7. Afficher et conserver le résultat.

Une invitation reçue pour un jeu absent propose son téléchargement, puis le retour vers la partie.

Le nombre de participants dépend du jeu. Une invitation expirée, une partie complète ou un utilisateur bloqué ne doit pas permettre une entrée non autorisée.

**12. Règles et fiabilité des parties**

Le serveur vérifie chaque action et conserve l’état officiel.

Il contrôle :

- L’identité et la participation du joueur.
- L’ordre des tours.
- La légalité de l’action.
- La version de la partie.
- Les délais.
- Les conditions de fin et les scores.

Les dés et autres tirages aléatoires compétitifs sont déterminés côté serveur.

Les informations secrètes ne sont envoyées qu’aux joueurs autorisés à les connaître.

Chaque action possède un identifiant unique. Une action répétée ou fondée sur un ancien état ne doit pas être appliquée deux fois.

Une déconnexion ne provoque pas automatiquement une défaite. La politique de reprise, de délai et d’abandon est définie pour chaque mode et présentée avant le début de la partie.

Les mises à jour ne modifient pas les règles d’une partie déjà commencée.

**13. Appels audio et vidéo**

Les appels font partie du produit cible et seront développés après la messagerie et le premier jeu.

Fonctions prévues :

- Appels individuels audio et vidéo.
- Accepter, refuser et terminer.
- Couper le micro ou la caméra.
- Historique des appels.
- Gestion des permissions.
- Affichage des interruptions et problèmes de connexion.

Les appels de groupe et le partage d’écran sont des évolutions.

Les appels entrants lorsque l’application est fermée ou suspendue doivent faire l’objet d’essais spécifiques. Aucune équivalence avec le comportement d’une application native ne sera annoncée sans validation.

**14. Confidentialité et sécurité**

Le chiffrement de bout en bout est retenu comme objectif pour les conversations privées et de groupe. Son implémentation doit être validée par un prototype avant la stabilisation du modèle de messagerie.

Exigences :

- Protocole éprouvé et bibliothèque maintenue.
- Clés privées conservées sur les appareils.
- Gestion des appareils multiples.
- Vérification des identités et changements de clés.
- Stratégie explicite de sauvegarde et récupération.
- Chiffrement des pièces jointes concernées.
- Aucune promesse d’E2EE avant validation du parcours complet.

Réinitialiser un mot de passe ne doit pas donner au serveur la capacité de déchiffrer l’historique.

La protection des appels est traitée séparément. Le serveur connaît les états de jeu nécessaires à l’arbitrage.

Autres exigences :

- HTTPS et WebSockets sécurisés.
- Sessions par cookies sécurisés et protection CSRF.
- Hachage robuste des mots de passe.
- Validation des données côté serveur.
- Autorisation vérifiée pour chaque ressource et action.
- Limites de débit, de taille et de connexions.
- Protection contre l’injection de scripts.
- Révocation des sessions et accès retirés.
- Secrets absents du code et des journaux.
- Sauvegardes chiffrées et restaurations testées.

**15. Isolation et publication des jeux**

Les jeux s’exécutent dans un environnement séparé de la messagerie.

Ils ne doivent pas accéder :

- Aux messages privés.
- Aux clés de chiffrement.
- Aux cookies de session du chat.
- Au carnet de contacts complet.
- Aux fonctions administratives.

Une interface limitée permet de recevoir l’état autorisé, proposer une action et demander une invitation confirmée dans Table Chat.

Toute communication entre le jeu et l’application est contrôlée.

La publication exige :

- Un compte autorisé.
- Une construction et des tests automatisés.
- Une vérification des dépendances.
- Des fichiers versionnés et immuables.
- Un manifeste authentifié et des contrôles d’intégrité.
- Un journal de publication.
- Une procédure de retrait et de retour à une version sûre.

L’équipe vérifie les droits d’utilisation des noms, images, sons, bibliothèques et dictionnaires.

**16. Administration et modération**

L’administration permet de :

- Gérer les comptes et suspensions.
- Examiner les signalements.
- Publier et retirer des versions de jeux.
- Consulter les incidents techniques.
- Configurer les limites d’usage.
- Auditer les actions sensibles.

Les administrateurs ne disposent pas d’un accès général au contenu des conversations chiffrées. Un signalement peut transmettre les éléments que l’utilisateur choisit explicitement de partager.

Les comptes de support, de modération et de publication disposent de droits distincts.

**17. Architecture et stack**

| Couche | Choix |
|---|---|
| Frontend | React, TypeScript, Vite |
| Interface | Tailwind CSS, composants accessibles |
| Navigation | React Router |
| Données serveur | TanStack Query |
| Formulaires | React Hook Form, Zod |
| PWA | Workbox, vite-plugin-pwa |
| Stockage local | IndexedDB, Dexie |
| Backend | Django, Django REST Framework |
| Temps réel | Django Channels, channels_redis |
| Base persistante | PostgreSQL |
| Présence et diffusion | Redis |
| Tâches différées | Celery |
| Fichiers | Stockage compatible S3 |
| Appels | WebRTC, LiveKit et connectivité TURN |
| Administration | Django Admin |
| Déploiement | Docker, serveur ASGI, reverse proxy HTTPS |
| Tests | pytest, Vitest, Playwright |

Le projet comprend une application web, un backend modulaire, un environnement isolé d’exécution des jeux et un dossier par jeu.

PostgreSQL conserve les messages enregistrés, les parties et les événements durables. Redis n’est pas l’unique stockage des données à préserver.

Les interfaces et événements sont documentés et versionnés.

**18. Exigences de qualité et exploitation**

- Les fichiers des jeux ne sont pas chargés à l’ouverture initiale du chat.
- Les historiques longs sont paginés.
- Les conversations reprennent après reconnexion.
- Les erreurs donnent une explication et une action possible.
- Les brouillons sont préservés pendant les mises à jour normales.
- Le stockage local est séparé entre comptes et nettoyé selon la politique de déconnexion.
- La restauration des sauvegardes est testée.
- Les environnements de test et de production sont séparés.
- Les erreurs et tâches bloquées déclenchent des alertes.
- Les journaux excluent les contenus privés et les secrets.

Les objectifs chiffrés de disponibilité, latence, charge simultanée et restauration seront fixés avant la bêta, à partir du budget et de mesures sur un environnement représentatif.

**19. Données personnelles**

Une politique doit préciser :

- Les données collectées et leurs finalités.
- Les durées de conservation.
- Les modalités d’export et de suppression.
- Le traitement des données dans les sauvegardes.
- Les prestataires utilisés.
- Les permissions demandées.
- Les modalités de signalement et de contact.

Les permissions sont demandées au moment utile. L’accès aux contacts, à la caméra ou au micro ne doit pas être une condition pour utiliser les fonctions qui n’en ont pas besoin.

Les règles applicables aux pays ciblés et au public mineur éventuel devront être validées avant le lancement.

**20. Critères de recette**

| Scénario | Résultat attendu |
|---|---|
| Message entre téléphone et ordinateur | Réception et historique cohérents |
| Coupure pendant un envoi | Reprise sans doublon |
| Accès à une conversation étrangère | Refus côté serveur |
| Session révoquée | Accès interrompu et reconnexion requise |
| Retrait d’un membre | Aucun nouveau message du groupe accessible |
| Téléchargement incomplet | Jeu non marqué comme installé |
| Stockage local effacé | Absence détectée et téléchargement proposé |
| Mise à jour pendant une partie | Partie conservée sur sa version compatible |
| Action de jeu illégale | Refus sans altération de l’état |
| Actions simultanées | État final cohérent |
| Reconnexion à une partie | Récupération de l’état officiel |
| Tentative d’accès du jeu au chat | Accès bloqué |
| Restauration de sauvegarde | Données récupérées et procédure vérifiée |
| Parcours avec clavier et lecteur d’écran | Fonctions essentielles utilisables |

La recette E2EE comprend les appareils multiples, les changements de clés et la récupération prévue. La recette des jeux comprend les informations cachées, les abandons et les conflits d’actions.

**21. Phases de réalisation**

| Phase | Livrables |
|---|---|
| 1. Conception | Maquettes, parcours, modèle de données et règles de confidentialité |
| 2. Prototypes structurants | E2EE et téléchargement d’un jeu isolé sur mobile |
| 3. Messagerie initiale | Comptes, contacts, conversations privées et synchronisation |
| 4. Bêta de messagerie | Groupes, fichiers, notifications, modération et sauvegardes |
| 5. Boutique | Catalogue, bibliothèque, téléchargement et mises à jour |
| 6. Premier jeu | Dames multijoueurs avec invitations et reconnexion |
| 7. Extensions | Ludo, échecs, jeu de lettres, appels audio et vidéo |
| 8. Évolutions | Tournois, classements, spectateurs et personnalisation |

La première version publique réunissant la promesse complète de Table Chat doit inclure une messagerie fiable, la boutique officielle et au moins un jeu multijoueur abouti.

**22. Livrables attendus**

- Maquettes mobile et ordinateur.
- Identité visuelle et composants partagés.
- Code source et historique des modifications.
- Documentation d’installation.
- Documentation des API et événements.
- Modèle de données et migrations.
- Tests automatisés et rapport de recette.
- Procédures de déploiement et de retour arrière.
- Procédures de sauvegarde et restauration.
- Guide de publication des jeux.
- Guide d’administration et de modération.
- Politique de confidentialité et conditions d’utilisation à valider.

**23. Points à fixer avant engagement du planning**

- Budget de réalisation et d’exploitation.
- Équipe disponible et responsabilités.
- Pays et public visés.
- Nom de domaine et identité graphique définitive.
- Variante des dames et règles du ludo.
- Limites de fichiers, groupes et stockage.
- Solution E2EE validée par le prototype.
- Politique de récupération des clés.
- Objectifs de charge et de disponibilité.
- Calendrier de la bêta et du lancement.

Ces décisions complètent le présent document. Aucun délai ni coût global n’est engagé par cette version du cahier des charges.