# Sauvegarde et restauration PostgreSQL

Les sauvegardes contiennent les comptes, profils, sessions et messages lisibles par le serveur. Elles sont donc sensibles. Les scripts ne transmettent aucun fichier à un service externe et n'inscrivent aucun mot de passe dans la ligne de commande ou le nom du fichier.

## Créer une sauvegarde

Depuis la racine du projet :

```powershell
.\scripts\backup-postgres.ps1
```

La destination par défaut est `./backups` et la rétention 14 jours. Elles peuvent être changées dans `.env` ou par paramètres :

```powershell
.\scripts\backup-postgres.ps1 -Destination "D:\Sauvegardes\TableChat" -RetentionDays 30
```

Le script utilise `pg_dump` au format personnalisé, vérifie que le fichier copié est non vide, applique une ACL limitée à l'utilisateur Windows courant et supprime uniquement les anciens fichiers `tablechat-*.dump` de la destination choisie. Toute erreur produit un code de sortie non nul et supprime le fichier incomplet.

## Vérifier une restauration sans toucher aux données actives

```powershell
.\scripts\verify-restore.ps1 -BackupPath ".\backups\tablechat-AAAAMMJJ-HHMMSS.dump"
```

Le script crée une base temporaire nommée `tablechat_restore_check_*` dans le conteneur PostgreSQL, y restaure le fichier, compte les utilisateurs, conversations et messages, puis supprime cette base dans un bloc `finally`. Il ne restaure jamais dans la base `tablechat` utilisée par l'application.

## Copie locale et vraie sauvegarde

Une copie conservée sur le même PC protège contre une suppression logique ou une mauvaise migration, mais pas contre la panne, le vol, un rançongiciel ou la perte du disque. Une vraie stratégie conserve au moins une copie chiffrée sur un autre support ou un autre lieu, avec accès limité et tests de restauration périodiques. Aucun envoi externe ne doit être ajouté sans autorisation explicite.

Les fichiers `.dump` ne sont pas chiffrés par `pg_dump`. Utiliser un volume chiffré (par exemple BitLocker) pour la destination et ne jamais les placer dans Git.
