#!/usr/bin/env bash
# RAGcoon one-click start: full Docker stack (frontend Vite + backend + postgres + ollama + pgadmin)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

step() { printf '\n==> %s\n' "$1"; }
warn() { printf '%s\n' "$1" >&2; }

need_docker() {
  step "Checking Docker"
  if ! docker info >/dev/null 2>&1; then
    warn "Docker is not running. Start Docker Desktop / the Docker daemon, then retry."
    exit 1
  fi
  echo "Docker is ready."
}

ensure_env_files() {
  step "Checking environment files"
  local example="$ROOT/.env.example"
  if [[ ! -f "$example" ]]; then
    warn ".env.example not found at repo root."
    exit 1
  fi

  if [[ ! -f "$ROOT/.env" ]]; then
    cp "$example" "$ROOT/.env"
    echo "Created .env from .env.example"
  else
    echo ".env already exists — leaving it unchanged"
  fi

  if [[ ! -f "$ROOT/backend/.env" ]]; then
    cp "$example" "$ROOT/backend/.env"
    echo "Created backend/.env from .env.example"
  else
    echo "backend/.env already exists — leaving it unchanged"
  fi
}

env_value() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || { echo ""; return; }
  # shellcheck disable=SC2162
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" == *"="* ]] || continue
    local k="${line%%=*}"
    local v="${line#*=}"
    k="$(echo "$k" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    v="$(echo "$v" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [[ "$k" == "$key" ]]; then
      echo "$v"
      return
    fi
  done < "$file"
  echo ""
}

warn_placeholders() {
  step "Checking for placeholder secrets"
  local backend_env="$ROOT/backend/.env"
  local warnings=()

  local qdrant_url qdrant_key jwt
  qdrant_url="$(env_value "$backend_env" "QDRANT_URL")"
  qdrant_key="$(env_value "$backend_env" "QDRANT_API_KEY")"
  jwt="$(env_value "$backend_env" "JWT_SECRET")"

  if [[ -z "$qdrant_url" || "$qdrant_url" =~ your-cluster|your-qdrant|example ]]; then
    warnings+=("- QDRANT_URL still looks like a placeholder. Set your Qdrant Cloud URL in backend/.env")
  fi
  if [[ -z "$qdrant_key" || "$qdrant_key" =~ your-qdrant-api-key|change-me|example ]]; then
    warnings+=("- QDRANT_API_KEY still looks like a placeholder. Set your Qdrant Cloud API key in backend/.env")
  fi
  if [[ -z "$jwt" || "$jwt" =~ change-in-production|change-me ]]; then
    warnings+=("- JWT_SECRET is still a default/example value (ok for local demo; change for shared use)")
  fi

  if ((${#warnings[@]} > 0)); then
    warn "Warning: some secrets are still placeholders:"
    local w
    for w in "${warnings[@]}"; do warn "$w"; done
    warn "Stack will still start, but chat/RAG features that need Qdrant may fail until you update backend/.env"
    echo
  else
    echo "No obvious placeholder secrets detected."
  fi
}

http_ready() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -o /dev/null --connect-timeout 5 "$url" >/dev/null 2>&1
    return $?
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -q --spider --timeout=5 "$url" >/dev/null 2>&1
    return $?
  fi
  return 1
}

wait_http() {
  local url="$1"
  local timeout_sec="${2:-600}"
  local start_ts end_ts
  start_ts="$(date +%s)"
  end_ts=$((start_ts + timeout_sec))
  while true; do
    if http_ready "$url"; then
      return 0
    fi
    if (( $(date +%s) >= end_ts )); then
      warn "Timed out waiting for $url"
      exit 1
    fi
    echo "Waiting for $url ..."
    sleep 5
  done
}

start_compose() {
  step "Starting Docker Compose stack (build + up)"
  echo "First run can take a long time (images + Ollama model pull)."
  if docker compose -p ragcoon up -d --build; then
    return 0
  fi

  echo "Compose up hit a conflict or error. Reclaiming RAGcoon containers and retrying..."
  for name in ragcoon-postgres ragcoon-pgadmin ragcoon-ollama ragcoon-backend ragcoon-frontend; do
    docker rm -f "$name" >/dev/null 2>&1 || true
  done
  docker compose -p ragcoon up -d --build
}

open_browser() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url" || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  else
    warn "Could not open browser automatically. Open $url manually."
  fi
}

need_docker
ensure_env_files
warn_placeholders
start_compose

step "Waiting for backend"
wait_http "http://localhost:8000/docs" 600
echo "Backend is up."

step "Waiting for frontend"
wait_http "http://localhost:5173" 300
echo "Frontend is up."

step "RAGcoon is ready"
echo "Frontend:  http://localhost:5173"
echo "Backend:   http://localhost:8000/docs"
echo "pgAdmin:   http://localhost:8080"
echo "Stop with: ./stop.sh   or   ./stop.bat   or   docker compose -p ragcoon down"

open_browser "http://localhost:5173"
