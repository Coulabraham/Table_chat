param(
    [string]$LanAddress = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if (-not $LanAddress) {
    $route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" |
        Where-Object { $_.NextHop -ne "0.0.0.0" } |
        Sort-Object RouteMetric, InterfaceMetric |
        Select-Object -First 1
    if (-not $route) {
        throw "Aucune route reseau active n'a ete trouvee."
    }
    $LanAddress = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "169.254.*" } |
        Select-Object -First 1 -ExpandProperty IPAddress
}

if (-not [System.Net.IPAddress]::TryParse($LanAddress, [ref]([System.Net.IPAddress]$null))) {
    throw "Adresse IPv4 invalide : $LanAddress"
}

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$daphne = Join-Path $projectRoot ".venv\Scripts\daphne.exe"
if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $daphne)) {
    throw "Environnement Python absent. Suivez d'abord l'installation locale du README."
}

$occupied = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in 3000, 8000 }
if ($occupied) {
    throw "Les ports 3000 ou 8000 sont deja occupes. Arretez les anciens serveurs avant de relancer ce script."
}

$env:USE_INMEMORY_CHANNELS = "true"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,$LanAddress"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://${LanAddress}:3000"

$backend = Start-Process -FilePath $daphne `
    -ArgumentList "-b", "0.0.0.0", "-p", "8000", "tablechat.asgi:application" `
    -WorkingDirectory (Join-Path $projectRoot "backend") `
    -WindowStyle Hidden `
    -PassThru

$frontendDirectory = Join-Path $projectRoot "frontend"
if (-not (Test-Path -LiteralPath (Join-Path $frontendDirectory ".next\BUILD_ID"))) {
    Push-Location $frontendDirectory
    try { npm run build } finally { Pop-Location }
}

$frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "start", "--", "-H", "0.0.0.0" `
    -WorkingDirectory $frontendDirectory `
    -WindowStyle Hidden `
    -PassThru

Write-Host "TableChat est disponible sur http://${LanAddress}:3000" -ForegroundColor Green
Write-Host "Backend PID : $($backend.Id) - Frontend PID : $($frontend.Id)"
