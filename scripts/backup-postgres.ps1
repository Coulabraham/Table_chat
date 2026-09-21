param(
    [string]$Destination = $env:BACKUP_DESTINATION,
    [int]$RetentionDays = 0
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Destination)) { $Destination = ".\backups" }
if ($RetentionDays -le 0) {
    $configuredRetention = 0
    if ([int]::TryParse($env:BACKUP_RETENTION_DAYS, [ref]$configuredRetention) -and $configuredRetention -gt 0) {
        $RetentionDays = $configuredRetention
    } else {
        $RetentionDays = 14
    }
}

New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$resolvedDestination = (Resolve-Path -LiteralPath $Destination).Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$fileName = "tablechat-$timestamp.dump"
$backupPath = Join-Path $resolvedDestination $fileName
$containerPath = "/tmp/$fileName"

try {
    docker compose exec -T db sh -lc "umask 077; pg_dump --username=`"`$POSTGRES_USER`" --dbname=`"`$POSTGRES_DB`" --format=custom --no-owner --no-acl --file='$containerPath'"
    if ($LASTEXITCODE -ne 0) { throw "pg_dump a échoué avec le code $LASTEXITCODE." }

    docker compose cp "db:$containerPath" $backupPath
    if ($LASTEXITCODE -ne 0) { throw "La copie de la sauvegarde a échoué avec le code $LASTEXITCODE." }
    if (-not (Test-Path -LiteralPath $backupPath) -or (Get-Item -LiteralPath $backupPath).Length -eq 0) {
        throw "Le fichier de sauvegarde est absent ou vide."
    }

    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $acl = New-Object System.Security.AccessControl.FileSecurity
        $acl.SetOwner([System.Security.Principal.NTAccount]$identity)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, "FullControl", "Allow")
        $acl.AddAccessRule($rule)
        Set-Acl -LiteralPath $backupPath -AclObject $acl
    }

    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    Get-ChildItem -LiteralPath $resolvedDestination -Filter "tablechat-*.dump" -File |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }

    Write-Output "Sauvegarde créée : $backupPath"
    Write-Output "Rétention locale appliquée : $RetentionDays jours"
} catch {
    if (Test-Path -LiteralPath $backupPath) { Remove-Item -LiteralPath $backupPath -Force }
    Write-Error "Sauvegarde interrompue : $($_.Exception.Message)"
    exit 1
} finally {
    docker compose exec -T db rm -f -- $containerPath 2>$null | Out-Null
}
