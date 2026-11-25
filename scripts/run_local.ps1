param(
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $RepoRoot "web\out"

if (-not (Test-Path (Join-Path $OutDir "index.html"))) {
    Write-Host "Static build not found in web\out. Building Next.js dashboard..." -ForegroundColor Yellow
    Push-Location (Join-Path $RepoRoot "web")
    cmd /c npm run build
    Pop-Location
}

Write-Host "Starting Lanna Power Dashboard local server at http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Judge Test Account: judge@lannapower.co.th / Lanna2025!" -ForegroundColor Cyan
Start-Process "http://127.0.0.1:$Port"
python -m http.server $Port --bind 127.0.0.1 --directory $OutDir
