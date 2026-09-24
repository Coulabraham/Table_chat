# Lot 3 — groupes, rôles et messages non lus

## Résultat livré

Le lot ajoute les conversations de groupe sans modifier le contrat des conversations privées : création, invitations internes, acceptation/refus/annulation/expiration, rôles propriétaire-administrateur-membre, transfert de propriété, départ, retrait immédiat, mise en sourdine et compteurs non lus synchronisables.

La migration `chat.0002_group_conversations` conserve les conversations et messages existants. Elle crée deux adhésions actives pour chaque conversation privée déjà présente. Aucun script de développement n’écrit dans la base de production.

## Garanties d’accès et concurrence

- Une invitation en attente ne donne aucun accès HTTP ou WebSocket.
- Chaque acceptation crée une période d’adhésion avec `joined_after_message_id` pris sous transaction. Les aperçus, compteurs et historiques appliquent la même borne.
- Un membre retiré perd immédiatement ses API et sa socket est fermée en `4403`. Une réinvitation crée une nouvelle période et ne révèle pas les messages de l’absence.
- Les changements de rôle, transferts, retraits, départs et acceptations verrouillent les lignes utiles avec `select_for_update` et revalident les droits dans la transaction.
- Il ne peut exister qu’une adhésion active par personne et conversation, un propriétaire actif par groupe et une invitation en attente par destinataire et groupe.
- Le curseur de lecture ne recule jamais, doit pointer dans la bonne conversation et ignore les messages de l’utilisateur dans le compteur.
- Un blocage interdit les nouvelles invitations dans les deux sens sans révéler son auteur. Il ne retire personne d’un groupe commun et n’y masque aucun message.

## Permissions

| Action | Propriétaire | Administrateur | Membre |
|---|---:|---:|---:|
| Modifier nom/description | oui | oui | non |
| Inviter/annuler une invitation | oui | oui | non |
| Retirer un membre simple | oui | oui | non |
| Promouvoir/rétrograder | oui | non | non |
| Transférer la propriété | oui | non | non |
| Quitter | après transfert, ou archivage si seul | oui | oui |

## Recette en 14 points

1. Créer un groupe : le créateur est propriétaire et seul membre.
2. Inviter par identifiant public ; avant acceptation toutes les URL du groupe sont refusées au destinataire.
3. Tester refus, annulation, expiration et doublon d’invitation.
4. Envoyer un message avant l’arrivée puis après : le nouveau membre ne voit que le second.
5. Connecter trois sessions et confirmer un seul événement temps réel par message et par session.
6. Promouvoir un administrateur et vérifier ses droits bornés.
7. Transférer la propriété depuis une autre session et constater le basculement atomique.
8. Retirer un membre groupe ouvert : fermeture `4403`, puis API 404.
9. Réinviter ce membre après de nouveaux messages : seul le nouvel historique est visible.
10. Bloquer deux membres d’un groupe commun : messages visibles, nouvelle invitation impossible.
11. Lire sur un appareil et constater la remise à zéro sur l’autre après événement ou actualisation.
12. Vérifier qu’un message propre ne compte pas et qu’un ancien curseur ne fait pas reculer la lecture.
13. Activer la sourdine, recharger et confirmer sa persistance.
14. Contrôler liste, groupe et administration à 320 px et sur ordinateur.

Automatisation : `backend/chat/tests/test_groups.py`, `backend/chat/tests/test_websocket.py`, tests unitaires frontend et build TypeScript. Captures : `docs/screenshots/lot3-*.png`.

## Rapport de validation

Implémenté : modèle et migration, API complète, autorisations transactionnelles, bornes d’historique, diffusion et révocation WebSocket, non-lus, sourdine, interface responsive, blocage compatible avec les groupes et documentation.

Testé localement : 43 tests backend, dont le parcours propriétaire/administrateur/membre/extérieur et trois WebSockets ; 7 tests frontend ; compilation Vite/TypeScript ; ESLint ; absence de migration manquante ; contrôle Django de déploiement ; configuration Compose ; cinq captures sans débordement à 320 px et 1440 px.

Restant à vérifier avant production : appliquer la migration sur une copie isolée de Supabase, exécuter la recette multi-appareils avec le Redis Upstash et la Preview Vercel, puis observer une charge concurrente PostgreSQL réelle. Ces contrôles n’ont pas été lancés contre la production afin de respecter l’interdiction de modifier ses données.

## Déploiement Vercel/Supabase, sans action automatique

1. Créer un backup Supabase et relever le commit actuellement déployé.
2. Ajouter si souhaité `GROUP_INVITATION_TTL_SECONDS=604800` et `GROUP_MAX_MEMBERS=50` dans Vercel. Les valeurs sont déjà les défauts applicatifs.
3. Dans un environnement de préproduction relié à une base isolée, exécuter `python manage.py migrate --plan`, puis `python manage.py migrate`.
4. Déployer le commit en Preview et exécuter la recette groupe, les tests HTTP et WebSocket et les contrôles à 320 px.
5. Déployer en production seulement après validation explicite. La migration ajoute des colonnes/tables et peuple les adhésions privées ; elle ne supprime aucun message.
6. Surveiller les erreurs API, fermetures WebSocket, latence PostgreSQL et Redis. En cas d’incident applicatif, redéployer le commit précédent ; ne pas inverser la migration après création de groupes sans export préalable de ces nouvelles données.

## Chiffrement de bout en bout futur

Cette version n’est pas chiffrée de bout en bout : le serveur peut lire les messages. Ajouter ensuite de l’E2EE changerait profondément les groupes : distribution et rotation des clés à chaque arrivée/retrait, multi-appareils, restauration, recherche, aperçus, modération et rattrapage. La borne d’historique serveur resterait utile, mais ne suffirait pas à garantir la confidentialité cryptographique des anciens messages ; il faudrait aussi empêcher la remise des anciennes clés aux nouveaux membres.
