# RAGcoon local dev: Docker stack (postgres/pgadmin/ollama/backend) + Vite frontend
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-DockerReady {
    # Avoid PowerShell treating docker stderr as a terminating error.
    cmd /c "docker info >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

function Ensure-DockerDesktop {
    Write-Step "Checking Docker"
    if (Test-DockerReady) {
        Write-Host "Docker is ready."
        return
    }

    $candidates = @(
        "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )

    # Resolve from docker.exe location (winget/user installs often live under Local\Programs\DockerDesktop)
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerCmd -and $dockerCmd.Source) {
        $binDir = Split-Path -Parent $dockerCmd.Source
        $candidates += @(
            (Join-Path (Split-Path -Parent $binDir) "Docker Desktop.exe"),
            (Join-Path (Split-Path -Parent (Split-Path -Parent $binDir)) "Docker Desktop.exe")
        )
    }

    $dockerDesktop = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

    if (-not $dockerDesktop) {
        throw "Docker is not running and Docker Desktop was not found. Install/start Docker, then retry."
    }

    Write-Host "Docker daemon is not up yet. Starting Docker Desktop..."
    Start-Process $dockerDesktop | Out-Null

    $deadline = (Get-Date).AddMinutes(5)
    do {
        Start-Sleep -Seconds 5
        if (Test-DockerReady) {
            Write-Host "Docker is ready."
            return
        }
        Write-Host "Waiting for Docker Desktop to finish starting..."
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for Docker Desktop. Open Docker Desktop manually, wait until it says Running, then retry: npm run dev"
}

function Test-HttpReady([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSec = 180) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        if (Test-HttpReady $Url) {
            return
        }
        Start-Sleep -Seconds 3
        Write-Host "Waiting for $Url ..."
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for $Url"
}

function Start-ComposeStack {
    $backendUrl = "http://localhost:8000/docs"
    if (Test-HttpReady $backendUrl) {
        Write-Step "Backend already running on http://localhost:8000 — skipping docker compose up"
        return
    }

    Write-Step "Starting Docker Compose stack (postgres, pgadmin, ollama, backend)"
    # Pin project name so root/backend compose files don't fight over container names.
    cmd /c "docker compose -p ragcoon up -d"
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Host "Compose up hit a name conflict or error. Reclaiming RAGcoon containers and retrying..."
    foreach ($name in @("ragcoon-postgres", "ragcoon-pgadmin", "ragcoon-ollama", "ragcoon-backend")) {
        cmd /c "docker rm -f $name >nul 2>&1"
    }
    cmd /c "docker compose -p ragcoon up -d"
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed"
    }
}

Ensure-DockerDesktop
Start-ComposeStack

Write-Step "Waiting for backend on http://localhost:8000"
Wait-Http "http://localhost:8000/docs" 300
Write-Host "Backend is up."

$frontendDir = Join-Path $Root "frontend"
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Step "Installing frontend dependencies"
    Push-Location $frontendDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    } finally {
        Pop-Location
    }
}

Write-Step "Starting frontend (Vite) on http://localhost:5173"
Write-Host "Press Ctrl+C to stop the frontend. Docker services keep running (docker compose down to stop them)."
Push-Location $frontendDir
try {
    npm run dev
} finally {
    Pop-Location
}
