param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"
$resolvedBackup = (Resolve-Path -LiteralPath $BackupPath).Path
if ([System.IO.Path]::GetExtension($resolvedBackup) -ne ".dump") {
    throw "Le fichier doit utiliser l'extension .dump."
}

$suffix = (Get-Date -Format "yyyyMMddHHmmss") + ([Guid]::NewGuid().ToString("N").Substring(0, 8))
$database = "tablechat_restore_check_$suffix"
$containerPath = "/tmp/tablechat-restore-$suffix.dump"
$databaseCreated = $false
$databaseUser = (docker compose exec -T db printenv POSTGRES_USER).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($databaseUser)) {
    throw "Impossible de lire l'utilisateur PostgreSQL depuis le conteneur."
}

try {
    docker compose cp $resolvedBackup "db:$containerPath"
    if ($LASTEXITCODE -ne 0) { throw "La copie du fichier vers PostgreSQL a échoué." }

    docker compose exec -T db createdb "--username=$databaseUser" $database
    if ($LASTEXITCODE -ne 0) { throw "La création de la base isolée a échoué." }
    $databaseCreated = $true

    docker compose exec -T db pg_restore "--username=$databaseUser" "--dbname=$database" --no-owner --no-acl $containerPath
    if ($LASTEXITCODE -ne 0) { throw "La restauration isolée a échoué." }

    $query = "SELECT (SELECT count(*) FROM accounts_user) AS users, (SELECT count(*) FROM chat_conversation) AS conversations, (SELECT count(*) FROM chat_message) AS messages;"
    $counts = docker compose exec -T db psql "--username=$databaseUser" "--dbname=$database" --tuples-only --no-align "--command=$query"
    if ($LASTEXITCODE -ne 0) { throw "La vérification SQL de la restauration a échoué." }
    Write-Output "Restauration isolée vérifiée : $counts"
} catch {
    Write-Error "Vérification de restauration interrompue : $($_.Exception.Message)"
    exit 1
} finally {
    if ($databaseCreated) {
        docker compose exec -T db dropdb "--username=$databaseUser" --if-exists $database 2>$null | Out-Null
    }
    docker compose exec -T db rm -f -- $containerPath 2>$null | Out-Null
}
