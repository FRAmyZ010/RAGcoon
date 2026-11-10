# RAGcoon one-click stop for the Docker Compose stack
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Stopping RAGcoon Docker stack" -ForegroundColor Cyan
cmd /c "docker compose -p ragcoon down"
if ($LASTEXITCODE -ne 0) {
    Write-Host "docker compose down failed" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Stopped. Volumes were kept (postgres/ollama data preserved)."
Write-Host "To wipe volumes too: docker compose -p ragcoon down -v"
