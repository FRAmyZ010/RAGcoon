# RAGcoon one-click start: full Docker stack (frontend Vite + backend + postgres + ollama + pgadmin)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Warn([string]$Message) {
    Write-Host $Message -ForegroundColor Yellow
}

function Test-DockerReady {
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

    throw "Timed out waiting for Docker Desktop. Open Docker Desktop, wait until Running, then retry."
}

function Ensure-EnvFiles {
    Write-Step "Checking environment files"
    $example = Join-Path $Root ".env.example"
    if (-not (Test-Path $example)) {
        throw ".env.example not found at repo root."
    }

    $rootEnv = Join-Path $Root ".env"
    $backendEnv = Join-Path $Root "backend\.env"

    if (-not (Test-Path $rootEnv)) {
        Copy-Item $example $rootEnv
        Write-Host "Created .env from .env.example"
    } else {
        Write-Host ".env already exists — leaving it unchanged"
    }

    if (-not (Test-Path $backendEnv)) {
        Copy-Item $example $backendEnv
        Write-Host "Created backend/.env from .env.example"
    } else {
        Write-Host "backend/.env already exists — leaving it unchanged"
    }
}

function Get-EnvValue([string]$Path, [string]$Key) {
    if (-not (Test-Path $Path)) { return $null }
    foreach ($line in Get-Content $Path) {
        if ($line -match "^\s*#" -or $line -notmatch "=") { continue }
        $parts = $line.Split("=", 2)
        if ($parts.Count -eq 2 -and $parts[0].Trim() -eq $Key) {
            return $parts[1].Trim()
        }
    }
    return $null
}

function Warn-Placeholders {
    Write-Step "Checking for placeholder secrets"
    $backendEnv = Join-Path $Root "backend\.env"
    $warnings = @()

    $qdrantUrl = Get-EnvValue $backendEnv "QDRANT_URL"
    $qdrantKey = Get-EnvValue $backendEnv "QDRANT_API_KEY"
    if (-not $qdrantUrl -or $qdrantUrl -match "your-cluster|your-qdrant|example") {
        $warnings += "- QDRANT_URL still looks like a placeholder. Set your Qdrant Cloud URL in backend/.env"
    }
    if (-not $qdrantKey -or $qdrantKey -match "your-qdrant-api-key|change-me|example") {
        $warnings += "- QDRANT_API_KEY still looks like a placeholder. Set your Qdrant Cloud API key in backend/.env"
    }

    $jwt = Get-EnvValue $backendEnv "JWT_SECRET"
    if (-not $jwt -or $jwt -match "change-in-production|change-me") {
        $warnings += "- JWT_SECRET is still a default/example value (ok for local demo; change for shared use)"
    }

    if ($warnings.Count -gt 0) {
        Write-Warn "Warning: some secrets are still placeholders:"
        foreach ($w in $warnings) { Write-Warn $w }
        Write-Warn "Stack will still start, but chat/RAG features that need Qdrant may fail until you update backend/.env"
        Write-Host ""
    } else {
        Write-Host "No obvious placeholder secrets detected."
    }
}

function Test-HttpReady([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSec = 600) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        if (Test-HttpReady $Url) { return }
        Start-Sleep -Seconds 5
        Write-Host "Waiting for $Url ..."
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Url"
}

function Start-ComposeStack {
    Write-Step "Starting Docker Compose stack (build + up)"
    Write-Host "First run can take a long time (images + Ollama model pull)."
    cmd /c "docker compose -p ragcoon up -d --build"
    if ($LASTEXITCODE -eq 0) { return }

    Write-Host "Compose up hit a conflict or error. Reclaiming RAGcoon containers and retrying..."
    foreach ($name in @(
            "ragcoon-postgres",
            "ragcoon-pgadmin",
            "ragcoon-ollama",
            "ragcoon-backend",
            "ragcoon-frontend"
        )) {
        cmd /c "docker rm -f $name >nul 2>&1"
    }
    cmd /c "docker compose -p ragcoon up -d --build"
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up --build failed"
    }
}

Ensure-DockerDesktop
Ensure-EnvFiles
Warn-Placeholders
Start-ComposeStack

Write-Step "Waiting for backend"
Wait-Http "http://localhost:8000/docs" 600
Write-Host "Backend is up."

Write-Step "Waiting for frontend"
Wait-Http "http://localhost:5173" 300
Write-Host "Frontend is up."

Write-Step "RAGcoon is ready"
Write-Host "Frontend:  http://localhost:5173"
Write-Host "Backend:   http://localhost:8000/docs"
Write-Host "pgAdmin:   http://localhost:8080"
Write-Host "Stop with: .\stop.bat   or   ./stop.sh   or   docker compose -p ragcoon down"

try {
    Start-Process "http://localhost:5173"
} catch {
    Write-Warn "Could not open browser automatically. Open http://localhost:5173 manually."
}
